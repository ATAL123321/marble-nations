import subprocess, soundfile as sf, numpy as np
from kokoro import KPipeline
TEXT = ("Heavenly Father, in this quiet moment I come to You with a tired heart. "
        "Calm my worries and fill this room with Your peace. "
        "Hold the people I love in Your gentle hands, and help me rest in Your care tonight. "
        "In Jesus' name, Amen.")
VOICES = ["am_michael", "am_onyx", "am_fenrir", "am_eric", "bm_george", "bm_lewis"]
pipes = {"a": KPipeline(lang_code="a"), "b": KPipeline(lang_code="b")}
for v in VOICES:
    audio = [a for _, _, a in pipes[v[0]](TEXT, voice=v, speed=0.88)]
    wav = np.concatenate([np.asarray(a) for a in audio])
    sf.write(f"voice/{v}.wav", wav, 24000)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"voice/{v}.wav", "-af", "apad=pad_dur=0.6",
                    "-c:a", "libmp3lame", "-b:a", "96k", f"voice/samples/{v}.mp3"], check=True)
    print("done", v, round(len(wav) / 24000, 1), "s")
