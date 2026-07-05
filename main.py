import os
import random
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor
import markdown as markdown_lib
from markdown.extensions.toc import TocExtension
import resend

from typing import List, Dict
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, abort, request, jsonify
from markupsafe import Markup

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, JSON, DateTime
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
# app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')

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


@app.template_global()
def markdown_toc(text):
    """Returns the heading outline (level/id/name) for a Markdown field, used
    to build the blog post's 'In this post' sidebar nav as real anchor links."""
    if not text:
        return []
    converter = _markdown_converter()
    converter.convert(text)
    return converter.toc_tokens


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    # Every submission lands here regardless of whether the notification
    # email succeeds, so nothing sent through the form is ever silently
    # lost — this flag just tells you whether you should also expect an
    # email for a given row, or need to check the table directly.
    email_sent: Mapped[bool] = mapped_column(nullable=False, default=False)


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
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
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

    response = requests.get(f"{url}/languages", headers=headers)
    if response.status_code != 200:
        lang_data = {}
    else:
        lang_data = response.json()

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
        db.session.commit()

    return results_dict


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
    all_projects = db.session.execute(db.select(Project)).scalars().all()
    return render_template('projects.html', projects=all_projects)


@app.route('/projects/<slug>')
def project_detail(slug):
    all_projects = db.session.execute(db.select(Project)).scalars().all()
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


@app.route('/blog')
def blog():
    posts = db.session.execute(db.select(BlogPost)).scalars().all()
    return render_template('blog.html', posts=posts)


@app.route('/blog/<slug>')
def blog_post(slug):
    post = db.session.execute(db.select(BlogPost).where(BlogPost.slug == slug)).scalar()
    if post is None:
        abort(404)

    prev_post = db.session.execute(db.select(BlogPost).where(BlogPost.order_index == post.order_index - 1)).scalar()
    next_post = db.session.execute(db.select(BlogPost).where(BlogPost.order_index == post.order_index + 1)).scalar()

    return render_template('blog-post.html', post=post, prev_post=prev_post, next_post=next_post)


def send_contact_email(name, email, message):
    """Sends a notification email via Resend's official Python SDK. Returns
    True/False — never raises, so a Resend outage or bad API key can't take
    down the /contact route or lose a message that's already been saved to
    the DB."""
    if not RESEND_API_KEY or not CONTACT_FROM_EMAIL:
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


if __name__ == '__main__':
    app.run(debug=True)
