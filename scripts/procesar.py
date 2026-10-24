#!/usr/bin/env python3
"""Genera y publica los episodios cuyos guiones son nuevos o cambiaron.

Cada episodio se define con dos archivos en guiones/:
  AAAA-MM-DD.txt   el guion, un párrafo por línea
  AAAA-MM-DD.json  {"titulo": "...", "descripcion": "..."}

Lo usa la GitHub Action; también se puede correr a mano.
Con --todo regenera todos los guiones de los últimos 60 días.
También convierte cada muestras/*.txt sin audio en muestras/*.mp3 (pruebas de voz).
Los errores quedan en estado.txt para poder revisarlos sin abrir los logs.
"""
import datetime, hashlib, json, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_audio, publicar_episodio

ROOT = Path(__file__).resolve().parent.parent
eps = {e["fecha"]: e for e in json.loads((ROOT / "episodios.json").read_text())} if (ROOT / "episodios.json").exists() else {}
hay_azure = bool(os.environ.get("AZURE_SPEECH_KEY"))
hoy = datetime.date.today()
todo = "--todo" in sys.argv
hechos = []

for guion in sorted((ROOT / "guiones").glob("*.txt")):
    fecha = guion.stem
    meta_f = guion.with_suffix(".json")
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
    sha = hashlib.sha1(guion.read_bytes()).hexdigest()[:12]
    e = eps.get(fecha, {})
    edad = (hoy - datetime.date.fromisoformat(fecha)).days
    if edad > 60:
        continue
    nuevo = e.get("guion_sha") != sha
    mejora = False  # los episodios ya publicados no se vuelven a grabar
    cambia_meta = meta and (meta.get("titulo") != e.get("titulo") or meta.get("descripcion") != e.get("descripcion"))
    if not (nuevo or mejora or todo or cambia_meta):
        continue
    titulo = meta.get("titulo") or e.get("titulo") or fecha
    descripcion = meta.get("descripcion") or e.get("descripcion") or ""
    if nuevo or mejora or todo:
        mp3 = Path(tempfile.mkdtemp()) / f"Resumen_{fecha}.mp3"
        sys.argv = ["generar_audio", str(guion), str(mp3)]
        motor = generar_audio.main()
    else:
        mp3 = Path(tempfile.mkdtemp()) / f"Resumen_{fecha}.mp3"
        mp3.write_bytes((ROOT / "episodios" / f"Resumen_{fecha}.mp3").read_bytes())
        motor = e.get("motor", "kokoro")
    publicar_episodio.publicar(fecha, mp3, titulo, descripcion, {"guion_sha": sha, "motor": motor})
    hechos.append(f"{fecha} ({motor})")

for muestra in sorted((ROOT / "muestras").glob("*.txt")) if (ROOT / "muestras").exists() else []:
    mp3 = muestra.with_suffix(".mp3")
    if not mp3.exists():
        sys.argv = ["generar_audio", str(muestra), str(mp3)]
        hechos.append(f"muestra {muestra.stem} ({generar_audio.main()})")

print("Episodios procesados:", ", ".join(hechos) or "ninguno")
