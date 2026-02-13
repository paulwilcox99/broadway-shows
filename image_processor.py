import os
from pathlib import Path
from typing import List, Tuple
from database import Database


class ImageProcessor:
    def __init__(self, config: dict, db: Database):
        self.config = config
        self.db = db
        self.image_extensions = config['settings']['image_extensions']

    def scan_directory(self, directory: str) -> List[str]:
        """Scan a directory for unprocessed images."""
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"Directory {directory} does not exist. Creating it...")
            dir_path.mkdir(parents=True, exist_ok=True)
            return []

        unprocessed_images = []

        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.image_extensions:
                image_path_str = str(file_path.absolute())
                if not self.db.is_image_processed(image_path_str):
                    unprocessed_images.append(image_path_str)

        return unprocessed_images

    def get_seen_status_from_directory(self, image_path: str) -> str:
        """Determine seen status based on which directory the image is in."""
        shows_seen = self.config['directories']['shows_seen']
        shows_wishlist = self.config['directories']['shows_wishlist']

        if shows_seen in image_path:
            return 'seen'
        elif shows_wishlist in image_path:
            return 'wishlist'
        else:
            # Default to wishlist if cannot determine
            return 'wishlist'
