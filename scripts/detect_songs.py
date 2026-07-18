"""カラオケ長時間録音から曲区間を検出する。
usage: python detect_songs.py <input_audio> <out_segments.json> [--work <16k_wav_path>]

手法(実運用で確定): 16kHz mono化 → 1秒RMS(dB) → 9秒移動平均 → 平滑dB>=SONG_TH を曲候補、
ギャップGAP秒許容・最短MINLEN秒。境界は生dB<SIL の無音まで前後拡張。
※低音比(60-250Hz)での判定はサビで声が主体だと破綻するため使わない(dBのみ)。
出力: [{"idx","start","end","dur"}]  (秒)
"""
import sys, os, json, subprocess, wave
import numpy as np

SONG_TH = -39.0   # 平滑dBがこれ以上=曲候補（録音が静かめならさらに下げる）
SIL = -45.0       # 生dBがこれ未満=無音
GAP = 12          # 曲内ギャップ許容(秒)
MINLEN = 90       # 最短曲長(秒)

def to_16k_mono(src, wav):
    subprocess.run(["ffmpeg","-y","-hide_banner","-i",src,"-ac","1","-ar","16000",
                    "-c:a","pcm_s16le",wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def movavg(x, k=9):
    r = k // 2; out = np.zeros_like(x)
    for i in range(len(x)):
        out[i] = x[max(0, i-r):min(len(x), i+r+1)].mean()
    return out

def detect(wav):
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); raw = w.readframes(w.getnframes())
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    T = len(data) // sr
    db = np.zeros(T)
    for i in range(T):
        seg = data[i*sr:(i+1)*sr]
        db[i] = 20*np.log10(np.sqrt(np.mean(seg**2))/32768 + 1e-9)
    sdb = movavg(db, 9); active = sdb >= SONG_TH
    coarse = []; i = 0
    while i < T:
        if active[i]:
            j = i; last = i; gap = 0
            while j < T:
                if active[j]: last = j; gap = 0
                else:
                    gap += 1
                    if gap > GAP: break
                j += 1
            coarse.append([i, last+1]); i = j
        else: i += 1
    coarse = [s for s in coarse if s[1]-s[0] >= MINLEN]
    def sb(p):
        while p > 0:
            if p-3 >= 0 and all(db[p-1-k] < SIL for k in range(3)): break
            p -= 1
        return p
    def sa(p):
        while p < T:
            if p+3 <= T and all(db[p+k] < SIL for k in range(3)): break
            p += 1
        return p
    segs = []
    for s, e in coarse:
        ns = max(0, sb(s)); ne = min(T, sa(e))
        if not segs or ns > segs[-1][1] + 5: segs.append([ns, ne])
        else: segs[-1][1] = ne
    return [{"idx": k+1, "start": int(s), "end": int(e), "dur": int(e-s)} for k, (s, e) in enumerate(segs)]

if __name__ == "__main__":
    src = sys.argv[1]; out_json = sys.argv[2]
    work = None
    if "--work" in sys.argv:
        work = sys.argv[sys.argv.index("--work")+1]
    else:
        work = os.path.splitext(out_json)[0] + "_16k.wav"
    if not os.path.exists(work):
        to_16k_mono(src, work)
    segs = detect(work)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=1)
    def mmss(s): return f"{s//60:02d}:{s%60:02d}"
    print(f"detected {len(segs)} segments")
    for s in segs:
        print(f'  {s["idx"]:2d} {mmss(s["start"])}-{mmss(s["end"])} ({mmss(s["dur"])})')
