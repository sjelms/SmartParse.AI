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
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import threading
import queue
from pync import Notifier

client = openai.OpenAI()

# Load environment variables from .env file
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define which model to use for each type
MODEL_TEXT = "gpt-3.5-turbo"
MODEL_PDF = "gpt-3.5-turbo"
MODEL_IMAGE = "gpt-4o-2024-11-20"

# Define the directory to watch (in iCloud Documents > SmartParseWatch)
WATCH_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Documents" / "SmartParseWatch"

# File extensions grouped by type
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".heic", ".heif", ".gif", ".bmp", ".tiff", ".tif"
}
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".html", ".htm", ".xhtml"
}
PDF_EXTENSION = ".pdf"

# Max files to queue for processing at a time
MAX_QUEUE_SIZE = 5
file_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)

def worker():
    while True:
        filepath = file_queue.get()
        if filepath is None:
            break
        FileHandler().handle_file(filepath)
        file_queue.task_done()

# Start the background worker
threading.Thread(target=worker, daemon=True).start()

# Note on Python function declarations:
# Functions are defined but not executed until they are called.
# This allows the script to define all necessary logic before any processing begins.

def mark_as_failed(filepath: Path):
    """
    Marks a file as failed by renaming it with a 'failed_' prefix in the same directory.
    This function is used to flag files that could not be processed successfully.
    """
    parent = filepath.parent
    failed_name = f"failed_{filepath.name}"
    failed_path = parent / failed_name
    try:
        filepath.rename(failed_path)
        print(f"Marked file as failed: {failed_path}")
        Notifier.notify(f"Could not process: {filepath.name}", title="SmartParse.AI", sound="default")
    except Exception as e:
        print(f"Could not mark file as failed ({filepath}): {e}")
    return failed_path

def move_file_to_subfolder(filepath: Path, folder_name: str):
    """
    Moves the given file to a specified subfolder within the WATCH_DIR.
    Creates the subfolder if it does not exist.
    """
    target_folder = WATCH_DIR / folder_name
    target_folder.mkdir(parents=True, exist_ok=True)
    target_path = target_folder / filepath.name
    filepath.rename(target_path)
    print(f"Moved file to: {target_path}")
    return target_path

