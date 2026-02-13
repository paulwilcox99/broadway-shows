import re
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from database import Database
from llm_providers import LLMProvider


class ShowManager:
    def __init__(self, db: Database, llm_provider: LLMProvider, config: Dict[str, Any]):
        self.db = db
        self.llm_provider = llm_provider
        self.config = config

    def normalize_string(self, s: str) -> str:
        """Normalize string for comparison (lowercase, remove punctuation, trim)."""
        s = s.lower().strip()
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'\s+', ' ', s)
        return s

    def find_duplicate(self, show_name: str, theater_name: str, date_attended: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Check if show already exists using fuzzy matching."""
        normalized_show = self.normalize_string(show_name)
        normalized_theater = self.normalize_string(theater_name)

        all_shows = self.db.get_all_shows()

        for show in all_shows:
            show_normalized = self.normalize_string(show['show_name'])
            theater_normalized = self.normalize_string(show['theater_name'])

            # Match on show name and theater name
            if show_normalized == normalized_show and theater_normalized == normalized_theater:
                # If date_attended is provided, check if it matches
                if date_attended:
                    if show.get('date_attended') == date_attended:
                        return show
                else:
                    # If no date provided, consider it a duplicate if same show/theater combo exists
                    return show

        return None

    def extract_shows_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract show information from a playbill/poster image."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Detect image type
        suffix = Path(image_path).suffix.lower()
        media_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"

        prompt = """Analyze this playbill or Broadway show poster image and extract:
1. Show name (the title of the Broadway show)
2. Theater name (the venue where it's performed)

Return ONLY a JSON array in this exact format, with no additional text:
[{"show_name": "Show Title", "theater_name": "Theater Name"}]

If you cannot clearly identify the information, return an empty array []."""

        try:
            # Use the provider's underlying client directly for custom prompts
            provider_name = self.config['llm']['provider']

            if provider_name == 'openai':
                response = self.llm_provider.client.chat.completions.create(
                    model=self.llm_provider.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                content = response.choices[0].message.content.strip()

            elif provider_name == 'anthropic':
                response = self.llm_provider.client.messages.create(
                    model=self.llm_provider.model,
                    max_tokens=500,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": image_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                )
                content = response.content[0].text.strip()

            elif provider_name == 'google':
                from PIL import Image
                image = Image.open(image_path)
                response = self.llm_provider.model.generate_content([prompt, image])
                content = response.text.strip()

            else:
                raise ValueError(f"Unknown provider: {provider_name}")

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error extracting shows from image: {e}")
            return []

    def enrich_show(self, show_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Enrich a show with LLM metadata.
        If force=False, only fetch fields that are empty/null.
        If force=True, re-fetch all fields.
        """
        show = self.db.get_show(show_id)
        if not show:
            raise ValueError(f"Show with ID {show_id} not found")

        # Determine which fields need enrichment
        enrichable_fields = [
            'lead_cast', 'director', 'choreographer', 'composer', 'lyricist', 'book_writer',
            'opening_date', 'closing_date', 'is_revival', 'original_production_year', 'production_type',
            'plot_summary', 'genre', 'tony_awards', 'other_awards',
            'musical_numbers', 'themes', 'running_time', 'intermission_count', 'llm_categories'
        ]

        if force:
            missing_fields = None  # Fetch all fields
        else:
            missing_fields = []
            for field in enrichable_fields:
                value = show.get(field)
                if value is None or value == '' or (isinstance(value, list) and len(value) == 0):
                    missing_fields.append(field)

            if not missing_fields:
                return show  # Nothing to enrich

        # Call LLM for enrichment
        print(f"Enriching show: {show['show_name']} at {show['theater_name']}")
        enriched_data = self._enrich_show_info(
            show['show_name'],
            show['theater_name'],
            missing_fields=missing_fields
        )

        # Update only the fields that were fetched
        updates = {}
        for field, value in enriched_data.items():
            if force or field in (missing_fields or enrichable_fields):
                updates[field] = value

        # Match against user categories if we have plot_summary
        plot_summary = updates.get('plot_summary') or show.get('plot_summary')
        if plot_summary and self.config['settings'].get('user_categories'):
            print("Matching user categories...")
            user_cats = self._match_user_categories(
                show['show_name'],
                show['theater_name'],
                plot_summary,
                self.config['settings']['user_categories']
            )
            updates['user_categories'] = user_cats

        # Update the database
        if updates:
            self.db.update_show(show_id, updates)

        # Return updated show
        return self.db.get_show(show_id)

    def _enrich_show_info(self, show_name: str, theater_name: str, missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich show information with detailed metadata using LLM."""
        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- lead_cast (list of dicts with "role" and "actor" keys for main cast members)
- director (name of director)
- choreographer (name of choreographer, if applicable)
- composer (name of composer, if applicable)
- lyricist (name of lyricist, if applicable)
- book_writer (name of book writer, if applicable)
- opening_date (YYYY-MM-DD format)
- closing_date (YYYY-MM-DD format or "still running")
- is_revival (true/false)
- original_production_year (year of original production if revival)
- production_type ("Broadway", "Off-Broadway", "Tour", etc.)
- plot_summary (2-3 sentences)
- genre ("Musical", "Play", "Musical Revival", etc.)
- tony_awards (list of Tony Awards won)
- other_awards (list of other major awards)
- musical_numbers (list of song titles, if applicable)
- themes (list of main themes)
- running_time (in minutes)
- intermission_count (number of intermissions)
- categories (list of auto-detected categories like "jukebox musical", "comedy", "drama", "golden age musical", etc.)"""

        prompt = f"""Provide detailed information about the Broadway show "{show_name}" that played/is playing at {theater_name}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "lead_cast": [{{"role": "Character Name", "actor": "Actor Name"}}, ...],
    "director": "...",
    "choreographer": "...",
    "composer": "...",
    "lyricist": "...",
    "book_writer": "...",
    "opening_date": "YYYY-MM-DD",
    "closing_date": "YYYY-MM-DD or still running",
    "is_revival": true or false,
    "original_production_year": year or null,
    "production_type": "Broadway/Off-Broadway/Tour",
    "plot_summary": "...",
    "genre": "Musical/Play/etc",
    "tony_awards": ["award1", "award2"],
    "other_awards": ["award1", "award2"],
    "musical_numbers": ["song1", "song2"],
    "themes": ["theme1", "theme2"],
    "running_time": 150,
    "intermission_count": 1,
    "categories": ["category1", "category2"]
}}

If information is not available, use null for single values or empty arrays [] for lists."""

        try:
            provider_name = self.config['llm']['provider']

            if provider_name == 'openai':
                response = self.llm_provider.client.chat.completions.create(
                    model=self.llm_provider.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000
                )
                content = response.choices[0].message.content.strip()

            elif provider_name == 'anthropic':
                response = self.llm_provider.client.messages.create(
                    model=self.llm_provider.model,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text.strip()

            elif provider_name == 'google':
                response = self.llm_provider.model.generate_content(prompt)
                content = response.text.strip()

            else:
                raise ValueError(f"Unknown provider: {provider_name}")

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error enriching show info: {e}")
            return {}

    def _match_user_categories(self, show_name: str, theater_name: str, plot_summary: str, predefined_categories: List[str]) -> List[str]:
        """Match show against predefined user categories."""
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this Broadway show:
Show Name: {show_name}
Theater: {theater_name}
Plot Summary: {plot_summary}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            provider_name = self.config['llm']['provider']

            if provider_name == 'openai':
                response = self.llm_provider.client.chat.completions.create(
                    model=self.llm_provider.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                content = response.choices[0].message.content.strip()

            elif provider_name == 'anthropic':
                response = self.llm_provider.client.messages.create(
                    model=self.llm_provider.model,
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text.strip()

            elif provider_name == 'google':
                response = self.llm_provider.model.generate_content(prompt)
                content = response.text.strip()

            else:
                raise ValueError(f"Unknown provider: {provider_name}")

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []

    def add_show(self, show_data: Dict[str, Any], source: str = 'manual', auto_enrich: bool = None) -> Tuple[int, str]:
        """
        Add a new show to the database.
        Returns (show_id, status) where status is 'added' or 'duplicate'.
        """
        # Check for duplicates
        duplicate = self.find_duplicate(
            show_data['show_name'],
            show_data['theater_name'],
            show_data.get('date_attended')
        )

        if duplicate:
            return duplicate['id'], 'duplicate'

        # Add the show
        show_id = self.db.add_show(show_data)

        # Auto-enrich if enabled
        should_enrich = auto_enrich if auto_enrich is not None else self.config['settings'].get('auto_enrich', True)

        if should_enrich:
            try:
                self.enrich_show(show_id, force=False)
            except Exception as e:
                print(f"Warning: Failed to enrich show: {e}")

        return show_id, 'added'

    def update_show(self, show_id: int, updates: Dict[str, Any]):
        """Update an existing show."""
        self.db.update_show(show_id, updates)

    def get_show(self, show_id: int) -> Optional[Dict[str, Any]]:
        """Get a show by ID."""
        return self.db.get_show(show_id)

    def search_shows(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search shows with filters."""
        return self.db.search_shows(filters)

    def format_show_display(self, show: Dict[str, Any], detailed: bool = False) -> str:
        """Format show information for display."""
        output = []
        output.append(f"ID: {show['id']}")
        output.append(f"Show: {show['show_name']}")
        output.append(f"Theater: {show['theater_name']}")
        output.append(f"Status: {show['seen_status']}")

        if show.get('date_attended'):
            output.append(f"Date Attended: {show['date_attended']}")

        if show.get('rating'):
            output.append(f"Rating: {show['rating']}/10")

        if detailed:
            if show.get('genre'):
                output.append(f"Genre: {show['genre']}")

            if show.get('opening_date'):
                output.append(f"Opening Date: {show['opening_date']}")

            if show.get('closing_date'):
                output.append(f"Closing Date: {show['closing_date']}")

            if show.get('production_type'):
                output.append(f"Production Type: {show['production_type']}")

            if show.get('plot_summary'):
                output.append(f"Plot: {show['plot_summary']}")

            if show.get('director'):
                output.append(f"Director: {show['director']}")

            if show.get('choreographer'):
                output.append(f"Choreographer: {show['choreographer']}")

            if show.get('composer'):
                output.append(f"Composer: {show['composer']}")

            if show.get('lyricist'):
                output.append(f"Lyricist: {show['lyricist']}")

            if show.get('lead_cast') and len(show['lead_cast']) > 0:
                output.append("Lead Cast:")
                for cast_member in show['lead_cast']:
                    if isinstance(cast_member, dict):
                        output.append(f"  - {cast_member.get('role', 'Unknown')}: {cast_member.get('actor', 'Unknown')}")
                    else:
                        output.append(f"  - {cast_member}")

            if show.get('tony_awards') and len(show['tony_awards']) > 0:
                output.append(f"Tony Awards: {', '.join(show['tony_awards'])}")

            if show.get('other_awards') and len(show['other_awards']) > 0:
                output.append(f"Other Awards: {', '.join(show['other_awards'])}")

            if show.get('themes') and len(show['themes']) > 0:
                output.append(f"Themes: {', '.join(show['themes'])}")

            if show.get('running_time'):
                output.append(f"Running Time: {show['running_time']} minutes")

            if show.get('llm_categories') and len(show['llm_categories']) > 0:
                output.append(f"Categories: {', '.join(show['llm_categories'])}")

            if show.get('user_categories') and len(show['user_categories']) > 0:
                output.append(f"User Categories: {', '.join(show['user_categories'])}")

            if show.get('personal_notes'):
                output.append(f"Notes: {show['personal_notes']}")

            if show.get('source_image_path'):
                output.append(f"Source Image: {show['source_image_path']}")

            output.append(f"Date Added: {show['date_added']}")

        return "\n".join(output)
