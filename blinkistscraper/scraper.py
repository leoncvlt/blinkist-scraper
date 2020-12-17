import os, time, requests, subprocess, argparse, json, pickle, html, argparse, time, re, sys, platform
from shutil import copyfile as copy_file
from datetime import datetime

import chromedriver_autoinstaller
from seleniumwire import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from utils import *
import logger

log = logger.get(f"blinkistscraper.{__name__}")


def has_login_cookies():
    return os.path.exists("cookies.pkl")


def get_login_cookies():
    return pickle.load(open("cookies.pkl", "rb"))


def load_login_cookies(driver):
    for cookie in get_login_cookies():
        # selenium doesn't like float-based cookies parameters
        # if 'expiry' in cookie:
        #   cookie['expiry'] = int(cookie['expiry'])
        driver.add_cookie(cookie)


def store_login_cookies(driver):
    pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))


def initialize_driver(headless=True, with_ublock=False, chromedriver_path=None):
    if not chromedriver_path:
        try:
            chromedriver_path = chromedriver_autoinstaller.install()
        except Exception as exception:
            log.critical(
                f"Failed to install the built-in chromedriver: {exception}\n"
                "download the correct version for your system at "
                "https://chromedriver.chromium.org/downloads and use the"
                "--chromedriver argument to point to the chromedriver executable"
            )
            sys.exit()

    log.info(f"Initialising chromedriver at {chromedriver_path}...")
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-logging")
    # allows selenium to accept cookies with a non-int64 'expiry' value
    chrome_options.add_experimental_option("w3c", False)
    # removes the 'DevTools listening' log message
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # prevent Cloudflare from detecting ChromeDriver as bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    if with_ublock:
        chrome_options.add_extension(
            os.path.join(os.getcwd(), "bin", "ublock", "ublock-extension.crx")
        )

    logs_path = os.path.join(os.getcwd(), "logs")
    if not (os.path.isdir(logs_path)):
        os.makedirs(logs_path)

    driver = webdriver.Chrome(
        executable_path=chromedriver_path,
        service_log_path=os.path.join(logs_path, "webdrive.log"),
        # Don't verify self-signed cert, should help with 502 errors
        # (https://github.com/wkeeling/selenium-wire/issues/55)
        # seleniumwire_options={"verify_ssl": False},
        options=chrome_options,
    )

    if with_ublock:
        log.debug("Configuring uBlock")

        # set up uBlock
        driver.get("chrome-extension://ilchdfhfciidacichehpmmjclkbfaecg/settings.html")

        # Un-hide the file upload button so we can use it
        element = driver.find_elements_by_class_name("hidden")
        driver.execute_script(
            "document.getElementsByClassName('hidden')[0].className = ''", element
        )
        # scroll down (for debugging)
        driver.execute_script("window.scrollTo(0, 2000)")
        uBlock_settings_file = str(
            os.path.join(os.getcwd(), "bin", "ublock", "ublock-settings.txt")
        )
        driver.find_element_by_id("restoreFilePicker").send_keys(uBlock_settings_file)
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            # click ok on pop up to accept overwrite
            driver.switch_to.alert.accept()
        except TimeoutException as ex:
            log.error("Timeout waiting for ublock config overwrite alert")
        # leave uBlock config
        driver.get("about:blank")

    return driver


