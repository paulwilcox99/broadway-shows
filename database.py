import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    def __init__(self, db_path: str = "shows.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database with schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create shows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Core Fields (user-entered or extracted)
                show_name TEXT NOT NULL,
                theater_name TEXT NOT NULL,
                date_added TEXT NOT NULL,
                date_attended TEXT,
                seen_status TEXT CHECK (seen_status IN ('seen', 'wishlist')),
                rating INTEGER CHECK (rating >= 1 AND rating <= 10),
                personal_notes TEXT,

                -- Enriched Metadata: Cast & Creative Team
                lead_cast TEXT,
                director TEXT,
                choreographer TEXT,
                composer TEXT,
                lyricist TEXT,
                book_writer TEXT,

                -- Enriched Metadata: Production Details
                opening_date TEXT,
                closing_date TEXT,
                is_revival BOOLEAN DEFAULT 0,
                original_production_year INTEGER,
                production_type TEXT,

                -- Enriched Metadata: Content & Awards
                plot_summary TEXT,
                genre TEXT,
                tony_awards TEXT,
                other_awards TEXT,

                -- Enriched Metadata: Technical & Themes
                musical_numbers TEXT,
                themes TEXT,
                running_time INTEGER,
                intermission_count INTEGER,

                -- Categories & Classification
                llm_categories TEXT,
                user_categories TEXT,

                -- Metadata
                source_image_path TEXT,
                last_updated TEXT NOT NULL,

                UNIQUE(show_name, theater_name, date_attended)
            )
        """)

        # Create processed_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT UNIQUE NOT NULL,
                processed_date TEXT NOT NULL,
                shows_extracted INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def add_show(self, show_data: Dict[str, Any]) -> int:
        """Add a new show to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        show_data['date_added'] = now
        show_data['last_updated'] = now

        # Convert lists to JSON strings
        json_fields = [
            'lead_cast', 'tony_awards', 'other_awards', 'musical_numbers',
            'themes', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if field in show_data and isinstance(show_data[field], list):
                show_data[field] = json.dumps(show_data[field])

        columns = ', '.join(show_data.keys())
        placeholders = ', '.join(['?' for _ in show_data])

        cursor.execute(
            f"INSERT INTO shows ({columns}) VALUES ({placeholders})",
            list(show_data.values())
        )

        show_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return show_id

    def update_show(self, show_id: int, updates: Dict[str, Any]):
        """Update an existing show."""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates['last_updated'] = datetime.now().isoformat()

        # Convert lists to JSON strings
        json_fields = [
            'lead_cast', 'tony_awards', 'other_awards', 'musical_numbers',
            'themes', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if field in updates and isinstance(updates[field], list):
                updates[field] = json.dumps(updates[field])

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])

        cursor.execute(
            f"UPDATE shows SET {set_clause} WHERE id = ?",
            list(updates.values()) + [show_id]
        )

        conn.commit()
        conn.close()

    def get_show(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get a show by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM shows WHERE id = ?", (show_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def get_show_by_name(self, show_name: str, theater_name: str = None) -> Optional[Dict[str, Any]]:
        """Get a show by name and optionally theater."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if theater_name:
            cursor.execute(
                "SELECT * FROM shows WHERE show_name = ? AND theater_name = ?",
                (show_name, theater_name)
            )
        else:
            cursor.execute("SELECT * FROM shows WHERE show_name = ?", (show_name,))

        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def search_shows(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search shows with various filters."""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM shows WHERE 1=1"
        params = []

        if 'show_name' in filters:
            query += " AND show_name LIKE ?"
            params.append(f"%{filters['show_name']}%")

        if 'theater_name' in filters:
            query += " AND theater_name LIKE ?"
            params.append(f"%{filters['theater_name']}%")

        if 'seen_status' in filters:
            query += " AND seen_status = ?"
            params.append(filters['seen_status'])

        if 'rating_min' in filters:
            query += " AND rating >= ?"
            params.append(filters['rating_min'])

        if 'rating_max' in filters:
            query += " AND rating <= ?"
            params.append(filters['rating_max'])

        if 'genre' in filters:
            query += " AND genre LIKE ?"
            params.append(f"%{filters['genre']}%")

        if 'category' in filters:
            query += " AND llm_categories LIKE ?"
            params.append(f"%{filters['category']}%")

        if 'user_category' in filters:
            query += " AND user_categories LIKE ?"
            params.append(f"%{filters['user_category']}%")

        if 'sort_by' in filters:
            sort_field = filters['sort_by']
            sort_order = filters.get('sort_order', 'ASC')
            query += f" ORDER BY {sort_field} {sort_order}"
        else:
            query += " ORDER BY date_added DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all shows."""
        return self.search_shows({})

    def mark_image_processed(self, image_path: str, shows_extracted: int):
        """Mark an image as processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO processed_images (image_path, processed_date, shows_extracted) VALUES (?, ?, ?)",
            (image_path, datetime.now().isoformat(), shows_extracted)
        )

        conn.commit()
        conn.close()

    def is_image_processed(self, image_path: str) -> bool:
        """Check if an image has been processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM processed_images WHERE image_path = ?", (image_path,))
        result = cursor.fetchone()

        conn.close()

        return result is not None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary with JSON fields parsed."""
        show = dict(row)

        # Parse JSON fields
        json_fields = [
            'lead_cast', 'tony_awards', 'other_awards', 'musical_numbers',
            'themes', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if show.get(field):
                try:
                    show[field] = json.loads(show[field])
                except json.JSONDecodeError:
                    show[field] = []

        return show
