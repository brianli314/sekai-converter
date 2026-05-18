# ScoreSync Pipeline

This repo imports Sonolus `.scp` packages into a patched ScoreSync-Modern server.

## Main Pieces

- `import_scp_to_scoresync.py`
  Imports playable `.scp` packages from `to_import/` into `scoresync/levels/` and `scoresync/playlists/`.

- `dev_scripts/install_scoresync_assets_from_scp.py`
  Installs global engine/UI assets from a reference `.scp` song or playlist.

## Reference SCP

The default reference package is:

```text
to_import/reference.scp
```

It is an exported song or playlist used only as an asset donor for the global engine/UI. The asset installer copies engine, skin, background, effect, particle, thumbnail, and metadata resources into:

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

`preview.mp3` comes from the source `.scp` preview resource. This is what makes song-select previews start at the intended excerpt instead of the silent beginning of the full BGM. If the `.scp` is formatted correctly, all of these fields should be present

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
This does not need to be done if directly cloned from the repository, the default assets come with the NextRush+ UI.

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

Replaces existing extracted packages and exported folders for content being imported. If a level/package from `to_import/` exports to a folder that already exists in `scoresync/levels/`, `--overwrite` deletes and recreates that matching output folder.

`--reference-scp`

Changes which `.scp` is treated as the reference package.

`--import-reference`

Also imports the reference package as playable chart content.

## Other 

Some PJSK `.scp` exports may be stripped and missing complete level metadata or repository blobs. The repair script can rebuild those exports by using a complete NextRUSH export as a donor source.

Script:

```text
dev_scripts/repair_pjsk_export.py
```
By default, it expects:
```
scps/extracted_pjsk
scps/extracted_nextrush
```
and writes the repaired export to `scps/extracted_pjsk_fixed`. 

**This is an old script that is not necessary for normal charts** 


## Limitations

- This is a patch over an older ScoreSync-Modern build, not a full modern Sonolus server.
- Levels and generated playlists are supported; posts, rooms, replays, and browsable engine/skin/effect/particle collections are not.
- The server uses one global engine/UI asset set from `scoresync/overrides/assets/`.
- The importer does not deeply convert chart formats.
- Some source charts may load incorrectly if their data does not match the installed global engine. This has only been tested on the standard [Sonolus PJSK server](https://sonolus.sekai.best) 
- Rebuild Docker after changing anything under `scoresync/overrides/`.
- If adding new songs, `docker compose restart` may be used
