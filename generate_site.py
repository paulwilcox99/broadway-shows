#!/usr/bin/env python3
"""
Generate a single-page application for the Broadway shows database.
Outputs: index.html + data.json
"""

import os
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "shows.db"
OUTPUT_DIR = "site"


def parse_json_field(value):
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [result]
    except:
        return [value] if value else []


def get_all_shows(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shows ORDER BY show_name")
    shows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for show in shows:
        show['cast_list'] = parse_json_field(show.get('notable_cast'))
        show['awards_list'] = parse_json_field(show.get('awards'))
        show['songs_list'] = parse_json_field(show.get('famous_songs'))
    
    return shows


def generate_data_json(shows):
    data = {
        'shows': [],
        'stats': {
            'total': len(shows),
            'seen': sum(1 for s in shows if s.get('seen_status') == 'seen'),
            'wishlist': sum(1 for s in shows if s.get('seen_status') == 'wishlist'),
        },
        'theaters': defaultdict(list),
        'types': defaultdict(list),
        'years': defaultdict(list),
    }
    
    ratings = [s['rating'] for s in shows if s.get('rating') and s.get('seen_status') == 'seen']
    data['stats']['avg_rating'] = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    for show in shows:
        show_data = {
            'id': show['id'],
            'name': show['show_name'],
            'theater': show.get('theater_name') or '',
            'status': show.get('seen_status') or 'wishlist',
            'date_attended': show.get('date_attended') or '',
            'rating': show.get('rating'),
            'date_added': show['date_added'][:10] if show.get('date_added') else '',
            'type': show.get('show_type') or '',
            'music_by': show.get('music_by') or '',
            'lyrics_by': show.get('lyrics_by') or '',
            'book_by': show.get('book_by') or '',
            'premiere_year': show.get('original_premiere_year'),
            'synopsis': show.get('synopsis') or '',
            'cast': show['cast_list'],
            'awards': show['awards_list'],
            'songs': show['songs_list'],
            'notes': show.get('personal_notes') or '',
        }
        data['shows'].append(show_data)
        
        if show.get('theater_name'):
            if show['id'] not in data['theaters'][show['theater_name']]:
                data['theaters'][show['theater_name']].append(show['id'])
        
        if show.get('show_type'):
            if show['id'] not in data['types'][show['show_type']]:
                data['types'][show['show_type']].append(show['id'])
        
        if show.get('date_attended'):
            try:
                year = show['date_attended'][:4]
                if show['id'] not in data['years'][year]:
                    data['years'][year].append(show['id'])
            except:
                pass
    
    data['stats']['theater_count'] = len(data['theaters'])
    
    data['theaters'] = dict(data['theaters'])
    data['types'] = dict(data['types'])
    data['years'] = dict(data['years'])
    
    return data


def generate_html():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paul's Broadway</title>
    <style>
        :root {
            --bg: #ffffff;
            --bg-card: #f8f9fa;
            --text: #2c3e50;
            --text-muted: #7f8c8d;
            --accent: #c41e3a;
            --accent-hover: #a01830;
            --border: #e0e0e0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Georgia, serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        .back-link {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
        }
        .back-link a { color: var(--text-muted); text-decoration: none; }
        .back-link a:hover { color: var(--accent); }
        h1 { color: var(--accent); font-size: 2.5rem; font-weight: normal; text-align: center; margin-bottom: 0.5rem; }
        .subtitle { text-align: center; color: var(--text-muted); font-style: italic; margin-bottom: 2rem; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            background: var(--bg-card);
            padding: 1.25rem;
            text-align: center;
            border: 2px solid var(--border);
            border-radius: 8px;
        }
        .stat-value { font-size: 2rem; color: var(--accent); }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: -apple-system, sans-serif; }
        .nav-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid var(--border);
            padding-bottom: 1rem;
        }
        .nav-tab {
            padding: 0.5rem 1rem;
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 6px;
            cursor: pointer;
            font-family: -apple-system, sans-serif;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .nav-tab:hover, .nav-tab.active { background: var(--accent); color: white; border-color: var(--accent); }
        .search-box {
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-family: Georgia, serif;
        }
        .search-box:focus { outline: none; border-color: var(--accent); }
        .filter-section { margin-bottom: 2rem; }
        .filter-title { font-size: 1.1rem; margin-bottom: 1rem; color: var(--text); }
        .filter-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .filter-tag {
            padding: 0.4rem 0.8rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
            font-family: -apple-system, sans-serif;
            transition: all 0.2s;
        }
        .filter-tag:hover { border-color: var(--accent); color: var(--accent); }
        .filter-tag .count { color: var(--text-muted); margin-left: 0.3rem; }
        .show-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        .show-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .show-card:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(196,30,58,0.1); }
        .show-card h3 { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.5rem; font-family: -apple-system, sans-serif; }
        .show-card .theater { color: var(--text-muted); font-style: italic; font-size: 0.95rem; }
        .show-card .meta { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; font-family: -apple-system, sans-serif; }
        .show-card .rating { color: var(--accent); }
        .status { 
            display: inline-block;
            padding: 0.2rem 0.5rem;
            font-size: 0.7rem;
            text-transform: uppercase;
            border-radius: 4px;
            font-family: -apple-system, sans-serif;
        }
        .status.seen { background: #d4edda; color: #155724; }
        .status.wishlist { background: #fff3cd; color: #856404; }
        .type-badge { 
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            margin-top: 0.5rem;
            font-family: -apple-system, sans-serif;
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            overflow-y: auto;
            padding: 2rem;
        }
        .modal-overlay.active { display: block; }
        .modal {
            background: white;
            max-width: 700px;
            margin: 0 auto;
            border-radius: 12px;
            padding: 2rem;
            position: relative;
        }
        .modal-close {
            position: absolute;
            top: 1rem; right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }
        .modal-close:hover { color: var(--accent); }
        .modal h2 { color: var(--accent); margin-bottom: 0.5rem; font-weight: normal; }
        .modal .theater { font-style: italic; color: var(--text-muted); margin-bottom: 1rem; font-size: 1.1rem; }
        .modal .meta-row { margin: 1rem 0; }
        .modal .label { font-weight: 600; color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; font-family: -apple-system, sans-serif; }
        .modal .songs { background: var(--bg-card); padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .modal .songs ul { margin-left: 1.5rem; }
        .modal .songs li { margin: 0.3rem 0; }
        
        .results-count { color: var(--text-muted); margin-bottom: 1rem; font-family: -apple-system, sans-serif; }
        footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center; font-family: -apple-system, sans-serif; }
    </style>
</head>
<body>
    <div class="back-link"><a href="https://pauls-collections.vercel.app">← All Collections</a></div>
    <h1>Paul's Broadway</h1>
    <p class="subtitle">A personal theater collection</p>
    
    <div class="stats" id="stats"></div>
    
    <div class="nav-tabs">
        <button class="nav-tab active" data-view="all">All Shows</button>
        <button class="nav-tab" data-view="theaters">Theaters</button>
        <button class="nav-tab" data-view="types">Show Types</button>
        <button class="nav-tab" data-view="years">Years</button>
    </div>
    
    <input type="text" class="search-box" id="search" placeholder="Search shows, theaters, songs...">
    
    <div id="filters" class="filter-section" style="display:none;"></div>
    <div class="results-count" id="results-count"></div>
    <div class="show-grid" id="shows"></div>
    
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-content"></div>
        </div>
    </div>
    
    <footer>Generated <span id="timestamp"></span></footer>
    
    <script>
    let DATA = null;
    let currentView = 'all';
    let currentFilter = null;
    
    async function init() {
        const resp = await fetch('data.json');
        DATA = await resp.json();
        document.getElementById('timestamp').textContent = new Date().toLocaleDateString();
        renderStats();
        renderShows(DATA.shows);
        setupEventListeners();
    }
    
    function renderStats() {
        const s = DATA.stats;
        document.getElementById('stats').innerHTML = `
            <div class="stat"><div class="stat-value">${s.total}</div><div class="stat-label">Shows</div></div>
            <div class="stat"><div class="stat-value">${s.seen}</div><div class="stat-label">Seen</div></div>
            <div class="stat"><div class="stat-value">${s.wishlist}</div><div class="stat-label">Wishlist</div></div>
            <div class="stat"><div class="stat-value">${s.avg_rating || 'N/A'}</div><div class="stat-label">Avg Rating</div></div>
            <div class="stat"><div class="stat-value">${s.theater_count}</div><div class="stat-label">Theaters</div></div>
        `;
    }
    
    function renderShows(shows) {
        document.getElementById('results-count').textContent = `${shows.length} show${shows.length !== 1 ? 's' : ''}`;
        document.getElementById('shows').innerHTML = shows.map(s => `
            <div class="show-card" onclick="showShow(${s.id})">
                <h3>${esc(s.name)}</h3>
                <div class="theater">${esc(s.theater) || 'Unknown theater'}</div>
                <div class="meta">
                    <span class="status ${s.status}">${s.status === 'seen' ? 'Seen' : 'Wishlist'}</span>
                    ${s.date_attended ? ` • ${s.date_attended}` : ''}
                    ${s.rating ? ` • <span class="rating">${'★'.repeat(s.rating)}${'☆'.repeat(10-s.rating)}</span>` : ''}
                </div>
                ${s.type ? `<span class="type-badge">${esc(s.type)}</span>` : ''}
            </div>
        `).join('');
    }
    
    function renderFilters(type) {
        let items = [];
        if (type === 'theaters') items = Object.entries(DATA.theaters).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'types') items = Object.entries(DATA.types).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'years') items = Object.entries(DATA.years).map(([k,v]) => [k, v.length]).sort((a,b) => b[0].localeCompare(a[0]));
        
        if (items.length === 0) {
            document.getElementById('filters').style.display = 'none';
            return;
        }
        
        document.getElementById('filters').style.display = 'block';
        document.getElementById('filters').innerHTML = `
            <div class="filter-title">${type.charAt(0).toUpperCase() + type.slice(1)} (${items.length})</div>
            <div class="filter-tags">
                ${items.map(([name, count]) => `<span class="filter-tag" data-filter="${esc(name)}">${esc(name)}<span class="count">(${count})</span></span>`).join('')}
            </div>
        `;
    }
    
    function filterShows(type, value) {
        let ids = [];
        if (type === 'theaters') ids = DATA.theaters[value] || [];
        else if (type === 'types') ids = DATA.types[value] || [];
        else if (type === 'years') ids = DATA.years[value] || [];
        
        const shows = DATA.shows.filter(s => ids.includes(s.id));
        renderShows(shows);
    }
    
    function searchShows(query) {
        const q = query.toLowerCase();
        const shows = DATA.shows.filter(s => 
            s.name.toLowerCase().includes(q) ||
            (s.theater && s.theater.toLowerCase().includes(q)) ||
            s.songs.some(x => x.toLowerCase().includes(q)) ||
            (s.synopsis && s.synopsis.toLowerCase().includes(q))
        );
        renderShows(shows);
    }
    
    function showShow(id) {
        const s = DATA.shows.find(x => x.id === id);
        if (!s) return;
        
        document.getElementById('modal-content').innerHTML = `
            <h2>${esc(s.name)}</h2>
            <div class="theater">${esc(s.theater) || 'Unknown theater'}</div>
            <div class="meta-row">
                <span class="status ${s.status}">${s.status === 'seen' ? 'Seen' : 'Wishlist'}</span>
                ${s.type ? ` • <span class="type-badge">${esc(s.type)}</span>` : ''}
                ${s.date_attended ? ` • Attended: ${s.date_attended}` : ''}
                ${s.rating ? ` • <span class="rating">${'★'.repeat(s.rating)}${'☆'.repeat(10-s.rating)} ${s.rating}/10</span>` : ''}
            </div>
            ${s.premiere_year ? `<div class="meta-row"><span class="label">Premiere:</span> ${s.premiere_year}</div>` : ''}
            ${s.music_by ? `<div class="meta-row"><span class="label">Music:</span> ${esc(s.music_by)}</div>` : ''}
            ${s.lyrics_by ? `<div class="meta-row"><span class="label">Lyrics:</span> ${esc(s.lyrics_by)}</div>` : ''}
            ${s.book_by ? `<div class="meta-row"><span class="label">Book:</span> ${esc(s.book_by)}</div>` : ''}
            ${s.synopsis ? `<div class="meta-row"><span class="label">Synopsis</span><p>${esc(s.synopsis)}</p></div>` : ''}
            ${s.cast.length ? `<div class="meta-row"><span class="label">Notable Cast:</span> ${esc(s.cast.join(', '))}</div>` : ''}
            ${s.songs.length ? `<div class="meta-row"><span class="label">Famous Songs</span><div class="songs"><ul>${s.songs.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div></div>` : ''}
            ${s.awards.length ? `<div class="meta-row"><span class="label">Awards:</span> ${esc(s.awards.join(', '))}</div>` : ''}
            ${s.notes ? `<div class="meta-row"><span class="label">Notes:</span> ${esc(s.notes)}</div>` : ''}
            <div class="meta-row" style="color: var(--text-muted); font-size: 0.85rem;">Added: ${s.date_added}</div>
        `;
        document.getElementById('modal').classList.add('active');
    }
    
    function closeModal() {
        document.getElementById('modal').classList.remove('active');
    }
    
    function setupEventListeners() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentView = tab.dataset.view;
                currentFilter = null;
                document.getElementById('search').value = '';
                
                if (currentView === 'all') {
                    document.getElementById('filters').style.display = 'none';
                    renderShows(DATA.shows);
                } else {
                    renderFilters(currentView);
                    renderShows(DATA.shows);
                }
            });
        });
        
        document.getElementById('filters').addEventListener('click', e => {
            if (e.target.classList.contains('filter-tag')) {
                currentFilter = e.target.dataset.filter;
                filterShows(currentView, currentFilter);
            }
        });
        
        document.getElementById('search').addEventListener('input', e => {
            if (e.target.value) searchShows(e.target.value);
            else if (currentFilter) filterShows(currentView, currentFilter);
            else renderShows(DATA.shows);
        });
        
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') closeModal();
        });
        
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });
    }
    
    function esc(s) { 
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); 
    }
    
    init();
    </script>
</body>
</html>'''


def generate_site():
    print("Generating broadway SPA...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    shows = get_all_shows(DB_PATH)
    print(f"Found {len(shows)} shows")
    
    data = generate_data_json(shows)
    with open(os.path.join(OUTPUT_DIR, 'data.json'), 'w') as f:
        json.dump(data, f)
    print("Generated data.json")
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(generate_html())
    print("Generated index.html")
    
    print(f"\n✓ Site generated in '{OUTPUT_DIR}/' (2 files)")


if __name__ == "__main__":
    generate_site()
