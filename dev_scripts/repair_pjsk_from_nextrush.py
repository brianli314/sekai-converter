#!/usr/bin/env python3
"""Repair a stripped PJSK Sonolus export using a complete NextRUSH export."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def get_level_item(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict) and isinstance(data.get("item"), dict):
        item = data["item"]
        return item if isinstance(item.get("name"), str) else None
    if isinstance(data, dict) and isinstance(data.get("name"), str) and isinstance(data.get("engine"), dict):
        return data
    return None


def collect_source_items(source_levels: Path) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for path in source_levels.iterdir():
        if not path.is_file() or path.name in {"info", "list"}:
            continue
        item = get_level_item(load_json(path))
        if item is not None:
            items[item["name"]] = item
    return items


def replace_level_items(value: Any, source_items: dict[str, dict[str, Any]]) -> int:
    if isinstance(value, dict):
        item_name = value.get("name")
        if isinstance(item_name, str) and item_name in source_items and isinstance(value.get("engine"), dict):
            value.clear()
            value.update(source_items[item_name])
            return 1

        changed = 0
        for child in value.values():
            changed += replace_level_items(child, source_items)
        return changed

    if isinstance(value, list):
        return sum(replace_level_items(child, source_items) for child in value)

    return 0


def replace_level_detail(path: Path, source_items: dict[str, dict[str, Any]]) -> bool:
    data = load_json(path)
    item = get_level_item(data)
    if item is None or item["name"] not in source_items:
        return False

    if isinstance(data, dict) and isinstance(data.get("item"), dict):
        data["item"] = source_items[item["name"]]
        replace_level_items(data.get("sections"), source_items)
    else:
        data = source_items[item["name"]]

    write_json(path, data)
    return True


def patch_json_files(root: Path, source_items: dict[str, dict[str, Any]]) -> tuple[int, int]:
    changed_files = 0
    changed_items = 0

    for section in ("levels", "replays"):
        section_dir = root / "sonolus" / section
        if not section_dir.exists():
            continue
        for path in section_dir.iterdir():
            if not path.is_file():
                continue
            if section == "levels" and path.name not in {"info", "list"}:
                if replace_level_detail(path, source_items):
                    changed_files += 1
                    changed_items += 1
                continue

            data = load_json(path)
            changed = replace_level_items(data, source_items)
            if changed:
                write_json(path, data)
                changed_files += 1
                changed_items += changed

    return changed_files, changed_items


def copy_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def copy_repository(source_root: Path, target_root: Path) -> int:
    source_repo = source_root / "sonolus" / "repository"
    target_repo = target_root / "sonolus" / "repository"
    target_repo.mkdir(parents=True, exist_ok=True)

    copied = 0
    for source in source_repo.iterdir():
        if not source.is_file():
            continue
        target = target_repo / source.name
        if not target.exists():
            shutil.copy2(source, target)
            copied += 1
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", default="scps/extracted_pjsk")
    parser.add_argument("--source-root", default="scps/extracted_nextrush")
    parser.add_argument("--output-root", default="scps/extracted_pjsk_fixed")
    args = parser.parse_args()

    target_root = Path(args.target_root)
    source_root = Path(args.source_root)
    output_root = Path(args.output_root)

    copy_tree(target_root, output_root)
    source_items = collect_source_items(source_root / "sonolus" / "levels")
    changed_files, changed_items = patch_json_files(output_root, source_items)
    copied = copy_repository(source_root, output_root)

    print(f"Patched {changed_items} level references across {changed_files} files.")
    print(f"Copied {copied} repository blobs.")
    print(f"Wrote {output_root}.")


if __name__ == "__main__":
    main()
