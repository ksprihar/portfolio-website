import os
import random
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import pyotp
import markdown as markdown_lib
from markdown.extensions.toc import TocExtension
import resend

from typing import List, Dict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, abort, request, jsonify, redirect, url_for, session
from markupsafe import Markup
from werkzeug.security import check_password_hash

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, JSON, DateTime, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from lang_colors import get_lang_color

GIT_USERNAME = 'ksprihar'
GIT_API = 'https://api.github.com/repos'
GIT_TOKEN = os.getenv('GIT_TOKEN')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
# Falls back to Resend's shared sandbox sender until you verify your own
# domain — once that's done, just set CONTACT_FROM_EMAIL in .env (e.g.
# "contact@ksprihar.com") and it'll switch over with no code changes.
CONTACT_FROM_EMAIL = os.getenv('CONTACT_FROM_EMAIL', 'onboarding@resend.dev')
CONTACT_TO_EMAIL = os.getenv('CONTACT_TO_EMAIL')

# Admin auth — a werkzeug password hash + a TOTP secret for Microsoft/Google
# Authenticator. Both the password and a valid 6-digit code are required to
# log in. See setup notes for how to generate these two .env values.
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')
ADMIN_TOTP_SECRET = os.getenv('ADMIN_TOTP_SECRET')

# Basic structural check (something@something.tld) — not full RFC 5322, just
# enough to reject obvious typos/junk. Mirrors the check in main.js; this
# server-side copy exists because the client-side one can be bypassed (the
# contact <form> uses novalidate, so the browser's own type="email" check no
# longer runs either).
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Base(DeclarativeBase):
    pass


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')

db = SQLAlchemy(app, model_class=Base)


def _markdown_converter():
    # A fresh converter per call — cheap, and avoids any shared-state issues
    # from reusing one Markdown() instance across requests. TocExtension
    # slugs every heading with an id, so blog post headings become anchor
    # targets for the sidebar "In this post" nav.
    return markdown_lib.Markdown(extensions=['fenced_code', 'tables', TocExtension(anchorlink=False)])


@app.template_filter('markdown')
def render_markdown(text):
    """Renders a Markdown-formatted DB field to HTML. Raw HTML blocks (e.g. a
    pasted Plotly chart embed) pass through untouched, since that's standard
    CommonMark behaviour. Content here is always self-authored, so trusting
    the raw-HTML passthrough is fine — same trust model as |safe, just no
    longer needed for every plain paragraph/list."""
    if not text:
        return ""
    return Markup(_markdown_converter().convert(text))


class Project(db.Model):
    __tablename__ = 'project_table'
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String, primary_key=True)
    tagline: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    about: Mapped[str] = mapped_column(String, nullable=False)
    why: Mapped[str] = mapped_column(String, nullable=False)
    how: Mapped[str] = mapped_column(String, nullable=False)
    results: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    stack: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    git_path: Mapped[str] = mapped_column(String, nullable=False)
    live: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    languages: Mapped[Dict] = mapped_column(JSON, nullable=True)
    primary_language: Mapped[str] = mapped_column(String, nullable=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    forks: Mapped[int] = mapped_column(Integer, nullable=False)

class BlogPost(db.Model):
    __tablename__ = 'blog_post_table'
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    date_display: Mapped[str] = mapped_column(String, nullable=False)
    read_time: Mapped[str] = mapped_column(String, nullable=False)
    excerpt: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)

class ContactMessage(db.Model):
    __tablename__ = 'contact_message_table'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    # Stored as Toronto local wall-clock time (naive, tzinfo stripped before
    # save — SQLite has no real timezone-aware column type, so this mirrors
    # the previous UTC convention but with America/Toronto clock values
    # instead). Handles EST/EDT automatically via zoneinfo.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.now(ZoneInfo("America/Toronto")).replace(tzinfo=None)
    )
    # Every submission lands here regardless of whether the notification
    # email succeeds, so nothing sent through the form is ever silently
    # lost — this flag just tells you whether you should also expect an
    # email for a given row, or need to check the table directly.
    email_sent: Mapped[bool] = mapped_column(nullable=False, default=False)
    # Triage state for the admin inbox — 'new' until you've acted on it.
    status: Mapped[str] = mapped_column(String, nullable=False, default='new')
    # Free-text internal note, never shown to the sender — for your own
    # triage/context, e.g. "already handled this one over LinkedIn".
    comment: Mapped[str] = mapped_column(String, nullable=True)
    starred: Mapped[bool] = mapped_column(nullable=False, default=False)


