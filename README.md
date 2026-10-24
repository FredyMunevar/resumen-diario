# El Tinto Tech

Resumen diario en audio de tecnología, diseño e inteligencia artificial, en español de Colombia. Un episodio nuevo cada madrugada.

**Feed del podcast:** https://fredymunevar.github.io/resumen-diario/feed.xml

Para escucharlo en Apple Podcasts: Biblioteca → ··· → *Seguir un programa por URL* → pega el enlace del feed.
También funciona en Pocket Casts, Overcast o cualquier app que acepte feeds RSS.

## Cómo se publica un episodio

1. Se sube el guion a `guiones/AAAA-MM-DD.txt` (un párrafo por línea) con su `guiones/AAAA-MM-DD.json` (`titulo`, `descripcion`).
2. La GitHub Action **Publicar episodios** genera el audio, lo guarda en `episodios/`, actualiza `episodios.json` y `feed.xml`, y despliega el sitio.

La voz se genera con Azure Speech (voz colombiana, `config.json`) si existe el secret `AZURE_SPEECH_KEY` (la región está en `config.json`); si no, con Kokoro como respaldo.
