import secrets
from datetime import datetime, timedelta

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_babel import gettext
from flask_login import current_user, login_required

from extensions import db
from forms import CsrfForm
from models import AppleMusicToken, DeezerToken, SpotifyToken, YandexMusicToken
from services.apple_music_service import AppleMusicService
from services.spotify_service import SpotifyService


def redirect_spotify_reauthorization():
    """Discard stored Spotify tokens and send the user through sign-in again."""
    SpotifyToken.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    db.session.expire(current_user, ['spotify_tokens'])
    flash(gettext('flash.spotify_reauthorization_required'))
    return redirect(url_for('spotify_auth'))


@login_required
def spotify_auth():
    """Начать авторизацию Spotify"""
    service = SpotifyService()
    state = secrets.token_urlsafe(32)
    session['spotify_oauth_state'] = state
    return redirect(service.get_auth_url(state=state))


@login_required
def spotify_callback():
    """Обработка callback от Spotify"""
    expected_state = session.pop('spotify_oauth_state', None)
    state = request.args.get('state') or ''
    if (
        not expected_state
        or not state
        or not secrets.compare_digest(state, expected_state)
    ):
        flash(gettext('flash.spotify_auth_invalid_state'))
        return redirect(url_for('index'))

    code = request.args.get('code')
    if not code:
        flash(gettext('flash.spotify_auth_error_no_code'))
        return redirect(url_for('index'))

    try:
        service = SpotifyService()
        token_info = service.get_access_token(code)
        expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
        SpotifyToken.query.filter_by(user_id=current_user.id).delete()
        db.session.add(SpotifyToken(
            user_id=current_user.id,
            access_token=token_info['access_token'],
            refresh_token=token_info['refresh_token'],
            expires_at=expires_at,
        ))
        db.session.commit()
        flash(gettext('flash.spotify_connected_success'))
        return redirect(url_for('index'))
    except Exception as error:
        flash(gettext('flash.spotify_auth_error', error=str(error)))
        return redirect(url_for('index'))


@login_required
def deezer_auth():
    flash(gettext('flash.public_playlist_no_auth'))
    return redirect(url_for('add_playlist'))


@login_required
def get_apple_music_developer_token():
    """Получить Developer Token для Apple Music"""
    try:
        service = AppleMusicService()
        token = service.get_developer_token()
        return jsonify({'token': token})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@login_required
def save_apple_music_user_token():
    """Сохранить User Token для Apple Music"""
    data = request.json
    user_token = data.get('user_token')
    expires_at_str = data.get('expires_at')
    if not user_token:
        return jsonify({'error': 'User token required'}), 400

    try:
        service = AppleMusicService()
        if not service.is_token_valid(user_token):
            return jsonify({'error': 'Invalid user token'}), 400
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        else:
            expires_at = datetime.utcnow() + timedelta(days=180)
        AppleMusicToken.query.filter_by(user_id=current_user.id).delete()
        db.session.add(AppleMusicToken(
            user_id=current_user.id,
            access_token=user_token,
            expires_at=expires_at,
        ))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as error:
        db.session.rollback()
        return jsonify({'error': str(error)}), 500


@login_required
def apple_music_auth():
    """Авторизация Apple Music через MusicKit JS"""
    return render_template('apple_music_auth.html')


@login_required
def yandex_music_auth():
    flash(gettext('flash.public_playlist_no_auth'))
    return redirect(url_for('add_playlist'))


@login_required
def disconnect_service(service):
    """Отвязать токен музыкального сервиса."""
    form = CsrfForm()
    if not form.validate_on_submit():
        flash(gettext('flash.invalid_form'))
        return redirect(url_for('index'))
    token_models = {
        'spotify': SpotifyToken,
        'deezer': DeezerToken,
        'apple_music': AppleMusicToken,
        'yandex_music': YandexMusicToken,
    }
    model = token_models.get(service)
    if model is None:
        flash(gettext('flash.playlist_not_found'))
        return redirect(url_for('index'))
    model.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash(gettext('flash.service_disconnected'))
    return redirect(url_for('index'))


def register_music_routes(app):
    app.add_url_rule('/auth/spotify', view_func=spotify_auth)
    app.add_url_rule('/auth/spotify/callback', view_func=spotify_callback)
    app.add_url_rule('/auth/deezer', view_func=deezer_auth)
    app.add_url_rule('/api/apple_music/developer_token', view_func=get_apple_music_developer_token)
    app.add_url_rule(
        '/api/apple_music/user_token',
        view_func=save_apple_music_user_token,
        methods=['POST'],
    )
    app.add_url_rule('/auth/apple_music', view_func=apple_music_auth)
    app.add_url_rule('/auth/yandex_music', view_func=yandex_music_auth)
    app.add_url_rule('/auth/<service>/disconnect', view_func=disconnect_service, methods=['POST'])
