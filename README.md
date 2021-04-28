# blinkist-scraper

A python script to download book summaries and audio from [Blinkist](https://www.blinkist.com/) and generate some pretty output files.

## Installation / Requirements

Make sure you're in your virtual environment of choice, then run
- `poetry install --no-dev` if you have [Poetry](https://python-poetry.org/) installed
- `pip install -r requirements.txt` otherwise

This script uses [ChromeDriver](chromedriver.chromium.org) to automate the Google Chrome browser - therefore Google Chrome needs to be installed in order to work.

The script will automatically try to download and use the appropriate chromedriver distribution for your OS and Chrome version. If this doesn't work, download the right version for you from https://chromedriver.chromium.org/downloads and use the `--chromedriver` argument to specify its path at runtime.

## Usage

```text
usage: blinkistscraper [-h] [--language {en,de}] [--match-language]
                       [--cooldown COOLDOWN] [--headless] [--audio]
                       [--concat-audio] [--keep-noncat] [--no-scrape]
                       [--book BOOK] [--daily-book] [--books BOOKS]
                       [--book-category BOOK_CATEGORY]
                       [--categories CATEGORIES [CATEGORIES ...]]
                       [--ignore-categories IGNORE_CATEGORIES [IGNORE_CATEGORIES ...]]
                       [--create-html] [--create-epub] [--create-pdf]
                       [--save-cover] [--embed-cover-art] 
                       [--chromedriver CHROMEDRIVER] [--no-ublock] [--no-sandbox] [-v]
                       email password

positional arguments:
  email                 The email to log into your premium Blinkist account
  password              The password to log into your premium Blinkist account

optional arguments:
  -h, --help            show this help message and exit
  --language {en,de}    The language to scrape books in - either 'en' for
                        english or 'de' for german
  --match-language      Skip scraping books if not in the requested language
                        (not all book are avaible in german)
  --cooldown COOLDOWN   Seconds to wait between scraping books, and
                        downloading audio files. Can't be smaller than 1
  --headless            Start the automated web browser in headless mode.
                        Works only if you already logged in once
  --audio               Download the audio blinks for each book.
  --concat-audio        Concatenate the audio blinks into a single file and
                        tag it. Requires ffmpeg
  --keep-noncat         Keep the individual blink audio files, instead of
                        deleting them (works with '--concat-audio' only)
  --no-scrape           Don't scrape the website, only process existing json
                        files in the dump folder. Do not provide email or
                        password with this option.
  --book BOOK           Scrapes this book only, takes the Blinkist URL for the
                        book (e.g. https://www.blinkist.com/en/books/... or
                        https://www.blinkist.com/en/nc/reader/...)
  --daily-book          Scrapes the free daily book only.
  --books BOOKS         Scrapes the list of books, takes a txt file with the
                        list of Blinkist URL's for the books (e.g.
                        https://www.blinkist.com/en/books/... or
                        https://www.blinkist.com/en/nc/reader/...)
  --book-category BOOK_CATEGORY
                        When scraping a single book, categorize it under this
                        category (works with '--book' and '--daily-book' only)
  --categories CATEGORIES [CATEGORIES ...]
                        Only the categories whose label contains at least one
                        string here will be scraped. Case-insensitive; use
                        spaces to separate categories. (e.g. '--categories
                        entrep market' will only scrape books under
                        'Entrepreneurship' and 'Marketing & Sales')
  --ignore-categories IGNORE_CATEGORIES [IGNORE_CATEGORIES ...]
                        If a category label contains anything in
                        ignored_categories, books under that category will not
                        be scraped. Case-insensitive; use spaces to separate
                        categories. (e.g. '--ignored-categories entrep market'
                        will skip scraping of 'Entrepreneurship' and
                        'Marketing & Sales')
  --create-html         Generate a formatted html document for the book
  --create-epub         Generate a formatted epub document for the book
  --create-pdf          Generate a formatted pdf document for the book.
                        Requires wkhtmltopdf
  --save-cover          Save a copy of the Blink cover artwork in the folder
  --embed-cover-art     Embed the Blink cover artwork into the concatenated
                        audio file (works with '--concat-audio' only)
  --chromedriver CHROMEDRIVER
                        Path to a specific chromedriver executable instead of
                        the built-in one
  --no-ublock           Disable the uBlock Chrome extension. This will
                        completely skip the installation (and setup) of
                        ublock. If you want to use ublock content blocking, then
                        run the script again without this flag.
  --no-sandbox          When running as root (e.g. in Docker), Chrome requires
                        the '--no-sandbox' argument     
  -v, --verbose         Increases logging verbosity
```

## Basic usage
`python blinkistscraper email password` where email and password are the login details to your premium Blinkist account.

The script uses Selenium with a Chrome driver to scrape the site automatically using the provided credentials. Sometimes during scraping, a captcha block-page will appear. When this happens, the script will try to pause and wait for the user to solve it. After some time (i.e. one minute), the script will time out.
The output files are stored in the `books` folder, arranged in subfolders by category and by the book's title and author.

## Customizing HTML output
The script builds a nice-looking html version of the book by using the 'book.html' and 'chapter.html' files in the 'templates' folder as a base. Every parameter between curly braces in those files (e.g. `{title}`) is replaced by the appropriate value from the book metadata (dumped in the `dump` folder upon scraping), following a 1-to-1 naming convention with the json parameters (.e.g `{title}` will be replaced by the `title` parameter, `{who_should_read}` but the `who_should_read` one and so on).

The special field `{__chapters__}` is replaced with all the book's chapters. Chapters are created by parsing each `chapter` object in the book metadata and using the `chapter.html` template file in the same fashion, replacing tokens with the parameters inside the `chapter` object.

## Generating .pdf
Add the `--create-pdf` argument to the script to generate a .pdf file from the .html one. This requires the [wkhtmltopdf](https://wkhtmltopdf.org/) tool to be installed and present in the PATH.

## Downloading audio
The script download audio blinks as well when adding the `--audio` argument. This is done by waiting for a request to the Blinkist's `audio` endpoint in their `library` api for the first chapter's audio blink which is sent as soon as the user navigates to a book's reader page; then re-using the valid request's headers to build additional requests to the rest of the chapter's audio files. The files are downloaded as `.m4a`.

## Concatenating audio files
Add the `--concat-audio` argument to the script to concatenate the individual audio blinks into a single file and tag it with the appropriate book title and author. Doing this will delete all individual blinks and replace them with one audio file (per book), only. To keep both the individual blink audio files, also, use the `--keep-noncat` argument together with the `--concat-audio` argument (i.e. `--concat-audio --keep-noncat`). This requires the [ffmpeg](https://www.ffmpeg.org/) tool to be installed and present in the PATH.

## Processing book dumps with no scraping
During scraping, the script saves all book's metadata in json files inside the `dump` folder. Those can be used by the script to re-generate the .html, .epub and .pdf output files without having to scrape the website again. To do so, pass the `--no-scrape` argument to the script without providing an email or a password.

## Scraping with a free account
If you don't have a Blinkist premium account, you can still scrape the free daily book. To do so automatically, pass the `--daily-book` argument - this behaves like scraping a single book.

## Quirks & known Bugs
- Some people have had troubles when dealing with long generated book files (> 260 characters in Windows). Although this should be handled gracefully by the script, if you keep seeing "FileNotFoundError" when trying to create the .html / .m4a files, try and turn on long filenames support on your system: https://www.itprotoday.com/windows-10/enable-long-file-name-support-windows-10, and make sure you have a recent distribution of ffmpeg if using it (old versions had some bugs in dealing with long filenames)

## Support [![Buy me a coffee](https://img.shields.io/badge/-buy%20me%20a%20coffee-lightgrey?style=flat&logo=buy-me-a-coffee&color=FF813F&logoColor=white "Buy me a coffee")](https://www.buymeacoffee.com/leoncvlt)
If this tool has proven useful to you, consider [buying me a coffee](https://www.buymeacoffee.com/leoncvlt) to support development of this and [many other projects](https://github.com/leoncvlt?tab=repositories).
