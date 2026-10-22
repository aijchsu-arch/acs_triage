"""STT 評估流程 A 段：合成（或真實）音檔 → Whisper 轉寫 → 原始結果 JSON（D-48）。

在 ASR 環境執行（不 import acs_triage；專案 .venv 沒有 mlx-whisper／opencc）：

    uv run --offline --no-project --python 3.14 \\
        --with mlx-whisper --with opencc-python-reimplemented \\
        python -P sim/stt_synth_asr.py --utterances reports/stt_utterances_2026-10-22.json \\
        --audio-dir <scratch>/stt_audio --out <scratch>/stt_asr_results.json [--limit 5]

- 所有 uv 指令一律 `--offline`；本程式另設 HF_HUB_OFFLINE=1，模型只讀本機快取，不會下載。
- 音檔一律放 --audio-dir（scratch），不得進 repo。
- 輸入：utterance 清單 JSON（list，每筆至少 id、text；由 `sim/stt_eval.py build` 產生）。
- 合成：macOS `say` 台灣中文語音，依 id 的數字尾碼輪流（Meijia／Grandma／Grandpa），並記錄在結果的 voice。
  音檔兩種：clean = 16 kHz mono wav；phone = 300–3400 Hz 帶通 → 8 kHz mono G.711 μ-law → 升回 16 kHz wav。
- 條件：clean／phone／phone_prompt（phone + initial_prompt）。可續跑：已完成的 (id, condition) 跳過。
- 換模型：--model（HF repo 名稱或本機路徑，須為 mlx_whisper 可載入的格式；Breeze-ASR-25 轉成 MLX 後即可）。
- 換成真實錄音：--recordings-dir DIR（內含 <id>.wav／.m4a 等，ffmpeg 讀得動即可）；
  條件改為 rec／rec_prompt（錄音轉 16 kHz mono，不再模擬線路），voice 記為 "recording"。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")        # 禁止連網下載模型

VOICES = ["Meijia", "Grandma (中文（台灣）)", "Grandpa (中文（台灣）)"]
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
PROMPT = "以下是台灣心臟科衛教專線的電話對話，可能提到冠心症、支架、舌下含片、保栓通、胸悶、胸口壓、喘、冒冷汗、快昏倒。"
# 條件 → (音檔種類, initial_prompt)
CONDITION_SPECS: dict[str, tuple[str, str | None]] = {
    "clean": ("clean", None),
    "phone": ("phone", None),
    "phone_prompt": ("phone", PROMPT),
    "rec": ("rec", None),
    "rec_prompt": ("rec", PROMPT),
}
SYNTH_CONDITIONS = ["clean", "phone", "phone_prompt"]
REC_CONDITIONS = ["rec", "rec_prompt"]
SAVE_EVERY = 25


# ---------------------------------------------------------------- 文字正規化
_CN_DIGITS = "零一二三四五六七八九"


def _arabic_to_cn(m: re.Match) -> str:
    """阿拉伯數字 → 中文數字（Whisper 常把「三年」寫成「3年」）；< 100 照中文讀法，其餘逐位。"""
    d = m.group()
    if len(d) > 2 or d.startswith("0"):
        return "".join(_CN_DIGITS[int(c)] for c in d)
    n = int(d)
    if n < 10:
        return _CN_DIGITS[n]
    tens, ones = divmod(n, 10)
    return ("" if tens == 1 else _CN_DIGITS[tens]) + "十" + (_CN_DIGITS[ones] if ones else "")


def normalize(text: str, t2s) -> str:
    """CER 用正規化：NFKC → 繁轉簡 → 阿拉伯數字轉中文數字、兩→二 → 去標點／符號／空白。"""
    s = t2s.convert(unicodedata.normalize("NFKC", text))
    s = re.sub(r"\d+", _arabic_to_cn, s).replace("两", "二").replace("兩", "二")
    return re.sub(r"[\W_]+", "", s).lower()


def to_tw(text: str, s2tw) -> str:
    """NFKC → 簡轉繁（台灣用字）。opencc 詞組表有「是只→是隻」，會把「是只有／是只要」誤轉成「是隻有／是隻要」
    （改用 s2twp 也一樣）；轉換前在「是」「只」之間切開，避免跨過這條詞組。"""
    return "".join(s2tw.convert(p) for p in re.split(r"(?<=是)(?=只)", unicodedata.normalize("NFKC", text)))


# ---------------------------------------------------------------- 音檔
def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def voice_for(utt_id: str, position: int) -> str:
    m = re.search(r"(\d+)$", utt_id)
    n = int(m.group(1)) - 1 if m else position
    return VOICES[n % len(VOICES)]


def check_voices() -> None:
    out = run(["say", "-v", "?"]).stdout.decode("utf-8", "replace")
    missing = [v for v in VOICES if v not in out]
    if missing:
        sys.exit(f"找不到 say 語音：{missing}（用 `say -v '?'` 確認名稱）")


def ffmpeg_wav(src: Path, dst: Path, *extra: str, rate: int = 16000, codec: str = "pcm_s16le") -> None:
    tmp = dst.with_name(dst.stem + ".tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), *extra, "-ac", "1", "-ar", str(rate), "-c:a", codec, str(tmp)])
    tmp.replace(dst)


def ensure_synth_audio(audio_dir: Path, utt_id: str, text: str, voice: str) -> dict[str, Path]:
    paths = {"clean": audio_dir / "clean" / f"{utt_id}.wav", "phone": audio_dir / "phone" / f"{utt_id}.wav"}
    if all(p.exists() for p in paths.values()):
        return paths
    ulaw = audio_dir / "phone_8k_ulaw" / f"{utt_id}.wav"
    for p in (*paths.values(), ulaw):
        p.parent.mkdir(parents=True, exist_ok=True)
    aiff = audio_dir / f"{utt_id}.tmp.aiff"
    try:
        run(["say", "-v", voice, "-o", str(aiff), "-f", "-"], input=text.encode("utf-8"))
        ffmpeg_wav(aiff, paths["clean"])
        # 電話線路：300–3400 Hz 帶通 → 8 kHz G.711 μ-law → 解回 16 kHz PCM
        ffmpeg_wav(aiff, ulaw, "-af", "highpass=f=300:poles=2,lowpass=f=3400:poles=2", rate=8000, codec="pcm_mulaw")
        ffmpeg_wav(ulaw, paths["phone"])
    finally:
        aiff.unlink(missing_ok=True)
    return paths


def ensure_recording(audio_dir: Path, rec_dir: Path, utt_id: str) -> dict[str, Path]:
    dst = audio_dir / "rec" / f"{utt_id}.wav"
    if not dst.exists():
        cands = sorted(p for p in rec_dir.glob(f"{utt_id}.*") if p.is_file())
        if not cands:
            raise FileNotFoundError(f"{rec_dir} 找不到 {utt_id}.*")
        dst.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_wav(cands[0], dst)
    return {"rec": dst}


# ---------------------------------------------------------------- ASR 後端（要換引擎只改這一個函式）
def transcribe(audio: Path, model: str, language: str, prompt: str | None) -> dict:
    import mlx_whisper

    kw = {"initial_prompt": prompt} if prompt else {}
    r = mlx_whisper.transcribe(str(audio), path_or_hf_repo=model, language=language,
                               word_timestamps=True, temperature=0.0, **kw)
    segs = [{k: s[k] for k in ("start", "end", "avg_logprob", "no_speech_prob", "compression_ratio")}
            for s in r["segments"]]
    words = [[w["word"], round(float(w["probability"]), 4)] for s in r["segments"] for w in s.get("words", [])]
    return {"text": r["text"].strip(), "segments": segs, "words": words}


# ---------------------------------------------------------------- 結果檔
def save(path: Path, doc: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--utterances", required=True, help="utterance 清單 JSON（id、text）")
    ap.add_argument("--audio-dir", required=True, help="音檔目錄（scratch，不得在 repo 內）")
    ap.add_argument("--out", required=True, help="原始結果 JSON（可續跑）")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--language", default="zh")
    ap.add_argument("--conditions", help="逗號分隔，預設：合成 clean,phone,phone_prompt；錄音 rec,rec_prompt")
    ap.add_argument("--recordings-dir", help="真實錄音目錄（<id>.*）；給了就不合成")
    ap.add_argument("--limit", type=int, help="只處理清單前 N 句（冒煙測試）")
    args = ap.parse_args()

    audio_dir, out = Path(args.audio_dir).resolve(), Path(args.out).resolve()
    rec_dir = Path(args.recordings_dir).resolve() if args.recordings_dir else None
    repo_root = Path(__file__).resolve().parents[1]
    if repo_root in audio_dir.parents or audio_dir == repo_root:
        sys.exit("--audio-dir 不得在 repo 內")
    conds = (args.conditions.split(",") if args.conditions else (REC_CONDITIONS if rec_dir else SYNTH_CONDITIONS))
    for c in conds:
        if c not in CONDITION_SPECS:
            sys.exit(f"未知條件 {c}；可用：{sorted(CONDITION_SPECS)}")
        if (CONDITION_SPECS[c][0] == "rec") != bool(rec_dir):
            sys.exit(f"條件 {c} 與音檔來源（{'recordings' if rec_dir else 'synth'}）不符")

    utts = json.loads(Path(args.utterances).read_text(encoding="utf-8"))
    if args.limit:
        utts = utts[: args.limit]
    if not rec_dir:
        check_voices()
    from opencc import OpenCC
    t2s, s2twp = OpenCC("t2s"), OpenCC("s2twp")

    audio_dir.mkdir(parents=True, exist_ok=True)
    if out.exists():
        doc = json.loads(out.read_text(encoding="utf-8"))
        if doc["meta"]["model"] != args.model or doc["meta"]["language"] != args.language:
            sys.exit(f"{out} 是用 {doc['meta']['model']}／{doc['meta']['language']} 跑的；換模型請用新的 --out")
    else:
        doc = {"meta": {"model": args.model, "language": args.language, "prompt": PROMPT,
                        "temperature": 0.0, "word_timestamps": True,
                        "source": "recordings" if rec_dir else "say+ffmpeg", "sessions": []},
               "results": []}
    results = doc["results"]
    done = {(r["id"], r["condition"]) for r in results}
    session = {"started": datetime.now().isoformat(timespec="seconds"), "conditions": conds, "n_new": 0, "wall_s": 0.0}
    doc["meta"]["sessions"].append(session)
    t_session = time.time()

    def flush() -> None:
        session["wall_s"] = round(time.time() - t_session, 1)
        save(out, doc)

    def _term(*_: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _term)         # 被 kill 時也先存檔
    try:
        for pos, u in enumerate(utts):
            todo = [c for c in conds if (u["id"], c) not in done]
            if not todo:
                continue
            voice = "recording" if rec_dir else voice_for(u["id"], pos)
            paths = (ensure_recording(audio_dir, rec_dir, u["id"]) if rec_dir
                     else ensure_synth_audio(audio_dir, u["id"], u["text"], voice))
            ref_norm = normalize(u["text"], t2s)
            for c in todo:
                kind, prompt = CONDITION_SPECS[c]
                t0 = time.time()
                r = transcribe(paths[kind], args.model, args.language, prompt)
                elapsed = round(time.time() - t0, 3)
                results.append({
                    "id": u["id"], "voice": voice, "condition": c, "ref": u["text"], "hyp": r["text"],
                    "hyp_tw": to_tw(r["text"], s2twp),
                    "ref_norm": ref_norm, "hyp_norm": normalize(r["text"], t2s),
                    "segments": r["segments"], "words": r["words"], "elapsed_s": elapsed,
                })
                session["n_new"] += 1
                if session["n_new"] % SAVE_EVERY == 0:
                    flush()
                    print(f"[{len(results)}] {u['id']} {c} {elapsed}s", flush=True)
    finally:
        flush()
    total = len(utts) * len(conds)
    print(f"完成：結果 {len(results)} 筆（本次新增 {session['n_new']}／目標 {total}），本次耗時 {session['wall_s']}s -> {out}")


if __name__ == "__main__":
    main()
