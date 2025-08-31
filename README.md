# SmartParse.AI

SmartParse.AI is an intelligent file renaming and organization tool for macOS. It uses AI to generate meaningful filenames for PDFs, images, and text files based on their content, then sorts them into subfolders automatically and assigns Finder tags.

---

### 🖱️ Quick Action (macOS Finder Right-Click)

To enable the right-click Finder action for SmartParse.AI:

1. Download or clone this repo.
2. Open the `SmartParse.workflow` file.
3. Double-click it to install into Automator.
4. Once added, right-click the `SmartParseWatch` folder in Finder and choose `Quick Actions → Run SmartParse.AI`.

This will run the script in batch mode, renaming and organizing all files in the watch folder.

Requires: Python 3.13, and the script path inside the workflow may need to be updated depending on your local setup.

## 📌 Intent

SmartParse.AI aims to automate the renaming of files using AI-generated content summaries and timestamps, while keeping your files organized with intelligent Finder tagging. It is particularly useful for managing screenshots, academic PDFs, meeting notes, and other content-rich files.

It is designed to be lightweight and non-intrusive, running only when triggered manually via a macOS right-click Finder action.

---

## ⚙️ Actions

- Watches a specified folder (`SmartParseWatch`) and all its subfolders.
- Detects new files and queues them for processing.
- Routes each file to a specific AI model based on type.
- Extracts metadata or content to generate a new filename.
- Renames and moves the file to an appropriate subfolder (`images`, `pdfs`, `text`).
- Assigns Finder tags based on content type and file category.
- Shows a persistent dialog with batch processing summary.
- Logs all operations to a JSON file for troubleshooting and auditing.
- Optional automation via macOS Automator workflow (included) enables on-demand use without needing Terminal.
- Processes files in safe batches (default: 20), continuing automatically until the folder is empty.
- Includes race condition check to ensure large files are fully written before processing.

---

## 📥 Input

- Drop any supported file type into the `SmartParseWatch` folder.
- Supported formats:
  - **Images:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`, `.gif`, `.bmp`, `.tiff`, `.tif`
  - **PDFs:** `.pdf`
  - **Text files:** `.txt`, `.md`, `.csv`, `.html`, `.htm`, `.xhtml`
  - **Microsoft Office:** `.docx`, `.xlsx`, `.pptx` (legacy formats `.doc`, `.xls`, `.ppt` are marked as failed)

---

## 📤 Output

- Files are renamed to:  
  `descriptive text_YYYY-MM-DD_HH.MM.SS.ext`

  - The description is lowercased natural language with no punctuation, followed by a timestamp.
  - Image filenames are longer for better searchability.
  - Category is assigned as a Finder tag (not in the filename).

- **Description Length by File Type:**
  - **Images:** 10–12 words by default. If the image contains visible text, the filename can extend up to 16 words to capture key text and sentiment.
  - **PDFs:** 7–10 words.
  - **Text/Office:** 7–10 words.

- **Finder Tags by File Type:**
  - **PDFs:** Tags (e.g., "Academic Paper", "Receipt", "Report")
  - **Images:** Tags (e.g., "Photo", "Screenshot", "Diagram")
  - **Text:** Tags (e.g., "Notes", "Draft", "Transcript")

- Examples:
  - `product configuration in construction patrik jensen_2025-07-19_13.05.10.pdf` (tagged: "Academic Paper")
  - `smartphone schematic diagram technical specifications with labeled components_2025-07-19_14.22.03.png` (tagged: "Diagram")
  - `event banner read join us today community cleanup saturday 10am_2025-07-19_15.40.12.png` (image with text; tagged: "Sign")
  - If a file cannot be processed, it is renamed with a `failed_` prefix and left in the watch folder.

---

## 🧠 Framework

- **Python 3.13.5**
- **OpenAI API** (gpt-3.5-turbo and gpt-4o)
- **PyMuPDF** for PDF processing
- **BeautifulSoup4 + lxml** for HTML parsing
- **python-docx, openpyxl, python-pptx** for Microsoft Office files
- **macos-tags** for Finder tag management
- **macOS Automator** integration via Quick Action workflow
- **Race condition handling** for stable file readiness before processing
- **watchdog** for file system monitoring
- **pync** and `terminal-notifier` for macOS notifications

---

## 🛠️ Troubleshooting

- **Files not renamed?** Check if the file type is supported and readable. Failed files are prefixed with `failed_`.
- **Tags not appearing?** Ensure the script has permission to modify Finder tags. New tags should appear in Finder.
- **Queue stuck or lagging?** Limit drops to under 5 files at once. Use `MAX_QUEUE_SIZE` in the script to adjust.
- **OpenAI errors?** Confirm that your `.env` file contains a valid API key:  
  `OPENAI_API_KEY=your-key-here`
- **ModuleNotFoundError for `macos_tags`?**
    - This means your script is not running in the correct Python virtual environment. You must activate your virtual environment before running the script, or use the full path to the Python interpreter in your venv.
    - **Example:**
      ```sh
      # Activate your virtual environment and run the script
      source ~/python-venv/bin/activate  # Ensures all required packages are available
      python3 **`/path/to/your/SmartParse.AI/smartparse_watch.py`**
      ```
      # Or, run directly with the venv's Python interpreter (recommended for Automator):
      ~/python-venv/bin/python **`/path/to/your/SmartParse.AI/smartparse_watch.py`**
      ```
    - This ensures the script uses the correct environment and all installed packages.
- **Dialog not appearing?** The summary dialog appears after all files are processed. Check that the script completed successfully.
- **Log files?** Check `logs/smartparse_log.jsonl` for detailed operation history and troubleshooting.
- **Still stuck?** Check the Terminal for error logs or debug messages printed during execution.

---

## 🚀 Roadmap & Future Features

- **Colored Finder Tags:** Enhanced tag system with automatic color coding (PDFs: Red, Images: Yellow, Text: Blue)
- **Batch Processing Improvements:** Better handling of large file drops and progress indicators
- **Custom Tag Categories:** User-configurable tag categories and naming conventions
