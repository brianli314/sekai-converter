import json
from pathlib import Path

from helpers.repository import repo


def load_metadata(folder_name):
    path = Path("levels") / folder_name / "metadata.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_engine_metadata():
    path = Path("assets") / "engine_metadata.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def apply_metadata(target, source):
    if not isinstance(source, dict):
        return
    for key in ("name", "source", "version", "title", "subtitle", "author", "tags"):
        if key in source:
            target[key] = source[key]


def create_level_item(request, data, folder_name):
    metadata = load_metadata(folder_name)
    engine_metadata = load_engine_metadata()

    engine_data = {
        "name": "NextRUSH_P",
        "version": 13,
        "tags": [],
        "title": "NextRUSH+",
        "subtitle": "NextRUSH+",
        "author": "hyeong",
        "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
        "configuration": repo.get_srl(request.app.files["engine_config"]),
        "playData": repo.get_srl(request.app.files["engine_play"]),
        "watchData": repo.get_srl(request.app.files["engine_watch"]),
        "previewData": repo.get_srl(request.app.files["engine_preview"]),
        "tutorialData": repo.get_srl(request.app.files["engine_tut"]),
        "rom": repo.get_srl(request.app.files["engine_rom"]),
        "skin": {
            "name": "nextrushpskin",
            "version": 4,
            "title": "JP v3",
            "subtitle": "JP v3",
            "author": "hyeong",
            "tags": [],
            "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
            "data": repo.get_srl(request.app.files["skin_data"]),
            "texture": repo.get_srl(request.app.files["skin_texture"]),
        },
        "background": {
            "name": "black",
            "version": 2,
            "title": "black",
            "subtitle": "black",
            "author": "RGB(0,0,0)",
            "tags": [],
            "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
            "data": repo.get_srl(request.app.files["bg_data"]),
            "configuration": repo.get_srl(request.app.files["bg_config"]),
            "image": repo.get_srl(request.app.files["bg_image"]),
        },
        "effect": {
            "name": "v3",
            "version": 5,
            "title": "v3",
            "subtitle": "v3",
            "author": "Burrito",
            "tags": [],
            "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
            "data": repo.get_srl(request.app.files["sfx_data"]),
            "audio": repo.get_srl(request.app.files["sfx_audio"]),
        },
        "particle": {
            "name": "Standard",
            "version": 3,
            "title": "Standard",
            "subtitle": "Standard",
            "author": "ToastedBread",
            "tags": [],
            "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
            "data": repo.get_srl(request.app.files["particle_data"]),
            "texture": repo.get_srl(request.app.files["particle_texture"]),
        },
    }
    apply_metadata(engine_data, engine_metadata.get("engine"))
    apply_metadata(engine_data["skin"], engine_metadata.get("skin"))
    apply_metadata(engine_data["background"], engine_metadata.get("background"))
    apply_metadata(engine_data["effect"], engine_metadata.get("effect"))
    apply_metadata(engine_data["particle"], engine_metadata.get("particle"))

    title = metadata.get("title") or folder_name
    artists = metadata.get("artists") or "???"
    author = metadata.get("author") or "you"
    rating = metadata.get("rating")
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []

    background = {
        "name": f"levelbg",
        "version": 2,
        "tags": [],
        "title": title,
        "subtitle": f"{title} Background",
        "author": "ScoreSync Modern",
        "thumbnail": repo.get_srl(request.app.files["thumbnail"]),
        "data": engine_data["background"]["data"],
        "image": repo.get_srl(data["background"]) or engine_data["background"]["image"],
        "configuration": engine_data["background"]["configuration"],
    }

    return {
        "name": data["id"],
        "version": 1,
        "tags": tags,
        "rating": rating if isinstance(rating, int) else 0,
        "title": title,
        "artists": artists,
        "author": author,
        "useSkin": {"useDefault": True},
        "useEffect": {"useDefault": True},
        "useParticle": {"useDefault": True},
        "useBackground": {"useDefault": False, "item": background},
        "engine": engine_data,
        "cover": repo.get_srl(data["cover"]),
        "bgm": repo.get_srl(data["music"]),
        "preview": repo.get_srl(data.get("preview")) or repo.get_srl(data["music"]),
        "data": repo.get_srl(data["score"]),
    }
