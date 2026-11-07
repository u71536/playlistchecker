from datetime import datetime

from flask import Response, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from extensions import db
from models import Notification, Playlist


def index():
    if current_user.is_authenticated:
        playlists = Playlist.query.filter_by(user_id=current_user.id).all()
        notifications = Notification.query.filter_by(
            user_id=current_user.id, is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        return render_template('dashboard.html', playlists=playlists, notifications=notifications)
    return render_template('index.html')


def about():
    """Страница о сервисе"""
    return render_template('about.html')


def why_check():
    """Перенаправление на страницу о сервисе"""
    return redirect(url_for('about'))


def health():
    """Проверка, что процесс жив и база отвечает."""
    try:
        db.session.execute(text('SELECT 1'))
    except Exception:
        return jsonify({'status': 'error'}), 503
    return jsonify({'status': 'ok'})


def sitemap():
    """Sitemap для поисковых систем с поддержкой двух языков"""
    base_url = request.url_root.rstrip('/')
    lastmod = datetime.now().strftime('%Y-%m-%d')
    pages = [
        {'path': '', 'changefreq': 'daily', 'priority': '1.0'},
        {'path': 'about', 'changefreq': 'weekly', 'priority': '0.8'},
        {'path': 'login', 'changefreq': 'monthly', 'priority': '0.6'},
        {'path': 'register', 'changefreq': 'monthly', 'priority': '0.6'},
    ]

    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    sitemap_content += 'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    for page in pages:
        url_path = page['path']
        page_url = f'{base_url}/{url_path}' if url_path else base_url
        sitemap_content += '    <url>\n'
        sitemap_content += f'        <loc>{page_url}</loc>\n'
        sitemap_content += f'        <lastmod>{lastmod}</lastmod>\n'
        sitemap_content += f'        <changefreq>{page["changefreq"]}</changefreq>\n'
        sitemap_content += f'        <priority>{page["priority"]}</priority>\n'
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="ru" href="{page_url}?lang=ru" />\n'
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="en" href="{page_url}?lang=en" />\n'
        sitemap_content += f'        <xhtml:link rel="alternate" hreflang="x-default" href="{page_url}" />\n'
        sitemap_content += '    </url>\n'
    sitemap_content += '</urlset>'
    return Response(sitemap_content, mimetype='application/xml')


def robots_txt():
    """Robots.txt для поисковых систем"""
    base_url = request.url_root.rstrip('/')
    robots_content = f'''User-agent: *
Allow: /

# Sitemap
Sitemap: {base_url}/sitemap.xml

# Disallow private areas
Disallow: /instance/
Disallow: /migrations/
Disallow: /__pycache__/
Disallow: /services/__pycache__/
Disallow: /api/

# Allow important pages
Allow: /
Allow: /about
Allow: /login
Allow: /register
Allow: /sitemap.xml
Allow: /robots.txt'''
    return Response(robots_content, mimetype='text/plain')


def register_page_routes(app):
    app.add_url_rule('/', view_func=index)
    app.add_url_rule('/about', view_func=about)
    app.add_url_rule('/why-check', view_func=why_check)
    app.add_url_rule('/health', view_func=health)
    app.add_url_rule('/sitemap.xml', view_func=sitemap)
    app.add_url_rule('/robots.txt', view_func=robots_txt)
