# SCP to NextRush+ chart server

Tools for importing Sonolus `.scp` packages into a self-hosted Sonolus server that renders the charts using the NextRush+ engine and UI. Server hosting is done using [ScoreSync-Modern](https://github.com/UntitledCharts/ScoreSync-Modern).

## Instructions
1. Put playable `.scp` packages in `to_import/`.
2. Import levels:

```bash
python3 import_scp_to_scoresync.py --clean --overwrite
```

If you just want to add a new song without re-importing all the levels, run it without the `--clean` and `--overwrite` flags. See [docs](docs/main_docs.md)

Run the server:

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

or in Sonolus, make a server with  

```text
http://<YOUR-PUBLIC-IP>:3939
```
For server issues, see the original [ScoreSync-Modern](https://github.com/UntitledCharts/ScoreSync-Modern) repository

## Extra Commands

The base version comes with the NextRush+ UI from the now-deleted SekaiRush Sonolus server. You can install custom UI assets by finding a song with the correct UI/assets that you want, and placing it as `to_import/reference.scp`. Then, run

```bash
python3 dev_scripts/install_scoresync_assets_from_scp.py
```

Clear Docker-owned runtime cache:

```bash
cd scoresync
docker compose down
cd ..
sudo rm -rf scoresync/levels_cache
```

## Notes

- `to_import/reference.scp` is skipped as playable content by default. It is used as an engine/UI asset donor.
- Generated level folders, generated playlists, extracted `.scp`s, and runtime caches are ignored by git.
- See [docs/SCORESYNC_PIPELINE.md](docs/main_docs.md) for details and limitations.
