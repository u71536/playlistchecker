import logging
import secrets
from datetime import datetime, timedelta

import jwt
from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_babel import gettext
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, limiter
from forms import CsrfForm, ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from models import User
from services.notification_service import notification_service

logger = logging.getLogger(__name__)


def _send_email_verification(user):
    """Отправить одноразовую ссылку подтверждения почты."""
    user.email_verify_nonce = secrets.token_hex(16)
    db.session.commit()
    token = jwt.encode({
        'sub': str(user.id),
        'exp': datetime.utcnow() + timedelta(days=2),
        'type': 'email_verify',
        'nonce': user.email_verify_nonce,
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    verify_url = url_for('verify_email', token=token, _external=True)
    subject = 'Подтверждение email'
    message = (
        f'Подтвердите email для PlaylistChecker: {verify_url}\n\n'
        'Ссылка действительна 2 дня.'
    )
    sent = notification_service.send_plain_email(user.email, subject, message)
    if not sent:
        logger.info('[EmailVerify] Ссылка: %s', verify_url)


@limiter.limit('5 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.email_verified:
                _send_email_verification(user)
                flash(gettext('flash.email_not_verified'))
                return render_template('login.html', form=form)
            login_user(user)
            return redirect(url_for('index'))
        flash(gettext('login.invalid_username_or_password'))
    return render_template('login.html', form=form)


def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash(gettext('flash.user_exists_username'))
            return render_template('register.html', form=form)

        if User.query.filter_by(email=form.email.data).first():
            flash(gettext('flash.user_exists_email'))
            return render_template('register.html', form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            email_verified=False,
        )
        db.session.add(user)
        db.session.commit()
        _send_email_verification(user)

        flash(gettext('flash.registration_check_email'))
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@login_required
def logout():
    form = CsrfForm()
    if not form.validate_on_submit():
        flash(gettext('flash.invalid_form'))
        return redirect(url_for('index'))
    logout_user()
    return redirect(url_for('index'))


def verify_email(token):
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        if data.get('type') != 'email_verify':
            raise jwt.InvalidTokenError('invalid type')
        user = db.session.get(User, int(data.get('sub')))
        nonce = data.get('nonce') or ''
        if (
            not user
            or not user.email_verify_nonce
            or not secrets.compare_digest(user.email_verify_nonce, nonce)
        ):
            raise jwt.InvalidTokenError('user not found')
    except Exception:
        flash(gettext('flash.email_verify_invalid'))
        return redirect(url_for('login'))
    user.email_verified = True
    user.email_verify_nonce = None
    db.session.commit()
    flash(gettext('flash.email_verified'))
    return redirect(url_for('login'))


@limiter.limit('3 per minute', methods=['POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        try:
            if user:
                user.password_reset_nonce = secrets.token_hex(16)
                db.session.commit()
                payload = {
                    'sub': str(user.id),
                    'exp': datetime.utcnow() + timedelta(hours=1),
                    'type': 'password_reset',
                    'nonce': user.password_reset_nonce,
                }
                token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
                reset_url = url_for('reset_password', token=token, _external=True)
                try:
                    subject = 'Восстановление пароля'
                    message = (
                        f'Чтобы сбросить пароль, перейдите по ссылке: {reset_url}\n\n'
                        'Ссылка действительна 1 час.'
                    )
                    sent = notification_service.send_email_notification(user.email, subject, message)
                    if not sent:
                        logger.info(
                            '[PasswordReset] Ссылка: %s (email не отправлен, проверьте SMTP настройки)',
                            reset_url,
                        )
                except Exception as error:
                    logger.error('[PasswordReset] Ошибка отправки письма: %s', error)
                    logger.info('[PasswordReset] Ссылка: %s', reset_url)
        finally:
            flash(gettext('flash.password_reset_email_sent'))
            return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)


@limiter.limit('5 per minute', methods=['POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        if data.get('type') != 'password_reset':
            raise jwt.InvalidTokenError('invalid type')
        user = db.session.get(User, int(data.get('sub')))
        nonce = data.get('nonce') or ''
        if (
            not user
            or not user.password_reset_nonce
            or not nonce
            or not secrets.compare_digest(user.password_reset_nonce, nonce)
        ):
            raise jwt.InvalidTokenError('user not found')
    except Exception:
        flash(gettext('flash.password_reset_invalid'))
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.password_reset_nonce = None
        db.session.commit()
        flash(gettext('flash.password_updated'))
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)


def clear_session():
    """Очистить сессию от старых Firestore данных"""
    session.clear()
    return redirect(url_for('index'))


def set_language(language=None):
    """Установить язык интерфейса"""
    if language not in current_app.config['LANGUAGES']:
        return redirect(request.referrer or url_for('index'))

    session['language'] = language
    if current_user.is_authenticated:
        current_user.language = language
        db.session.commit()

    return redirect(request.referrer or url_for('index'))


def register_auth_routes(app):
    app.add_url_rule('/login', view_func=login, methods=['GET', 'POST'])
    app.add_url_rule('/register', view_func=register, methods=['GET', 'POST'])
    app.add_url_rule('/logout', view_func=logout, methods=['POST'])
    app.add_url_rule('/verify_email/<token>', view_func=verify_email)
    app.add_url_rule('/forgot_password', view_func=forgot_password, methods=['GET', 'POST'])
    app.add_url_rule('/reset_password/<token>', view_func=reset_password, methods=['GET', 'POST'])
    app.add_url_rule('/clear_session', view_func=clear_session)
    app.add_url_rule('/set_language/<language>', view_func=set_language)
