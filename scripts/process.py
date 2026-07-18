"""区間を整音チェーン(M1)・無フェードで切出し、曲名+日付+歌唱開始時刻で命名。
usage: python process.py <source_audio> <segments.json> <names.json> <out_dir> <rec_start_seconds> <YYYY-MM-DD> [--gain 3.8]

names.json: {"1":"曲名", "2":null, ...}  (idxを文字列キー。null=会話等でスキップ)
歌唱開始時刻 = rec_start_seconds + 区間開始オフセット。ファイル名 {曲名}_{日付}_{HH-MM}.m4a
※作成日時の設定は set_dates.ps1 で（このスクリプトは切出し・命名のみ）。
"""
import sys, os, json, subprocess

BAD = {'\\':'＼','/':'／',':':'：','*':'＊','?':'？','"':'”','<':'＜','>':'＞','|':'｜'}
def sanitize(name):
    return "".join(BAD.get(c, c) for c in name)

def m1_af(gain):
    return (f"highpass=f=40,afftdn=nr=6:nf=-30,treble=g=6:f=3200,treble=g=4:f=9000,"
            f"volume={gain}dB,alimiter=level_in=1:level_out=1:limit=0.85:attack=5:release=60")

if __name__ == "__main__":
    src = sys.argv[1]; seg_json = sys.argv[2]; names_json = sys.argv[3]
    out_dir = sys.argv[4]; rec = int(sys.argv[5]); date = sys.argv[6]
    gain = 3.8
    if "--gain" in sys.argv: gain = float(sys.argv[sys.argv.index("--gain")+1])
    os.makedirs(out_dir, exist_ok=True)
    af = m1_af(gain)
    segs = json.load(open(seg_json, encoding="utf-8"))
    names = json.load(open(names_json, encoding="utf-8"))
    done = 0
    for s in segs:
        name = names.get(str(s["idx"]))
        if not name: continue
        st = rec + s["start"]; hh = st // 3600; mm = (st % 3600) // 60
        fn = f"{sanitize(name)}_{date}_{hh:02d}-{mm:02d}.m4a"
        out = os.path.join(out_dir, fn)
        subprocess.run(["ffmpeg","-y","-hide_banner","-ss",str(s["start"]),"-t",str(s["dur"]),
            "-i",src,"-af",af,"-ac","2","-ar","48000","-c:a","aac","-b:a","256k",
            "-metadata",f"title={name}",out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{fn} ok={os.path.exists(out)}")
        done += 1
    print(f"processed {done} clips -> {out_dir}")
    print("次: set_dates.ps1 で作成日時を歌唱時刻に設定")
