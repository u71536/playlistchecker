from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from services.check_schedule import TIMEZONES


class LoginForm(FlaskForm):
    username = StringField(lazy_gettext('login.username'), validators=[DataRequired()])
    password = PasswordField(lazy_gettext('login.password'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('base.login'))


class RegisterForm(FlaskForm):
    username = StringField(lazy_gettext('login.username'), validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField(
        lazy_gettext('login.password'),
        validators=[DataRequired(), Length(min=8, message=lazy_gettext('form.password_min_length'))],
    )
    submit = SubmitField(lazy_gettext('form.register'))


class PlaylistForm(FlaskForm):
    service = SelectField(lazy_gettext('form.service'), choices=[
        ('spotify', 'Spotify'),
        ('deezer', 'Deezer'),
        ('apple_music', 'Apple Music'),
        ('yandex_music', 'Yandex Music')
    ], validators=[DataRequired()])
    playlist_url = StringField(lazy_gettext('form.playlist_url'), validators=[DataRequired()])
    submit = SubmitField(lazy_gettext('add_playlist.add_playlist'))


class NotificationSettingsForm(FlaskForm):
    """Форма настроек уведомлений"""
    email_notifications_enabled = BooleanField(lazy_gettext('notification_settings.email_notifications'))
    telegram_notifications_enabled = BooleanField(lazy_gettext('notification_settings.telegram_notifications'))
    browser_notifications_enabled = BooleanField(lazy_gettext('notification_settings.browser_notifications'))
    check_hour = SelectField(
        lazy_gettext('notification_settings.check_hour'),
        choices=[(hour, f'{hour:02d}:00') for hour in range(24)],
        coerce=int,
        validators=[DataRequired()],
    )
    timezone = SelectField(
        lazy_gettext('notification_settings.timezone'),
        choices=list(TIMEZONES),
        validators=[DataRequired()],
    )
    submit = SubmitField(lazy_gettext('form.save_settings'))


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField(lazy_gettext('form.send'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        lazy_gettext('login.password'),
        validators=[DataRequired(), Length(min=8, message=lazy_gettext('form.password_min_length'))],
    )
    submit = SubmitField(lazy_gettext('form.save'))


class CsrfForm(FlaskForm):
    pass


class DeletePlaylistForm(FlaskForm):
    submit = SubmitField(lazy_gettext('playlists.delete'))
