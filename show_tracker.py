#!/usr/bin/env python3
import click
import yaml
import json
import csv
from pathlib import Path
from typing import Optional
from datetime import datetime

from database import Database
from llm_providers import get_provider
from image_processor import ImageProcessor
from show_manager import ShowManager


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save configuration to config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_managers():
    """Initialize and return database, LLM provider, and show manager."""
    config = load_config()

    # Validate API key
    provider_name = config['llm']['provider']
    api_key_field = f"{provider_name}_api_key"

    if not config['llm'].get(api_key_field) or config['llm'][api_key_field] == f"your-{provider_name}-api-key-here":
        click.echo(f"Error: Please configure your {provider_name.upper()} API key in config.yaml", err=True)
        raise click.Abort()

    db = Database(config['database']['path'])
    llm_provider = get_provider(config)
    show_manager = ShowManager(db, llm_provider, config)

    return config, db, llm_provider, show_manager


@click.group()
def cli():
    """Broadway Show Tracker - Track your Broadway shows with AI-powered metadata."""
    pass


@cli.command()
@click.option('--directory', type=click.Choice(['shows_seen', 'shows_wishlist', 'all']), default='all',
              help='Directory to scan for images')
def scan(directory):
    """Scan directories for playbill/poster images and extract information."""
    config, db, llm_provider, show_manager = get_managers()
    image_processor = ImageProcessor(config, db)

    directories = []
    if directory == 'all':
        directories = [config['directories']['shows_seen'], config['directories']['shows_wishlist']]
    else:
        directories = [config['directories'][directory]]

    total_shows_added = 0

    for dir_name in directories:
        click.echo(f"\nScanning directory: {dir_name}")
        unprocessed_images = image_processor.scan_directory(dir_name)

        if not unprocessed_images:
            click.echo(f"No new images found in {dir_name}")
            continue

        click.echo(f"Found {len(unprocessed_images)} unprocessed image(s)")

        for image_path in unprocessed_images:
            click.echo(f"\nProcessing: {Path(image_path).name}")

            try:
                # Extract shows from image
                shows = show_manager.extract_shows_from_image(image_path)

                if not shows:
                    click.echo("  No shows detected in image")
                    db.mark_image_processed(image_path, 0)
                    continue

                click.echo(f"  Detected {len(shows)} show(s)")

                # Determine seen status from directory
                seen_status = image_processor.get_seen_status_from_directory(image_path)

                shows_added = 0
                for show_data in shows:
                    show_name = show_data['show_name']
                    theater_name = show_data['theater_name']

                    click.echo(f"  - {show_name} at {theater_name}")

                    # Prepare show data
                    show_entry = {
                        'show_name': show_name,
                        'theater_name': theater_name,
                        'seen_status': seen_status,
                        'source_image_path': image_path
                    }

                    # If seen, prompt for date attended and rating
                    if seen_status == 'seen':
                        date_attended = click.prompt("    Date attended (YYYY-MM-DD or leave empty)",
                                                    type=str, default='', show_default=False)
                        if date_attended:
                            try:
                                # Validate date format
                                datetime.fromisoformat(date_attended)
                                show_entry['date_attended'] = date_attended
                            except ValueError:
                                click.echo("    Invalid date format, skipping date")

                        rating = click.prompt("    Rate this show (1-10, or 0 to skip)", type=int, default=0)
                        if rating > 0:
                            show_entry['rating'] = rating

                        notes = click.prompt("    Personal notes (or leave empty)", type=str, default='', show_default=False)
                        if notes:
                            show_entry['personal_notes'] = notes

                    # Add show
                    show_id, status = show_manager.add_show(show_entry)

                    if status == 'duplicate':
                        click.echo(f"    Already in database (ID: {show_id})")
                    elif status == 'added':
                        click.echo(f"    Added to database (ID: {show_id})")
                        shows_added += 1

                total_shows_added += shows_added

                # Mark image as processed
                db.mark_image_processed(image_path, shows_added)

            except Exception as e:
                click.echo(f"  Error processing image: {e}", err=True)
                continue

    click.echo(f"\n✓ Scan complete. Added {total_shows_added} new show(s).")


