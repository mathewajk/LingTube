#!/usr/bin/env python3

import argparse
import Base

from sys import path


def run(args):

    scraper = None

    source        = args.source
    browser       = args.browser
    group         = args.group
    pause_time    = args.wait
    cutoff        = args.limit
    ignore_videos = args.novideos
    screen        = args.screen
    overwrite     = args.overwrite

    if args.c:
        if 'http' in source:
            scraper = Base.ChannelHandler(source, browser, pause_time, cutoff, group, ignore_videos, screen)
        else:
            scraper = Base.MultiChannelHandler(source, browser, pause_time, cutoff, group, ignore_videos, screen)
    elif args.v:
        if 'http' in source:
            scraper = Base.VideoHandler(source, browser, pause_time, cutoff, group, ignore_videos, overwrite, screen)
        else:
            scraper = Base.MultiVideoHandler(source, browser, pause_time, cutoff, group, ignore_videos, overwrite, screen)
    else:
        print('ERROR: Please specify whether the input is a channel (-c) or video (-v)')
        exit(1)

    scraper.process()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape video URLs from a YouTube channel based on channel URL(s) or video URL(s)')

    parser.add_argument('source', type=str, help='URL or file path to list of URLs to scrape')

    parser.add_argument('-c', '-channel',    action='store_true', default=False, help='Source is a channel or list of channels')
    parser.add_argument('-v', '-video',      action='store_true', default=False, help='Source is a video or list of videos')
    parser.add_argument('-g', '--group',     default=None, type=str, help='grouping for the output files (will create a subfolder, e.g., screened_urls/$group)')
    parser.add_argument('-b', '--browser',   default="Firefox", type=str, help='browser to use for scraping ("Firefox" or "Chrome")')
    parser.add_argument('-n', '--novideos',  action='store_true', default=False, help='only scrape about page(s); ignore video URLs')
    parser.add_argument('-l', '--limit',     type=int, default=-1, help='maximum number of times to scroll the page when scraping videos')
    parser.add_argument('-w', '--wait',      type=int, default=1, help='how long to pause between scrolls; increase for slower connections')
    parser.add_argument('-s', '--screen',    action='store_true', default=False, help='download files for screening purposes')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False, help='overwrite files rather than appending (applies to video lists only)')

    args = parser.parse_args()
    run(args)
