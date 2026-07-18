"""各区間の末尾「伴奏終止後の会話」を検出し、トリム後の区間(start/dur)を提案。
usage: python trim_trailing.py <wav16k> <segments.json> [--lyrics <dir>] [--low -52] [--tail 3] [--min 4]

伴奏終止 = 末尾から遡り「低音(60-250Hz)>low かつ 総dB>-42(無音でない)」な最後の秒。その+tail秒を新end。
会話(伴奏が無いのに音がある=低音欠落+総dBそこそこ)は伴奏終止の後ろに来るので切れる。
★重要(実運用の教訓): このスクリプト(レベルのみ)は**単体では不正確**。会話に低音(人の声)が乗ると
  伴奏と誤認して会話が残り、逆に器楽アウトロを会話と誤検出して切りすぎる。
  → **タイムスタンプ付き文字起こしと必ず併用**：
    - 末尾が**本物の会話**(トイレどこ/ピザ/2人だよ等)→会話開始で切る。
    - 末尾が**Whisperの定番幻覚**(ご視聴ありがとう/おやすみ/お疲れ様/あ〜〜/ピピ＝伴奏や無音の上に出てるだけ)
      →**切らず**、伴奏(総dB)が無音に落ちる点まで残す。
  --lyrics で各区間の文字起こし末尾(seg_XX.txt)を併記できる。詳細は references/recipe.md の「末尾会話トリム」節。
出力: <segments>_trimmed.json （トリム反映済み。process.pyにそのまま渡せる）
"""
import sys, os, json, wave
import numpy as np

def opt(name, default):
    return sys.argv[sys.argv.index(name)+1] if name in sys.argv else default

if __name__ == "__main__":
    wav = sys.argv[1]; seg_json = sys.argv[2]
    lyr = opt("--lyrics", None)
    LOW = float(opt("--low", -52)); TAIL = int(opt("--tail", 3)); MINT = int(opt("--min", 4))
    with wave.open(wav, "rb") as w:
        sr = w.getframerate(); data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    N = sr; freqs = np.fft.rfftfreq(N, 1.0/sr); lowm = (freqs >= 60) & (freqs < 250)
    segs = json.load(open(seg_json, encoding="utf-8"))
    out = []
    for s in segs:
        st, dur = s["start"], s["dur"]
        rows = []
        for k in range(st, st+dur):
            seg = data[k*sr:(k+1)*sr]
            if len(seg) < sr: break
            tot = 20*np.log10(np.sqrt(np.mean(seg**2))/32768 + 1e-9)
            X = np.fft.rfft(seg); lo = np.fft.irfft(X*lowm, n=N)
            lowdb = 20*np.log10(np.sqrt(np.mean(lo**2))/32768 + 1e-9)
            rows.append((tot, lowdb))
        n = len(rows); lows = [r[1] for r in rows]
        sm = [np.mean(lows[max(0,i-1):i+2]) for i in range(n)]
        last = next((i for i in range(n-1, -1, -1) if sm[i] > LOW and rows[i][0] > -42), n)
        newdur = min(n, last + TAIL); trim = dur - newdur
        new = dict(s); new["dur"] = newdur; new["end"] = st + newdur
        out.append(new)
        tailtxt = ""
        if lyr:
            f = os.path.join(lyr, f'seg_{s["idx"]:02d}.txt')
            if os.path.exists(f):
                tailtxt = " | 歌詞末尾: " + " / ".join(open(f, encoding="utf-8").read().splitlines()[-3:])
        mark = "★TRIM" if trim >= MINT else "ok   "
        print(f'{mark} idx{s["idx"]:02d} dur{dur}->{newdur} (会話{trim}s){tailtxt}')
    tj = os.path.splitext(seg_json)[0] + "_trimmed.json"
    json.dump(out, open(tj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {tj}  （★TRIMは歌詞末尾を見て会話か確認してから採用）")
