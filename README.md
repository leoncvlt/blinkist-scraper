# blinkist-scraper

A python script to download book summaries and audio from [Blinkist](https://www.blinkist.com/) and generate some pretty output files.

## Installation / Requirements

`pip install -r requirements.txt`

This script uses [ChromeDriver](chromedriver.chromium.org) to automate the Google Chrome browser - therefore Google Chrome needs to be installed in order to work.

## Usage

```text
usage: main.py [-h] [--language {de,en}] [--match-language]
               [--cooldown COOLDOWN] [--headless] [--audio] [--concat-audio]
               [--no-scrape] [--book BOOK] [--category CATEGORY]
               [--create-html] [--create-epub] [--create-pdf]
               email password                                              
                                                                              
Example with non-optional arguments                                           
                                                                              
positional arguments:                                                         
  email                The email to log into your premium Blinkist account    
  password             The password to log into your premium Blinkist account 
                                                                              
optional arguments:                                                           
  -h, --help           show this help message and exit
  --language {en,de}   The language to scrape books in - either 'en' for
                       english or 'de' for german (default en)
  --match-language     Skip scraping books if not in the requested language
                       (not all book are avaible in german, default false)
  --cooldown COOLDOWN  Seconds to wait between scraping books, and downloading
                       audio files. Can't be smaller than 1 (default 1)                  
  --headless           Start the automated web browser in headless mode. Works
                       only if you already logged in once (default false)                       
  --audio              Download the audio blinks for each book (default true)               
  --concat-audio       Concatenate the audio blinks into a single file and tag
                       it. Requires ffmpeg (default false)                                    
  --no-scrape          Don't scrape the website, only process existing json   
                       files in the dump folder (default false)
  --book BOOK          Scrapes this book only, takes the blinkist url for the
                       book (e.g. https://www.blinkist.com/en/books/... or
                       nhttps://www.blinkist.com/en/nc/reader/...)
  --category CATEGORY  When scraping a single book, categorize it under this
                       category (works with '--book' only)
  --create-html        Generate a formatted html document for the book (default true)        
  --create-epub        Generate a formatted epub document for the book (default true)       
  --create-pdf         Generate a formatted pdf document for the book.
                       Requires wkhtmltopdf (default false)                                   
```

## Basic usage
`python main.py email password` where email and password are the login details to your premium Blinkist account.

The script uses Selenium with a Chrome driver to scrape the site. Blinkist uses captchas on login, so the script will wait for the user to solve it and login on first run (although the email and password fields are filled in automatically from the arguments)  - the sessions cookies are stored so the script can be run in headless mode with the appropriate flag afterwards. The output files are stored in the `books` folder, arranged in subfolders by category and by the book's title and author.

## Customizing HTML output
The script builds a nice-looking html version of the book by using the 'book.html' and 'chapter.html' files in the 'templates' folder as a base. Every parameter between curly braces in those files (e.g. `{title}`) is replaced by the appropriate value from the book metadata (dumped in the `dump` folder upon scraping), following a 1-to-1 naming convention with the json parameters (.e.g `{title}` will be replaced by the `title` parameter, `{who_should_read}` but the `who_should_read` one and so on). 

The special field `{__chapters__}` is replaced with all the book's chapters. Chapters are created by parsing each `chapter` object in the book metadata and using the `chapter.html` template file in the same fashion, replacing tokens with the parameters inside the `chapter` object. 

## Generating .pdf
Add the `--create-pdf` argument to the script to generate a .pdf file from the .html one. This requires the [wkhtmltopdf](https://wkhtmltopdf.org/) tool to be installed and present in the PATH.

## Downloading audio
The script download audio blinks as well. This is done by waiting for a request to the Blinkist's `audio` endpoint in their `library` api for the first chapter's audio blink which is sent as soon as the user navigates to a book's reader page; then re-using the valid request's headers to build additional requests to the rest of the chapter's audio files. The files are downloaded as `.m4a`.

## Concatenating audio files
Add the `--concat-audio` argument to the script to concatenate the individual audio blinks into a single file and tag it with the appropriate book title and author. This requires the [ffmpeg](https://www.ffmpeg.org/) tool to be installed and present in the PATH.

## Processing book dumps with no scraping
During scraping, the script saves all book's metadata in json files inside the `dump` folder. Those can be used by the script to re-generate the .html, .epub and .pdf output files without having to scrape the website again. To do so, pass the `--no-scrape` argument to the script.

# Quirks & known Bugs
- Some people have had troubles when dealing with long generated book files (> 260 characters in Windows). Although this should be handled gracefully by the script, if you keep seeing "FileNotFoundError" when trying to create the .html / .m4a files, try and turn on long filenames support on your system: https://www.itprotoday.com/windows-10/enable-long-file-name-support-windows-10
