from routes.auth import register_auth_routes
from routes.music import register_music_routes
from routes.notifications import register_notification_routes
from routes.pages import register_page_routes
from routes.playlists import register_playlist_routes


def register_routes(app):
    register_page_routes(app)
    register_auth_routes(app)
    register_playlist_routes(app)
    register_music_routes(app)
    register_notification_routes(app)
