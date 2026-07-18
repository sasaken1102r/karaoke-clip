"""境界解析: 指定範囲の 総RMS(dB) と 低音域(60-250Hz)RMS(dB) を1秒ごとに出す。
usage: python boundary_probe.py <wav16k> <start_sec> <end_sec>

用途:
  - 伴奏終止の特定: 総dBが急落し低音(伴奏)が消える点=曲の終わり。ここで切る(歌後の会話は切る/伴奏アウトロは残す)。
  - 2曲マージの分割: 範囲内の無音ギャップ(総dB<-44が3秒以上)=曲の切れ目。各パートを別々に切出す。
  - 会話 vs 音楽: 会話は低音(伴奏)がほぼ無い。伴奏があるうちは曲。
"""
import sys, wave
import numpy as np

def main(wav, a, b):
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); raw = w.readframes(w.getnframes())
    data = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    N = sr; freqs = np.fft.rfftfreq(N, 1.0/sr); low = (freqs >= 60) & (freqs < 250)
    rows = []
    for s in range(a, b):
        seg = data[s*sr:(s+1)*sr]
        if len(seg) < sr: break
        tot = 20*np.log10(np.sqrt(np.mean(seg**2))/32768 + 1e-9)
        X = np.fft.rfft(seg); lo = np.fft.irfft(X*low, n=N)
        lowdb = 20*np.log10(np.sqrt(np.mean(lo**2))/32768 + 1e-9)
        rows.append((s, tot, lowdb))
    # 無音ギャップ(2曲の切れ目候補)
    gaps = []; i = 0
    while i < len(rows):
        if rows[i][1] < -44:
            j = i
            while j < len(rows) and rows[j][1] < -44: j += 1
            if j-i >= 3: gaps.append((rows[i][0], rows[j-1][0]))
            i = j
        else: i += 1
    print("=== 無音ギャップ(曲の切れ目候補) ===")
    for gs, ge in gaps:
        print(f"  {gs//60:02d}:{gs%60:02d} 〜 {ge//60:02d}:{ge%60:02d} (元{gs}-{ge}s)")
    print("=== 1秒毎 (sec tot low music?) ===")
    for s, tot, lowdb in rows:
        print(f"  {s}s ({s//60:02d}:{s%60:02d}): tot={tot:6.1f} low={lowdb:6.1f} {'M(伴奏)' if lowdb > -55 else '.'}")

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