with app.app_context():
    db.create_all()


# Simple in-memory cache for per-project GitHub API data (repo info +
# languages). Listing pages (home, /projects) now render a card per project,
# and each card needs the same live stats the detail page shows — without a
# cache that's N sequential GitHub API calls on every single page load. A
# short TTL keeps stats fresh-ish while avoiding hitting the API on every
# visit. This is process-local (resets on restart), which is fine for a
# single-instance personal site.
_GITHUB_CACHE_TTL = 600  # seconds
_github_cache = {}


def get_project_github_data(slug):
    """Fetches (or returns cached) GitHub repo + language stats for a project
    slug. Returns a dict with url, git_path, live, tags, languages,
    primary_language, stars, forks."""
    now = time.time()
    cached = _github_cache.get(slug)
    if cached and now - cached[0] < _GITHUB_CACHE_TTL:
        return cached[1]

    url = f"{GIT_API}/{GIT_USERNAME}/{slug}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GIT_TOKEN}",
    }
    # timeout so a hung GitHub call can't block a request worker forever —
    # on timeout requests raises, which we treat the same as a bad status.
    try:
        response = requests.get(url, headers=headers, timeout=5)
        status = response.status_code
    except requests.RequestException:
        status = None
    if status != 200:
        data = {
            'description': '',
            'html_url': '',
            'homepage': '',
            'topics': [],
            'stargazers_count': 0,
            'forks_count': 0,
        }
    else:
        data = response.json()

    try:
        response = requests.get(f"{url}/languages", headers=headers, timeout=5)
        lang_data = response.json() if response.status_code == 200 else {}
    except requests.RequestException:
        lang_data = {}

    github_data = {
        'about': data['description'],
        'url': data['html_url'],
        'git_path': data['html_url'].replace('https://', '').replace('http://', ''),
        'live': data['homepage'],
        'tags': data['topics'],
        'languages': {language: get_lang_color(language) for language in lang_data.keys()},
        'primary_language': next(iter(lang_data.keys()), None),
        'stars': data['stargazers_count'],
        'forks': data['forks_count'],
    }
    _github_cache[slug] = (now, github_data)

    return github_data


def get_projects_github_data(slugs):
    """Same data as get_project_github_data, but for a list of slugs, fetched
    concurrently instead of one-after-another. Each project still needs its
    own 2 GitHub requests (repo info + languages), so on a cold cache this
    turns N sequential round-trips (~N x latency) into all of them happening
    at once (~1x latency) — the fix for the slow first-load on the home and
    /projects pages. Cache-hit slugs resolve instantly either way; the pool
    only matters for the ones that actually need to hit the network."""
    if not slugs:
        return {}
    with ThreadPoolExecutor(max_workers=len(slugs)) as executor:
        results = executor.map(get_project_github_data, slugs)

    results_dict = dict(zip(slugs, results))
    for slug, values in results_dict.items():
        existing = db.session.execute(db.select(Project).where(Project.slug == slug)).scalar()
        if existing:
            existing.forks = values['forks']
            existing.stars = values['stars']
    # One commit for the whole batch — committing inside the loop meant one
    # transaction per slug for what is logically a single update.
    db.session.commit()

    return results_dict


