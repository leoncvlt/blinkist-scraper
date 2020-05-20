import argparse, sys, os, glob, time

from utils import get_book_pretty_filepath, get_book_pretty_filename

import scraper
import generator

def check_cooldown(value):
  ivalue = int(value)
  if ivalue < 1:
    raise argparse.ArgumentTypeError("Can't be smaller than 1")
  return ivalue

parser = argparse.ArgumentParser(description='Scrape blinkist.com and generate pretty output')
parser.add_argument('email', help='The email to log into your premium Blinkist account')
parser.add_argument('password', help='The password to log into your premium Blinkist account')
parser.add_argument('--language', choices={'en', 'de'}, default='en', help='The language to scrape books in - either \'en\' for english or \'de\' for german')
parser.add_argument('--match-language', action='store_true', default=False, help='Skip scraping books if not in the requested language (not all book are avaible in german)')
parser.add_argument('--cooldown', type=check_cooldown, default=1, help='Seconds to wait between scraping books, and downloading audio files. Can\'t be smaller than 1')
parser.add_argument('--headless', action='store_true', default=False, help='Start the automated web browser in headless mode. Works only if you already logged in once')
parser.add_argument('--audio', action='store_true', default=True, help='Download the audio blinks for each book')
parser.add_argument('--concat-audio', action='store_true', default=False, help='Concatenate the audio blinks into a single file and tag it. Requires ffmpeg')
parser.add_argument('--keep-noncat', action='store_true', default=False, help='Keep the individual blink audio files, instead of deleting them (works with \'--concat-audio\' only')
parser.add_argument('--no-scrape', action='store_true', default=False, help='Don\'t scrape the website, only process existing json files in the dump folder')
parser.add_argument('--book', default=False, help='Scrapes this book only, takes the blinkist url for the book (e.g. https://www.blinkist.com/en/books/... or nhttps://www.blinkist.com/en/nc/reader/...)')
parser.add_argument('--category', default="Uncategorized", help='When scraping a single book, categorize it under this category (works with \'--book\' only')
parser.add_argument('--create-html', action='store_true', default=True, help='Generate a formatted html document for the book')
parser.add_argument('--create-epub', action='store_true', default=True, help='Generate a formatted epub document for the book')
parser.add_argument('--create-pdf', action='store_true', default=False, help='Generate a formatted pdf document for the book. Requires wkhtmltopdf')
args = parser.parse_args()

def process_book_json(book_json, processed_books = 0):
  if (args.create_html): 
    generator.generate_book_html(book_json)
  if (args.create_epub): 
    generator.generate_book_epub(book_json)
  if (args.create_pdf): 
    generator.generate_book_pdf(book_json)
  return processed_books + 1

def scrape_book(driver, processed_books, book_url, category, match_language):
  book_json, dump_exists = scraper.scrape_book(driver, book_url, category=category, match_language=match_language)
  if (book_json):
    if (args.audio):

      # Check if we need to download audio (so that we don't have to revisit the webpage for each book, needlesly)
      filepath = get_book_pretty_filepath(book_json) # dl location
      concat_audio_filename = get_book_pretty_filename(book_json, ".m4a")
      concat_audio_exists = os.path.exists(os.path.join(filepath, concat_audio_filename))
      audio_files_in_folder = glob.glob1(filepath,"*.m4a") # switch to regex or loop
      audio_files_count = len(audio_files_in_folder)
      json_chapter_count = book_json['number_of_chapters']
      chapter_audio_is_complete = (audio_files_count == json_chapter_count)
      if (audio_files_in_folder and (not concat_audio_exists)):
        print(f"[.] Found {audio_files_count} out of {json_chapter_count}")
      if not (concat_audio_exists): # or if re-downloading individual tracks
        # check if we need more audio
        if (chapter_audio_is_complete): # or if concat_audio_exists
            # All of the audio has already been downloaded
            audio_files = audio_files_in_folder
            # add full path to each item in 'audio_files'
            for index in range(len(audio_files)):
              file_name = audio_files[index]
              full_path = os.path.join(filepath, file_name)
              audio_files[index] = full_path
            print("[.] Audio is already downloaded. Skipping.")
        else:
            audio_files = scraper.scrape_book_audio(driver, book_json, args.language)

        if (audio_files and args.concat_audio):
            generator.combine_audio(book_json, audio_files, args.keep_noncat)
      else:
        print("[.] Concated audio already exists. Skipping download.")
    processed_books = process_book_json(book_json, processed_books)
  return dump_exists

def finish(driver, start_time, processed_books):
  if (driver):
    driver.close()
  elapsed_time = time.time() - start_time
  formatted_time = '{:02d}:{:02d}:{:02d}'.format(int(elapsed_time // 3600), int(elapsed_time % 3600 // 60), int(elapsed_time % 60))
  print(f"[#] Processed {processed_books} books in {formatted_time}")

#  Add code to turn this into a callable function

if __name__ == '__main__':
  processed_books = 0
  print('[.] Init...')
  start_time = time.time()
  try:
    if (args.no_scrape):
      # if the --no-scrape argument is passed, just process the existing json dump files
      for file in glob.glob(os.path.join("dump", "*.json")):
        process_book_json(file, processed_books)
      finish(None, start_time, processed_books)
    else:
      match_language = args.language if args.match_language else ""
      # if no login cookies were found, don't start a headless browser
      # so that the user can solve recaptcha and log in
      start_headless = args.headless
      if not scraper.has_login_cookies():
        start_headless = False
      # add uBlock (if the conditions are right)
      if not (args.book or args.headless): # causes problems, I think
        use_ublock = True
      else:
        use_ublock = False
      driver = scraper.initialize_driver(headless=start_headless, uBlock=use_ublock)

      if (use_ublock):
        print('[..] Configuring uBlock')

        # set up uBlock
        driver.get('chrome-extension://ilchdfhfciidacichehpmmjclkbfaecg/settings.html')

        # Un-hide the file upload button so we can use it
        element = driver.find_elements_by_class_name("hidden")
        driver.execute_script("document.getElementsByClassName('hidden')[0].className = ''", element)
        driver.execute_script("window.scrollTo(0, 2000)") # scroll down (for debugging)
        uBlock_settings_file = str(os.path.join(os.getcwd(), "my-ublock-backup_2020-04-20_17.13.57.txt"))
        driver.find_element_by_id("restoreFilePicker").send_keys(uBlock_settings_file) #upload
        driver.switch_to.alert.accept() # click ok on pop up to accept overwrite
        print('[..] uBlock configured')

        # leave uBlock config
        driver.get("about:blank")

      print('[...] Starting Scraper, logging in. Loading homepage.')
      is_logged_in = scraper.login(driver, args.language, args.email, args.password)
      if (is_logged_in):
        if (args.book):
          scrape_book(driver, processed_books, args.book, category={ "label" : args.category}, match_language=match_language)
        else:
          categories = scraper.get_categories(driver, args.language)
          for category in categories:
            books_urls = scraper.get_all_books_for_categories(driver, category)
            for book_url in books_urls: 
              dump_exists = scrape_book(driver, processed_books, book_url, category=category, match_language=match_language)            
              # if we processed the book from an existing dump 
              # no scraping was involved, no need to cooldown
              if not dump_exists:
                time.sleep(args.cooldown)
        finish(driver, start_time, processed_books)
  except KeyboardInterrupt:
    print('[#] Interrupted by user')
    finish(driver, start_time, processed_books)
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    



