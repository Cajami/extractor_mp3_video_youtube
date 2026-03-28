import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(r"C:\Musica_Boda")
CATALOG_FILE_NAME = "catalogo.json"
SIMILARITY_THRESHOLD = 0.76
ANSI_RESET = "\033[0m"
ANSI_CYAN = "\033[96m"
ANSI_RED = "\033[91m"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Descarga videos y MP3 de YouTube en C:\\Musica_Boda."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Ruta base de salida (por defecto: C:\\Musica_Boda)",
    )
    parser.add_argument(
        "--name-template",
        default="%(title)s [%(id)s].%(ext)s",
        help="Plantilla de nombre para los archivos (por defecto: %%(title)s [%%(id)s].%%(ext)s)",
    )
    parser.add_argument(
        "--audio-quality",
        default="192",
        help="Calidad del MP3 en kbps (por defecto: 192)",
    )
    parser.add_argument(
        "--keep-thumbnail",
        action="store_true",
        help="Guarda tambien la miniatura del video si esta disponible.",
    )
    parser.add_argument(
        "--rebuild-catalog",
        action="store_true",
        help="Reconstruye catalogo.json desde los archivos ya existentes y termina.",
    )
    return parser


def ensure_dependencies() -> None:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print(
            "Falta la dependencia 'yt-dlp'. Instalala con: pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if find_ffmpeg_bin() is None:
        print(
            "No se encontro ffmpeg/ffprobe. Instalalos para descargar y convertir correctamente.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if shutil.which("node") is None:
        print(
            "No se encontro node en el PATH. Instalarlo ayuda a evitar advertencias y mejora la extraccion en YouTube.",
            file=sys.stderr,
        )


def find_ffmpeg_bin() -> Path | None:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return Path(ffmpeg_path).resolve().parent

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not winget_packages.exists():
        return None

    candidates = sorted(winget_packages.glob("Gyan.FFmpeg.Essentials*"))
    for package_dir in reversed(candidates):
        for ffmpeg_exe in package_dir.glob("**/bin/ffmpeg.exe"):
            ffprobe_exe = ffmpeg_exe.parent / "ffprobe.exe"
            if ffprobe_exe.exists():
                return ffmpeg_exe.parent.resolve()

    return None


def sanitize_path(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()


def build_yt_dlp_base_options() -> dict:
    node_path = shutil.which("node")
    options: dict = {}
    if node_path:
        options["extractor_args"] = {"youtube": {"player_client": ["default"]}}
        options["js_runtimes"] = {"node": {"path": node_path}}
    return options


def colorize(text: str, color_code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color_code}{text}{ANSI_RESET}"


def print_error(message: str) -> None:
    print(colorize(message, ANSI_RED), file=sys.stderr)


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = re.sub(r"\[[^\]]*\]|\([^\)]*\)", " ", normalized)
    normalized = re.sub(
        r"\b(official|video|audio|lyric|lyrics|hd|4k|remaster(?:ed)?|version|live|mix|cover|karaoke|remix|edit|full|album)\b",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b(19|20)\d{2}\b", " ", normalized)
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def split_title_tokens(title: str) -> set[str]:
    normalized = normalize_title(title)
    return {token for token in normalized.split() if len(token) > 1}


def load_catalog(catalog_path: Path) -> list[dict]:
    if not catalog_path.exists():
        return []

    try:
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    return data if isinstance(data, list) else []


def save_catalog(catalog_path: Path, entries: list[dict]) -> None:
    catalog_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_existing_by_id(entries: list[dict], youtube_id: str) -> tuple[int, dict] | None:
    for index, entry in enumerate(entries, start=1):
        if entry.get("youtube_id") == youtube_id:
            return index, entry
    return None


def find_similar_entries(entries: list[dict], title: str) -> list[tuple[int, dict, float]]:
    normalized_title = normalize_title(title)
    input_tokens = split_title_tokens(title)
    matches: list[tuple[int, dict, float]] = []
    for index, entry in enumerate(entries, start=1):
        existing_title = entry.get("title", "")
        existing_normalized = normalize_title(existing_title)
        sequence_score = SequenceMatcher(None, normalized_title, existing_normalized).ratio()
        existing_tokens = split_title_tokens(existing_title)
        token_union = input_tokens | existing_tokens
        token_score = (
            len(input_tokens & existing_tokens) / len(token_union)
            if token_union
            else 0.0
        )
        score = max(sequence_score, token_score)
        if score >= SIMILARITY_THRESHOLD:
            matches.append((index, entry, score))

    matches.sort(key=lambda item: item[2], reverse=True)
    return matches[:3]


def prompt_yes_no(message: str) -> bool:
    while True:
        answer = input(f"{message} [s/n]: ").strip().lower()
        if answer in {"s", "si", "sí", "y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Respuesta no valida. Escribi 's' o 'n'.")


def parse_title_and_id_from_stem(stem: str) -> tuple[str, str | None]:
    match = re.match(r"^(?P<title>.+?)\s+\[(?P<youtube_id>[A-Za-z0-9_-]{6,})\]$", stem)
    if not match:
        return stem, None
    return match.group("title").strip(), match.group("youtube_id").strip()


def extract_video_info(url: str) -> dict:
    from yt_dlp import YoutubeDL

    ydl_opts = {"noplaylist": True, "quiet": True, "skip_download": True}
    ydl_opts.update(build_yt_dlp_base_options())
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(info: dict, video_dir: Path, name_template: str, keep_thumbnail: bool) -> Path:
    from yt_dlp import YoutubeDL

    video_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = find_ffmpeg_bin()

    ydl_opts = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "writethumbnail": keep_thumbnail,
        "outtmpl": str(video_dir / name_template),
        "ffmpeg_location": str(ffmpeg_bin) if ffmpeg_bin else None,
    }
    ydl_opts.update(build_yt_dlp_base_options())

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(info["webpage_url"], download=True)
        video_path = Path(ydl.prepare_filename(result))
        requested_ext = result.get("ext")
        if requested_ext and video_path.suffix.lower() != f".{requested_ext.lower()}":
            candidate = video_path.with_suffix(f".{requested_ext.lower()}")
            if candidate.exists():
                video_path = candidate
        if not video_path.exists():
            mp4_candidate = video_path.with_suffix(".mp4")
            if mp4_candidate.exists():
                video_path = mp4_candidate
        return video_path


def convert_video_to_mp3(video_path: Path, audio_dir: Path, audio_quality: str) -> Path:
    audio_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = find_ffmpeg_bin()
    if ffmpeg_bin is None:
        raise RuntimeError("No se encontro ffmpeg para convertir el audio.")

    ffmpeg_exe = ffmpeg_bin / "ffmpeg.exe"
    output_path = audio_dir / f"{video_path.stem}.mp3"
    command = [
        str(ffmpeg_exe),
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        f"{audio_quality}k",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    return output_path


def cleanup_partial_files(base_dir: Path, youtube_id: str | None) -> list[Path]:
    if not youtube_id:
        return []

    removed_files: list[Path] = []
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".part":
            continue
        if f"[{youtube_id}]" not in path.name:
            continue
        path.unlink(missing_ok=True)
        removed_files.append(path)

    return removed_files


def build_song_list(audio_dir: Path, output_file: Path) -> None:
    songs = sorted(
        (path.stem for path in audio_dir.glob("*.mp3") if path.is_file()),
        key=str.lower,
    )
    lines = [f"{index:03d}. {song}" for index, song in enumerate(songs, start=1)]
    output_file.write_text("\n".join(lines), encoding="utf-8")


def rebuild_catalog_from_disk(base_dir: Path) -> list[dict]:
    audio_dir = base_dir / "audio"
    video_dir = base_dir / "video"
    entries_by_key: dict[str, dict] = {}

    if audio_dir.exists():
        for audio_path in sorted(audio_dir.glob("*.mp3")):
            title, youtube_id = parse_title_and_id_from_stem(audio_path.stem)
            key = youtube_id or normalize_title(title) or audio_path.stem.lower()
            entry = entries_by_key.setdefault(
                key,
                {
                    "youtube_id": youtube_id,
                    "title": title,
                    "webpage_url": None,
                    "video_file": None,
                    "audio_file": None,
                    "downloaded_at": None,
                    "source": "local_scan",
                },
            )
            entry["audio_file"] = audio_path.name
            entry["title"] = title
            entry["youtube_id"] = youtube_id or entry.get("youtube_id")

    if video_dir.exists():
        for video_path in sorted(video_dir.glob("*.*")):
            if video_path.suffix.lower() not in {".mp4", ".mkv", ".webm", ".mov", ".avi"}:
                continue
            title, youtube_id = parse_title_and_id_from_stem(video_path.stem)
            key = youtube_id or normalize_title(title) or video_path.stem.lower()
            entry = entries_by_key.setdefault(
                key,
                {
                    "youtube_id": youtube_id,
                    "title": title,
                    "webpage_url": None,
                    "video_file": None,
                    "audio_file": None,
                    "downloaded_at": None,
                    "source": "local_scan",
                },
            )
            entry["video_file"] = video_path.name
            entry["title"] = title
            entry["youtube_id"] = youtube_id or entry.get("youtube_id")

    entries = list(entries_by_key.values())
    entries.sort(key=lambda item: (item.get("title") or "").lower())
    return entries


def prompt_for_url() -> str | None:
    print()
    typed_url = input("Pega un link de YouTube o presiona 's' para salir: ").strip()
    if not typed_url:
        return None
    if typed_url.lower() in {"s", "salir", "exit", "q"}:
        raise SystemExit(0)
    return typed_url


def show_title_checks(info: dict, entries: list[dict]) -> bool:
    title = info.get("title", "Sin titulo")
    youtube_id = info.get("id", "")
    print(f"Titulo detectado: {title}")
    print(f"ID detectado: {youtube_id}")

    existing = find_existing_by_id(entries, youtube_id)
    if existing:
        index, entry = existing
        print()
        print(f"Este video ya fue descargado exactamente y aparece en la lista con el nro {index}.")
        print(f"Titulo existente: {entry.get('title', 'Sin titulo')}")
        return prompt_yes_no("Deseas descargarlo nuevamente?")

    similar_entries = find_similar_entries(entries, title)
    if similar_entries:
        print()
        print(f"Estas intentando descargar: {colorize(title, ANSI_CYAN)}")
        print("Se encontraron las siguientes similitudes en la lista:")
        for index, entry, score in similar_entries:
            percentage = round(score * 100, 1)
            print(f"  {index}. {entry.get('title', 'Sin titulo')} ({percentage}% similitud)")
        return prompt_yes_no("Deseas descargar este video de todas formas?")

    return True


def enrich_existing_entry(entry: dict, info: dict) -> dict:
    entry["youtube_id"] = info.get("id")
    entry["webpage_url"] = info.get("webpage_url")
    if not entry.get("title"):
        entry["title"] = info.get("title")
    return entry


def offer_link_existing_entry(entries: list[dict], info: dict) -> tuple[list[dict], bool]:
    title = info.get("title", "")
    similar_entries = find_similar_entries(entries, title)
    if not similar_entries:
        return entries, False

    top_index, top_entry, top_score = similar_entries[0]
    if top_entry.get("youtube_id") or top_score < 0.9:
        return entries, False

    print()
    print(
        f"Parece que el video corresponde a un registro previo sin ID ni URL en la posicion {top_index}:"
    )
    print(f"  {top_entry.get('title', 'Sin titulo')}")
    if prompt_yes_no("Deseas vincular esta URL a ese registro existente?"):
        entries[top_index - 1] = enrich_existing_entry(top_entry, info)
        return entries, True

    return entries, False


def append_or_update_catalog(entries: list[dict], info: dict, video_path: Path, audio_path: Path) -> list[dict]:
    new_entry = {
        "youtube_id": info.get("id"),
        "title": info.get("title"),
        "webpage_url": info.get("webpage_url"),
        "video_file": video_path.name,
        "audio_file": audio_path.name,
        "downloaded_at": datetime.now().isoformat(timespec="seconds"),
    }

    existing = find_existing_by_id(entries, info.get("id", ""))
    if existing:
        index, _entry = existing
        entries[index - 1] = new_entry
        return entries

    entries.append(new_entry)
    entries.sort(key=lambda item: (item.get("title") or "").lower())
    return entries


def run_download_cycle(base_dir: Path, name_template: str, audio_quality: str, keep_thumbnail: bool) -> None:
    video_dir = base_dir / "video"
    audio_dir = base_dir / "audio"
    list_file = base_dir / "lista.txt"
    catalog_file = base_dir / CATALOG_FILE_NAME
    if not catalog_file.exists():
        rebuilt_entries = rebuild_catalog_from_disk(base_dir)
        if rebuilt_entries:
            save_catalog(catalog_file, rebuilt_entries)
            print(f"Se reconstruyo {catalog_file.name} con {len(rebuilt_entries)} registros existentes.")
            build_song_list(audio_dir=audio_dir, output_file=list_file)

    print(f"Destino actual: {base_dir}")
    print("Los archivos se guardaran en:")
    print(f"  Video: {video_dir}")
    print(f"  Audio: {audio_dir}")
    print(f"  Lista: {list_file}")

    while True:
        try:
            url = prompt_for_url()
        except SystemExit:
            print("Proceso finalizado.")
            break

        if not url:
            print("No ingresaste un link. Proba nuevamente.")
            continue

        entries = load_catalog(catalog_file)

        try:
            info = extract_video_info(url)
        except Exception as exc:
            print_error(f"No pude leer la informacion del video: {exc}")
            continue

        entries, linked_existing = offer_link_existing_entry(entries, info)
        if linked_existing:
            save_catalog(catalog_file, entries)
            if not prompt_yes_no("Deseas descargar este video ahora?"):
                print("Se guardo la URL en el catalogo y se omitio la descarga.")
                continue

        if not show_title_checks(info, entries):
            print("Descarga cancelada por el usuario.")
            continue

        try:
            video_path = download_video(
                info=info,
                video_dir=video_dir,
                name_template=name_template,
                keep_thumbnail=keep_thumbnail,
            )
            audio_path = convert_video_to_mp3(
                video_path=video_path,
                audio_dir=audio_dir,
                audio_quality=audio_quality,
            )
            updated_entries = append_or_update_catalog(
                entries=entries,
                info=info,
                video_path=video_path,
                audio_path=audio_path,
            )
            save_catalog(catalog_file, updated_entries)
            build_song_list(audio_dir=audio_dir, output_file=list_file)
        except Exception as exc:
            removed_files = cleanup_partial_files(video_dir, info.get("id"))
            print_error(f"No se pudo completar la descarga: {exc}")
            if removed_files:
                print_error("Se eliminaron archivos parciales inconclusos:")
                for removed_file in removed_files:
                    print_error(f"  - {removed_file.name}")
            continue

        print("Descarga completada.")
        print(f"Video guardado en: {video_path}")
        print(f"Audio guardado en: {audio_path}")
        print(f"Lista actualizada en: {list_file}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    ensure_dependencies()
    base_dir = sanitize_path(args.output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    if args.rebuild_catalog:
        catalog_file = base_dir / CATALOG_FILE_NAME
        entries = rebuild_catalog_from_disk(base_dir)
        save_catalog(catalog_file, entries)
        build_song_list(audio_dir=base_dir / "audio", output_file=base_dir / "lista.txt")
        print(f"Catalogo reconstruido en: {catalog_file}")
        print(f"Registros detectados: {len(entries)}")
        return

    run_download_cycle(
        base_dir=base_dir,
        name_template=args.name_template,
        audio_quality=args.audio_quality,
        keep_thumbnail=args.keep_thumbnail,
    )


if __name__ == "__main__":
    main()
