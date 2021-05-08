import argparse
import sys
import os
import glob
import time

import scraper
import generator
import logger

log = logger.get("blinkistscraper")


def scraped_audio_exists(book_json):
    from utils import get_book_pretty_filepath, get_book_pretty_filename

    filepath = get_book_pretty_filepath(book_json)
    concat_audio = os.path.join(
        filepath, get_book_pretty_filename(book_json, ".m4a"))
    existing_audio_files = []
    chapters = book_json["chapters"]
    chapter_count = len(chapters)

    for chapter in enumerate(chapters):
        # index = chapter[0]
        chapter_data = chapter[1]
        chapter_audio_filename = str(chapter_data["order_no"]) + ".m4a"
        chapter_audio_path = os.path.join(filepath, chapter_audio_filename)
        chapter_audio_exists = os.path.exists(chapter_audio_path)
        if chapter_audio_exists:
            existing_audio_files.append(chapter_audio_path)

    if not (os.path.exists(concat_audio)):
        if len(existing_audio_files) == chapter_count:
            # all audio blinks for the book have already been downloaded
            log.debug(f"Audio for all {chapter_count} blinks already exists")
            return existing_audio_files
        else:
            if len(existing_audio_files) > 0:
                log.debug(
                    f"Found audio files for {len(existing_audio_files)} out "
                    f"of {chapter_count} blinks"
                )
            return False
    else:
        log.debug("Concatenated audio already exists")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Scrape blinkist.com and generate pretty output"
    )

    parser.add_argument(
        "--language",
        choices={"en", "de"},
        default="en",
        help="The language to scrape books in - either 'en' for english or "
        "'de' for german"
    )
    parser.add_argument(
        "--match-language",
        action="store_true",
        default=False,
        help="Skip scraping books if not in the requested language (not all "
        "book are avaible in german)"
    )

    def check_cooldown(value):
        if int(value) < 1:
            raise argparse.ArgumentTypeError("Can't be smaller than 1")
        return int(value)

    parser.add_argument(
        "--cooldown",
        type=check_cooldown,
        default=1,
        help="Seconds to wait between scraping books, and downloading audio "
        "files. Can't be smaller than 1"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Start the automated web browser in headless mode. Works only if "
        "you already logged in once"
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        default=False,
        help="Download the audio blinks for each book"
    )
    parser.add_argument(
        "--concat-audio",
        action="store_true",
        default=False,
        help="Concatenate the audio blinks into a single file and tag it. "
        "Requires ffmpeg"
    )
    parser.add_argument(
        "--keep-noncat",
        action="store_true",
        default=False,
        help="Keep the individual blink audio files, instead of deleting them "
        "(works with '--concat-audio' only)"
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        default=False,
        help="Don't scrape the website, only process existing json files in "
        "the dump folder. Do not provide email or password with this option."
    )
    parser.add_argument(
        "--book",
        default=False,
        help="Scrapes this book only, takes the Blinkist URL for the book "
        "(e.g. https://www.blinkist.com/en/books/... or "
        "https://www.blinkist.com/en/nc/reader/...)"
    )
    parser.add_argument(
        "--daily-book",
        action="store_true",
        default=False,
        help="Scrapes the free daily book only."
    )
    parser.add_argument(
        "--books",
        default=False,
        help="Scrapes the list of books, takes a txt file with the list of "
        "Blinkist URL's for the books "
        "(e.g. https://www.blinkist.com/en/books/... "
        "or https://www.blinkist.com/en/nc/reader/...)"
    )
    parser.add_argument(
        "--book-category",
        default="Uncategorized",
        help="When scraping a single book, categorize it under this category "
        "(works only with '--daily-book', '--book', and '--books')"
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        default="",
        help="Only the categories whose label contains at least one string "
        "here will be scraped. Case-insensitive; use spaces to separate "
        "categories. (e.g. '--categories entrep market' will only scrape "
        "books under 'Entrepreneurship' and 'Marketing & Sales')"
    )
    parser.add_argument(
        "--ignore-categories",
        type=str,
        nargs="+",
        default="",
        help="If a category label contains anything in ignored_categories, "
        "books under that category will not be scraped. Case-insensitive; "
        "use spaces to separate categories. (e.g. '--ignored-categories entrep"
        " market' will skip scraping of 'Entrepreneurship' and 'Marketing & "
        "Sales')"
    )
    parser.add_argument(
        "--create-html",
        action="store_true",
        default=True,
        help="Generate a formatted html document for the book"
    )
    parser.add_argument(
        "--create-epub",
        action="store_true",
        default=True,
        help="Generate a formatted epub document for the book"
    )
    parser.add_argument(
        "--create-pdf",
        action="store_true",
        default=False,
        help="Generate a formatted pdf document for the book. Requires "
        "wkhtmltopdf"
    )
    parser.add_argument(
        "--save-cover",
        action="store_true",
        default=False,
        help="Save a copy of the Blink cover artwork in the folder"
    )
    parser.add_argument(
        "--embed-cover-art",
        action="store_true",
        default=False,
        help="Embed the Blink cover artwork into the concatenated audio file "
        "(works with '--concat-audio' only)"
    )
    parser.add_argument(
        "--chromedriver",
        help="Path to a specific chromedriver executable instead of the built-"
        "in one"
    )
    parser.add_argument(
        "--no-ublock",
        action="store_true",
        default=False,
        help="Disable the uBlock Chrome extension. "
        "This will completely skip the installation (and setup) of ublock. "
        "If you want to use ublock content blocking, then run the script "
        "again without this flag."
    )
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        default=False,
        help="When running as root (e.g. in Docker), Chrome requires the "
        "'--no-sandbox' argument",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Increases logging verbosity"
    )

    if "--no-scrape" not in sys.argv:
        parser.add_argument(
            "email",
            help="The email to log into your premium Blinkist account"
        )
        parser.add_argument(
            "password",
            help="The password to log into your premium Blinkist account"
        )

    args = parser.parse_args()

    # set up logger verbosity
    logger.set_verbose(log, args.verbose)

    def generate_book_outputs(book_json, cover_img=False):
        if args.create_html:
            generator.generate_book_html(book_json, cover_img)
        if args.create_epub:
            generator.generate_book_epub(book_json)
        if args.create_pdf:
            generator.generate_book_pdf(book_json, cover_img)

    def scrape_book(
        driver, processed_books, book_url, category, match_language
    ):
        book_json, dump_exists = scraper.scrape_book_data(
            driver, book_url, category=category, match_language=match_language
        )
        if book_json:
            cover_img_file = False
            cover_tmp_file = False
            if args.audio:
                audio_files = scraped_audio_exists(book_json)
                if not audio_files:
                    audio_files = scraper.scrape_book_audio(
                        driver, book_json, args.language
                    )
                if audio_files and args.concat_audio:
                    if type(audio_files) == list:
                        if args.embed_cover_art:
                            cover_tmp_file = scraper.download_book_cover_image(
                                book_json, filename="_cover.jpg",
                                alt_file="cover.jpg"
                            )
                        generator.combine_audio(
                            book_json, audio_files, args.keep_noncat,
                            cover_tmp_file
                        )
            if args.save_cover:
                cover_img_file = scraper.download_book_cover_image(
                    book_json, filename="cover.jpg", alt_file="_cover.jpg"
                )
                generate_book_outputs(book_json, cover_img=cover_img_file)
            else:
                generate_book_outputs(book_json)
            if cover_tmp_file:
                if os.path.exists(cover_tmp_file):
                    log.debug(f"Deleting {cover_tmp_file}")
                    os.remove(cover_tmp_file)
                else:
                    log.debug(f'Could not find "{cover_tmp_file}"')
            processed_books.append(book_url)
        return dump_exists

    def finish(start_time, processed_books, driver=None):
        if driver:
            driver.close()
        elapsed_time = time.time() - start_time
        formatted_time = "{:02d}:{:02d}:{:02d}".format(
            int(elapsed_time // 3600),
            int(elapsed_time % 3600 // 60),
            int(elapsed_time % 60),
        )
        total_books = len(processed_books)
        log.info(
            f"Processed {total_books} book{'s' if total_books != 1 else ''} "
            f"in {formatted_time}"
        )

    # start scraping
    log.info("Starting scrape run...")
    processed_books = []
    start_time = time.time()

    if args.no_scrape:
        # if the --no-scrape argument is passed, just process the
        # existing json dump files
        for file in glob.glob(os.path.join(os.getcwd(), "dump", "*.json")):
            generate_book_outputs(file)
            processed_books.append(file)
        finish(start_time, processed_books)
    else:
        match_language = args.language if args.match_language else ""
        start_headless = args.headless
        # add uBlock (except on headless)
        use_ublock = not args.no_ublock and not args.headless
        driver = scraper.initialize_driver(
            headless=start_headless,
            with_ublock=use_ublock,
            no_sandbox=args.no_sandbox,
            chromedriver_path=args.chromedriver,
        )

        is_logged_in = scraper.login(
            driver, args.language, args.email, args.password)
        if is_logged_in:
            if args.book or args.daily_book:
                # scrape single book
                book_url = (
                    args.book
                    if not args.daily_book
                    else scraper.get_daily_book_url(driver, args.language)
                )
                scrape_book(
                    driver,
                    processed_books,
                    book_url,
                    category={"label": args.book_category},
                    match_language=match_language,
                )
            elif args.books:
                # scrape list of books
                with open(args.books, "r") as books_urls:
                    for book_url in books_urls.readlines():
                        dump_exists = scrape_book(
                            driver,
                            processed_books,
                            book_url.strip(),
                            category={"label": args.book_category},
                            match_language=match_language,
                        )
                        if not dump_exists:
                            time.sleep(args.cooldown)
            else:
                # scrape all categories
                categories = scraper.get_categories(
                    driver,
                    args.language,
                    specified_categories=args.categories,
                    ignored_categories=args.ignore_categories,
                )
                for category in categories:
                    books_urls = scraper.get_all_books_for_categories(
                        driver, category)
                    for book_url in books_urls:
                        dump_exists = scrape_book(
                            driver,
                            processed_books,
                            book_url,
                            category=category,
                            match_language=match_language,
                        )
                        # if we processed the book from an existing dump
                        # no scraping was involved, no need to cooldown
                        if not dump_exists:
                            time.sleep(args.cooldown)
                # scrape all books to process uncategorized books
                all_books = scraper.get_all_books(driver, match_language)
                uncategorized_books = [
                    x for x in all_books if x not in processed_books]
                log.info(
                    f"Scraping {len(uncategorized_books)} remaining "
                    "uncategorized books..."
                )
                for book_url in uncategorized_books:
                    dump_exists = scrape_book(
                        driver,
                        processed_books,
                        book_url,
                        category={"label": "Uncategorized"},
                        match_language=match_language,
                    )
                    if not dump_exists:
                        time.sleep(args.cooldown)
        else:
            log.error("Unable to login into Blinkist")
        finish(start_time, processed_books, driver)


# operating-system level exit
def sys_exit():
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)


# catch all errors and exit properly
try:
    main()

# exiting via keyboard
except KeyboardInterrupt:
    log.critical("Interrupted by user")
    sys_exit()

# other errors...
except Exception as e:
    log.exception(e)
    log.critical('Uncaught Exception. Exiting...')
    sys_exit()
