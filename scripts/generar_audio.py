#!/usr/bin/env python3
"""Convierte un guion en el MP3 del episodio.

Uso: python3 scripts/generar_audio.py guion.txt salida.mp3 [carpeta_kokoro]

Motor de voz:
- Azure Speech (voz colombiana) si existen las variables de entorno
  AZURE_SPEECH_KEY y AZURE_SPEECH_REGION.
- Si no, Kokoro local (acento latinoamericano), que necesita la carpeta
  con kokoro-v1.0.onnx y voices-v1.0.bin.

La voz, la velocidad y la música se definen en config.json.
"""
import json, os, re, random, subprocess, sys, tempfile, urllib.request, urllib.error
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())


def parrafos(guion):
    return [l.strip() for l in Path(guion).read_text(encoding="utf-8").splitlines() if l.strip()]


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, args)], check=True)


# ---------- Azure Speech ----------

def azure(guion, tmp):
    a = os.environ["AZURE_SPEECH_KEY"].strip()
    b = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    norm = lambda v: re.sub(r"[^a-z0-9]", "", v.lower().replace("(us)", ""))
    # si los dos secrets quedaron invertidos, se acomodan solos
    if len(norm(a)) <= 25 < len(b):
        a, b = b, a
    key, region = a, norm(b) or "eastus"
    if len(region) > 25:
        raise SystemExit("El secret AZURE_SPEECH_REGION no parece una región (debería ser algo como eastus).")
    print(f"Azure: región {region}")
    voz, rate = CFG["azure"]["voz"], CFG["azure"].get("velocidad", "+0%")
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    # bloques de varios párrafos, por debajo de los límites de una petición
    bloques, actual = [], []
    for p in parrafos(guion):
        if actual and sum(len(x) for x in actual) + len(p) > 2500:
            bloques.append(actual); actual = []
        actual.append(p)
    if actual:
        bloques.append(actual)
    piezas = []
    for i, b in enumerate(bloques):
        cuerpo = '<break time="650ms"/>'.join(escape(p) for p in b)
        ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-CO">'
                f'<voice name="{voz}"><prosody rate="{rate}">{cuerpo}</prosody></voice></speak>')
        req = urllib.request.Request(url, data=ssml.encode("utf-8"), method="POST", headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            "User-Agent": "el-tinto-tech"})
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if intento == 2 or e.code not in (429, 500, 502, 503):
                    raise SystemExit(f"Azure respondió {e.code}: {e.read()[:300]!r}")
        pieza = tmp / f"az{i:03d}.mp3"
        pieza.write_bytes(data)
        piezas.append(pieza)
    pausa = tmp / "pausa.wav"
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.65", pausa)
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p}'\nfile '{pausa}'\n" for p in piezas))
    salida = tmp / "voz_m.wav"
    ffmpeg("-f", "concat", "-safe", "0", "-i", lista, "-af", "highpass=f=60", "-ar", "44100", salida)
    return salida


# ---------- Kokoro (respaldo local) ----------

def kokoro(guion, tmp, mdir):
    import numpy as np, soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{mdir}/kokoro-v1.0.onnx", f"{mdir}/voices-v1.0.bin")
    cfg = CFG["kokoro"]
    random.seed(7); sr = 24000; partes = []
    sil = lambda s: np.zeros(int(sr * s), dtype=np.float32)
    for p in parrafos(guion):
        for f in re.split(r'(?<=[.!?…])\s+', p):
            if not f.strip():
                continue
            s, sr = k.create(f, voice=cfg["voz"], speed=cfg["velocidad"] * random.uniform(0.97, 1.03), lang="es-419")
            idx = np.where(np.abs(s) > 0.01)[0]
            if len(idx):
                s = s[max(0, idx[0] - 240): idx[-1] + 1200]
            partes += [s.astype(np.float32), sil((0.42 if f.rstrip().endswith('?') else 0.30) * random.uniform(0.85, 1.15))]
        partes.append(sil(0.55))
    sf.write(tmp / "voz.wav", np.concatenate(partes), sr)
    salida = tmp / "voz_m.wav"
    ffmpeg("-i", tmp / "voz.wav", "-af",
           "highpass=f=70,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3500:t=q:w=1.2:g=2.5,"
           "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,aecho=0.8:0.5:18:0.06",
           "-ar", "44100", salida)
    return salida


def main():
    guion, out = sys.argv[1], sys.argv[2]
    mdir = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("KOKORO_DIR", str(ROOT / ".kokoro"))
    tmp = Path(tempfile.mkdtemp())
    if os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"):
        motor, voz = "azure", azure(guion, tmp)
    else:
        motor, voz = "kokoro", kokoro(guion, tmp, mdir)
    ffmpeg("-i", voz, "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-codec:a", "libmp3lame", "-q:a", "3", out)
    print("ok", motor, out)
    return motor


if __name__ == "__main__":
    main()
