from . import homepage, level_details, levels, playlists, repository

routers = [
    repository.router,
    homepage.router,
    playlists.router,
    levels.router,
    level_details.router,
]