@cli.command()
@click.option('--name', 'show_name', required=True, help='Show name')
@click.option('--theater', 'theater_name', required=True, help='Theater name')
@click.option('--seen', is_flag=True, help='Mark as seen')
@click.option('--wishlist', is_flag=True, help='Mark as wishlist')
@click.option('--date-attended', help='Date attended (YYYY-MM-DD)')
@click.option('--rating', type=click.IntRange(1, 10), help='Rating (1-10)')
@click.option('--notes', help='Personal notes')
def add(show_name, theater_name, seen, wishlist, date_attended, rating, notes):
    """Manually add a show to the database."""
    config, db, llm_provider, show_manager = get_managers()

    # Determine seen status
    if not seen and not wishlist:
        seen = click.confirm("Have you seen this show?", default=False)

    seen_status = 'seen' if seen else 'wishlist'

    # Prepare show data
    show_data = {
        'show_name': show_name,
        'theater_name': theater_name,
        'seen_status': seen_status
    }

    if seen_status == 'seen':
        if date_attended:
            try:
                datetime.fromisoformat(date_attended)
                show_data['date_attended'] = date_attended
            except ValueError:
                click.echo("Invalid date format. Use YYYY-MM-DD", err=True)
                raise click.Abort()
        else:
            date_input = click.prompt("Date attended (YYYY-MM-DD or leave empty)",
                                     type=str, default='', show_default=False)
            if date_input:
                try:
                    datetime.fromisoformat(date_input)
                    show_data['date_attended'] = date_input
                except ValueError:
                    click.echo("Invalid date format, proceeding without date")

        if rating:
            show_data['rating'] = rating
        else:
            rating_input = click.prompt("Rate this show (1-10, or 0 to skip)", type=int, default=0)
            if rating_input > 0:
                show_data['rating'] = rating_input

    if notes:
        show_data['personal_notes'] = notes

    # Add show
    try:
        show_id, status = show_manager.add_show(show_data)

        if status == 'duplicate':
            click.echo(f"Show already exists in database (ID: {show_id})")
            if click.confirm("Do you want to update it?"):
                updates = {}
                if rating:
                    updates['rating'] = rating
                if notes:
                    updates['personal_notes'] = notes
                if date_attended:
                    updates['date_attended'] = date_attended
                if updates:
                    show_manager.update_show(show_id, updates)
                    click.echo("✓ Show updated")
        elif status == 'added':
            click.echo(f"✓ Show added successfully (ID: {show_id})")

    except Exception as e:
        click.echo(f"Error adding show: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--name', help='Filter by show name (partial match)')
@click.option('--theater', help='Filter by theater (partial match)')
@click.option('--seen', is_flag=True, help='Show only seen shows')
@click.option('--wishlist', is_flag=True, help='Show only wishlist shows')
@click.option('--genre', help='Filter by genre')
@click.option('--category', help='Filter by LLM category')
@click.option('--user-category', help='Filter by user category')
@click.option('--rating-min', type=click.IntRange(1, 10), help='Minimum rating')
@click.option('--rating-max', type=click.IntRange(1, 10), help='Maximum rating')
def search(name, theater, seen, wishlist, genre, category, user_category, rating_min, rating_max):
    """Search for shows with various filters."""
    config, db, llm_provider, show_manager = get_managers()

    filters = {}

    if name:
        filters['show_name'] = name
    if theater:
        filters['theater_name'] = theater
    if seen:
        filters['seen_status'] = 'seen'
    elif wishlist:
        filters['seen_status'] = 'wishlist'
    if genre:
        filters['genre'] = genre
    if category:
        filters['category'] = category
    if user_category:
        filters['user_category'] = user_category
    if rating_min:
        filters['rating_min'] = rating_min
    if rating_max:
        filters['rating_max'] = rating_max

    shows = show_manager.search_shows(filters)

    if not shows:
        click.echo("No shows found matching the criteria.")
        return

    click.echo(f"\nFound {len(shows)} show(s):\n")

    for show in shows:
        click.echo(show_manager.format_show_display(show))
        click.echo()


@cli.command(name='list')
@click.option('--seen', is_flag=True, help='Show only seen shows')
@click.option('--wishlist', is_flag=True, help='Show only wishlist shows')
@click.option('--sort-by', type=click.Choice(['name', 'theater', 'rating', 'date']), default='date',
              help='Sort by field')
def list_shows(seen, wishlist, sort_by):
    """List all shows in the database."""
    config, db, llm_provider, show_manager = get_managers()

    filters = {}
    if seen:
        filters['seen_status'] = 'seen'
    elif wishlist:
        filters['seen_status'] = 'wishlist'

    # Map friendly names to database columns
    sort_map = {
        'name': 'show_name',
        'theater': 'theater_name',
        'rating': 'rating',
        'date': 'date_added'
    }
    filters['sort_by'] = sort_map[sort_by]

    shows = show_manager.search_shows(filters)

    if not shows:
        click.echo("No shows in database.")
        return

    click.echo(f"\n{len(shows)} show(s) in database:\n")

    for show in shows:
        click.echo(show_manager.format_show_display(show))
        click.echo()


@cli.command()
@click.argument('show_id', type=int)
def show(show_id):
    """Show detailed information about a show by ID."""
    config, db, llm_provider, show_manager = get_managers()

    show_data = show_manager.get_show(show_id)

    if not show_data:
        click.echo(f"Show not found: {show_id}", err=True)
        raise click.Abort()

    click.echo("\n" + show_manager.format_show_display(show_data, detailed=True) + "\n")


@cli.command()
@click.argument('show_id', type=int)
@click.option('--rating', type=click.IntRange(1, 10), help='Update rating')
@click.option('--notes', help='Update personal notes')
@click.option('--date-attended', help='Update date attended (YYYY-MM-DD)')
@click.option('--seen', is_flag=True, help='Mark as seen')
@click.option('--wishlist', is_flag=True, help='Mark as wishlist')
def update(show_id, rating, notes, date_attended, seen, wishlist):
    """Update show information."""
    config, db, llm_provider, show_manager = get_managers()

    show_data = show_manager.get_show(show_id)
    if not show_data:
        click.echo(f"Show not found: {show_id}", err=True)
        raise click.Abort()

    updates = {}

    if rating:
        updates['rating'] = rating
    if notes:
        updates['personal_notes'] = notes
    if date_attended:
        try:
            datetime.fromisoformat(date_attended)
            updates['date_attended'] = date_attended
        except ValueError:
            click.echo("Invalid date format. Use YYYY-MM-DD", err=True)
            raise click.Abort()
    if seen:
        updates['seen_status'] = 'seen'
    elif wishlist:
        updates['seen_status'] = 'wishlist'

    if not updates:
        click.echo("No updates specified.")
        return

    show_manager.update_show(show_id, updates)
    click.echo("✓ Show updated successfully")


@cli.command()
@click.argument('show_id', type=int)
@click.option('--force', is_flag=True, help='Re-fetch all fields, overwriting existing data')
def enrich(show_id, force):
    """Enrich a show with detailed metadata from LLM."""
    config, db, llm_provider, show_manager = get_managers()

    show_data = show_manager.get_show(show_id)

    if not show_data:
        click.echo(f"Show not found: {show_id}", err=True)
        raise click.Abort()

    try:
        if force:
            click.echo("Re-fetching all metadata fields...")
        else:
            click.echo("Fetching missing metadata fields...")

        updated_show = show_manager.enrich_show(show_id, force=force)
        click.echo("✓ Show enriched successfully\n")
        click.echo(show_manager.format_show_display(updated_show, detailed=True))

    except Exception as e:
        click.echo(f"Error enriching show: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['csv', 'json']), required=True, help='Export format')
@click.option('--output', required=True, help='Output file path')
def export(output_format, output):
    """Export all shows to CSV or JSON."""
    config, db, llm_provider, show_manager = get_managers()

    shows = show_manager.search_shows({})

    if not shows:
        click.echo("No shows to export.")
        return

    try:
        if output_format == 'json':
            with open(output, 'w') as f:
                json.dump(shows, f, indent=2)
        elif output_format == 'csv':
            with open(output, 'w', newline='') as f:
                # Get all possible fields
                fieldnames = ['id', 'show_name', 'theater_name', 'seen_status', 'date_attended',
                              'rating', 'date_added', 'personal_notes', 'lead_cast', 'director',
                              'choreographer', 'composer', 'lyricist', 'book_writer', 'opening_date',
                              'closing_date', 'is_revival', 'original_production_year', 'production_type',
                              'plot_summary', 'genre', 'tony_awards', 'other_awards', 'musical_numbers',
                              'themes', 'running_time', 'intermission_count', 'llm_categories',
                              'user_categories', 'source_image_path', 'last_updated']

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for show in shows:
                    # Convert lists to comma-separated strings for CSV
                    row = show.copy()
                    for field in ['lead_cast', 'tony_awards', 'other_awards', 'musical_numbers',
                                  'themes', 'llm_categories', 'user_categories']:
                        if isinstance(row.get(field), list):
                            if field == 'lead_cast':
                                # Special handling for lead_cast dicts
                                row[field] = '; '.join([f"{c.get('role', '')}: {c.get('actor', '')}"
                                                       for c in row[field] if isinstance(c, dict)])
                            else:
                                row[field] = ', '.join([str(item) for item in row[field]])
                    writer.writerow(row)

        click.echo(f"✓ Exported {len(shows)} show(s) to {output}")

    except Exception as e:
        click.echo(f"Error exporting shows: {e}", err=True)
        raise click.Abort()


@cli.group()
def categories():
    """Manage predefined user categories."""
    pass


@categories.command(name='list')
def list_categories():
    """List all predefined user categories."""
    config = load_config()
    user_categories = config['settings'].get('user_categories', [])

    if not user_categories:
        click.echo("No user categories defined.")
        return

    click.echo("\nPredefined user categories:")
    for i, category in enumerate(user_categories, 1):
        click.echo(f"  {i}. {category}")
    click.echo()


@categories.command(name='add')
@click.argument('category')
def add_category(category):
    """Add a new predefined user category."""
    config = load_config()

    # Normalize category (lowercase, trim)
    category = category.lower().strip()

    if not category:
        click.echo("Category name cannot be empty.", err=True)
        raise click.Abort()

    user_categories = config['settings'].get('user_categories', [])

    if category in user_categories:
        click.echo(f"Category '{category}' already exists.")
        return

    user_categories.append(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Added category: {category}")


@categories.command(name='remove')
@click.argument('category')
def remove_category(category):
    """Remove a predefined user category."""
    config = load_config()

    category = category.lower().strip()
    user_categories = config['settings'].get('user_categories', [])

    if category not in user_categories:
        click.echo(f"Category '{category}' not found.")
        return

    user_categories.remove(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Removed category: {category}")


if __name__ == '__main__':
    cli()
