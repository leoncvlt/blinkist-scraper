import os, json
from shutil import which

def get_or_read_json(book_json_or_file):
  if (type(book_json_or_file) is dict):
    return book_json_or_file
  else:
    with open(book_json_or_file) as f:
      return json.load(f)

def get_book_dump_filename(book_json_or_url):
  if ("blinkist.com" in book_json_or_url):
    return os.path.join('dump', book_json_or_url.split('/')[-1] + '.json')
  else:
    return os.path.join('dump', book_json_or_url['slug'] + '.json')

def get_book_pretty_filepath(book_json):
  return os.path.join('books', book_json['category'], get_book_pretty_filename(book_json))

def get_book_pretty_filename(book_json, extension=""):
  return f"{book_json['author']} - {book_json['title']}" + extension

def get_book_short_pretty_filename(book_json, extension=""):
  return f"{book_json['title']}" + extension

def is_installed(tool):
  return which(tool)