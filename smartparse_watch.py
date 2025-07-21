# smartparse_watch.py
# This script monitors a folder and its subfolders for new files (PDFs or images)
# and routes them to appropriate processing functions.

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from dotenv import load_dotenv
import openai
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import threading
import queue
import base64
import sys

try:
    from pync import Notifier
    notifier_available = True
except ImportError:
    notifier_available = False

# Load environment variables from .env file
load_dotenv()

openai.api_key = None
api_key = None
try:
    api_key = openai.api_key or None
except Exception:
    api_key = None

if not api_key:
    api_key = None
    try:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set")

client = openai.OpenAI(api_key=api_key)

# Define which model to use for each type
MODEL_TEXT = "gpt-3.5-turbo"
MODEL_PDF = "gpt-3.5-turbo"
MODEL_IMAGE = "gpt-4o-2024-11-20"

if len(sys.argv) > 1:
    WATCH_DIR = Path(sys.argv[1]).expanduser().resolve()
else:
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
file_queue: queue.Queue[Path] = queue.Queue(maxsize=MAX_QUEUE_SIZE)

def notify_user(message: str, title: str = "SmartParse.AI", sound: str = "default") -> None:
    """
    Sends a user notification if possible. Falls back to print if no GUI notifier is available.
    """
    if notifier_available:
        try:
            Notifier.notify(message, title=title, sound=sound)
        except Exception:
            print(f"Notification failed: {message}")
    else:
        print(f"{title}: {message}")

def worker() -> None:
    """
    Background worker thread that processes files from the queue.
    """
    while True:
        filepath = file_queue.get()
        if filepath is None:
            break
        FileHandler().handle_file(filepath)
        file_queue.task_done()
        if file_queue.empty():
            refill_queue()



# Start the background worker thread
threading.Thread(target=worker, daemon=True).start()


def refill_queue() -> None:
    """
    Scans the WATCH_DIR for any remaining unprocessed files and queues the next batch.
    Skips files already renamed or moved.
    """
    print("Scanning for additional files to queue...")
    try:
        files = list(WATCH_DIR.glob("*"))
        queued = 0
        for filepath in files:
            if (
                not filepath.is_file()
                or filepath.name.startswith("failed_")
                or filepath.name.startswith(".")  # Ignore hidden files like .DS_Store
                or filepath.parent != WATCH_DIR
                or queued >= MAX_QUEUE_SIZE
            ):
                continue
            try:
                file_queue.put_nowait(filepath)
                print(f"Re-queued file: {filepath}")
                queued += 1
            except queue.Full:
                print("Queue is full. Refill paused.")
                break
    except Exception as e:
        print(f"Error during refill queue scan: {e}")

def mark_as_failed(filepath: Path) -> Path:
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
        notify_user(f"Could not process: {filepath.name}")
    except Exception as e:
        print(f"Could not mark file as failed ({filepath}): {e}")
    return failed_path

