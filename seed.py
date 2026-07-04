"""
Populates project_table and blog_post_table with the portfolio's content.

Run with:
    python seed.py

Safe to re-run: existing rows (matched by slug) are updated in place rather
than duplicated, so you can edit the .md files under raw_data/ and just
re-run this whenever a write-up changes.

Content fields (why/how/results/code for projects, body for posts) are
stored as Markdown, not HTML. main.py's `| markdown` Jinja filter renders it
at request time via python-markdown. Standard Markdown passes raw HTML
blocks straight through untouched, so a pasted embed (e.g. a Plotly chart
export) can be dropped directly into a Markdown field — see
raw_data/projects/ontario-energy-mix.md's "## Results" section for a live
example.

Real content lives as individual .md files with YAML frontmatter under
raw_data/projects/ and raw_data/blogs/ (filename = slug). raw_data/demo/
holds documented example files showing the expected structure — it is never
scanned here, so it can't accidentally get seeded as real content.

Project-level GitHub stats (url, git_path, live, tags, languages,
primary_language, stars, forks) are populated by get_projects_github_data()
at seed time — see main.py.
"""
import re

from main import app, db, Project, BlogPost, get_projects_github_data

from pathlib import Path
import frontmatter


PROJECTS_DIR = Path("raw_data/projects")
BLOG_DIR = Path("raw_data/blogs")

# Controls DB insert order, since folder.glob() has no guaranteed order of
# its own. This order is what home()/projects() in main.py slice from (top 4
# projects / top 3 posts on the home page) and what project_detail()'s
# "other projects" sidebar picks from -- so it's not just cosmetic.
PROJECT_ORDER = [
    "ontario-energy-mix",
    "energy-audit-dashboard",
    "hvac-efficiency-classifier",
    "enerquery",
    "sql-energy-queries",
]

BLOG_ORDER = [
    "pandas-groupby-energy-reports",
    "cleaning-energy-audit-exports",
    "blower-door-to-box-plots",
    "first-sql-database-audit-records",
]


def load_blog_post(path):
    blog = frontmatter.load(path)
    post_dict = blog.metadata
    post_dict['body'] = blog.content
    post_dict['slug'] = Path(path).stem
    return post_dict


def load_project(path):
    project = frontmatter.load(path)
    project_dict = project.metadata
    project_dict['slug'] = Path(path).stem
    content = project.content
    content_list = re.split(r'(^## .+$)', content, flags=re.MULTILINE)

    accepted_keys = ['why', 'how', 'results', 'code']
    for i, c in enumerate(content_list):
        if re.findall(r'^## (.+)$', c):
            dict_key = re.findall(r'^## (.+)$', c)[0].lower().strip()
            if dict_key not in accepted_keys:
                file_name = Path(path).name
                raise ValueError(f"The project file {file_name} has an unexpected heading {dict_key}.\n"
                                 f"Please check the demo_project.md file located in raw_data/demo directory "
                                 f"for the correct structure.")
            dict_value = content_list[i + 1].strip()
            project_dict[dict_key] = dict_value
        else:
            pass

    return project_dict


def _load_folder(folder: Path, order: list[str], loader) -> list[dict]:
    """Loads every .md file in `folder` with `loader`, then returns them
    ordered according to `order` (by slug). Any file present but missing
    from `order` is still seeded -- just appended after the explicitly
    ordered ones, so a new .md file you forget to add to PROJECT_ORDER/
    BLOG_ORDER doesn't silently vanish, it just sorts last."""
    by_slug = {}
    for md_file in sorted(folder.glob("*.md")):
        entry = loader(md_file)
        by_slug[entry["slug"]] = entry

    ordered = [by_slug[slug] for slug in order if slug in by_slug]
    leftover = [entry for slug, entry in by_slug.items() if slug not in order]
    return ordered + leftover


def seed():
    with app.app_context():
        projects_seed = _load_folder(PROJECTS_DIR, PROJECT_ORDER, load_project)
        blog_seed = _load_folder(BLOG_DIR, BLOG_ORDER, load_blog_post)

        # Safety net: an empty folder almost certainly means raw_data/ isn't
        # populated yet (or got misconfigured), not "delete everything in
        # the DB". Skip orphan-deletion in that case rather than silently
        # wiping every existing row.
        safe_to_prune_projects = len(projects_seed) > 0
        safe_to_prune_posts = len(blog_seed) > 0
        if not safe_to_prune_projects:
            print(f"Warning: no .md files found in {PROJECTS_DIR} -- skipping project deletion.")
        if not safe_to_prune_posts:
            print(f"Warning: no .md files found in {BLOG_DIR} -- skipping post deletion.")

        project_slugs = [project['slug'] for project in projects_seed]
        git_call = get_projects_github_data(project_slugs)
        for entry in projects_seed:
            # Updating the entry with git_call
            git_call_entry = git_call[entry['slug']]
            key_to_add = git_call[entry['slug']].keys()
            for key in key_to_add:
                entry[key] = git_call_entry[key]

            existing = db.session.get(Project, entry["slug"])
            if existing:
                for key, value in entry.items():
                    setattr(existing, key, value)
                print(f"Updated project: {entry['slug']}")
            else:
                db.session.add(Project(**entry))
                print(f"Inserted project: {entry['slug']}")

        for entry in blog_seed:
            existing = db.session.get(BlogPost, entry["slug"])
            if existing:
                for key, value in entry.items():
                    setattr(existing, key, value)
                print(f"Updated post: {entry['slug']}")
            else:
                db.session.add(BlogPost(**entry))
                print(f"Inserted post: {entry['slug']}")

        if safe_to_prune_projects:
            seen_project_slugs = {entry["slug"] for entry in projects_seed}
            for project in db.session.execute(db.select(Project)).scalars().all():
                if project.slug not in seen_project_slugs:
                    db.session.delete(project)
                    print(f"Deleted orphaned project (no matching .md file): {project.slug}")

        if safe_to_prune_posts:
            seen_blog_slugs = {entry["slug"] for entry in blog_seed}
            for post in db.session.execute(db.select(BlogPost)).scalars().all():
                if post.slug not in seen_blog_slugs:
                    db.session.delete(post)
                    print(f"Deleted orphaned post (no matching .md file): {post.slug}")

        db.session.commit()
        print(f"Done — {len(projects_seed)} project(s), {len(blog_seed)} post(s) seeded.")


if __name__ == "__main__":
    seed()
