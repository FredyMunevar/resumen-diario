#!/usr/bin/env python3
"""Convierte el guion en el MP3 del episodio.

Uso: python3 scripts/generar_audio.py guion.txt salida.mp3 carpeta_kokoro

Lee config.json (voz, velocidad, musica). Sintetiza frase por frase con
Kokoro en acento latinoamericano (es-419), con pausas naturales, aplica
una mezcla tipo estudio y, si "musica" es true, agrega intro y cama musical.
"""
import json, re, random, subprocess, sys, tempfile, numpy as np, soundfile as sf
from pathlib import Path
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "config.json").read_text())
inp, out, mdir = sys.argv[1:4]
k = Kokoro(f"{mdir}/kokoro-v1.0.onnx", f"{mdir}/voices-v1.0.bin")
random.seed(7); sr = 24000; parts = []
sil = lambda s: np.zeros(int(sr * s), dtype=np.float32)

for para in [l.strip() for l in open(inp, encoding="utf-8") if l.strip()]:
    for f in re.split(r'(?<=[.!?…])\s+', para):
        if not f.strip():
            continue
        s, sr = k.create(f, voice=cfg["voz"], speed=cfg["velocidad"] * random.uniform(0.97, 1.03), lang="es-419")
        idx = np.where(np.abs(s) > 0.01)[0]
        if len(idx):
            s = s[max(0, idx[0] - 240): idx[-1] + 1200]
        parts += [s.astype(np.float32), sil((0.42 if f.rstrip().endswith('?') else 0.30) * random.uniform(0.85, 1.15))]
    parts.append(sil(0.55))

tmp = Path(tempfile.mkdtemp())
sf.write(tmp / "voz.wav", np.concatenate(parts), sr)
master = ("highpass=f=70,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=2.5,"
          "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,aecho=0.8:0.5:18:0.06")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp / "voz.wav", "-af", master, "-ar", "44100", tmp / "voz_m.wav"], check=True)

if cfg.get("musica"):
    dur = len(np.concatenate(parts)) / sr
    subprocess.run([sys.executable, ROOT / "scripts" / "cama.py", tmp / "cama.wav", str(dur + 9)], check=True)
    fc = (f"[0:a]lowpass=f=2500,volume=0.55[m];[1:a]adelay=4000|4000,apad=pad_dur=5[v];[v]asplit[v1][v2];"
          f"[m][v1]sidechaincompress=threshold=0.02:ratio=12:attack=30:release=900[md];"
          f"[md]afade=t=in:d=1.5,afade=t=out:st={dur + 5:.1f}:d=4[mf];"
          f"[mf][v2]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5")
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", tmp / "cama.wav", "-i", tmp / "voz_m.wav", "-filter_complex", fc]
else:
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", tmp / "voz_m.wav", "-af", "loudnorm=I=-16:TP=-1.5"]
subprocess.run(cmd + ["-ar", "44100", "-codec:a", "libmp3lame", "-q:a", "3", out], check=True)
print("ok", out)
