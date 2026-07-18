"""区間を整音チェーン(M1)・無フェードで切出し、曲名+日付+歌唱開始時刻で命名。
usage: python process.py <source_audio> <segments.json> <names.json> <out_dir> <rec_start_seconds> <YYYY-MM-DD> [--gain 3.8] [--no-deharsh]

names.json: {"1":"曲名", "2":null, ...}  (idxを文字列キー。null=会話等でスキップ)
歌唱開始時刻 = rec_start_seconds + 区間開始オフセット。ファイル名 {曲名}_{日付}_{HH-MM}.m4a
※作成日時の設定は set_dates.ps1 で（このスクリプトは切出し・命名のみ）。

刺さり対策(deharsh, 既定ON): presenceを3.2kディップに置換＋2.5-4.5kHzを大声時だけ動的圧縮
（大声/ベルティングの「い」等の母音の刺さり対策。recipe.md参照）。--no-deharsh で従来の明るいM1に。
"""
import sys, os, json, subprocess

BAD = {'\\':'＼','/':'／',':':'：','*':'＊','?':'？','"':'”','<':'＜','>':'＞','|':'｜'}
def sanitize(name):
    return "".join(BAD.get(c, c) for c in name)

ALIML = "alimiter=level_in=1:level_out=1:limit=0.85:attack=5:release=60"

def af_bright(gain):  # 従来M1（presenceブースト・明るい）
    return (f"highpass=f=40,afftdn=nr=6:nf=-30,treble=g=6:f=3200,treble=g=4:f=9000,"
            f"volume={gain}dB,{ALIML}")

def fc_deharsh(gain):  # 刺さり対策（3.2kディップ＋2.5-4.5kマルチバンド動的圧縮）
    pre = "highpass=f=40,afftdn=nr=6:nf=-30,equalizer=f=3200:t=q:w=1.6:g=-5,treble=g=4:f=9000"
    mb = ("acrossover=split=2500 4500[lo][mid][hi];"
          "[mid]acompressor=threshold=-28dB:ratio=6:attack=3:release=90[midc];"
          "[lo][midc][hi]amix=inputs=3:normalize=0")
    return f"[0:a]{pre}[pre];[pre]{mb},volume={gain}dB,{ALIML}[out]"

if __name__ == "__main__":
    src = sys.argv[1]; seg_json = sys.argv[2]; names_json = sys.argv[3]
    out_dir = sys.argv[4]; rec = int(sys.argv[5]); date = sys.argv[6]
    gain = 3.8
    if "--gain" in sys.argv: gain = float(sys.argv[sys.argv.index("--gain")+1])
    deharsh = "--no-deharsh" not in sys.argv
    os.makedirs(out_dir, exist_ok=True)
    segs = json.load(open(seg_json, encoding="utf-8"))
    names = json.load(open(names_json, encoding="utf-8"))
    done = 0
    for s in segs:
        name = names.get(str(s["idx"]))
        if not name: continue
        st = rec + s["start"]; hh = st // 3600; mm = (st % 3600) // 60
        fn = f"{sanitize(name)}_{date}_{hh:02d}-{mm:02d}.m4a"
        out = os.path.join(out_dir, fn)
        base = ["ffmpeg","-y","-hide_banner","-ss",str(s["start"]),"-t",str(s["dur"]),"-i",src]
        if deharsh:
            cmd = base + ["-filter_complex", fc_deharsh(gain), "-map", "[out]"]
        else:
            cmd = base + ["-af", af_bright(gain)]
        cmd += ["-ac","2","-ar","48000","-c:a","aac","-b:a","256k","-metadata",f"title={name}",out]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{fn} ok={os.path.exists(out)}")
        done += 1
    print(f"processed {done} clips ({'deharsh' if deharsh else 'bright'}) -> {out_dir}")
    print("次: set_dates.ps1 で作成日時を歌唱時刻に設定")
