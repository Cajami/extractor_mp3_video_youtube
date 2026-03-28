import argparse
from pathlib import Path


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera un TXT enumerado con los nombres de canciones encontradas en una carpeta."
    )
    parser.add_argument(
        "target_dir",
        help="Carpeta raiz del contenido o carpeta de audio a listar.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="Archivo TXT de salida. Si no se indica, se genera music_dir\\lista.txt",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Busca canciones tambien dentro de subcarpetas.",
    )
    return parser


def resolve_music_dir(target_dir: Path) -> Path:
    audio_dir = target_dir / "audio"
    if audio_dir.exists() and audio_dir.is_dir():
        return audio_dir
    return target_dir


def collect_song_names(music_dir: Path, recursive: bool) -> list[str]:
    pattern = "**/*" if recursive else "*"
    files = [
        path.stem
        for path in music_dir.glob(pattern)
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(files, key=str.lower)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    target_dir = Path(args.target_dir).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        raise SystemExit(f"La carpeta no existe o no es valida: {target_dir}")

    music_dir = resolve_music_dir(target_dir)

    output_file = (
        Path(args.output_file).expanduser().resolve()
        if args.output_file
        else target_dir / "lista.txt"
    )
    songs = collect_song_names(music_dir, args.recursive)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{index}. {song}" for index, song in enumerate(songs, start=1)]
    output_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"Se generaron {len(songs)} nombres en: {output_file}")


if __name__ == "__main__":
    main()
