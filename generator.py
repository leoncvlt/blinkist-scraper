import os, json, subprocess

from utils import *
from ebooklib import epub

def generate_book_html(book_json_or_file):
  book_json = get_or_read_json(book_json_or_file)
  filepath = get_book_pretty_filepath(book_json)
  filename = get_book_pretty_filename(book_json, ".html")
  html_file = os.path.join(filepath, filename)
  if (os.path.exists(html_file)):
    print(f"[.] Html file for {book_json['slug']} already exists, not generating...")
    return html_file
  print(f"[.] Generating .html for {book_json['slug']}")

  # open the book html template and replace every occurency of {{key}}
  # with the relevant parameter from the json file
  book_template_file = open(os.path.join("templates", "book.html"), "r")
  book_template = book_template_file.read()
  book_html = book_template
  for key in book_json:
    book_html = book_html.replace(f'{{{key}}}', str(book_json[key]))

  # when the special tag {__chapters__} is found, open the chapter template file
  # and do the same, then add the template chapter's html into the book's html
  if ('{__chapters__}' in book_template):
    chapters_html = []
    chapter_template_file = open(os.path.join("templates", "chapter.html"), "r")
    chapter_template = chapter_template_file.read()
    for chapter_json in book_json['chapters']:
      chapter_html = chapter_template
      for chapter_key in chapter_json:
        chapter_html = chapter_html.replace(f'{{{chapter_key}}}', str(chapter_json[chapter_key]))
      chapters_html.append(chapter_html)

  book_html = book_html.replace('{__chapters__}', "\n".join(chapters_html))
  book_html = book_html.replace('<p>&nbsp;</p>', '')
  
  # finally, export the finished book html
  if not os.path.exists(filepath):
    os.makedirs(filepath)
  with open(html_file, 'w',  encoding='utf-8') as outfile:
    outfile.write(book_html)
  return html_file

def generate_book_epub(book_json_or_file):
  book_json = get_or_read_json(book_json_or_file)
  filepath = get_book_pretty_filepath(book_json)
  filename = get_book_pretty_filename(book_json, ".epub")
  epub_file = os.path.join(filepath, filename)
  if (os.path.exists(epub_file)):
    print(f"[.] Epub file for {book_json['slug']} already exists, not generating...")
    return epub_file
  print(f"[.] Generating .epub for {book_json['slug']}")
  book = epub.EpubBook()

  # set metadata
  book.set_identifier(book_json['id'])
  book.set_title(book_json['title'])
  book.set_language('en')
  book.add_author(book_json['author'])
  book.add_metadata('DC', 'description', book_json['about_the_book'])

  # add chapters
  chapters = []
  for chapter_json in book_json['chapters']:
    chapter = epub.EpubHtml(title=chapter_json['title'], file_name=f"chapter_{chapter_json['order_no']}.xhtml", lang='hr')
    chapter.content = f"<h2>{chapter_json['title']}</h2>" + chapter_json['content']
    book.add_item(chapter)
    chapters.append(chapter)

  # define Table Of Contents
  book.toc = chapters

  # add default NCX and Nav file
  book.add_item(epub.EpubNcx())
  book.add_item(epub.EpubNav())

  # define CSS style
  style = open(os.path.join("templates", "epub.css"), "r").read()
  nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
  book.add_item(nav_css)

  # basic spine
  book.spine = ['nav'] + chapters

  # write to the file
  if not os.path.exists(filepath):
    os.makedirs(filepath)
  epub.write_epub(epub_file, book, {})
  return epub_file

def generate_book_pdf(book_json_or_file):
  if not is_installed("wkhtmltopdf"):
    print(f"[!] wkhtmltopdf needs to be installed and added to PATH to generate pdf files")
    return

  book_json = get_or_read_json(book_json_or_file)
  filepath = get_book_pretty_filepath(book_json)
  filename = get_book_pretty_filename(book_json, ".pdf")
  pdf_file = os.path.join(filepath, filename)
  if (os.path.exists(pdf_file)):
    print(f"[.] Pdf file for {book_json['slug']} already exists, not generating...")
    return pdf_file

  # generates the html file if it doesn't already exists
  html_file = os.path.join(get_book_pretty_filepath(book_json), get_book_pretty_filename(book_json, ".html"))
  if not os.path.exists(html_file):
    generate_book_html(book_json_or_file)

  print(f"[.] Generating .pdf for {book_json['slug']}")
  pdf_command = f"wkhtmltopdf --quiet \"{html_file}\" \"{pdf_file}\""
  os.system(pdf_command)
  return pdf_file

def combine_audio(book_json, files):
  if not is_installed("ffmpeg"):
    print(f"[!] ffmpeg needs to be installed and added to PATH to combine audio files")
    return

  print(f"[.] Combining audio files for {book_json['slug']}")
  filepath = get_book_pretty_filepath(book_json)
  filename = get_book_pretty_filename(book_json, ".m4a")

  files_list = os.path.abspath(os.path.join(filepath, "temp.txt"))
  combined_audio_file = os.path.abspath(os.path.join(filepath, "concat.m4a"))
  tagged_audio_file = os.path.abspath(os.path.join(filepath, filename))

  # ffmpeg fails on windows if the output filepath is longer than 260 chars
  if len(tagged_audio_file) >= 260:
    print(f"[!] ffmpeg output file longer than 260 characters. Trying shorter filename...")
    tagged_audio_file = os.path.abspath(os.path.join(filepath, get_book_short_pretty_filename(book_json, ".m4a")))
    if len(tagged_audio_file) >= 260:
      print(f"[!] shorter filename still too long! Consider running the script from a shorter path.")
      return

  with open(files_list, 'w',  encoding='utf-8') as outfile:
    for file in files:
      # escape any quotes for the ffmpeg concat's command file list
      sanitized_file = os.path.abspath(file).replace("'", "'\\''")
      outfile.write(f"file '{sanitized_file}'\n")
  silent = "-nostats -loglevel 0 -y"
  concat_command = f"ffmpeg {silent} -f concat -safe 0 -i \"{files_list}\" -c copy \"{combined_audio_file}\""
  os.system(concat_command)
  tag_command = f"ffmpeg {silent} -i \"{combined_audio_file}\" -c copy -metadata title=\"{book_json['title']}\" -metadata artist=\"{book_json['author']}\" \"{tagged_audio_file}\""
  os.system(tag_command)

  # clean up files
  if (os.path.exists(files_list)):
    os.remove(files_list)
  if (os.path.exists(combined_audio_file)):
    os.remove(combined_audio_file)
  for file in files:
    if (os.path.exists(file)):
      os.remove(os.path.abspath(file))