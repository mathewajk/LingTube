#!/usr/bin/env python3

from sys import argv
from os import path
import argparse
import Base


def main(args):

    urls_in = args.urls_in
    log_fp = None
    language = args.language
    group = args.group
    screen = args.screen
    include_audio = args.audio
    include_auto = args.auto
    convert_srt = args.srt
    limit = args.limit
    overwrite = args.overwrite

    if path.isfile(urls_in):
        scraper = Base.MultiVideoScraper(urls_in, log_fp, language, group, screen, include_audio, include_auto, convert_srt, limit, overwrite)
        scraper.process_videos()

    elif path.isdir(urls_in):
        scraper = Base.BatchVideoScraper(urls_in, language, group, screen, include_audio, include_auto, convert_srt, limit, overwrite)
        scraper.process_files()

    else:
        group = urls_in
        group_path = ''

        if screen:
            group_path = path.join('corpus', 'unscreened_videos')
        else:
            group_path = path.join('corpus', 'screened_urls')

        group_path = path.join(group_path, group, 'channel_urls')

        if path.isdir(group_path):
             scraper = Base.BatchVideoScraper(group_path, language, group, screen, include_audio, include_auto, convert_srt, limit, overwrite)
             scraper.process_files()

        # TODO: Error will be weird if the user inputs a missing directory or file since it will be treated like a group
        else:
            print("Directory not found: {0}\nPlease input a valid group name, file path, or directory path and double-check your command-line flags (e.g. -s)".format(group_path))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Download available subtitles and audio from a list or lists of YouTube video urls.')

    parser.add_argument('urls_in', type=str, help='a group name, file, or directory containing the URLs to scrape')

    # LingTube organization
    parser.add_argument('-g', '--group',     default="ungrouped", metavar='NAME', type=str, help='group to use if file or directory is input')
    parser.add_argument('-l', '--language', default=None, type=str, help='filter captions by language name (e.g. "Korean"); if unspecified, all captions will be downloaded')

    # Download parameters
    parser.add_argument('-a','--auto',  action='store_true', default=False, help='include automatically-generated captions; else, only manual captions will be downloaded')
    parser.add_argument('-aud', '--audio', action='store_true', default=False, help='include audio download; else, only captions will be downloaded')
    parser.add_argument('--srt',            action='store_true', default=False, help='convert captions to SRT format; else, captions will be in XML format')
    parser.add_argument('-lim', '--limit', type=int, metavar='N', default=-1, help='limit processing to N videos or files; if unspecfied, all available videos or files will be processed')

    # LingTube options
    parser.add_argument('-o', '--overwrite', choices = ["all", "channel"], help='all: overwrite all audio and caption files; channel: overwrite only if channel already exists')
    parser.add_argument('-s',  '--screen',   action='store_true', default=False, help='download files into a folder for further screening (e.g., unscreened_videos/subtitles); else, downloads into "raw_subtitles"')

    args = parser.parse_args()

    main(args)
