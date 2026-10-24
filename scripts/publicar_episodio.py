#!/usr/bin/env python3
"""Publica un episodio y regenera el feed del podcast.

Uso:
  python3 scripts/publicar_episodio.py AAAA-MM-DD ruta/al/audio.mp3 "Título" "Descripción breve"

Guarda el MP3 en episodios/ (mono, 56 kbps), agrega el episodio a
episodios.json, conserva solo los 60 más recientes y regenera feed.xml.
Después hay que hacer commit y push del repositorio.
"""
import json, os, subprocess, sys, email.utils, datetime, html
from pathlib import Path

REPO = "FredyMunevar/resumen-diario"
ROOT = Path(__file__).resolve().parent.parent
SITE = "https://fredymunevar.github.io/resumen-diario"
SHOW = {
    "title": "El Tinto Tech",
    "author": "Fredy Munevar",
    "description": "Resumen diario de tecnología, diseño e inteligencia artificial, en español de Colombia, listo cada madrugada.",
}


def duracion(mp3):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(mp3)], capture_output=True, text=True).stdout
    return int(float(out.strip() or 0))


def subir(fecha, mp3):
    """Copia el audio a episodios/ en mono 56 kbps (voz) y devuelve su URL pública."""
    carpeta = ROOT / "episodios"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"Resumen_{fecha}.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mp3), "-ac", "1",
                    "-ar", "44100", "-codec:a", "libmp3lame", "-b:a", "56k", str(destino)], check=True)
    return destino, f"{SITE}/episodios/{destino.name}"


def limpiar(eps, conservar=60):
    """Deja en el feed y en el repositorio solo los episodios más recientes."""
    eps = sorted(eps, key=lambda x: x["fecha"])
    for viejo in eps[:-conservar]:
        (ROOT / "episodios" / f"Resumen_{viejo['fecha']}.mp3").unlink(missing_ok=True)
    return eps[-conservar:]


def construir_feed(eps):
    items = []
    for e in sorted(eps, key=lambda x: x["fecha"], reverse=True):
        d = datetime.datetime.fromisoformat(e["fecha"] + "T04:30:00-05:00")
        mins, segs = divmod(e["duracion"], 60)
        items.append(f"""    <item>
      <title>{html.escape(e['titulo'])}</title>
      <description>{html.escape(e['descripcion'])}</description>
      <pubDate>{email.utils.format_datetime(d)}</pubDate>
      <guid isPermaLink="false">resumen-{e['fecha']}</guid>
      <enclosure url="{e['url']}" length="{e['bytes']}" type="audio/mpeg"/>
      <itunes:duration>{mins}:{segs:02d}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SHOW['title']}</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>es-co</language>
    <description>{SHOW['description']}</description>
    <itunes:author>{SHOW['author']}</itunes:author>
    <itunes:summary>{SHOW['description']}</itunes:summary>
    <itunes:image href="{SITE}/cover.jpg"/>
    <itunes:category text="Technology"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""


def main():
    fecha, mp3, titulo, descripcion = sys.argv[1:5]
    archivo, url = subir(fecha, mp3)
    db = ROOT / "episodios.json"
    eps = json.loads(db.read_text()) if db.exists() else []
    eps = [e for e in eps if e["fecha"] != fecha]
    eps.append({"fecha": fecha, "titulo": titulo, "descripcion": descripcion, "url": url,
                "bytes": os.path.getsize(archivo), "duracion": duracion(archivo)})
    eps = limpiar(eps)
    db.write_text(json.dumps(sorted(eps, key=lambda x: x["fecha"]), ensure_ascii=False, indent=2) + "\n")
    (ROOT / "feed.xml").write_text(construir_feed(eps))
    print("ok", url)


if __name__ == "__main__":
    main()
