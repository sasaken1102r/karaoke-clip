"""区間ごとにGPU文字起こし(faster-whisper large-v3)。
usage: python transcribe.py <source_audio> <segments.json> <out_lyrics_dir>

★重要(実運用の教訓):
  - initial_prompt を付けるとプロンプトをエコーする幻覚が出る → 付けない
  - VADは歌声を弾いて幻覚化 → vad_filter=False
  - no_speech_prob での過剰フィルタは歌詞ごと消す → >0.9 の明白な幻覚のみ除去
  - 声強調前処理(highpass120 + loudnorm)で認識が安定
出力: 各 seg_XX.txt と ALL_SUMMARY.txt(各区間の冒頭)。
"""
import sys, os, json, subprocess, site

def reg_cuda_dll():
    for base in [site.getusersitepackages()] + list(site.getsitepackages()):
        for sub in ("cublas", "cudnn"):
            d = os.path.join(base, "nvidia", sub, "bin")
            if os.path.isdir(d):
                os.add_dll_directory(d)

def extract_vocal(src, start, dur, wav):
    subprocess.run(["ffmpeg","-y","-hide_banner","-ss",str(start),"-t",str(dur),"-i",src,
                    "-af","highpass=f=120,loudnorm=I=-14:TP=-1.5","-ac","1","-ar","16000",
                    "-c:a","pcm_s16le",wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

if __name__ == "__main__":
    src = sys.argv[1]; seg_json = sys.argv[2]; out_dir = sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, "_segwav"); os.makedirs(tmp, exist_ok=True)
    reg_cuda_dll()
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segs = json.load(open(seg_json, encoding="utf-8"))
    summary = []
    for s in segs:
        wav = os.path.join(tmp, f'seg_{s["idx"]:02d}.wav')
        extract_vocal(src, s["start"], s["dur"], wav)
        it, info = model.transcribe(wav, language="ja", vad_filter=False,
            condition_on_previous_text=False, temperature=[0,0.2,0.4,0.6,0.8], beam_size=5)
        lines = []; prev = None
        for seg in it:
            t = seg.text.strip()
            if seg.no_speech_prob is not None and seg.no_speech_prob > 0.9: continue
            if t == prev: continue
            lines.append(t); prev = t
        text = "\n".join(lines)
        open(os.path.join(out_dir, f'seg_{s["idx"]:02d}.txt'), "w", encoding="utf-8").write(text)
        summary.append(f'--- seg_{s["idx"]:02d} ({s["start"]//60:02d}:{s["start"]%60:02d}, {s["dur"]}s) ---\n' + " ".join(lines)[:240])
        print(f'seg_{s["idx"]:02d} done ({len(lines)} lines)')
    open(os.path.join(out_dir, "ALL_SUMMARY.txt"), "w", encoding="utf-8").write("\n\n".join(summary))
    print("ALL_DONE")
