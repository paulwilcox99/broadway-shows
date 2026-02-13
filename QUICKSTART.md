# Quick Start Guide

## Installation

```bash
cd /home/paul/code/shows
pip install -r requirements.txt
cp config.yaml.example config.yaml
# Edit config.yaml and add your API key for your chosen provider
```

## Command Reference

### Scanning Images

Scan directories for playbill/poster images and extract show information:

```bash
# Scan all directories
python show_tracker.py scan

# Scan specific directory
python show_tracker.py scan --directory shows_seen
python show_tracker.py scan --directory shows_wishlist
```

The scanner will:
1. Find unprocessed images
2. Extract show name and theater using LLM vision
3. Prompt for additional details (date, rating, notes for seen shows)
4. Add shows to database
5. Auto-enrich with metadata (if enabled in config)

### Adding Shows Manually

```bash
# Add a seen show with all details
python show_tracker.py add \
  --name "Hamilton" \
  --theater "Richard Rodgers Theatre" \
  --seen \
  --date-attended 2024-01-15 \
  --rating 10 \
  --notes "Amazing experience!"

# Add a wishlist show
python show_tracker.py add \
  --name "Wicked" \
  --theater "Gershwin Theatre" \
  --wishlist

# Interactive mode (will prompt for missing information)
python show_tracker.py add --name "Hamilton" --theater "Richard Rodgers Theatre"
```

### Listing Shows

```bash
# List all shows
python show_tracker.py list

# List only seen shows
python show_tracker.py list --seen

# List only wishlist shows
python show_tracker.py list --wishlist

# Sort by different fields
python show_tracker.py list --sort-by name
python show_tracker.py list --sort-by theater
python show_tracker.py list --sort-by rating
python show_tracker.py list --sort-by date
```

### Viewing Show Details

```bash
# View by ID
python show_tracker.py show 1

# Shows full details including enriched metadata
```

### Searching Shows

```bash
# Search by show name
python show_tracker.py search --name "Hamilton"

# Search by theater
python show_tracker.py search --theater "Rodgers"

# Search seen shows with rating filter
python show_tracker.py search --seen --rating-min 8

# Search by genre
python show_tracker.py search --genre "Musical"

# Combine filters
python show_tracker.py search --seen --genre "Musical" --rating-min 9
```

### Updating Shows

```bash
# Update rating
python show_tracker.py update 1 --rating 9

# Update notes
python show_tracker.py update 1 --notes "Saw it again, still amazing!"

# Update date attended
python show_tracker.py update 1 --date-attended 2024-02-20

# Change status
python show_tracker.py update 1 --seen
python show_tracker.py update 1 --wishlist
```

### Enriching Shows

```bash
# Enrich a show (fetches missing metadata only)
python show_tracker.py enrich 1

# Force re-fetch all metadata (overwrites existing)
python show_tracker.py enrich 1 --force
```

Enrichment adds:
- Cast & creative team
- Production details (opening/closing dates, revival status)
- Awards (Tony Awards, others)
- Plot summary, themes, musical numbers
- Auto-detected categories
- User category matching

### Exporting Data

```bash
# Export to JSON
python show_tracker.py export --format json --output shows.json

# Export to CSV
python show_tracker.py export --format csv --output shows.csv
```

### Managing Categories

```bash
# List predefined user categories
python show_tracker.py categories list

# Add a new category
python show_tracker.py categories add "classics"

# Remove a category
python show_tracker.py categories remove "old-category"
```

Categories from config.yaml:
- favorites
- date night shows
- must see again
- family friendly

When you enrich shows, they're automatically matched against these categories.

### Generating Website

```bash
# Generate static website
python generate_site.py

# Force regeneration even if database unchanged
python generate_site.py --force

# Open the website
open site/index.html  # macOS
xdg-open site/index.html  # Linux
```

The website includes:
- **index.html** - Dashboard with statistics
- **timeline.html** - Shows by year/month attended
- **shows.html** - All shows grid
- **theaters.html** - Theater index
- **theaters/{slug}.html** - Shows at each theater
- **genres.html** - Genre index
- **categories.html** - Category index
- **shows/{slug}.html** - Individual show pages

## Workflow Examples

### Workflow 1: Scan and Enrich

```bash
# 1. Place playbill photos in shows_seen/
# 2. Scan images
python show_tracker.py scan

# 3. Generate website
python generate_site.py
```

### Workflow 2: Manual Entry

```bash
# 1. Add show
python show_tracker.py add --name "Wicked" --theater "Gershwin Theatre" --seen --rating 9

# 2. Enrich metadata
python show_tracker.py enrich 1

# 3. Generate website
python generate_site.py
```

### Workflow 3: Update Existing Show

```bash
# 1. Find show ID
python show_tracker.py list | grep "Wicked"

# 2. Update rating
python show_tracker.py update 5 --rating 10 --notes "Saw it again!"

# 3. Regenerate website
python generate_site.py
```

## Tips

- **Auto-enrichment**: Set `auto_enrich: true` in config.yaml to automatically enrich shows when added
- **Smart regeneration**: Website only rebuilds if database changed (use `--force` to override)
- **Duplicate detection**: System prevents duplicate shows based on (show_name, theater_name, date_attended)
- **Provider selection**: Change LLM provider in config.yaml (openai, anthropic, or google)
- **Image formats**: Supports .jpg, .jpeg, .png, .webp

## Troubleshooting

**"Error: Please configure your API key"**
- Edit config.yaml and add your API key for the selected provider

**"No shows detected in image"**
- Ensure image is clear and shows the title/theater prominently
- Try a different image or add manually

**"Database unchanged"**
- Website won't regenerate if no changes detected
- Use `--force` flag to regenerate anyway

**Enrichment fails**
- Check API key is valid
- Verify internet connection
- Try with `--force` to refetch data
