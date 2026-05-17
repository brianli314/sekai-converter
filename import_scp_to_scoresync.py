#!/usr/bin/env python3
"""Import Sonolus .scp packages into ScoreSync-Modern's levels folder."""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


REPO_REF_KEYS = ("hash",)
DIFFICULTY_TAGS = ("#APPEND", "#MASTER", "#EXPERT", "#HARD", "#NORMAL", "#EASY")


@dataclass
class ImportStats:
    packages: int = 0
    levels_seen: int = 0
    levels_exported: int = 0
    levels_skipped: int = 0
    missing_cover: int = 0
    missing_bgm: int = 0
    missing_data: int = 0
    missing_preview: int = 0
    playlists_exported: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract playable ScoreSync level folders from Sonolus .scp packages.",
    )
    parser.add_argument("--import-dir", type=Path, default=Path("to_import"))
    parser.add_argument("--extract-dir", type=Path, default=Path("imported_scps"))
    parser.add_argument("--scoresync-dir", type=Path, default=Path("scoresync"))
    parser.add_argument("--levels-dir", type=Path, help="Defaults to <scoresync-dir>/levels.")
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Create folders even when cover, bgm, or chart data is missing.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing extracted package and exported level folders.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete previously generated ScoreSync levels/playlists before importing.",
    )
    parser.add_argument(
        "--reference-scp",
        type=Path,
        default=Path("to_import/reference.scp"),
        help="Template .scp used only for server UI assets; skipped as chart content when present.",
    )
    parser.add_argument(
        "--import-reference",
        action="store_true",
        help="Also import --reference-scp as playable chart content.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    levels_dir = args.levels_dir or args.scoresync_dir / "levels"
    stats = ImportStats()

    all_scp_paths = sorted(args.import_dir.glob("*.scp"))
    reference_scp = args.reference_scp.resolve()
    scp_paths = [
        path
        for path in all_scp_paths
        if args.import_reference or path.resolve() != reference_scp
    ]
    if not scp_paths:
        raise SystemExit(f"No .scp files found in {args.import_dir}")
    for skipped_path in all_scp_paths:
        if skipped_path not in scp_paths:
            print(f"Using {skipped_path} as UI reference only; not importing as chart content.")

    args.extract_dir.mkdir(parents=True, exist_ok=True)
    levels_dir.mkdir(parents=True, exist_ok=True)
    if args.clean:
        clean_generated_scoresync_data(
            levels_dir,
            levels_dir.parent / "playlists",
            levels_dir.parent / "levels_cache",
        )

    for scp_path in scp_paths:
        stats.packages += 1
        package_root = extract_scp(scp_path, args.extract_dir, overwrite=args.overwrite)
        package_stats = export_package(
            package_root=package_root,
            levels_dir=levels_dir,
            include_incomplete=args.include_incomplete,
            overwrite=args.overwrite,
        )
        merge_stats(stats, package_stats)

    print()
    print("Import complete")
    print(f"  packages:        {stats.packages}")
    print(f"  levels seen:     {stats.levels_seen}")
    print(f"  levels exported: {stats.levels_exported}")
    print(f"  levels skipped:  {stats.levels_skipped}")
    print(f"  missing cover:   {stats.missing_cover}")
    print(f"  missing bgm:     {stats.missing_bgm}")
    print(f"  missing data:    {stats.missing_data}")
    print(f"  missing preview: {stats.missing_preview}")
    print(f"  playlists:       {stats.playlists_exported}")
    print(f"  ScoreSync path:  {levels_dir}")


def extract_scp(scp_path: Path, extract_dir: Path, *, overwrite: bool) -> Path:
    target = extract_dir / scp_path.stem
    if target.exists() and overwrite:
        shutil.rmtree(target)
    if not target.exists():
        target.mkdir(parents=True)
        with zipfile.ZipFile(scp_path) as archive:
            safe_extract(archive, target)

    package_root = target / "sonolus"
    if not package_root.exists():
        raise FileNotFoundError(f"{scp_path} did not contain a sonolus/ directory")

    print(f"Extracted {scp_path} -> {target}")
    return package_root


def safe_extract(archive: zipfile.ZipFile, target: Path) -> None:
    target = target.resolve()
    for member in archive.infolist():
        member_path = (target / member.filename).resolve()
        try:
            member_path.relative_to(target)
        except ValueError as exc:
            raise ValueError(f"Unsafe zip path: {member.filename}") from exc
        archive.extract(member, target)


def export_package(
    *,
    package_root: Path,
    levels_dir: Path,
    include_incomplete: bool,
    overwrite: bool,
) -> ImportStats:
    stats = ImportStats()
    scoresync_dir = levels_dir.parent
    playlists_dir = scoresync_dir / "playlists"
    list_path = package_root / "levels" / "list"
    if not list_path.exists():
        print(f"Skipping {package_root}: no levels/list")
        return stats

    collection = collect_level_collection(package_root)
    items = collection["items"]
    item_to_folder: dict[str, str] = {}

    for item_name, listed_item in items.items():
        stats.levels_seen += 1
        detail_path = package_root / "levels" / item_name
        detail = load_json(detail_path) if detail_path.exists() else {"item": listed_item}
        item = detail.get("item", detail) if isinstance(detail, dict) else {}
        if not isinstance(item, dict):
            stats.levels_skipped += 1
            continue

        export_name = level_folder_name(item)
        output_dir = unique_output_dir(levels_dir, export_name, item_name, overwrite=overwrite)
        resources = {
            "cover": resolve_resource(package_root, item.get("cover")),
            "bgm": resolve_resource(package_root, item.get("bgm")),
            "preview": resolve_resource(package_root, item.get("preview")),
            "data": resolve_resource(package_root, item.get("data")),
        }

        required_resources = {name: resources[name] for name in ("cover", "bgm", "data")}
        missing = [name for name, path in required_resources.items() if path is None]
        if missing:
            if "cover" in missing:
                stats.missing_cover += 1
            if "bgm" in missing:
                stats.missing_bgm += 1
            if "data" in missing:
                stats.missing_data += 1
            stats.levels_skipped += 1
            print(f"Skip {item_name}: missing {', '.join(missing)}")
            if not include_incomplete:
                continue
        if resources["preview"] is None:
            stats.missing_preview += 1

        if output_dir.exists() and overwrite:
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if resources["cover"]:
            shutil.copyfile(resources["cover"], output_dir / "cover.png")
        if resources["bgm"]:
            shutil.copyfile(resources["bgm"], output_dir / "music.mp3")
        if resources["preview"]:
            shutil.copyfile(resources["preview"], output_dir / "preview.mp3")
        if resources["data"]:
            write_score_file(resources["data"], output_dir / "LevelData.json")

        write_metadata(output_dir, item, source_package=package_root.parent.name)
        item_to_folder[item_name] = output_dir.name
        stats.levels_exported += 1
        print(f"Exported {item_name} -> {output_dir}")

    exported_playlists = write_playlists(
        playlists_dir=playlists_dir,
        playlists=collection["playlists"],
        item_to_folder=item_to_folder,
        overwrite=overwrite,
        source_package=package_root.parent.name,
    )
    stats.playlists_exported += exported_playlists

    return stats


def collect_level_collection(package_root: Path) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    playlists: list[dict[str, Any]] = []

    list_path = package_root / "levels" / "list"
    list_data = load_json(list_path)
    listed_items = list_data.get("items", []) if isinstance(list_data, dict) else []
    add_level_items(items, listed_items)

    levels_dir = package_root / "levels"
    for path in sorted(levels_dir.iterdir()):
        if not path.is_file() or path.name in {"info", "list"}:
            continue
        detail = load_json(path)
        item = detail.get("item", detail) if isinstance(detail, dict) else {}
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            items[item["name"]] = item

    playlists_dir = package_root / "playlists"
    if playlists_dir.exists():
        for path in sorted(playlists_dir.iterdir()):
            if not path.is_file() or path.name in {"info", "list"}:
                continue
            playlist = load_json(path)
            extracted_playlist = extract_playlist(playlist)
            if extracted_playlist is not None:
                playlists.append(extracted_playlist)
                add_level_items(items, extracted_playlist["levels"])

    return {"items": items, "playlists": playlists}


def extract_playlist(value: Any) -> Optional[dict[str, Any]]:
    if isinstance(value, dict):
        item = value.get("item")
        if isinstance(item, dict):
            return extract_playlist(item)

        levels = value.get("levels")
        if isinstance(levels, list):
            return {
                "name": value.get("name"),
                "title": value.get("title") or value.get("name") or "Playlist",
                "subtitle": value.get("subtitle") or "",
                "author": value.get("author") or "ScoreSync Modern",
                "tags": value.get("tags", []),
                "levels": [level for level in levels if isinstance(level, dict)],
            }

    return None


def add_level_items(items: dict[str, dict[str, Any]], candidates: list[Any]) -> None:
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        name = candidate.get("name")
        if isinstance(name, str) and isinstance(candidate.get("data"), dict):
            items[name] = candidate


def write_playlists(
    *,
    playlists_dir: Path,
    playlists: list[dict[str, Any]],
    item_to_folder: dict[str, str],
    overwrite: bool,
    source_package: str,
) -> int:
    if not playlists:
        return 0

    playlists_dir.mkdir(parents=True, exist_ok=True)
    exported = 0

    for playlist in playlists:
        level_folders = []
        for level in playlist["levels"]:
            name = level.get("name")
            if isinstance(name, str) and name in item_to_folder:
                level_folders.append(item_to_folder[name])

        if not level_folders:
            continue

        playlist_name = sanitize_folder_name(str(playlist.get("title") or playlist.get("name") or "Playlist"))
        path = playlists_dir / f"{playlist_name}.json"
        if path.exists() and not overwrite:
            path = playlists_dir / f"{playlist_name} - {source_package}.json"

        data = {
            "name": sanitize_identifier(str(playlist.get("name") or playlist_name)),
            "title": playlist.get("title") or playlist_name,
            "subtitle": playlist.get("subtitle") or "",
            "author": playlist.get("author") or "ScoreSync Modern",
            "tags": playlist.get("tags", []),
            "levelFolders": level_folders,
            "sourcePackage": source_package,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        exported += 1
        print(f"Exported playlist {data['title']} -> {path}")

    return exported


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_resource(package_root: Path, ref: Any) -> Optional[Path]:
    if not isinstance(ref, dict):
        return None

    for key in REPO_REF_KEYS:
        value = ref.get(key)
        if isinstance(value, str) and value:
            path = package_root / "repository" / value
            if path.exists():
                return path

    url = ref.get("url")
    if isinstance(url, str) and "/sonolus/repository/" in url:
        hash_name = url.rsplit("/", 1)[-1]
        path = package_root / "repository" / hash_name
        if path.exists():
            return path

    return None


def write_score_file(source: Path, target: Path) -> None:
    raw = source.read_bytes()
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    target.write_bytes(raw)


def write_metadata(output_dir: Path, item: dict[str, Any], *, source_package: str) -> None:
    metadata = {
        "name": item.get("name"),
        "title": item.get("title"),
        "artists": item.get("artists"),
        "author": item.get("author"),
        "rating": item.get("rating"),
        "tags": item.get("tags", []),
        "source": item.get("source"),
        "sourcePackage": source_package,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def level_folder_name(item: dict[str, Any]) -> str:
    title = str(item.get("title") or item.get("name") or "Untitled")
    difficulty = difficulty_from_tags(item.get("tags", []))
    version = version_from_tags(item.get("tags", []))
    rating = item.get("rating")
    parts = [title]
    if version:
        parts.append(version)
    if difficulty:
        parts.append(difficulty)
    if isinstance(rating, int):
        parts.append(str(rating))
    return sanitize_folder_name(" - ".join(parts))


def version_from_tags(tags: Any) -> Optional[str]:
    if not isinstance(tags, list):
        return None
    titles = [tag.get("title") for tag in tags if isinstance(tag, dict)]
    for title in titles:
        if isinstance(title, str) and title not in DIFFICULTY_TAGS:
            return title
    return None


def difficulty_from_tags(tags: Any) -> Optional[str]:
    if not isinstance(tags, list):
        return None
    titles = [tag.get("title") for tag in tags if isinstance(tag, dict)]
    for difficulty in DIFFICULTY_TAGS:
        if difficulty in titles:
            return difficulty.removeprefix("#")
    return None


def sanitize_folder_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or "Untitled"


def sanitize_identifier(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return value[:120] or "playlist"


def unique_output_dir(levels_dir: Path, folder_name: str, item_name: str, *, overwrite: bool) -> Path:
    output_dir = levels_dir / folder_name
    if overwrite or not output_dir.exists():
        return output_dir
    return levels_dir / sanitize_folder_name(f"{folder_name} - {item_name}")


def clean_generated_scoresync_data(levels_dir: Path, playlists_dir: Path, levels_cache_dir: Path) -> None:
    if levels_dir.exists():
        for folder in levels_dir.iterdir():
            if folder.is_dir() and (folder / "metadata.json").exists():
                shutil.rmtree(folder)

    if playlists_dir.exists():
        for playlist in playlists_dir.glob("*.json"):
            playlist.unlink()



def merge_stats(total: ImportStats, part: ImportStats) -> None:
    total.levels_seen += part.levels_seen
    total.levels_exported += part.levels_exported
    total.levels_skipped += part.levels_skipped
    total.missing_cover += part.missing_cover
    total.missing_bgm += part.missing_bgm
    total.missing_data += part.missing_data
    total.missing_preview += part.missing_preview
    total.playlists_exported += part.playlists_exported


if __name__ == "__main__":
    main()
