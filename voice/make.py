import subprocess, soundfile as sf, numpy as np
from kokoro import KPipeline
TEXT = ("Heavenly Father, in this quiet moment I come to You with a tired heart. "
        "Calm my worries and fill this room with Your peace. "
        "Hold the people I love in Your gentle hands, and help me rest in Your care tonight. "
        "In Jesus' name, Amen.")
RUNS = [("am_onyx", 0.82), ("am_onyx", 0.76), ("am_onyx", 0.70), ("am_onyx", 0.64)]
pipes = {"a": KPipeline(lang_code="a"), "b": KPipeline(lang_code="b")}
for v, sp in RUNS:
    audio = [a for _, _, a in pipes[v[0]](TEXT, voice=v, speed=sp)]
    name = f"{v}_{int(sp*100)}"
    wav = np.concatenate([np.asarray(a) for a in audio])
    sf.write(f"voice/{name}.wav", wav, 24000)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"voice/{name}.wav", "-af", "apad=pad_dur=0.6",
                    "-c:a", "libmp3lame", "-b:a", "96k", f"voice/samples/{name}.mp3"], check=True)
    print("done", name, round(len(wav) / 24000, 1), "s")
