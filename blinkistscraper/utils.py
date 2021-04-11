import os
import json
import re
from shutil import which


def get_or_read_json(book_json_or_file):
    if type(book_json_or_file) is dict:
        return book_json_or_file
    else:
        with open(book_json_or_file) as f:
            return json.load(f)


def sanitize_name(name):
    return re.sub(r'[\\/*?:"<>|.]', "", name).strip()


def get_book_dump_filename(book_json_or_url):
    if "blinkist.com" in book_json_or_url:
        return os.path.join("dump", book_json_or_url.split("/")[-1] + ".json")
    else:
        return os.path.join("dump", book_json_or_url["slug"] + ".json")


def get_book_pretty_filepath(book_json):
    path = os.path.join(
        "books", book_json["category"], get_book_pretty_filename(book_json)
    )
    if len(path) >= 260:
        return "\\\\?\\" + path.replace("/", "\\")
    else:
        return path


def get_book_pretty_filename(book_json, extension=""):
    author = sanitize_name(book_json["author"])
    title = sanitize_name(book_json["title"])
    return f"{author} - {title}" + extension


def is_installed(tool):
    return which(tool)
