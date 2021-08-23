#!/usr/bin/env python3

import argparse, logging
from glob import glob
from csv import DictWriter
from pytube import YouTube, exceptions, helpers
from os import makedirs, path, walk, rename
from re import sub, findall
from time import sleep, strftime
from sys import argv


def main(args):

    if not args.clean:
        if not path.isfile(args.urls_in) and not path.isdir(args.urls_in):
            logging.error("url_list must be a file or directory")
            exit(2)

        if not path.exists(path.join("corpus", "logs")):
            makedirs(path.join("corpus", "logs"))
        if args.screen:
            if not path.exists(path.join("corpus", "unscreened_urls", "logs")):
                makedirs(path.join("corpus", "unscreened_urls", "logs"))

        if(args.resume):
            print("Resuming from video {0}".format(args.resume))

        if path.isfile(args.urls_in):
            process_videos(args.urls_in, False, args.language, args.group, args.screen, args.audio, args.auto, args.srt, args.resume, args.limit, args.overwrite)

        if path.isdir(args.urls_in):
            process_files(args.urls_in, args.language, args.group, args.screen, args.audio, args.auto, args.srt, args.resume, args.limit, args.overwrite)

    if args.screen:
        out_path = path.join('corpus', 'unscreened_urls')
    else:
        out_path = path.join('corpus', 'raw_subtitles')

    for dirpath, dirnames, files in walk(out_path):
         for filename in files:
             name, ext = path.splitext(filename)
             if ext in ['.srt', '.xml']:
                 clean_filename = name.rsplit(' ',1)[0]+ext
                 rename(path.join(dirpath, filename),
                           path.join(dirpath, clean_filename))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download available subtitles and audio from a list of YouTube video urls.')

    parser.add_argument('urls_in', type=str, help='path to a file or directory containing the URLs to scrape')

    parser.add_argument('--language',  '-l', default=None, type=str, help='filter captions by language name (e.g. "Korean"); if unspecified, all captions will be downloaded')
    parser.add_argument('--group',     '-g', default=None, metavar='NAME', type=str, help='a name for the group; if unspecified, channel names will be used')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite logs and files rather than appending')

    parser.add_argument('--auto',     '-a', action='store_true', default=False, help='include automatically-generated captions')
    parser.add_argument('--audio',    '-s', action='store_true', default=False, help='download audio')
    parser.add_argument('--srt',            action='store_true', default=False, help='download captions in SRT format')

    parser.add_argument('--resume', '-res', type=int, metavar='N', default=0,  help='resume downloading from Nth video or file')
    parser.add_argument('--limit',  '-lim', type=int, metavar='N', default=-1, help='limit processing to N videos or files')
    parser.add_argument('--screen',         action='store_true', default=False, help='downloading files for screening purposes')
    parser.add_argument('--clean',          action='store_true', default=False, help='skip scraping and only clean dowloaded caption filenames of langcode')

    args = parser.parse_args()

    main(args)
