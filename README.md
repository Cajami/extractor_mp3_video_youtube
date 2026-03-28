# Extractor MP3 / Video Desde YouTube

## Origen De Esta Necesidad

Este proyecto nació por una necesidad muy concreta: preparar música para un evento que tengo pronto, pero sin depender de las páginas gratuitas que existen en internet para descargar audio o MP3 desde YouTube.

La razón principal es seguridad. Muchas de esas páginas pueden incluir publicidad agresiva, redirecciones sospechosas o incluso riesgos de descargar archivos no confiables. En lugar de exponer la máquina a ese tipo de herramientas, decidí construir una solución propia, controlada y transparente.

Además, como actualmente estoy entrando al mundo de los agentes, aproveché esta necesidad real para desarrollar este proyecto desde cero con el apoyo de CODEX y GPT-5.4. El resultado es una herramienta personalizada, pensada para mi flujo de trabajo, con control sobre cómo se descargan los videos, cómo se convierten a MP3 y cómo se organiza todo el contenido descargado.

## Que Hace Este Proyecto

Este proyecto permite descargar contenido desde YouTube usando Python.

El flujo actual hace lo siguiente:

- recibe una URL de YouTube en modo interactivo
- descarga el video
- extrae el audio en formato MP3 a partir del video descargado
- guarda los archivos fuera del workspace de scripts
- actualiza una lista en texto
- actualiza un catalogo en JSON
- detecta duplicados exactos y similitudes por nombre

## Libreria Utilizada

La libreria principal utilizada es:

- `yt-dlp`

Repositorio oficial:

- [https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)

Adicionalmente el proyecto usa:

- `ffmpeg` para convertir el video descargado a MP3
- `node` como runtime JavaScript de apoyo para `yt-dlp`
- `yt-dlp[default]` / `yt-dlp-ejs` para mejorar compatibilidad con YouTube

## Estructura De Salida

Las descargas no se guardan en la carpeta donde estan estos scripts.

Actualmente se guardan en un directorio externo:

- `C:\Musica_Boda`

Dentro de esa ruta se usan estas carpetas y archivos:

- `C:\Musica_Boda\video`
- `C:\Musica_Boda\audio`
- `C:\Musica_Boda\lista.txt`
- `C:\Musica_Boda\catalogo.json`

## Que Se Actualiza En Cada Descarga

Cuando una descarga termina correctamente:

- se guarda el video en `video`
- se genera el MP3 en `audio`
- se actualiza `lista.txt`
- se actualiza `catalogo.json`

`lista.txt`:

- guarda una lista enumerada de canciones
- el formato actual usa 3 digitos: `001`, `002`, `003`, etc.

`catalogo.json`:

- guarda informacion estructurada de cada descarga
- incluye `youtube_id`, `title`, `webpage_url`, `video_file`, `audio_file`, `downloaded_at`

## Duplicados Y Similitud

El script intenta evitar descargas repetidas de dos maneras:

- compara por `youtube_id` si el video ya fue descargado
- compara por similitud de titulo si encuentra nombres parecidos

Si detecta una similitud:

- muestra el titulo del video que se intenta descargar
- muestra coincidencias parecidas encontradas en la lista
- le pregunta al usuario si desea continuar o no

## Manejo De Descargas Incompletas

Si una descarga falla:

- se muestra un mensaje de error en rojo
- se eliminan los archivos `.part` relacionados con esa descarga inconclusa

Eso evita dejar archivos temporales que despues confundan el conteo entre `audio` y `video`.

## Archivo Principal

El script principal es:

- [youtube_media_downloader.py](C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py)

Tambien existe este auxiliar:

- [generate_song_list.py](C:\OneDrive\DESARROLLOS\extractor_mp3\generate_song_list.py)

## Cambiar El Directorio De Descarga

La ruta por defecto se define en el codigo fuente dentro de:

- [youtube_media_downloader.py](C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py)

Buscando esta linea:

```python
DEFAULT_OUTPUT_DIR = Path(r"C:\Musica_Boda")
```

Actualmente esa definicion esta en:

- [youtube_media_downloader.py](C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py):14

Si se desea usar otra carpeta, se puede cambiar esa linea por otra ruta.

## Como Ejecutarlo

Ejecutar el script principal:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py
```

El script:

- pide una URL de YouTube
- permite salir escribiendo `s`
- descarga video y audio
- actualiza `lista.txt` y `catalogo.json`

## Continuidad Con Otro Agente

Si este proyecto se va a continuar con otro agente, ya existe un archivo de estado con el contexto tecnico y decisiones tomadas:

- [PROJECT_STATUS.md](C:\OneDrive\DESARROLLOS\extractor_mp3\PROJECT_STATUS.md)

Ese archivo resume:

- lo que ya se hizo
- decisiones tecnicas tomadas
- dependencias instaladas
- flujo del script
- recomendaciones para continuar el desarrollo
