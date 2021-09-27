#!/usr/bin/env python3

from sys import argv
from os import path
import argparse
import Base


def main(args):

    log_fp = None
    language = args.language
    group = args.group
    screen = args.screen
    include_audio = args.audio
    include_auto = args.auto
    convert_srt = (not args.xml)
    resume_from = args.resume
    limit_to = args.limit
    overwrite = args.overwrite

    if resume_from:
        print("Resuming from video {0}".format(resume_from))

    if limit_to != -1:
        print("Limiting to {0} videos".format(limit_to))

    if path.isfile(args.urls_in):
        scraper = Base.MultiVideoScraper(args.urls_in, None, language, group, screen, include_audio, include_auto, convert_srt, resume_from, limit_to, overwrite)
        scraper.process_videos()

    if path.isdir(args.urls_in):
        scraper = Base.BatchVideoScraper(args.urls_in, args.language, args.group, args.screen, args.audio, args.auto, args.srt, args.resume, args.limit, args.overwrite)
        scraper.process_videos()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download available subtitles and audio from a list of YouTube video urls.')

    parser.add_argument('urls_in', type=str, help='path to a file or directory containing the URLs to scrape')

    # LingTube organization
    parser.add_argument('--language',  '-l', default=None, type=str, help='filter captions by language name (e.g. "Korean"); if unspecified, all captions will be downloaded')
    parser.add_argument('--group',     '-g', default=None, metavar='NAME', type=str, help='a name for the group; if unspecified, channel names will be used')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite logs and files rather than appending')
    parser.add_argument('--screen',         action='store_true', default=False, help='download video URLs into a separate folder ("unscreened_urls") for further screening; default folder is "screened_urls"')

    # Download parameters
    parser.add_argument('--auto',     '-a', action='store_true', default=False, help='include automatically-generated captions')
    parser.add_argument('--audio',    '-s', action='store_true', default=False, help='download audio')
    parser.add_argument('--xml',            action='store_true', default=False, help='download captions in XML format')
    parser.add_argument('--resume', '-res', type=int, metavar='N', default=0,  help='resume downloading from Nth video or file')
    parser.add_argument('--limit',  '-lim', type=int, metavar='N', default=-1, help='limit processing to N videos or files')

    args = parser.parse_args()

    main(args)
