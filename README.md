# SmartParse.AI

SmartParse.AI is an intelligent file renaming and organization tool for macOS. It uses AI to generate meaningful filenames for PDFs, images, and text files based on their content, then sorts them into subfolders automatically.

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

SmartParse.AI aims to automate the renaming of files using AI-generated content summaries and timestamps, while keeping your files organized. It is particularly useful for managing screenshots, academic PDFs, meeting notes, and other content-rich files.

It is designed to be lightweight and non-intrusive, running only when triggered manually via a macOS right-click Finder action.

---

## ⚙️ Actions

- Watches a specified folder (`SmartParseWatch`) and all its subfolders.
- Detects new files and queues them for processing.
- Routes each file to a specific AI model based on type.
- Extracts metadata or content to generate a new filename.
- Renames and moves the file to an appropriate subfolder (`images`, `pdfs`, `text`).
- Sends macOS notifications when processing is complete or if a file fails.
- Optional automation via macOS Automator workflow (included) enables on-demand use without needing Terminal.
- Processes files in safe batches (default: 20), continuing automatically until the folder is empty.
- Includes race condition check to ensure large files are fully written before processing.

---

## 📥 Input

- Drop any supported file type into the `SmartParseWatch` folder.
- Supported formats:
  - Images: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.heif`, `.gif`, `.bmp`, `.tiff`, `.tif`
  - PDFs: `.pdf`
  - Text files: `.txt`, `.md`, `.csv`, `.html`, `.htm`, `.xhtml`

---

## 📤 Output

- Files are renamed to:  
  `descriptive text keyword_YYYY-MM-DD_HH.MM.SS.ext`

  - The filename contains a natural-language description (up to 10 lowercase words) with no punctuation, followed by a single underscore and a category keyword (e.g. quote, article, receipt, cartoon, diagram).
  - Category is inferred from file type and content.

- Example:
  - `smartphone_schematic_diagram_2025-07-19_14.22.03.png`
  - `modular_housing_case_study_2025-07-19_13.05.10.pdf`
- If a file cannot be processed, it is renamed with a `failed_` prefix and left in the watch folder.

---

## 🧠 Framework

- **Python 3.13.5**
- **OpenAI API** (gpt-3.5-turbo and gpt-4o)
- **PyMuPDF** for PDF processing
- **BeautifulSoup4 + lxml**
- **PyMuPDF** for metadata and visual text extraction in PDFs
- **macOS Automator** integration via Quick Action workflow
- **Race condition handling** for stable file readiness before processing
- **watchdog** for file system monitoring
- **pync** and `terminal-notifier` for macOS notifications

---

## 🛠️ Troubleshooting

- **Files not renamed?** Check if the file type is supported and readable. Failed files are prefixed with `failed_`.
- **Notifications not appearing?** Ensure Terminal has notification permission in System Settings > Notifications.
- **Queue stuck or lagging?** Limit drops to under 5 files at once. Use `MAX_QUEUE_SIZE` in the script to adjust.
- **OpenAI errors?** Confirm that your `.env` file contains a valid API key:  
  `OPENAI_API_KEY=your-key-here`
- **Still stuck?** Check the Terminal for error logs or debug messages printed during execution.

---