def move_file_to_subfolder(filepath: Path, folder_name: str) -> Path:
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
    def on_created(self, event) -> None:
        """
        Called when a file or directory is created.
        """
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        print(f"Queued file: {filepath}")
        try:
            file_queue.put_nowait(filepath)
        except queue.Full:
            print(f"Queue full. Skipping file: {filepath}")

    def process_image(self, filepath: Path) -> None:
        """
        Processes image files using GPT-4o vision model to generate a descriptive filename.
        Renames and moves the file to the 'images' subfolder.
        """
        print(f"Processing image: {filepath}")
        try:
            with open(filepath, "rb") as img_file:
                image_data = img_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            messages = [
                {
                    "role": "system",
                    "content": (
    "You are a helpful assistant that generates short, descriptive filenames "
    "based on the visual and textual content of an image. If text is present, extract key themes, names, or messages. "
    "Return a filename with up to 10 lowercase words with no punctuation between words, followed by a single underscore and then a category keyword (e.g. quote, sign, cartoon). "
    "Do not include file extensions. "
    "Example: dog riding skateboard_photo "
    "Example: elie wiesel quote silence supports oppressor_quote"
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
                max_tokens=30,
                temperature=0.2,
                n=1,
            )
            description = response.choices[0].message.content.strip()
            description = description.lower().strip()
            timestamp = get_file_datetime_string(filepath)
            # Only add underscore before timestamp, not between words
            new_name = f"{description}_{timestamp}{filepath.suffix.lower()}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed image to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "images")
            notify_user("Image processed and renamed")

        except Exception as e:
            print(f"Error processing image file {filepath}: {e}")
            mark_as_failed(filepath)

    def process_pdf(self, filepath: Path) -> None:
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
                # Use metadata title only if it's likely meaningful
                check_description = generate_filename_from_text(title.strip(), model=MODEL_PDF)
                if check_description.lower().strip() != "title":
                    description = check_description
                else:
                    if doc.page_count > 0:
                        try:
                            page = doc.load_page(0)
                            text = page.get_text().strip()
                        except Exception as e:
                            print(f"Error extracting text from first page: {e}")
                            text = ""
                    else:
                        text = ""
                    if not text:
                        print(f"PDF {filepath} has no extractable text. Marking as failed.")
                        mark_as_failed(filepath)
                        return
                    description = generate_filename_from_text(text, model=MODEL_PDF)
            else:
                if doc.page_count > 0:
                    try:
                        page = doc.load_page(0)
                        text = page.get_text().strip()
                    except Exception as e:
                        print(f"Error extracting text from first page: {e}")
                        text = ""
                else:
                    text = ""
                if not text:
                    print(f"PDF {filepath} has no extractable text. Marking as failed.")
                    mark_as_failed(filepath)
                    return
                description = generate_filename_from_text(text, model=MODEL_PDF)
            # Clean description: lowercase with spaces, no underscores
            description = description.lower().replace("_", " ").strip()
            timestamp = get_file_datetime_string(filepath)
            new_name = f"{description}_{timestamp}{filepath.suffix.lower()}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed PDF to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "pdfs")
            notify_user("PDF processed and renamed")
        except Exception as e:
            print(f"Error processing PDF file {filepath}: {e}")
            mark_as_failed(filepath)

    def process_textfile(self, filepath: Path) -> None:
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
            description = description.lower().replace("_", " ").strip()
            timestamp = get_file_datetime_string(filepath)
            new_name = f"{description}_{timestamp}{ext}"
            new_path = filepath.with_name(new_name)
            filepath.rename(new_path)
            print(f"Renamed file to: {new_path}")
            moved_path = move_file_to_subfolder(new_path, "text")
            notify_user("Text file processed and renamed")
        except Exception as e:
            print(f"Error processing text file {filepath}: {e}")
            mark_as_failed(filepath)

    def handle_file(self, filepath: Path) -> None:
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
    The filename consists of up to 10 lowercase words with no punctuation between words,
    followed by a single underscore and a category keyword (e.g. article, report, draft).
    """
    messages = [
        {"role": "system", "content": (
            "You are a helpful assistant that generates short, descriptive filenames based on provided file content. Return a short, descriptive filename using up to 10 lowercase words with no punctuation between words, followed by a single underscore and then a category keyword (e.g. article, report, draft). Do not include file extensions. If applicable, prioritize including key identifiers such as paper titles, author names, organizations (e.g. McKinsey, Ministry of Housing, Columbia University), or publication dates.\n\nExample: product configuration in construction patrik jensen_article\nExample: 2024 housing policy report uk government_report"
        )},
        {"role": "user", "content": text},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=50,
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
    print(f"Running SmartParse.AI batch processor on: {WATCH_DIR}")

    try:
        files = list(WATCH_DIR.glob("*"))
        for filepath in files:
            if (
                filepath.is_file()
                and not filepath.name.startswith("failed_")
                and filepath.parent == WATCH_DIR
                and not filepath.name.startswith(".")
            ):
                try:
                    file_queue.put_nowait(filepath)
                    print(f"Queued file: {filepath}")
                except queue.Full:
                    print(f"Queue full. Skipping file: {filepath}")
                    break

        # Wait for queue to be processed and exit
        file_queue.join()
        file_queue.put(None)  # Signal the worker thread to exit

    except Exception as e:
        print(f"Batch processing failed: {e}")