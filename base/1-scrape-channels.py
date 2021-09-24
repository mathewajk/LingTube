#!/usr/bin/env python3

import argparse
import Base

from sys import path


def run(args):

    scraper = None

    source        = args.source
    from_video    = args.video
    browser       = args.browser
    group         = args.group
    pause_time    = args.wait
    cutoff        = args.limit
    about = args.about
    overwrite     = args.overwrite
    screen        = args.screen

    if 'http' in source:
        scraper = Base.ChannelHandler(source, from_video, browser, pause_time, cutoff, group, about, overwrite, screen)
    else:
        scraper = Base.MultiChannelHandler(source, from_video, browser, pause_time, cutoff, group, about, overwrite, screen)

    scraper.process()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape video URLs from a YouTube channel based on channel URL(s) [default] or video URL(s)')

    parser.add_argument('source', type=str, help='URL or file path to list of URLs to scrape (by default, source assumed to be channel URLs; to treat as video URLs, add -v)')

    parser.add_argument('-v', '--video',   action='store_true', default=False, help='source is a video or list of videos')
    parser.add_argument('-g', '--group',     default=None, type=str, help='grouping for the output files (will create a subfolder, e.g., screened_urls/$group)')
    parser.add_argument('-b', '--browser',   default="Firefox", type=str, help='browser to use for scraping ("Firefox" or "Chrome")')
    parser.add_argument('-a', '--about',  action='store_true', default=False, help='only scrape about page(s); do not scrape video URLs')
    parser.add_argument('-l', '--limit',     type=int, default=-1, help='maximum number of times to scroll the page when scraping videos')
    parser.add_argument('-w', '--wait',      type=int, default=1, help='how long to pause between scrolls; increase for slower connections')
    parser.add_argument('-s', '--screen',    action='store_true', default=False, help='videos require screening for adequacy')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False, help='overwrite files rather than appending (applies to video lists only)')

    args = parser.parse_args()
    run(args)