def login(driver, language, email, password):
    # we need to navigate to a page first in order to load eventual cookies
    driver.get(f"https://www.blinkist.com/{language}")
    is_logged_in = False

    # if we have any stored login cookie, load them into the driver
    if has_login_cookies():
        load_login_cookies(driver)

    # navigate to the login page and check for the login email input
    # if not found, assume we're logged in
    sign_in_url = f"https://www.blinkist.com/{language}/nc/login"
    driver.get(sign_in_url)
    try:
        driver.find_element_by_id("login-form_login_email")
    except NoSuchElementException:
        is_logged_in = True
    # try:
    #     WebDriverWait(driver, 360).until(
    #         EC.presence_of_element_located((By.ID, "login-form_login_email"))
    #     )
    # except TimeoutException as ex:
    #     log.error("Error logging in.")
    #     return False

    # if not logged in, autofill the email and password inputs with the provided data
    # the user will still have to solve the captcha and click the log in button afterwards
    if not is_logged_in:
        log.info("Not logged into Blinkist: navigating to sign in page...")
        driver.find_element_by_id("login-form_login_email").send_keys(email)
        driver.find_element_by_id("login-form_login_password").send_keys(password)
        log.info("Waiting for user to solve recaptcha and log in...")

    try:
        WebDriverWait(driver, 360).until(
            EC.presence_of_element_located((By.CLASS_NAME, "main-banner-headline-v2"))
        )
    except TimeoutException as ex:
        log.error("Error logging in.")
        return False

    # login successful, store login cookies for future operations
    store_login_cookies(driver)
    return True


def get_categories(driver, language, specified_categories=None, ignored_categories=[]):
    url_with_categories = f"https://www.blinkist.com/{language}/nc/login"
    driver.get(url_with_categories)
    categories_links = []

    # click the discover dropdown to reveal categories links
    try:
        categories_menu = driver.find_element_by_class_name("header-menu__trigger")
        categories_menu.click()
    except NoSuchElementException:
        log.warning(f"Could not find categories dropdown element")

    # find the categories links container
    categories_list = None
    categories_elements = ["discover-menu__categories", "category-list"]
    for classname in categories_elements:
        try:
            categories_list = driver.find_element_by_class_name(classname)
            break
        except:
            log.warning(
                f"Could not find categories container element with class '{classname}'"
            )

    # parse the invidual category links
    categories_items = categories_list.find_elements_by_tag_name("li")
    for item in categories_items:
        link = item.find_element_by_tag_name("a")
        href = link.get_attribute("href")
        label = link.find_element_by_tag_name("span").get_attribute("innerHTML")

        # Do not add this category if specific_categories is specified AND
        # the label doesn't contain anything specified there
        if specified_categories:
            if not list(
                filter(lambda oc: oc.lower() in label.lower(), specified_categories)
            ):
                continue
        # Do not add this category if the label contains any strings from ignored_categories
        if list(filter(lambda ic: ic.lower() in label.lower(), ignored_categories)):
            continue

        category = {"label": " ".join(label.split()).replace("&amp;", "&"), "url": href}
        categories_links.append(category)
    log.info(f"Scraping for categories: {[ c['label'] for c in categories_links ]}")
    return categories_links


def get_all_books_for_categories(driver, category):
    log.info(f"Getting all books for category {category['label']}...")
    books_links = []
    driver.get(category["url"] + "/books")
    books_items = driver.find_elements_by_class_name("letter-book-list__item")
    for item in books_items:
        href = item.get_attribute("href")
        books_links.append(href)
    log.info(f"Found {len(books_links)} books")
    return books_links


def get_all_books(driver, language):
    log.info(f"Getting all Blinkist books from sitemap...")
    all_books_links = []
    driver.get("https://www.blinkist.com/en/sitemap")
    books_items = driver.find_elements_by_css_selector(
        f".sitemap__section.sitemap__section--books a[href$='{language}']"
    )
    for item in books_items:
        href = item.get_attribute("href")
        all_books_links.append(href)
    log.info(f"Found {len(all_books_links)} books")
    return all_books_links


def get_daily_book_url(driver, language):
    driver.get(f"https://www.blinkist.com/{language}/nc/daily")
    daily_book_url = driver.find_element_by_css_selector(".daily-book__infos a")
    if daily_book_url:
        return daily_book_url.get_attribute("href")
    else:
        return ""


