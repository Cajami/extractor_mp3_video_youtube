# Estado Del Proyecto

## Resumen

Este proyecto contiene un descargador interactivo en Python para YouTube que:

- descarga el video en `C:\Musica_Boda\video`
- extrae un MP3 localmente en `C:\Musica_Boda\audio`
- actualiza `C:\Musica_Boda\lista.txt`
- mantiene un catalogo en `C:\Musica_Boda\catalogo.json`

El objetivo principal es evitar duplicados, ayudar a detectar similitudes entre canciones, y permitir que cualquier agente pueda retomar el estado sin revisar toda la conversacion previa.

## Archivos Del Workspace

- [youtube_media_downloader.py](C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py): script principal interactivo.
- [generate_song_list.py](C:\OneDrive\DESARROLLOS\extractor_mp3\generate_song_list.py): genera `lista.txt` a partir de una carpeta raiz o de `audio`.
- [requirements.txt](C:\OneDrive\DESARROLLOS\extractor_mp3\requirements.txt): dependencia base `yt-dlp>=2026.3.17`.

## Ruta De Trabajo Externa

El script trabaja por defecto sobre:

- `C:\Musica_Boda`

Estructura esperada:

- `C:\Musica_Boda\video`
- `C:\Musica_Boda\audio`
- `C:\Musica_Boda\lista.txt`
- `C:\Musica_Boda\catalogo.json`

## Dependencias Y Herramientas Instaladas

Se instalaron o validaron estas dependencias en la maquina:

- Python `3.14.3`
- `yt-dlp` `2026.3.17`
- `yt-dlp[default]` para incluir `yt-dlp-ejs`
- `FFmpeg` via `winget` (`Gyan.FFmpeg.Essentials`)
- `node` ya estaba disponible en la maquina y el script lo usa para `yt-dlp`

Notas:

- `ffmpeg` fue instalado via `winget`.
- El script tiene logica para encontrar `ffmpeg` aunque el `PATH` del shell no se haya refrescado.
- Se ajusto `yt-dlp` para usar `node` como runtime JavaScript.
- Antes aparecian warnings de YouTube/EJS; luego se instalo `yt-dlp[default]` para resolverlos.

## Comportamiento Actual Del Script Principal

Al ejecutar:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py
```

el script:

1. valida dependencias
2. usa `C:\Musica_Boda` por defecto
3. si no existe `catalogo.json`, lo reconstruye desde disco
4. pide un link de YouTube o `s` para salir
5. consulta el titulo y el ID del video
6. detecta duplicados exactos por `youtube_id`
7. detecta similitudes por titulo normalizado
8. permite vincular una URL nueva a un registro antiguo sin `youtube_id` ni `webpage_url`
9. descarga el video
10. extrae el MP3 localmente desde el video con `ffmpeg`
11. actualiza `catalogo.json`
12. regenera `lista.txt`

## Decisiones Importantes Tomadas

### 1. Una sola descarga desde YouTube

Antes se consideraba descargar video y audio por separado. Se cambio a:

- descargar el video una sola vez
- convertir localmente a MP3 con `ffmpeg`

Esto evita conexiones duplicadas a YouTube y mantiene nombres consistentes entre video y audio.

### 2. Catalogo Persistente

Se introdujo `catalogo.json` para guardar:

- `youtube_id`
- `title`
- `webpage_url`
- `video_file`
- `audio_file`
- `downloaded_at`

Si un registro fue reconstruido desde disco y no desde una URL real, puede quedar con:

- `youtube_id: null`
- `webpage_url: null`
- `source: "local_scan"`

### 3. Reconstruccion Desde Disco

Se agrego un modo de reconstruccion:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py --output-dir "C:\Musica_Boda" --rebuild-catalog
```

Ese modo:

- reconstruye `catalogo.json` desde `audio` y `video`
- intenta recuperar `youtube_id` desde nombres tipo `Titulo [ID].ext`
- deja `youtube_id` y `webpage_url` en `null` si no puede inferirlos

### 4. Vinculacion Sin Redescarga

Si el usuario pega una URL de un video ya descargado pero cuya entrada viene de `local_scan`:

- el script puede detectar similitud alta
- ofrecer vincular el `youtube_id` y la `webpage_url`
- guardar esos datos sin necesidad de descargar otra vez

### 5. Deteccion De Similitud

La similitud fue afinada para ignorar o reducir el peso de:

- years como `2024`
- numeros
- palabras comunes como `official`, `video`, `live`, `mix`, `karaoke`, `remix`, `album`

La comparacion usa:

- ratio de texto normalizado
- overlap de tokens

El script muestra hasta 3 coincidencias y resalta en color el titulo que se intenta descargar.

### 6. UX De Consola

Mejoras aplicadas:

- prompt para salir con `s`
- color cian para el titulo que se intenta descargar cuando hay similitudes
- mensajes de confirmacion claros

### 7. Numeracion De `lista.txt`

Se cambio el formato de enumeracion a 3 digitos:

- `001`
- `002`
- `003`

La generacion actual usa:

```text
001. Nombre de cancion
002. Nombre de cancion
```

## Detalles Funcionales Del Script Principal

### Nombre De Archivo

Para descargas nuevas el template por defecto es:

```text
%(title)s [%(id)s].%(ext)s
```

Eso ayuda a:

- detectar duplicados exactos por ID
- reconstruir catalogos futuros con mas precision

### JS Runtime

`yt-dlp` fue configurado para usar `node` si esta disponible:

- `js_runtimes = {"node": {"path": ...}}`

### Uso De `ffmpeg`

El MP3 se genera desde el video ya descargado, usando:

- `libmp3lame`
- bitrate configurable con `--audio-quality`

## Comandos Utiles

Ejecutar el descargador interactivo:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py
```

Reconstruir catalogo desde archivos existentes:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\youtube_media_downloader.py --output-dir "C:\Musica_Boda" --rebuild-catalog
```

Regenerar solo la lista desde la carpeta raiz:

```powershell
python C:\OneDrive\DESARROLLOS\extractor_mp3\generate_song_list.py "C:\Musica_Boda"
```

## Riesgos O Pendientes

- Los registros antiguos sin `youtube_id` solo pueden enriquecerse si el usuario vuelve a pegar la URL.
- No se agrego barra de progreso personalizada porque `yt-dlp` ya muestra progreso suficiente y se prefirio no recargar la consola.
- El proyecto no tiene tests automatizados; la validacion realizada fue principalmente por sintaxis, ejecucion de comandos y uso real del usuario.

## Recomendaciones Para El Siguiente Agente

- No cambiar la ruta por defecto `C:\Musica_Boda` salvo pedido explicito del usuario.
- No eliminar ni reordenar manualmente `lista.txt` ni `catalogo.json` sin confirmar con el usuario.
- Si vuelven warnings de YouTube/EJS, revisar la configuracion de `node`, `yt-dlp-ejs` y la wiki oficial de `yt-dlp`.
- Si se necesita mejorar mas la similitud, partir de `normalize_title`, `split_title_tokens` y `find_similar_entries`.
