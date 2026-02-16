#!/usr/bin/env python3
"""
Migration script to assign major themes to all existing shows.
"""

import sqlite3
import json
from theme_categories import get_major_theme

DB_FILE = "shows.db"

def migrate():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all shows with themes
    cursor.execute("SELECT id, show_name, themes FROM shows WHERE themes IS NOT NULL AND themes != '[]'")
    shows = cursor.fetchall()
    
    updated = 0
    skipped = 0
    
    for show in shows:
        try:
            themes_list = json.loads(show['themes'])
            major_theme = get_major_theme(themes_list)
            
            if major_theme:
                cursor.execute(
                    "UPDATE shows SET major_theme = ? WHERE id = ?",
                    (major_theme, show['id'])
                )
                updated += 1
                print(f"✓ {show['show_name'][:50]:<50} → {major_theme}")
            else:
                skipped += 1
                print(f"✗ {show['show_name'][:50]:<50} → No matching major theme")
        except json.JSONDecodeError:
            skipped += 1
            print(f"✗ {show['show_name'][:50]:<50} → Invalid themes JSON")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Updated: {updated} shows")
    print(f"  Skipped: {skipped} shows")

if __name__ == "__main__":
    migrate()
