

# smartparse_watch.py
# This script monitors a folder and its subfolders for new files (PDFs or images)
# and routes them to appropriate processing functions.

import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from dotenv import load_dotenv
import openai

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define the directory to watch (in iCloud Documents > SmartParseWatch)
WATCH_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Documents" / "SmartParseWatch"

# File extensions grouped by type
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PDF_EXTENSION = ".pdf"

# Handler for file creation events
class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Only handle files, not directories
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        ext = filepath.suffix.lower()

        # Log file detection
        print(f"Detected new file: {filepath}")

        # Route based on file type
        if ext in IMAGE_EXTENSIONS:
            self.process_image(filepath)
        elif ext == PDF_EXTENSION:
            self.process_pdf(filepath)
        else:
            print(f"Skipped unsupported file type: {filepath}")

    def process_image(self, filepath):
        # Placeholder for image processing logic
        print(f"Processing image: {filepath}")
        # Future: call GPT-4o vision model to generate name

    def process_pdf(self, filepath):
        # Placeholder for PDF processing logic
        print(f"Processing PDF: {filepath}")
        # Future: extract text and send to GPT to generate name

# Set up and start the observer
if __name__ == "__main__":
    print(f"Starting SmartParse.AI watcher on: {WATCH_DIR}")
    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)  # Keep the script alive
    except KeyboardInterrupt:
        observer.stop()
        print("Stopped SmartParse.AI watcher.")

    observer.join()