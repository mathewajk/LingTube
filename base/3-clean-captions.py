#!/usr/bin/env python3
import argparse
import Base

# TODO: Make routes for (1) xml files

def main(args):

    group = args.group
    lang_code = args.lang_code
    fave = args.fave
    text = args.text
    overwrite = args.overwrite

    cleaner = Base.CaptionCleaner(group, lang_code, fave, text, overwrite)
    cleaner.process_captions()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube SRT captions to cleaned transcript text format.')

    parser.set_defaults(func=None)
    parser.add_argument('-g', '--group', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: cleaned_subtitles/$group)')
    parser.add_argument('-l','--lang_code',  default=None, type=str, help='open captions with a specific a language code (e.g., "en"); if unspecified, goes through all available language code in subtitle directory')
    parser.add_argument('-f', '--fave', action='store_true', default=False, help='additionally output Fave-format file')
    parser.add_argument('-t', '--text', action='store_true', default=False, help='additionally output text-only file')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
