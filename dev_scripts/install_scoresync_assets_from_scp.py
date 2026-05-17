#!/usr/bin/env python3
"""Install engine/UI assets from an extracted Sonolus package into ScoreSync overrides."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Optional


RESOURCE_MAP = {
    ("thumbnail",): "thumbnail.png",
    ("configuration",): "engine/EngineConfiguration",
    ("playData",): "engine/EnginePlayData",
    ("watchData",): "engine/EngineWatchData",
    ("previewData",): "engine/EnginePreviewData",
    ("tutorialData",): "engine/EngineTutorialData",
    ("rom",): "engine/EngineRom",
    ("skin", "data"): "skin/data",
    ("skin", "texture"): "skin/texture",
    ("background", "data"): "background/data",
    ("background", "image"): "background/image.png",
    ("background", "configuration"): "background/configuration",
    ("effect", "data"): "effect/data",
    ("effect", "audio"): "effect/audio",
    ("particle", "data"): "particle/data",
    ("particle", "texture"): "particle/texture",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy newer Sonolus engine/UI resources into ScoreSync's Docker overlay.",
    )
    parser.add_argument(
        "--scp",
        type=Path,
        default=Path("to_import/reference.scp"),
        help="UI override .scp to extract and use as the asset source.",
    )
    parser.add_argument(
        "--extract-dir",
        type=Path,
        default=Path("imported_scps"),
        help="Where --scp should be extracted.",
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        help="Path to an already extracted package's sonolus directory. Overrides --scp.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("scoresync/overrides/assets"),
        help="Where ScoreSync Docker overlay assets should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package_root = args.package_root or extract_scp(args.scp, args.extract_dir)
    output_dir = args.output_dir

    level = find_level_with_engine(package_root)
    if level is None:
        raise SystemExit(f"No level with a complete engine object found in {package_root}")

    engine = level["engine"]
    write_engine_metadata(output_dir / "engine_metadata.json", engine)
    copied = 0
    missing: list[str] = []

    for key_path, relative_output in RESOURCE_MAP.items():
        ref = nested_get(engine, key_path)
        source = resolve_resource(package_root, ref)
        if source is None:
            missing.append(".".join(key_path))
            continue

        target = output_dir / relative_output
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    print(f"Installed {copied} ScoreSync asset overrides from {package_root}.")
    print(f"Engine: {engine.get('title')} ({engine.get('name')})")
    if missing:
        print("Missing optional/required refs:")
        for item in missing:
            print(f"  - {item}")


def extract_scp(scp_path: Path, extract_dir: Path) -> Path:
    target = extract_dir / scp_path.stem
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(scp_path) as archive:
        safe_extract(archive, target)

    package_root = target / "sonolus"
    if not package_root.exists():
        raise FileNotFoundError(f"{scp_path} did not contain a sonolus/ directory")
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


def write_engine_metadata(path: Path, engine: dict[str, Any]) -> None:
    metadata = {
        "engine": item_metadata(engine),
        "skin": item_metadata(engine.get("skin")),
        "background": item_metadata(engine.get("background")),
        "effect": item_metadata(engine.get("effect")),
        "particle": item_metadata(engine.get("particle")),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def item_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value[key]
        for key in ("name", "source", "version", "title", "subtitle", "author", "tags")
        if key in value
    }


def find_level_with_engine(package_root: Path) -> Optional[dict[str, Any]]:
    for item in iter_level_items(package_root):
        engine = item.get("engine")
        if isinstance(engine, dict) and has_required_refs(package_root, engine):
            return item
    return None


def iter_level_items(package_root: Path):
    levels_dir = package_root / "levels"
    if levels_dir.exists():
        for path in sorted(levels_dir.iterdir()):
            if not path.is_file() or path.name in {"info", "list"}:
                continue
            item = item_from_json(load_json(path))
            if item is not None:
                yield item

        list_path = levels_dir / "list"
        if list_path.exists():
            data = load_json(list_path)
            for item in data.get("items", []) if isinstance(data, dict) else []:
                if isinstance(item, dict):
                    yield item

    playlists_dir = package_root / "playlists"
    if playlists_dir.exists():
        for path in sorted(playlists_dir.iterdir()):
            if not path.is_file() or path.name in {"info", "list"}:
                continue
            data = load_json(path)
            playlist = item_from_json(data)
            if not isinstance(playlist, dict):
                continue
            for item in playlist.get("levels", []):
                if isinstance(item, dict):
                    yield item


def item_from_json(data: Any) -> Optional[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("item"), dict):
        return data["item"]
    if isinstance(data, dict):
        return data
    return None


def has_required_refs(package_root: Path, engine: dict[str, Any]) -> bool:
    required = [
        ("playData",),
        ("watchData",),
        ("previewData",),
        ("tutorialData",),
        ("rom",),
        ("configuration",),
        ("skin", "data"),
        ("skin", "texture"),
        ("effect", "data"),
        ("effect", "audio"),
        ("particle", "data"),
        ("particle", "texture"),
    ]
    return all(resolve_resource(package_root, nested_get(engine, path)) is not None for path in required)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nested_get(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def resolve_resource(package_root: Path, ref: Any) -> Optional[Path]:
    if not isinstance(ref, dict):
        return None

    hash_name = ref.get("hash")
    if not isinstance(hash_name, str) or not hash_name:
        url = ref.get("url")
        if isinstance(url, str) and "/sonolus/repository/" in url:
            hash_name = url.rsplit("/", 1)[-1]

    if not isinstance(hash_name, str) or not hash_name:
        return None

    path = package_root / "repository" / hash_name
    return path if path.exists() else None


if __name__ == "__main__":
    main()
