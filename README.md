# ScoreSync SCP Importer

Tools for importing Sonolus `.scp` packages into a local ScoreSync-Modern server.

The normal workflow is:

1. Put playable `.scp` packages in `to_import/`.
2. Put the UI reference package at `to_import/reference.scp` if you need to install/reinstall the global UI assets.
3. Import levels:

```bash
python3 import_scp_to_scoresync.py --clean --overwrite
```

4. Run the server:

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

## Layout

```text
.
├── import_scp_to_scoresync.py
├── dev_scripts/
│   ├── install_scoresync_assets_from_scp.py
│   └── repair_pjsk_from_nextrush.py
├── scoresync/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── overrides/
│   └── requirements.txt
├── to_import/
└── docs/
    └── SCORESYNC_PIPELINE.md
```

## Commands

Import levels from `to_import/`:

```bash
python3 import_scp_to_scoresync.py --clean --overwrite
```

Install UI assets from `to_import/reference.scp`:

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
- See [docs/SCORESYNC_PIPELINE.md](docs/SCORESYNC_PIPELINE.md) for details and limitations.