# Handler class that responds to file system events such as file creation.
class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        print(f"Queued file: {filepath}")
        try:
            file_queue.put_nowait(filepath)
        except queue.Full:
            print(f"Queue full. Skipping file: {filepath}")

    def process_image(self, filepath):
        """
        Processes image files using GPT-4o vision model to generate a descriptive filename.
        Renames and moves the file to the 'images' subfolder.
        """
        print(f"Processing image: {filepath}")
        try:
            import base64

            with open(filepath, "rb") as img_file:
                image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that generates short, descriptive filenames "
                        "based on the visual content of the image. Return a short, descriptive filename using up to 7 lowercase words, "
                        "separated by underscores, followed by a category keyword such as photo, screenshot, illustration, diagram, cartoon, etc. "
                        "Use only lowercase words, no punctuation, and no file extensions. Separate the main description and keyword with an underscore. "
                        "Example: dog_riding_skateboard_photo"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{filepath.suffix[1:]};base64,{image_base64}"
                            },
                        }
                    ],
                },
            ]

            response = client.chat.completions.create(
                model=MODEL_IMAGE,
                messages=messages,
                max_tokens=20,
                temperature=0.2,
                n=1,
            )
            description = response.choices[0].message.content.strip()
            parts = description.lower().split()
            description = "_".join(parts)
            timestamp = get_file_datetime_string(filepath)
            new_name = f"{description}_{timestamp}{filepath.suffix.lower()}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed image to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "images")
            Notifier.notify("Image processed and renamed", title="SmartParse.AI")

        except Exception as e:
            print(f"Error processing image file {filepath}: {e}")
            mark_as_failed(filepath)

    def process_pdf(self, filepath):
        """
        Processes PDF files by extracting metadata or text to generate a descriptive filename.
        Renames and moves the file to the 'pdfs' subfolder.
        """
        print(f"Processing PDF: {filepath}")
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(filepath)
            # Try to get title from metadata
            title = doc.metadata.get("title", "")
            if title and title.strip():
                description = title.strip()
            else:
                # No title, extract text from first page
                text = ""
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    text = page.get_text().strip()
                if not text:
                    print(f"PDF {filepath} has no extractable text. Marking as failed.")
                    mark_as_failed(filepath)
                    return
                description = generate_filename_from_text(text, model=MODEL_PDF)
            # Clean description: replace spaces with underscores, lowercase, remove punctuation
            description = "_".join(description.lower().split())
            timestamp = get_file_datetime_string(filepath)
            new_name = f"{description}_{timestamp}{filepath.suffix.lower()}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed PDF to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "pdfs")
            Notifier.notify("PDF processed and renamed", title="SmartParse.AI")
        except Exception as e:
            print(f"Error processing PDF file {filepath}: {e}")
            mark_as_failed(filepath)

    def process_textfile(self, filepath):
        """
        Processes text files by reading their content, generating a descriptive filename,
        renaming, and moving them to the 'text' subfolder.
        Supports plain text and HTML files.
        """
        ext = filepath.suffix.lower()
        try:
            if ext in {".html", ".htm", ".xhtml"}:
                with open(filepath, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    text = soup.get_text(separator=' ', strip=True)
            else:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            if not text.strip():
                print(f"Text file {filepath} has insufficient content. Marking as failed.")
                mark_as_failed(filepath)
                return
            description = generate_filename_from_text(text, model=MODEL_TEXT)
            timestamp = get_file_datetime_string(filepath)
            new_name = f"{description}_{timestamp}{ext}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed file to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "text")
            Notifier.notify("Text file processed and renamed", title="SmartParse.AI")
        except Exception as e:
            print(f"Error processing text file {filepath}: {e}")
            mark_as_failed(filepath)

    def handle_file(self, filepath: Path):
        """
        Determines the file type based on extension and routes to the correct processor.
        """
        ext = filepath.suffix.lower()
        if ext == PDF_EXTENSION:
            self.process_pdf(filepath)
        elif ext in IMAGE_EXTENSIONS:
            self.process_image(filepath)
        elif ext in TEXT_EXTENSIONS:
            self.process_textfile(filepath)
        else:
            print(f"Unsupported file type: {filepath.name}")
            mark_as_failed(filepath)

def generate_filename_from_text(text: str, model: str) -> str:
    """
    Uses OpenAI's API to generate a short, descriptive filename based on provided text.
    The filename consists of up to 7 lowercase words separated by underscores,
    without any dates, punctuation, or file extensions.
    """
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant that generates short, descriptive filenames "
            "based on provided file content. Return a short, descriptive filename using up to "
            "7 lowercase words, separated by underscores. Do not include any dates, punctuation, or file extensions."
        )},
        {"role": "user", "content": text},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=20,
        temperature=0.2,
        n=1,
    )
    return response.choices[0].message.content.strip()

def get_file_datetime_string(file_path: Path) -> str:
    """
    Returns the file's creation time (preferred) or modification time if creation time is unavailable.
    The timestamp is formatted as 'YYYY-MM-DD_HH.MM.SS'.
    """
    try:
        # Try to get the creation time (macOS)
        timestamp = file_path.stat().st_birthtime
    except AttributeError:
        # Fallback to modified time (cross-platform)
        timestamp = file_path.stat().st_mtime

    # Format the timestamp to 'YYYY-MM-DD_HH.MM.SS'
    return time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime(timestamp))

# Main execution block to start the folder watcher
if __name__ == "__main__":
    print(f"Starting SmartParse.AI watcher on: {WATCH_DIR}")
    event_handler = FileHandler()
    observer = Observer()
    # Schedule the observer to watch the directory recursively
    observer.schedule(event_handler, str(WATCH_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)  # Keep the script alive
    except KeyboardInterrupt:
        observer.stop()
        print("Stopped SmartParse.AI watcher.")
        file_queue.put(None)  # Signal the worker to exit

    observer.join()