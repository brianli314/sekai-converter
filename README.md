# SCP to NextRush+ chart server

Tools for importing Sonolus `.scp` packages into a self-hosted Sonolus server that renders the charts using the NextRush+ engine and UI. Server hosting is done using [ScoreSync-Modern](https://github.com/UntitledCharts/ScoreSync-Modern).

This can be used to take [Sonolus PJSK server](https://sonolus.sekai.best) chart exports, which work but have a less polished/default Sonolus presentation, and repackaging them into a server that is closer to the now-shutdown SekaiRush UI and looks more similar to chart-playing in Project Sekai.

## Instructions
1. Put playable `.scp` packages in `to_import/`.
2. Import levels:

```bash
python3 import_scp_to_scoresync.py --clean --overwrite
```

If you just want to add a new song without re-importing all the levels, run it without the `--clean` and `--overwrite` flags. See [docs](docs/main_docs.md) for more.

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

or in Sonolus, add a server with  

```text
http://<YOUR-HOST-IP>:3939
```
For server issues, see the original [ScoreSync-Modern](https://github.com/UntitledCharts/ScoreSync-Modern) repository

## Editing UI

The base version comes with the NextRush+ UI from the now-deleted SekaiRush Sonolus server. You can install custom UI assets by finding a song with the correct UI/assets that you want, and placing it as `to_import/reference.scp`. See [docs](docs/main_docs.md) for more.

## Notes

- `to_import/reference.scp` is skipped as playable content by default. It is used as an engine/UI asset donor.
- This has only been tested on standard Sonolus charts from the [PJSK server](https://sonolus.sekai.best)
- See [docs](docs/main_docs.md) for details and limitations, or any errors you encouters.
