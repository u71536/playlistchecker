from datetime import datetime, timedelta

from flask import flash, redirect, render_template, url_for
from flask_babel import gettext
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from extensions import db, monitor
from forms import CsrfForm, DeletePlaylistForm, PlaylistForm
from models import Notification, NotificationHistory, Playlist, Track
from routes.music import redirect_spotify_reauthorization
from services.spotify_service import (
    SpotifyReauthorizationRequired,
    SpotifyService,
    TokenExpiredError,
)


@login_required
def playlists():
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template(
        'playlists.html',
        playlists=user_playlists,
        delete_form=DeletePlaylistForm(),
    )


@login_required
def add_playlist():
    form = PlaylistForm()
    if form.validate_on_submit():
        try:
            playlist = monitor.add_playlist(
                user=current_user,
                service=form.service.data,
                playlist_url=form.playlist_url.data,
            )
            flash(gettext('flash.playlist_added_success', playlist_name=playlist.name))
            return redirect(url_for('playlists'))
        except SpotifyReauthorizationRequired:
            return redirect_spotify_reauthorization()
        except ValueError as error:
            flash(gettext('flash.error_generic', error=str(error)), 'error')
        except IntegrityError:
            db.session.rollback()
            flash(gettext('flash.playlist_already_added'), 'error')
        except Exception as error:
            flash(gettext('flash.error_adding_playlist', error=str(error)), 'error')
    return render_template('add_playlist.html', form=form)


@login_required
def spotify_playlists():
    """Получить все плейлисты пользователя из Spotify"""
    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash(gettext('flash.connect_spotify_first'))
        return redirect(url_for('index'))

    try:
        service = SpotifyService()
        new_token_info = service.check_and_refresh_token(
            spotify_token.access_token,
            spotify_token.refresh_token,
            spotify_token.expires_at,
        )
        if new_token_info:
            spotify_token.access_token = new_token_info['access_token']
            if 'refresh_token' in new_token_info:
                spotify_token.refresh_token = new_token_info['refresh_token']
            spotify_token.expires_at = datetime.utcnow() + timedelta(
                seconds=new_token_info['expires_in']
            )
            db.session.commit()
            flash(gettext('flash.spotify_token_updated'), 'info')

        user_playlists = service.get_user_playlists(
            spotify_token.access_token, spotify_token.refresh_token
        )
        return render_template('spotify_playlists.html', playlists=user_playlists)
    except SpotifyReauthorizationRequired:
        return redirect_spotify_reauthorization()
    except TokenExpiredError as error:
        if error.new_token_info:
            spotify_token.access_token = error.new_token_info['access_token']
            if 'refresh_token' in error.new_token_info:
                spotify_token.refresh_token = error.new_token_info['refresh_token']
            spotify_token.expires_at = datetime.utcnow() + timedelta(
                seconds=error.new_token_info['expires_in']
            )
            db.session.commit()
            try:
                user_playlists = service.get_user_playlists(
                    spotify_token.access_token, spotify_token.refresh_token
                )
                flash(gettext('flash.spotify_token_updated'), 'info')
                return render_template('spotify_playlists.html', playlists=user_playlists)
            except SpotifyReauthorizationRequired:
                return redirect_spotify_reauthorization()
            except Exception as retry_error:
                flash(gettext(
                    'flash.error_getting_playlists_after_token_update',
                    error=str(retry_error),
                ))
                return redirect(url_for('index'))
        flash(gettext('flash.error_getting_playlists', error=str(error)))
        return redirect(url_for('index'))
    except Exception as error:
        flash(gettext('flash.error_getting_playlists', error=str(error)))
        return redirect(url_for('index'))


@login_required
def add_spotify_playlist(playlist_id):
    form = CsrfForm()
    if not form.validate_on_submit():
        flash(gettext('flash.invalid_form'))
        return redirect(url_for('spotify_playlists'))

    spotify_token = current_user.spotify_tokens[0] if current_user.spotify_tokens else None
    if not spotify_token:
        flash(gettext('flash.connect_spotify_first'))
        return redirect(url_for('index'))

    try:
        playlist_url = f'https://open.spotify.com/playlist/{playlist_id}'
        playlist = monitor.add_playlist(
            user=current_user,
            service='spotify',
            playlist_url=playlist_url,
        )
        flash(gettext('flash.playlist_added_success', playlist_name=playlist.name))
        return redirect(url_for('playlists'))
    except SpotifyReauthorizationRequired:
        return redirect_spotify_reauthorization()
    except ValueError as error:
        flash(gettext('flash.error_generic', error=str(error)))
    except Exception as error:
        flash(gettext('flash.error_generic_short', error=str(error)))

    return redirect(url_for('spotify_playlists'))


@login_required
def check_playlists_now():
    """Принудительная проверка плейлистов"""
    form = CsrfForm()
    if not form.validate_on_submit():
        flash(gettext('flash.invalid_form'))
        return redirect(url_for('playlists'))
    try:
        monitor.check_user_playlists(current_user)
        flash(gettext('flash.playlists_checked'))
    except SpotifyReauthorizationRequired:
        return redirect_spotify_reauthorization()
    except Exception as error:
        flash(gettext('flash.error_checking_playlists', error=str(error)))
    return redirect(url_for('playlists'))


@login_required
def playlist_tracks(playlist_id):
    """Показать треки плейлиста"""
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
    if not playlist:
        flash(gettext('flash.playlist_not_found'))
        return redirect(url_for('playlists'))

    tracks = Track.query.filter_by(playlist_id=playlist_id).order_by(Track.added_at.desc()).all()
    return render_template('playlist_tracks.html', playlist=playlist, tracks=tracks)


@login_required
def delete_playlist(playlist_id):
    """Удалить плейлист из мониторинга вместе с треками и уведомлениями."""
    form = DeletePlaylistForm()
    if not form.validate_on_submit():
        flash(gettext('flash.invalid_form'))
        return redirect(url_for('playlists'))

    playlist = Playlist.query.filter_by(
        id=playlist_id,
        user_id=current_user.id,
    ).first()
    if not playlist:
        flash(gettext('flash.playlist_not_found'))
        return redirect(url_for('playlists'))

    Notification.query.filter_by(playlist_id=playlist.id).delete(synchronize_session=False)
    NotificationHistory.query.filter_by(playlist_id=playlist.id).delete(synchronize_session=False)
    db.session.delete(playlist)
    db.session.commit()
    flash(gettext('flash.playlist_deleted'))
    return redirect(url_for('playlists'))


def register_playlist_routes(app):
    app.add_url_rule('/playlists', view_func=playlists)
    app.add_url_rule('/add_playlist', view_func=add_playlist, methods=['GET', 'POST'])
    app.add_url_rule('/spotify_playlists', view_func=spotify_playlists)
    app.add_url_rule(
        '/add_spotify_playlist/<playlist_id>',
        view_func=add_spotify_playlist,
        methods=['POST'],
    )
    app.add_url_rule('/check_playlists_now', view_func=check_playlists_now, methods=['POST'])
    app.add_url_rule('/playlist/<int:playlist_id>/tracks', view_func=playlist_tracks)
    app.add_url_rule(
        '/playlist/<int:playlist_id>/delete',
        view_func=delete_playlist,
        methods=['POST'],
    )