@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 in the site's own style — covers both unknown URLs and
    abort(404) from the detail routes (bad project/blog slug)."""
    return render_template('404.html'), 404


@app.route('/')
def home():
    projects = db.session.execute(db.select(Project).order_by(Project.order_index).limit(4)).scalars().all()
    posts = db.session.execute(db.select(BlogPost).order_by(BlogPost.order_index).limit(3)).scalars().all()
    return render_template('index.html', projects=projects, posts=posts)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/projects')
def projects():
    all_projects = db.session.execute(db.select(Project).order_by(Project.order_index)).scalars().all()
    return render_template('projects.html', projects=all_projects)


@app.route('/projects/<slug>')
def project_detail(slug):
    all_projects = db.session.execute(db.select(Project).order_by(Project.order_index)).scalars().all()
    project = db.session.execute(db.select(Project).where(Project.slug == slug)).scalar()
    if project is None:
        abort(404)

    indexes = [0 if project.order_index != 0 else 1]
    while len(indexes) < min(3, len(all_projects) - 1):
        new_index = random.randint(0, len(all_projects) - 1)
        if new_index not in indexes and new_index != project.order_index:
            indexes.append(new_index)

    other_projects = [project for project in all_projects if project.order_index in indexes]

    return render_template('project-detail.html', project=project, other_projects=other_projects)


@app.route('/api/project-stats')
def project_stats():
    """Background-refresh endpoint for stars/forks — pages render these
    fields straight from the DB (fast, no live API call on page load), then
    main.js calls this shortly after load to quietly check GitHub for
    anything newer and animate the number in place if it changed. Only
    accepts slugs that already exist in the DB, so this can't be used to
    make the server hit GitHub for arbitrary/junk repo names."""
    requested_slugs = [s for s in request.args.get('slugs', '').split(',') if s]
    if not requested_slugs:
        return jsonify({})

    known_slugs = {
        row[0] for row in db.session.execute(
            db.select(Project.slug).where(Project.slug.in_(requested_slugs))
        ).all()
    }
    slugs = [s for s in requested_slugs if s in known_slugs]
    if not slugs:
        return jsonify({})

    data = get_projects_github_data(slugs)
    return jsonify({slug: {'stars': values['stars'], 'forks': values['forks']} for slug, values in data.items()})


@app.route('/blog')
def blog():
    posts = db.session.execute(db.select(BlogPost).order_by(BlogPost.order_index)).scalars().all()
    return render_template('blog.html', posts=posts)


@app.route('/blog/<slug>')
def blog_post(slug):
    post = db.session.execute(db.select(BlogPost).where(BlogPost.slug == slug)).scalar()
    if post is None:
        abort(404)

    prev_post = db.session.execute(db.select(BlogPost).where(BlogPost.order_index == post.order_index - 1)).scalar()
    next_post = db.session.execute(db.select(BlogPost).where(BlogPost.order_index == post.order_index + 1)).scalar()

    # Convert the body once and reuse the same converter's toc_tokens for
    # the sidebar — previously the template ran `post.body | markdown` AND
    # markdown_toc(post.body), converting the whole post twice per request.
    converter = _markdown_converter()
    body_html = Markup(converter.convert(post.body))

    return render_template('blog-post.html', post=post, body_html=body_html,
                           toc=converter.toc_tokens, prev_post=prev_post, next_post=next_post)


def send_contact_email(name, email, message):
    """Sends a notification email via Resend's official Python SDK. Returns
    True/False — never raises, so a Resend outage or bad API key can't take
    down the /contact route or lose a message that's already been saved to
    the DB."""
    if not RESEND_API_KEY or not CONTACT_FROM_EMAIL or not CONTACT_TO_EMAIL:
        return False
    resend.api_key = RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": f"Portfolio contact form <{CONTACT_FROM_EMAIL}>",
            "to": [CONTACT_TO_EMAIL],
            "reply_to": email,
            "subject": f"New portfolio message from {name}",
            "text": f"From: {name} <{email}>\n\n{message}",
        })
        return True
    except Exception as e:
        print(e)
        return False


# In-memory per-IP rate limit for the contact form — same pattern as the
# GitHub cache above (process-local dict, fine for a single-instance
# personal site). Caps abuse from a single source without needing a DB
# table or an external store.
_CONTACT_RATE_LIMIT = 3      # max submissions...
_CONTACT_RATE_WINDOW = 600   # ...per this many seconds, per IP
_contact_submissions = {}


def _is_rate_limited(ip):
    now = time.time()
    recent = [t for t in _contact_submissions.get(ip, []) if now - t < _CONTACT_RATE_WINDOW]
    _contact_submissions[ip] = recent
    return len(recent) >= _CONTACT_RATE_LIMIT


@app.route('/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    message = (data.get('message') or '').strip()

    # Honeypot — a hidden field real visitors never see or fill. Bots that
    # blindly fill every input on the form will fill this one. Respond with
    # a fake success (not an error) so the bot has no signal it was caught,
    # and skip saving/emailing entirely.
    if (data.get('company') or '').strip():
        return jsonify({"success": True})

    if not name or not email or not message:
        return jsonify({"success": False, "error": "Please fill in all fields."}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400

    ip = (request.headers.get('X-Forwarded-For', request.remote_addr) or '').split(',')[0].strip()
    if _is_rate_limited(ip):
        return jsonify({"success": False, "error": "Too many messages sent recently. Please try again in a bit."}), 429
    _contact_submissions.setdefault(ip, []).append(time.time())

    # Save first — the message is never lost even if the email send below fails.
    contact_msg = ContactMessage(name=name, email=email, message=message)
    db.session.add(contact_msg)
    db.session.commit()

    contact_msg.email_sent = send_contact_email(name, email, message)
    db.session.commit()

    return jsonify({"success": True})


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        code = request.form.get('code', '').strip()
        valid_password = bool(ADMIN_PASSWORD_HASH) and check_password_hash(ADMIN_PASSWORD_HASH, password)
        valid_code = bool(ADMIN_TOTP_SECRET) and pyotp.TOTP(ADMIN_TOTP_SECRET).verify(code)
        if valid_password and valid_code:
            session['is_admin'] = True
            return redirect(request.args.get('next') or url_for('admin_home'))
        error = "Incorrect password or code."
    return render_template('admin-login.html', error=error)


@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))


@app.route('/admin')
@admin_required
def admin_home():
    return render_template('admin.html')


def _messages_redirect(form):
    """Redirects back to the filtered admin_messages view a per-message
    action form was submitted from, using the hidden status/starred/q
    fields every such form carries — so changing a status, star, or
    comment doesn't kick you out of whatever filtered/searched view you
    were looking at."""
    params = {k: v for k, v in {
        'status': form.get('status_filter', ''),
        'starred': form.get('starred_filter', ''),
        'q': form.get('q', ''),
    }.items() if v}
    return redirect(url_for('admin_messages', **params))


@app.route('/admin/messages')
@admin_required
def admin_messages():
    status_filter = request.args.get('status', '').strip()
    starred_filter = request.args.get('starred', '').strip()
    query_text = request.args.get('q', '').strip()

    stmt = db.select(ContactMessage)
    if status_filter in ('new', 'responded', 'resolved'):
        stmt = stmt.where(ContactMessage.status == status_filter)
    if starred_filter == '1':
        stmt = stmt.where(ContactMessage.starred.is_(True))
    if query_text:
        like = f"%{query_text}%"
        stmt = stmt.where(or_(
            ContactMessage.name.ilike(like),
            ContactMessage.email.ilike(like),
            ContactMessage.message.ilike(like),
        ))
    stmt = stmt.order_by(ContactMessage.created_at.desc())
    messages = db.session.execute(stmt).scalars().all()

    return render_template('admin-messages.html', messages=messages,
                            status_filter=status_filter, starred_filter=starred_filter,
                            query_text=query_text)


@app.route('/admin/messages/<int:message_id>/status', methods=['POST'])
@admin_required
def admin_message_status(message_id):
    msg = db.session.get(ContactMessage, message_id)
    if msg is None:
        abort(404)
    new_status = request.form.get('status')
    if new_status in ('new', 'responded', 'resolved'):
        msg.status = new_status
        db.session.commit()
    return _messages_redirect(request.form)


@app.route('/admin/messages/<int:message_id>/star', methods=['POST'])
@admin_required
def admin_message_star(message_id):
    msg = db.session.get(ContactMessage, message_id)
    if msg is None:
        abort(404)
    msg.starred = not msg.starred
    db.session.commit()
    return _messages_redirect(request.form)


@app.route('/admin/messages/<int:message_id>/comment', methods=['POST'])
@admin_required
def admin_message_comment(message_id):
    msg = db.session.get(ContactMessage, message_id)
    if msg is None:
        abort(404)
    msg.comment = (request.form.get('comment') or '').strip() or None
    db.session.commit()
    return _messages_redirect(request.form)


if __name__ == '__main__':
    app.run(debug=True)