def scrape_book_data(
    driver, book_url, match_language="", category={"label": "Uncategorized"}, force=False
):
    # check if this book has already been dumped, unless we are forcing scraping
    # if so return the content of the dump, alonside with a flash saying it already existed
    if os.path.exists(get_book_dump_filename(book_url)) and not force:
        log.debug(f"Json dump for book {book_url} already exists, skipping scraping...")
        with open(get_book_dump_filename(book_url)) as f:
            return json.load(f), True

    # if not, proceed scraping the reader page
    log.info(f"Scraping book at {book_url}")
    if not "/nc/reader/" in book_url:
        book_url = book_url.replace("/books/", "/nc/reader/")
    if not driver.current_url == book_url:
        driver.get(book_url)
    reader = driver.find_element_by_class_name("reader__container")

    # get the book's metadata from the blinkist API using its ID
    book_id = reader.get_attribute("data-book-id")
    book_json = requests.get(url=f"https://api.blinkist.com/v4/books/{book_id}").json()
    book = book_json["book"]

    if match_language and book["language"] != match_language:
        log.warning(
            f"Book not available in the selected language ({match_language}), skipping scraping..."
        )
        return None, False

    # sanitize the book's title and author since they will be used for paths and such
    book["title"] = sanitize_name(book["title"])
    book["author"] = sanitize_name(book["author"])

    # check if the book's metadata already has chapter content
    # (this is the case for the free book of the day)
    json_needs_content = False
    for chapter_json in book["chapters"]:
        if not "text" in chapter_json:
            json_needs_content = True
            break
        else:
            # change the text content key name for compatibility with the script methods
            chapter_json["content"] = chapter_json.pop("text")

    if json_needs_content:
        # scrape the chapter's content on the reader page
        # and extend the book json data by inserting the scraped content
        # in the appropriate chapter section to get a complete data file
        book_chapters = driver.find_elements(By.CSS_SELECTOR, ".chapter.chapter")
        for chapter in book_chapters:
            chapter_no = chapter.get_attribute("data-chapterno")
            chapter_content = chapter.find_element_by_class_name("chapter__content")
            for chapter_json in book["chapters"]:
                if chapter_json["order_no"] == int(chapter_no):
                    chapter_json["content"] = chapter_content.get_attribute("innerHTML")
                    break

        # look for any supplement sections
        book_supplements = driver.find_elements(By.CSS_SELECTOR, ".chapter.supplement")
        for supplement in book_supplements:
            chapter_no = supplement.get_attribute("data-chapterno")
            supplement_content = chapter.find_element_by_class_name("chapter__content")
            for chapter_json in book["chapters"]:
                if chapter_json["order_no"] == int(chapter_no):
                    if not chapter_json.get("supplement", None):
                        supplement_text = supplement_content.get_attribute("innerHTML")
                        chapter_json["supplement"] = supplement_text
                    break

    # if we are scraping by category, add it to the book metadata
    book["category"] = category["label"]

    # store the book json metadata for future use
    dump_book(book)

    # return a tuple with the book json metadata, and a boolean indicating whether
    # the json dump already existed or not
    return book, False


def dump_book(book_json):
    # dump the book's metadata in a json file within the dump folder
    filepath = get_book_dump_filename(book_json)
    if not os.path.exists(os.path.dirname(filepath)):
        os.makedirs(os.path.dirname(filepath))
    with open(filepath, "w") as outfile:
        json.dump(book_json, outfile, indent=4)
    return filepath


