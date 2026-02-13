# Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- API key from one of:
  - OpenAI (https://platform.openai.com/api-keys)
  - Anthropic (https://console.anthropic.com/)
  - Google AI (https://makersuite.google.com/app/apikey)

## Installation Steps

### 1. Navigate to Project Directory

```bash
cd /home/paul/code/shows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `click` - CLI framework
- `openai` - OpenAI API client
- `anthropic` - Anthropic API client
- `google-generativeai` - Google Gemini API client
- `pyyaml` - YAML configuration parsing
- `python-dateutil` - Date parsing utilities
- `pillow` - Image processing

### 3. Configure API Keys

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
llm:
  provider: "openai"  # Change to "anthropic" or "google" if preferred
  openai_api_key: "sk-..."  # Add your actual API key here
  anthropic_api_key: "sk-ant-..."
  google_api_key: "..."
```

**Important**: Only the API key for your selected provider needs to be configured.

### 4. Verify Setup

```bash
# Test CLI is working
python show_tracker.py --help

# You should see the command list
```

### 5. Initialize Directories

The application will automatically create directories when first run, but you can create them manually:

```bash
mkdir -p shows_seen shows_wishlist
```

## Configuration Options

### LLM Provider Selection

Choose your preferred LLM provider in `config.yaml`:

```yaml
llm:
  provider: "openai"  # or "anthropic" or "google"
```

**Provider Comparison**:
- **OpenAI (GPT-4o)**: Most widely used, excellent vision and text capabilities
- **Anthropic (Claude 3.5 Sonnet)**: Strong reasoning, detailed responses
- **Google (Gemini 2.0 Flash)**: Fast, cost-effective

### Model Configuration

Customize models for each provider:

```yaml
llm:
  model:
    openai: "gpt-4o"  # or "gpt-4-turbo", "gpt-4o-mini"
    anthropic: "claude-3-5-sonnet-20241022"  # or "claude-3-opus-20240229"
    google: "gemini-2.0-flash-exp"  # or "gemini-1.5-pro"
```

### Database Path

Change database location if needed:

```yaml
database:
  path: "shows.db"  # Default location
```

### Directory Customization

Customize image directory names:

```yaml
directories:
  shows_seen: "shows_seen"  # Folder for seen show images
  shows_wishlist: "shows_wishlist"  # Folder for wishlist show images
```

### Auto-Enrichment

Enable/disable automatic metadata enrichment:

```yaml
settings:
  auto_enrich: true  # Set to false to manually enrich each show
```

When enabled, shows are automatically enriched with metadata after being added.

### Image Extensions

Customize supported image formats:

```yaml
settings:
  image_extensions:
    - ".jpg"
    - ".jpeg"
    - ".png"
    - ".webp"
    - ".heic"  # Add additional formats if needed
```

### User Categories

Define custom categories for show classification:

```yaml
settings:
  user_categories:
    - "favorites"
    - "date night shows"
    - "must see again"
    - "family friendly"
    - "comedies"  # Add your own categories
    - "classics"
```

Shows are automatically matched against these categories during enrichment.

## Directory Structure

After setup, your directory should look like:

```
/home/paul/code/shows/
├── show_tracker.py          # CLI interface
├── show_manager.py          # Business logic
├── database.py              # Data layer
├── llm_providers.py         # LLM integration
├── image_processor.py       # Image handling
├── generate_site.py         # Website generator
├── config.yaml              # Your configuration (not in git)
├── config.yaml.example      # Configuration template
├── requirements.txt         # Dependencies
├── README.md                # Project overview
├── QUICKSTART.md            # Command reference
├── SETUP.md                 # This file
├── shows_seen/              # Playbill images for seen shows
├── shows_wishlist/          # Playbill images for wishlist shows
├── shows.db                 # SQLite database (auto-created)
├── .site_state.json         # Website generation state (auto-created)
└── site/                    # Generated website (auto-created)
    ├── index.html
    ├── timeline.html
    ├── shows.html
    ├── theaters.html
    ├── genres.html
    ├── categories.html
    ├── shows/
    ├── theaters/
    ├── genres/
    └── categories/
```

## Testing Setup

### Test 1: Manual Show Entry

```bash
python show_tracker.py add \
  --name "The Phantom of the Opera" \
  --theater "Majestic Theatre" \
  --seen \
  --rating 9 \
  --notes "Classic!"
```

Expected output:
```
✓ Show added successfully (ID: 1)
Enriching show: The Phantom of the Opera at Majestic Theatre
✓ Show enriched successfully
```

### Test 2: View Show

```bash
python show_tracker.py show 1
```

Should display full show details including enriched metadata.

### Test 3: Generate Website

```bash
python generate_site.py
```

Expected output:
```
Generating site...
Found 1 shows
Generated 1 show pages
Generated 1 theater pages
Generated 1 genre pages
...
✓ Site generated in 'site/'
  Open site/index.html to view
```

### Test 4: Image Scanning (Optional)

1. Place a clear playbill image in `shows_seen/`
2. Run: `python show_tracker.py scan`
3. Verify show is detected and added

## Troubleshooting

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'click'`

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### API Key Errors

**Error**: `Error: Please configure your API key in config.yaml`

**Solution**:
1. Verify `config.yaml` exists (not `config.yaml.example`)
2. Check API key is correctly formatted
3. Ensure no extra quotes or spaces

### Database Errors

**Error**: `no such table: shows`

**Solution**: Delete `shows.db` and let it recreate:
```bash
rm shows.db
python show_tracker.py list  # Creates new database
```

### Permission Errors

**Error**: `Permission denied`

**Solution**: Make scripts executable
```bash
chmod +x show_tracker.py generate_site.py
```

### Image Processing Errors

**Error**: `No shows detected in image`

**Possible causes**:
- Image quality too low
- Text not clearly visible
- Wrong image type (not a playbill/poster)

**Solutions**:
- Try a clearer image
- Add show manually instead
- Adjust image to show title/theater more prominently

## Advanced Configuration

### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Deactivate when done
deactivate
```

### Custom Database Location

For multiple collections or backups:

```yaml
database:
  path: "/path/to/custom/shows.db"
```

### Environment Variables

Instead of storing API keys in config.yaml:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

Note: Current implementation reads from config.yaml. To use environment variables, modify `llm_providers.py` to read from `os.environ`.

## Next Steps

1. See [QUICKSTART.md](QUICKSTART.md) for command reference
2. See [README.md](README.md) for feature overview
3. Start adding shows:
   - Place playbill images in `shows_seen/` or `shows_wishlist/`
   - Run `python show_tracker.py scan`
   - Or add manually with `python show_tracker.py add`
4. Generate your website: `python generate_site.py`
