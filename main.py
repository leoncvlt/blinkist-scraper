import argparse, sys, os, glob, time

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
parser.add_argument('--cooldown', type=check_cooldown, default=1, help='Seconds to wait between scraping books, and downloading audio files. Can\'t be smaller than 1')
parser.add_argument('--headless', action='store_true', default=False, help='Start the automated web browser in headless mode. Works only if you already logged in once')
parser.add_argument('--audio', action='store_true', default=True, help='Download the audio blinks for each book')
parser.add_argument('--concat-audio', action='store_true', default=False, help='Concatenate the audio blinks into a single file and tag it. Requires ffmpeg')
parser.add_argument('--no-scrape', action='store_true', default=False, help='Don\'t scrape the website, only process existing json files in the dump folder')
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

def finish(start_time, processed_books):
  elapsed_time = time.time() - start_time
  formatted_time = '{:02d}:{:02d}:{:02d}'.format(int(elapsed_time // 3600), int(elapsed_time % 3600 // 60), int(elapsed_time % 60))
  print(f"[#] Processed {processed_books} books in {formatted_time}")

if __name__ == '__main__':
  processed_books = 0
  start_time = time.time()
  try:
    if (args.no_scrape):
      # if the --no-scrape argument is passed, just process the existing json dump files
      for file in glob.glob(os.path.join("dump", "*.json")):
        process_book_json(file, processed_books)
    else:
      # if no login cookies were found, don't start a headless browser
      # so that the user can solve recaptcha and log in
      start_headless = args.headless
      if not scraper.has_login_cookies():
        start_headless = False
      driver = scraper.initialize_driver(headless=start_headless)
      is_logged_in = scraper.login(driver, args.email, args.password)
      if (is_logged_in):
        categories = scraper.get_categories(driver)
        for category in categories:
          books_urls = scraper.get_all_books_for_categories(driver, category)
          for book_url in books_urls:
            book_json, dump_exists = scraper.scrape_book(driver, book_url, category=category)
            if (args.audio):
              audio_files = scraper.scrape_book_audio(driver, book_json)
              if (audio_files and args.concat_audio):
                generator.combine_audio(book_json, audio_files)
            processed_books = process_book_json(book_json, processed_books)
            # if we processed the book from an existing dump 
            # no scraping was involved, no need to cooldown
            if not dump_exists:
              time.sleep(args.cooldown)
  except KeyboardInterrupt:
    print('[#] Interrupted by user')
    finish(start_time, processed_books)
    try:
      sys.exit(0)
    except SystemExit:
      os._exit(0)
    



