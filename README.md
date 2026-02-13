# Broadway Shows Catalog

Track your Broadway shows with AI-powered metadata enrichment. Scan playbill photos, manage your theater wishlist, and generate a beautiful static website of your collection.

## Features

### 🎭 Show Tracking
- **Image Scanning**: Use LLM vision to extract show names and theaters from playbill/poster photos
- **Manual Entry**: Add shows manually with full details
- **Seen & Wishlist**: Track which shows you've seen and which are on your wishlist
- **Ratings & Notes**: Rate shows 1-10 and add personal notes

### 🤖 AI-Powered Enrichment
Automatically enrich shows with comprehensive metadata:
- Cast & creative team (director, choreographer, composer, lyricist, book writer, lead cast)
- Production details (opening/closing dates, revival status, production type)
- Awards (Tony Awards, other major awards)
- Content (plot summary, themes, musical numbers, genre)
- Smart category matching

### 🌐 Static Website Generator
Generate a beautiful, responsive static website with:
- **Timeline View**: Shows grouped by year and month attended
- **Theater Pages**: Dedicated pages for each theater with statistics
- **Statistics Dashboard**: Total shows, average ratings, shows per year
- **Browse Options**: By theater, genre, category
- **Smart Regeneration**: Only rebuilds when database changes

### 🔌 Multi-Provider LLM Support
Choose from multiple AI providers:
- OpenAI (GPT-4o)
- Anthropic (Claude)
- Google (Gemini)

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml and add your API key
   ```

3. **Add Shows**
   - Place playbill images in `shows_seen/` or `shows_wishlist/`
   - Run: `python show_tracker.py scan`
   - Or add manually: `python show_tracker.py add --name "Hamilton" --theater "Richard Rodgers Theatre"`

4. **Generate Website**
   ```bash
   python generate_site.py
   open site/index.html
   ```

## Architecture

Built on proven patterns from book_manager and albums applications:

- **CLI Interface** (`show_tracker.py`): Click-based command-line interface
- **Business Logic** (`show_manager.py`): CRUD operations, enrichment, duplicate detection
- **Data Layer** (`database.py`): SQLite with JSON field support
- **LLM Integration** (`llm_providers.py`): Multi-provider abstraction
- **Image Processing** (`image_processor.py`): Directory scanning and image handling
- **Site Generator** (`generate_site.py`): Static HTML generation with MD5 hash detection

## Commands

See [QUICKSTART.md](QUICKSTART.md) for detailed command reference.

Basic commands:
- `scan` - Scan directories for playbill images
- `add` - Manually add a show
- `list` - List all shows
- `show <id>` - View show details
- `enrich <id>` - Enrich show with AI metadata
- `search` - Search shows with filters
- `update <id>` - Update show information
- `export` - Export to CSV or JSON
- `categories` - Manage user categories

## Database Schema

Shows are stored with:
- Core fields (show_name, theater_name, seen_status, rating, personal_notes)
- Enriched metadata (cast, creative team, awards, themes, plot)
- Categories (LLM auto-detected and user-defined)
- Timestamps (date_added, date_attended, last_updated)

## Website Features

The generated static website includes:
- **Index Page**: Statistics dashboard and quick navigation
- **Timeline View**: Chronological view of shows attended
- **Theater Pages**: Shows by theater with statistics
- **Genre/Category Pages**: Browse by genre or custom categories
- **Individual Show Pages**: Full details for each show
- **Responsive Design**: Works on desktop and mobile

## Development

This application follows the same architecture as the book_manager project, adapted for Broadway shows. Key differences:
- Shows tracked by (show_name, theater_name, date_attended) uniqueness
- Image scanning extracts show/theater pairs instead of title/author
- Enhanced website with timeline view and theater statistics

## License

Personal use project.
