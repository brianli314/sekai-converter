import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from helpers.create_level_item import create_level_item
from helpers.levels import load_levels_directory
from helpers.repository import repo

router = APIRouter()

PLAYLISTS_DIR = Path("playlists")
ITEMS_PER_PAGE = 10


def load_playlist_manifests() -> list[dict]:
    if not PLAYLISTS_DIR.exists():
        return []

    playlists = []
    for path in sorted(PLAYLISTS_DIR.glob("*.json"), key=lambda item: item.name.lower()):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            playlists.append(data)
    return playlists


def playlist_item(playlist: dict, level_items: list[dict]) -> dict:
    item = {
        "name": playlist["name"],
        "version": 1,
        "title": playlist.get("title") or playlist["name"],
        "subtitle": playlist.get("subtitle") or "",
        "author": playlist.get("author") or "ScoreSync Modern",
        "tags": playlist.get("tags") if isinstance(playlist.get("tags"), list) else [],
        "levels": level_items,
    }
    if level_items:
        item["thumbnail"] = level_items[0]["cover"]
    return item


def level_items_by_folder(request: Request, levels: dict) -> dict[str, dict]:
    out = {}
    for folder_name, level_data in levels.items():
        try:
            item = create_level_item(request, level_data, folder_name)
        except Exception:
            continue
        if item["cover"] is None or item["bgm"] is None or item["data"] is None:
            continue
        out[folder_name] = item
    return out


async def playlist_items(request: Request, playlists: list[dict]) -> list[dict]:
    levels = await request.app.run_blocking(load_levels_directory, request.app.bgver)
    by_folder = level_items_by_folder(request, levels)
    items = []

    for playlist in playlists:
        level_items = [
            by_folder[folder]
            for folder in playlist.get("levelFolders", [])
            if isinstance(folder, str) and folder in by_folder
        ]
        if level_items:
            items.append(playlist_item(playlist, level_items))

    return items


@router.get("/sonolus/playlists/info")
async def playlists_info(request: Request):
    playlists = load_playlist_manifests()
    items = await playlist_items(request, playlists[:20])
    data = {
        "sections": [
            {
                "title": "#PLAYLIST",
                "itemType": "playlist",
                "items": items,
            }
        ]
    }
    data["banner"] = repo.get_srl(request.app.files["banner"])
    return data


@router.get("/sonolus/playlists/list")
async def playlists_list(request: Request):
    page = int(request.query_params.get("page", 0))
    playlists = load_playlist_manifests()
    page_count = (len(playlists) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = await playlist_items(request, playlists[start:end])
    return {
        "pageCount": page_count,
        "items": items,
    }


@router.get("/sonolus/playlists/{playlist_name}")
async def playlist_details(request: Request, playlist_name: str):
    playlist = next(
        (item for item in load_playlist_manifests() if item.get("name") == playlist_name),
        None,
    )
    if playlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    items = await playlist_items(request, [playlist])
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item = items[0]
    level_items = item["levels"]

    return {
        "item": item,
        "description": "",
        "actions": [],
        "hasCommunity": False,
        "leaderboards": [],
        "sections": [
            {
                "title": "#LEVEL",
                "itemType": "level",
                "items": level_items,
            }
        ],
    }
