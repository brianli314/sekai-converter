# ScoreSync Pipeline

This repo imports Sonolus `.scp` packages into a patched ScoreSync-Modern server.

## Main Pieces

- `import_scp_to_scoresync.py`
  Imports playable `.scp` packages from `to_import/` into `scoresync/levels/` and `scoresync/playlists/`.

- `dev_scripts/install_scoresync_assets_from_scp.py`
  Installs global engine/UI assets from a reference `.scp`.

- `scoresync/overrides/`
  Patches copied over the bundled ScoreSync app when Docker builds.

- `scoresync/docker-compose.yml`
  Runs the server on port `3939`.

## Reference SCP

The default reference package is:

```text
to_import/reference.scp
```

It is used only as an asset donor for the global engine/UI. The asset installer copies engine, skin, background, effect, particle, thumbnail, and metadata resources into:

```text
scoresync/overrides/assets/
```

After those assets are installed and Docker is rebuilt, the server does not need `reference.scp` at runtime.

The importer skips `to_import/reference.scp` as playable chart content by default. Use `--import-reference` only if you want it imported as playable levels too.

## Imported Level Output

Each generated level folder contains:

- `cover.png`
- `music.mp3`
- `preview.mp3`
- `LevelData.json`
- `metadata.json`

`preview.mp3` comes from the source `.scp` preview resource. This is what makes song-select previews start at the intended excerpt instead of the silent beginning of the full BGM.

## Playlists

The importer writes playlist manifests into:

```text
scoresync/playlists/
```

The custom playlist route in `scoresync/overrides/routes/playlists.py` serves those as Sonolus playlists.

## Normal Workflow

Install or refresh global UI assets:

```bash
python3 dev_scripts/install_scoresync_assets_from_scp.py
```

Import playable content:

```bash
python3 import_scp_to_scoresync.py --clean --overwrite
```

Run:

```bash
cd scoresync
docker compose down
docker compose build --no-cache
docker compose up
```

Open:

```text
http://localhost:3939
```

## Flags

`--clean`

Deletes generated level/playlists before importing. Use this when `scoresync/levels/` should exactly match `to_import/`.

`--overwrite`

Replaces existing extracted packages and exported folders for content being imported.

`--reference-scp`

Changes which `.scp` is treated as the reference package.

`--import-reference`

Also imports the reference package as playable chart content.

## Limitations

- This is a patch over an older ScoreSync-Modern build, not a full modern Sonolus server.
- Levels and generated playlists are supported; posts, rooms, replays, and browsable engine/skin/effect/particle collections are not.
- The server uses one global engine/UI asset set from `scoresync/overrides/assets/`.
- The importer does not deeply convert chart formats.
- Some source charts may load incorrectly if their data does not match the installed global engine.
- `scoresync/levels_cache/` can be created by Docker as `nobody:nobody`; clear it with `sudo rm -rf scoresync/levels_cache` if stale data persists.
- Rebuild Docker after changing anything under `scoresync/overrides/`.
