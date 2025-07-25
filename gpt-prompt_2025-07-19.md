Here’s a concise prompt you can paste into a new ChatGPT session to pick up where we left off:

⸻

I’m building a macOS utility script called SmartParse.AI using Python. It watches a folder for newly added files and renames them using GPT-generated descriptions, then moves them to subfolders by type (images, PDFss, text). It’s working well overall, but we need to debug and refine a few things.

✅ What’s Done So Far
	•	Watchdog detects files added to the SmartParseWatch folder.
	•	File types supported: images, PDFs, and text/HTML.
	•	Files are queued in batches (max 5 at a time) to avoid overload.
	•	GPT-4o is used for image descriptions; GPT-3.5-turbo for text and PDF.
	•	Notification support added using pync and terminal-notifier.
	•	Processed files are renamed using a structured format:
[description][category keyword][timestamp].[ext]
	•	Filenames exclude punctuation, and a model prompt enforces lowercase.

⚠️ Still to Fix
	1.	Underscore issue: Filenames are incorrectly replacing spaces in the description with underscores — the only underscore should appear between the description and the category keyword.
Example of what’s wrong:
elie_wiesel_quote_silence_supports_oppressor_quote_2019-11-03_17.08.24.jpg
What I want instead:
elie wiesel quote silence supports oppressor_quote_2019-11-03_17.08.24.jpg
	2.	Description accuracy for text-heavy images: The model sometimes ignores key quote content. The system prompt needs to stress using visible text as a clue for filenames.
	3.	Queue logic is working, but ensure the refill mechanism keeps processing all files in the watch folder until empty.
	4.	General polish: Add race condition checks (done), improve logging, and later extend support to other file types.

Please help me:
	•	Fix the filename formatting issue (#1 above)
	•	Verify that image processing uses text in the image when available
	•	Confirm the queue runs until all files are processed
	•	Keep filenames Spotlight-search-friendly (no special characters or punctuation between words)

The script is called smartparse_watch.py.

⸻

Let me know if you’d like this saved as a reusable snippet or turned into a .md file for your repo.