def scrape_book_audio(driver, book_json, language):
    # check if the book actually has audio blinks
    if not (book_json["is_audio"]):
        log.debug(
            f"Book {book_json['slug']} does not have audio blinks, skipping scraping audio..."
        )
        return False

    # clear out previous captured requests and restrict scope to the blinkist site
    del driver.requests
    driver.scopes = [".*blinkist.*"]

    # navigate to the book's reader page which also contains the media player for the first audio blink
    book_reader_url = f'https://www.blinkist.com/{language}/nc/reader/{book_json["slug"]}'
    driver.get(book_reader_url)

    # wait until the request to the audio endpoint is captured,
    # then its headers for future requests
    try:
        captured_request = driver.wait_for_request("audio", timeout=30)
        audio_request_headers = captured_request.headers
    except TimeoutException as ex:
        log.error("Could not capture an audio endpoint request")
        return False

    audio_files = []
    error = False
    # go through every chapter object in the book json data
    # and build a request to the audio endpoint using the book and chapter ID
    for chapter_json in book_json["chapters"]:
        time.sleep(1.0)
        api_url = f"https://www.blinkist.com/api/books/{book_json['id']}/chapters/{chapter_json['id']}/audio"
        try:
            audio_request = requests.get(api_url, headers=audio_request_headers)
            audio_request_json = audio_request.json()
            if "url" in audio_request_json:
                audio_url = audio_request_json["url"]
                audio_file = download_book_chapter_audio(
                    book_json, chapter_json["order_no"], audio_url
                )
                audio_files.append(audio_file)
            else:
                log.warning(
                    "Could not find audio url in request, aborting audio scrape..."
                )
                error = True
                break
        except json.decoder.JSONDecodeError:
            log.error(f"Received malformed json data: {audio_request.text}")
            log.warning("Could not find audio url in request, aborting audio scrape...")
            error = True
            break
        except Exception as e:
            log.error(f"Request timed out or other unexpected error: {e}")
            error = True
            break

    if not error:
        return audio_files
    else:
        log.error("Error processing audio url, aborting audio scrape...")
        return []


def download_book_chapter_audio(book_json, chapter_no, audio_url):
    filepath = get_book_pretty_filepath(book_json)
    filename = str(chapter_no) + ".m4a"
    audio_file = os.path.join(filepath, filename)
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    if not os.path.exists(audio_file):
        log.info(
            f"Downloading audio file for blink {chapter_no} of {book_json['slug']}..."
        )
        download_request = requests.get(audio_url)
        with open(audio_file, "wb") as outfile:
            outfile.write(download_request.content)
    else:
        log.debug(f"Audio for blink {chapter_no} already downloaded, skipping...")
    return audio_file


def download_book_cover_image(
    book_json, filename="_cover.jpg", size="640", type="1_1", alt_file="cover.jpg"
):
    """ 
    Downloads the cover image specified in 'book_json'.
    
    book_json -- dictionary object with book metadata. 
    filename -- filename of the output files
    size -- the width of the image in pixels. 
            The 'sizes' options (generally) are: 130, 250, 470, 640, 1080, and 1400.
    type -- the aspect ratio of for the cover image. 
            The 'types' options (generally) are: '1_1', '2-2_1', and '3_4'.
    alt_file -- an identical file to the expected image, but with a different name.
    
    The default 'image_url' (used by the HTML output) is type: '3_4', size: 640.
    """

    # default cover image:
    # cover_img_url = book_json["image_url"]

    # variable size/resolution: (default is 640*640 px)
    cover_img_url_tmplt = book_json["images"]["url_template"]
    cover_img_url = cover_img_url_tmplt.replace("%type%", type).replace("%size%", size)

    filepath = get_book_pretty_filepath(book_json)
    cover_img_file = os.path.join(filepath, filename)
    cover_img_alt_file = os.path.join(filepath, alt_file)
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    if not os.path.exists(cover_img_file):
        # check if we have the "alternative" image file avaible
        if not os.path.exists(cover_img_alt_file):
            # download the image
            log.info(f'Downloading "{cover_img_url}" as "{filename}"')
            download_request = requests.get(cover_img_url)
            with open(cover_img_file, "wb") as outfile:
                outfile.write(download_request.content)
        else:
            # copy the image file
            log.debug(f"Copying {alt_file} as {filename}")
            copy_file(cover_img_alt_file, cover_img_file)
    else:
        log.debug(f"{filename} already exists, skipping...")
    return cover_img_file

