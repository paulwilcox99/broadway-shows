#!/usr/bin/env python3
"""
Generate a static website from the shows database.
Only regenerates if the database has changed since last run.
"""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html import escape

# Configuration
DB_PATH = "shows.db"
OUTPUT_DIR = "site"
STATE_FILE = ".site_state.json"


def get_db_hash(db_path):
    """Get hash of database file to detect changes."""
    with open(db_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def load_state():
    """Load previous generation state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save generation state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def parse_json_field(value):
    """Parse a JSON field, returning empty list if invalid."""
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
        return [result]
    except:
        return [value] if value else []


def slugify(text):
    """Convert text to URL-safe slug."""
    if not text:
        return "unknown"
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:50]


def get_all_shows(db_path):
    """Fetch all shows from database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shows ORDER BY show_name")
    shows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for show in shows:
        show['lead_cast_list'] = parse_json_field(show['lead_cast'])
        show['tony_awards_list'] = parse_json_field(show['tony_awards'])
        show['other_awards_list'] = parse_json_field(show['other_awards'])
        show['musical_numbers_list'] = parse_json_field(show['musical_numbers'])
        show['themes_list'] = parse_json_field(show['themes'])
        show['user_categories_list'] = parse_json_field(show['user_categories'])
        show['llm_categories_list'] = parse_json_field(show['llm_categories'])

    return shows


# HTML Templates
def html_header(title, breadcrumbs=None, home_link="index.html"):
    """Generate HTML header."""
    bc_html = ""
    if breadcrumbs:
        bc_parts = [f'<a href="{home_link}">Home</a>']
        for name, link in breadcrumbs:
            if link:
                bc_parts.append(f'<a href="{link}">{escape(name)}</a>')
            else:
                bc_parts.append(escape(name))
        bc_html = f'<nav class="breadcrumbs">{" → ".join(bc_parts)}</nav>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} - Broadway Shows</title>
    <style>
        :root {{
            --bg: #f5f5fa;
            --bg-card: #ffffff;
            --text: #1a1a2e;
            --text-muted: #6b6b7c;
            --accent: #c41e3a;
            --accent-hover: #9a0f26;
            --link: #0f4c81;
            --link-hover: #082e4f;
            --border: #d4d4dc;
            --border-light: #e8e8ef;
            --genre-musical: #ffeaa7;
            --genre-play: #dfe6e9;
            --genre-revival: #81ecec;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        a {{ color: var(--link); text-decoration: none; }}
        a:hover {{ color: var(--link-hover); text-decoration: underline; }}
        h1 {{
            color: var(--text);
            margin-bottom: 1.5rem;
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            border-bottom: 3px solid var(--accent);
            padding-bottom: 0.75rem;
        }}
        h2 {{
            color: var(--text);
            margin: 2rem 0 1rem;
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        h3 {{ color: var(--text); margin: 1.25rem 0 0.75rem; font-size: 1.2rem; font-weight: 600; }}
        .breadcrumbs {{ margin-bottom: 2rem; color: var(--text-muted); font-size: 0.9rem; }}
        .breadcrumbs a {{ color: var(--link); }}
        .card {{
            background: var(--bg-card);
            padding: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        .show-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .show-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .show-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(196,30,58,0.1); }}
        .show-card h3 {{ margin: 0 0 0.5rem; font-size: 1.1rem; font-weight: 700; }}
        .show-card h3 a {{ text-decoration: none; color: var(--text); }}
        .show-card h3 a:hover {{ color: var(--accent); }}
        .show-card .theater {{ color: var(--text-muted); font-size: 0.95rem; margin-bottom: 0.75rem; }}
        .show-card .meta {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 0.75rem; }}
        .rating {{ color: var(--accent); font-weight: 600; }}
        .status {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            border-radius: 4px;
        }}
        .status.seen {{ background: #d4edda; color: #155724; }}
        .status.wishlist {{ background: #fff3cd; color: #856404; }}
        .genre-badge {{
            display: inline-block;
            background: var(--genre-musical);
            color: var(--text);
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            margin-right: 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        .genre-badge.play {{ background: var(--genre-play); }}
        .genre-badge.revival {{ background: var(--genre-revival); }}
        .tag {{
            display: inline-block;
            background: var(--bg);
            color: var(--text-muted);
            padding: 0.3rem 0.8rem;
            font-size: 0.85rem;
            margin: 0.25rem;
            border: 1px solid var(--border);
            border-radius: 4px;
            text-decoration: none;
        }}
        .tag:hover {{ background: var(--accent); color: white; border-color: var(--accent); text-decoration: none; }}
        .nav-sections {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .nav-section {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
        }}
        .nav-section h3 {{ margin-bottom: 1rem; color: var(--accent); font-size: 1rem; font-weight: 700; }}
        .nav-section ul {{ list-style: none; }}
        .nav-section li {{ margin: 0.5rem 0; font-size: 0.95rem; }}
        .nav-section a {{ text-decoration: none; }}
        .nav-section a:hover {{ text-decoration: underline; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .stat {{
            background: var(--bg-card);
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--border-light);
            border-radius: 8px;
        }}
        .stat-value {{ font-size: 2.5rem; color: var(--accent); font-weight: 700; }}
        .stat-label {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem; }}
        .timeline-year {{
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 2px solid var(--border-light);
        }}
        .timeline-year h2 {{
            color: var(--accent);
            font-size: 2rem;
            margin-bottom: 1.5rem;
            border: none;
        }}
        .timeline-month {{ margin-bottom: 2rem; }}
        .timeline-month h3 {{
            color: var(--text-muted);
            font-size: 1.2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        dl {{ margin: 1.25rem 0; }}
        dt {{ color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem; text-transform: uppercase; letter-spacing: 0.03em; font-weight: 600; }}
        dd {{ margin-left: 0; margin-top: 0.5rem; }}
        .cast-list {{ margin-left: 1rem; }}
        .cast-member {{ margin: 0.5rem 0; }}
    </style>
</head>
<body>
{bc_html}
<h1>{escape(title)}</h1>
'''


def html_footer():
    """Generate HTML footer."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f'''
<footer style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center;">
    Generated on {timestamp}
</footer>
</body>
</html>
'''


def generate_show_page(show, output_dir):
    """Generate individual show page."""
    slug = f"show-{show['id']}-{slugify(show['show_name'])}"
    filepath = os.path.join(output_dir, "shows", f"{slug}.html")

    html = html_header(show['show_name'], [("Shows", "../shows.html"), (show['show_name'], None)], home_link="../index.html")

    html += '<div class="card">'
    html += f'<p class="theater" style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 1rem;">📍 {escape(show["theater_name"])}</p>'

    # Status and rating
    html += '<p style="margin: 1rem 0;">'
    status_class = show['seen_status']
    status_text = "Seen" if status_class == "seen" else "Wishlist"
    html += f'<span class="status {status_class}">{status_text}</span>'

    if show['genre']:
        genre_class = "play" if "Play" in show['genre'] else ("revival" if "Revival" in show['genre'] else "musical")
        html += f' <span class="genre-badge {genre_class}">{escape(show["genre"])}</span>'

    if show['rating']:
        html += f' <span class="rating">{"★" * show["rating"]}{"☆" * (10 - show["rating"])}</span> {show["rating"]}/10'
    html += '</p>'

    html += '<dl>'

    if show['date_attended']:
        html += f'<dt>Date Attended</dt><dd>{escape(show["date_attended"])}</dd>'

    if show['opening_date']:
        html += f'<dt>Opening Date</dt><dd>{escape(show["opening_date"])}</dd>'

    if show['closing_date']:
        html += f'<dt>Closing/Closed</dt><dd>{escape(show["closing_date"])}</dd>'

    if show['production_type']:
        html += f'<dt>Production Type</dt><dd>{escape(show["production_type"])}</dd>'

    if show['running_time']:
        html += f'<dt>Running Time</dt><dd>{show["running_time"]} minutes</dd>'

    html += '</dl>'

    if show['plot_summary']:
        html += f'<h2>Plot Summary</h2><p>{escape(show["plot_summary"])}</p>'

    # Cast & Creative Team
    if show['lead_cast_list'] or show['director'] or show['choreographer']:
        html += '<h2>Cast & Creative Team</h2>'

        if show['director']:
            html += f'<p><strong>Director:</strong> {escape(show["director"])}</p>'
        if show['choreographer']:
            html += f'<p><strong>Choreographer:</strong> {escape(show["choreographer"])}</p>'
        if show['composer']:
            html += f'<p><strong>Composer:</strong> {escape(show["composer"])}</p>'
        if show['lyricist']:
            html += f'<p><strong>Lyricist:</strong> {escape(show["lyricist"])}</p>'
        if show['book_writer']:
            html += f'<p><strong>Book:</strong> {escape(show["book_writer"])}</p>'

        if show['lead_cast_list']:
            html += '<h3>Lead Cast</h3><div class="cast-list">'
            for cast in show['lead_cast_list']:
                if isinstance(cast, dict):
                    role = cast.get('role', 'Unknown')
                    actor = cast.get('actor', 'Unknown')
                    html += f'<div class="cast-member"><strong>{escape(role)}:</strong> {escape(actor)}</div>'
            html += '</div>'

    if show['tony_awards_list'] or show['other_awards_list']:
        html += '<h2>Awards</h2>'
        if show['tony_awards_list']:
            html += '<h3>Tony Awards</h3><ul>'
            for award in show['tony_awards_list']:
                html += f'<li>{escape(str(award))}</li>'
            html += '</ul>'
        if show['other_awards_list']:
            html += '<h3>Other Awards</h3><ul>'
            for award in show['other_awards_list']:
                html += f'<li>{escape(str(award))}</li>'
            html += '</ul>'

    if show['themes_list']:
        html += '<h2>Themes</h2><p>'
        for theme in show['themes_list']:
            html += f'<span class="tag">{escape(str(theme))}</span>'
        html += '</p>'

    if show['user_categories_list']:
        html += '<h2>Categories</h2><p>'
        for cat in show['user_categories_list']:
            cat_slug = slugify(str(cat))
            html += f'<a href="../categories/{cat_slug}.html" class="tag">{escape(str(cat))}</a>'
        html += '</p>'

    if show['personal_notes']:
        html += f'<h2>Personal Notes</h2><p>{escape(show["personal_notes"])}</p>'

    html += f'<p style="margin-top: 1.5rem; font-size: 0.85rem; color: var(--text-muted);">Added: {show["date_added"][:10]}</p>'

    html += '</div>'
    html += html_footer()

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(html)

    return slug


def generate_list_page(title, items, output_path, breadcrumbs, intro=""):
    """Generate a list page (theaters, genres, categories index)."""
    html = html_header(title, breadcrumbs)

    if intro:
        html += f'<p style="margin-bottom: 1.5rem; color: var(--text-muted);">{intro}</p>'

    html += '<ul style="list-style: none; columns: 2; column-gap: 2rem;">'
    for name, link, count in sorted(items, key=lambda x: x[0].lower()):
        html += f'<li style="margin: 0.5rem 0;"><a href="{link}">{escape(name)}</a> <span style="color: var(--text-muted);">({count})</span></li>'
    html += '</ul>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_group_page(title, shows, output_path, breadcrumbs, home_link="index.html"):
    """Generate a page showing a group of shows."""
    html = html_header(title, breadcrumbs, home_link=home_link)

    html += f'<p style="margin-bottom: 1.5rem; color: var(--text-muted);">{len(shows)} show(s)</p>'

    html += '<div class="show-grid">'
    for show in sorted(shows, key=lambda s: s['show_name'].lower()):
        slug = f"show-{show['id']}-{slugify(show['show_name'])}"

        html += f'''<div class="show-card">
            <h3><a href="../shows/{slug}.html">{escape(show['show_name'])}</a></h3>
            <p class="theater">📍 {escape(show['theater_name'])}</p>
            <p class="meta">'''

        status_class = show['seen_status']
        status_text = "Seen" if status_class == "seen" else "Wishlist"
        html += f'<span class="status {status_class}">{status_text}</span>'

        if show['rating']:
            html += f' <span class="rating">{"★" * show["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_theater_page(theater_name, theater_shows, output_path, breadcrumbs, home_link="index.html"):
    """Generate enhanced theater page with statistics."""
    html = html_header(theater_name, breadcrumbs, home_link=home_link)

    seen_shows = [s for s in theater_shows if s['seen_status'] == 'seen']
    rated_shows = [s for s in seen_shows if s['rating']]
    avg_rating = sum(s['rating'] for s in rated_shows) / len(rated_shows) if rated_shows else 0

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(theater_shows)}</div><div class="stat-label">Total Shows</div></div>
        <div class="stat"><div class="stat-value">{len(seen_shows)}</div><div class="stat-label">Seen</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
    </div>'''

    html += '<div class="show-grid">'
    for show in sorted(theater_shows, key=lambda s: s.get('date_attended') or '9999', reverse=True):
        slug = f"show-{show['id']}-{slugify(show['show_name'])}"

        html += f'''<div class="show-card">
            <h3><a href="../shows/{slug}.html">{escape(show['show_name'])}</a></h3>'''

        if show['date_attended']:
            html += f'<p class="theater">📅 {escape(show["date_attended"])}</p>'

        html += '<p class="meta">'

        status_class = show['seen_status']
        status_text = "Seen" if status_class == "seen" else "Wishlist"
        html += f'<span class="status {status_class}">{status_text}</span>'

        if show['rating']:
            html += f' <span class="rating">{"★" * show["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    with open(output_path, 'w') as f:
        f.write(html)


def generate_timeline(shows, output_dir):
    """Generate timeline view grouped by year and month."""
    html = html_header("Timeline", [("Timeline", None)])

    # Separate seen shows with dates from wishlist
    seen_shows = [s for s in shows if s['seen_status'] == 'seen' and s['date_attended']]
    wishlist_shows = [s for s in shows if s['seen_status'] == 'wishlist']

    # Group by year and month
    timeline = defaultdict(lambda: defaultdict(list))
    for show in seen_shows:
        try:
            date = datetime.fromisoformat(show['date_attended'])
            year = date.year
            month = date.strftime('%B')  # Full month name
            timeline[year][month].append(show)
        except:
            pass

    # Wishlist section
    if wishlist_shows:
        html += '<div class="timeline-year">'
        html += '<h2>📌 Upcoming / Wishlist</h2>'
        html += '<div class="show-grid">'
        for show in sorted(wishlist_shows, key=lambda s: s['show_name'].lower()):
            slug = f"show-{show['id']}-{slugify(show['show_name'])}"
            html += f'''<div class="show-card">
                <h3><a href="shows/{slug}.html">{escape(show['show_name'])}</a></h3>
                <p class="theater">📍 {escape(show['theater_name'])}</p>
            </div>'''
        html += '</div></div>'

    # Year sections (most recent first)
    for year in sorted(timeline.keys(), reverse=True):
        html += f'<div class="timeline-year"><h2>{year}</h2>'

        # Month sections within year
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']

        for month in month_order:
            if month not in timeline[year]:
                continue

            month_shows = timeline[year][month]
            html += f'<div class="timeline-month"><h3>{month}</h3>'
            html += '<div class="show-grid">'

            for show in sorted(month_shows, key=lambda s: s['date_attended'], reverse=True):
                slug = f"show-{show['id']}-{slugify(show['show_name'])}"
                html += f'''<div class="show-card">
                    <h3><a href="shows/{slug}.html">{escape(show['show_name'])}</a></h3>
                    <p class="theater">📍 {escape(show['theater_name'])}</p>'''

                if show['date_attended']:
                    html += f'<p class="theater">📅 {escape(show["date_attended"])}</p>'

                html += '<p class="meta">'
                if show['rating']:
                    html += f'<span class="rating">{"★" * show["rating"]}</span> {show["rating"]}/10'
                html += '</p></div>'

            html += '</div></div>'

        html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "timeline.html"), 'w') as f:
        f.write(html)


def generate_shows_index(shows, output_dir):
    """Generate all shows index page."""
    html = html_header("All Shows", [("All Shows", None)])

    seen_count = sum(1 for s in shows if s['seen_status'] == 'seen')
    wishlist_count = len(shows) - seen_count

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(shows)}</div><div class="stat-label">Total Shows</div></div>
        <div class="stat"><div class="stat-value">{seen_count}</div><div class="stat-label">Seen</div></div>
        <div class="stat"><div class="stat-value">{wishlist_count}</div><div class="stat-label">Wishlist</div></div>
    </div>'''

    html += '<div class="show-grid">'
    for show in sorted(shows, key=lambda s: s['show_name'].lower()):
        slug = f"show-{show['id']}-{slugify(show['show_name'])}"

        html += f'''<div class="show-card">
            <h3><a href="shows/{slug}.html">{escape(show['show_name'])}</a></h3>
            <p class="theater">📍 {escape(show['theater_name'])}</p>
            <p class="meta">'''

        status_class = show['seen_status']
        status_text = "Seen" if status_class == "seen" else "Wishlist"
        html += f'<span class="status {status_class}">{status_text}</span>'

        if show['rating']:
            html += f' <span class="rating">{"★" * show["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "shows.html"), 'w') as f:
        f.write(html)


def generate_index(shows, theaters_count, genres_count, categories_count, output_dir):
    """Generate main index page with statistics dashboard."""
    html = html_header("Broadway Shows Collection")

    seen_shows = [s for s in shows if s['seen_status'] == 'seen']
    wishlist_shows = [s for s in shows if s['seen_status'] == 'wishlist']
    rated_shows = [s for s in seen_shows if s['rating']]
    avg_rating = sum(s['rating'] for s in rated_shows) / len(rated_shows) if rated_shows else 0

    # Calculate shows per year
    years_with_shows = set()
    for show in seen_shows:
        if show['date_attended']:
            try:
                year = datetime.fromisoformat(show['date_attended']).year
                years_with_shows.add(year)
            except:
                pass
    shows_per_year = len(seen_shows) / len(years_with_shows) if years_with_shows else 0

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(shows)}</div><div class="stat-label">Total Shows</div></div>
        <div class="stat"><div class="stat-value">{len(seen_shows)}</div><div class="stat-label">Seen</div></div>
        <div class="stat"><div class="stat-value">{len(wishlist_shows)}</div><div class="stat-label">Wishlist</div></div>
        <div class="stat"><div class="stat-value">{theaters_count}</div><div class="stat-label">Theaters</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
        <div class="stat"><div class="stat-value">{shows_per_year:.1f}</div><div class="stat-label">Shows/Year</div></div>
    </div>'''

    html += '<div class="nav-sections">'

    html += f'''<div class="nav-section">
        <h3>🎭 Browse</h3>
        <ul>
            <li><a href="shows.html">All Shows ({len(shows)})</a></li>
            <li><a href="timeline.html">Timeline View</a></li>
            <li><a href="theaters.html">By Theater ({theaters_count})</a></li>
            <li><a href="genres.html">By Genre ({genres_count})</a></li>
            <li><a href="categories.html">By Category ({categories_count})</a></li>
        </ul>
    </div>'''

    # Recently added
    recent = sorted(shows, key=lambda s: s['date_added'], reverse=True)[:5]
    html += '<div class="nav-section"><h3>🕐 Recently Added</h3><ul>'
    for show in recent:
        slug = f"show-{show['id']}-{slugify(show['show_name'])}"
        html += f'<li><a href="shows/{slug}.html">{escape(show["show_name"])}</a></li>'
    html += '</ul></div>'

    # Top rated
    top_rated = sorted(rated_shows, key=lambda s: s['rating'], reverse=True)[:5]
    if top_rated:
        html += '<div class="nav-section"><h3>⭐ Top Rated</h3><ul>'
        for show in top_rated:
            slug = f"show-{show['id']}-{slugify(show['show_name'])}"
            html += f'<li><a href="shows/{slug}.html">{escape(show["show_name"])}</a> ({show["rating"]}/10)</li>'
        html += '</ul></div>'

    # Wishlist
    if wishlist_shows:
        html += '<div class="nav-section"><h3>📌 Wishlist</h3><ul>'
        for show in wishlist_shows[:5]:
            slug = f"show-{show['id']}-{slugify(show['show_name'])}"
            html += f'<li><a href="shows/{slug}.html">{escape(show["show_name"])}</a></li>'
        html += '</ul></div>'

    html += '</div>'
    html += html_footer()

    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(html)


def generate_site(force=False):
    """Generate the complete static site."""
    # Check if regeneration needed
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False

    current_hash = get_db_hash(DB_PATH)
    state = load_state()

    if not force and state.get('db_hash') == current_hash:
        print("Database unchanged. Use --force to regenerate anyway.")
        return True

    print("Generating site...")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "shows"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "theaters"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "genres"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "categories"), exist_ok=True)

    # Get all shows
    shows = get_all_shows(DB_PATH)
    print(f"Found {len(shows)} shows")

    # Generate individual show pages
    for show in shows:
        generate_show_page(show, OUTPUT_DIR)
    print(f"Generated {len(shows)} show pages")

    # Build indexes
    theaters_index = defaultdict(list)
    genres_index = defaultdict(list)
    categories_index = defaultdict(list)

    for show in shows:
        if show['theater_name']:
            theaters_index[show['theater_name']].append(show)
        if show['genre']:
            genres_index[show['genre']].append(show)
        for cat in show['user_categories_list']:
            if cat:
                categories_index[cat].append(show)

    # Generate theater pages (enhanced)
    theater_items = []
    for theater, theater_shows in theaters_index.items():
        slug = slugify(theater)
        filepath = os.path.join(OUTPUT_DIR, "theaters", f"{slug}.html")
        generate_theater_page(theater, theater_shows, filepath, [("Theaters", "../theaters.html"), (theater, None)], home_link="../index.html")
        theater_items.append((theater, f"theaters/{slug}.html", len(theater_shows)))

    generate_list_page("Theaters", theater_items,
                      os.path.join(OUTPUT_DIR, "theaters.html"),
                      [("Theaters", None)],
                      f"{len(theaters_index)} theaters visited")
    print(f"Generated {len(theaters_index)} theater pages")

    # Generate genre pages
    genre_items = []
    for genre, genre_shows in genres_index.items():
        slug = slugify(genre)
        filepath = os.path.join(OUTPUT_DIR, "genres", f"{slug}.html")
        generate_group_page(genre, genre_shows, filepath, [("Genres", "../genres.html"), (genre, None)], home_link="../index.html")
        genre_items.append((genre, f"genres/{slug}.html", len(genre_shows)))

    generate_list_page("Genres", genre_items,
                      os.path.join(OUTPUT_DIR, "genres.html"),
                      [("Genres", None)],
                      f"{len(genres_index)} genres")
    print(f"Generated {len(genres_index)} genre pages")

    # Generate category pages
    category_items = []
    for cat, cat_shows in categories_index.items():
        slug = slugify(cat)
        filepath = os.path.join(OUTPUT_DIR, "categories", f"{slug}.html")
        generate_group_page(cat, cat_shows, filepath, [("Categories", "../categories.html"), (cat, None)], home_link="../index.html")
        category_items.append((cat, f"categories/{slug}.html", len(cat_shows)))

    generate_list_page("Categories", category_items,
                      os.path.join(OUTPUT_DIR, "categories.html"),
                      [("Categories", None)],
                      f"{len(categories_index)} categories")
    print(f"Generated {len(categories_index)} category pages")

    # Generate timeline view
    generate_timeline(shows, OUTPUT_DIR)
    print("Generated timeline view")

    # Generate all shows page
    generate_shows_index(shows, OUTPUT_DIR)

    # Generate main index
    generate_index(shows, len(theaters_index), len(genres_index), len(categories_index), OUTPUT_DIR)

    # Save state
    save_state({'db_hash': current_hash, 'generated_at': datetime.now().isoformat()})

    print(f"\n✓ Site generated in '{OUTPUT_DIR}/'")
    print(f"  Open {OUTPUT_DIR}/index.html to view")

    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    success = generate_site(force=force)
    sys.exit(0 if success else 1)
