#!/usr/bin/env python3

import argparse
import Base

from sys import path


def run(args):

    source        = args.source
    browser       = args.browser
    group         = args.group
    cutoff        = args.limit
    about         = args.about
    overwrite     = args.overwrite
    screen        = args.screen

    scraper = Base.MultiChannelScraper(source, browser, cutoff, group, about, overwrite, screen)
    scraper.process()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape video URLs from a YouTube channel based on channel URL(s) or video URL(s)')

    parser.add_argument('source', type=str, help='URL or file path to list of URLs to scrape')

    # LingTube organization
    parser.add_argument('-g', '--group',   default="ungrouped", type=str, help='a name for grouping the output files (will create a subfolder, e.g., screened_urls/$group)')

    # Scraping parameters
    parser.add_argument('-a', '--about',     action='store_true', default=False, help='only scrape about page(s), not video URLs; else, both about and video URLS will be scraped')
    parser.add_argument('-lim', '--limit',  type=int, metavar='N', default=-1, help='maximum number of (additional) channel URLs to collect; if unspecfied, collects all available channel URLs')
    parser.add_argument('-b', '--browser',   default="Firefox", type=str, help='browser to use for scraping ("Firefox" or "Chrome"); if unspecfied, uses Firefox')

    # LingTube options
    parser.add_argument('-o', '--overwrite', action='store_true', default=False, help='overwrite full sub-folder rather than appending')
    parser.add_argument('-s',  '--screen',   action='store_true', default=False, help='download video URLs into a folder for further screening ("unscreened_videos"); else, downloads into "screened_urls"')


    args = parser.parse_args()
    run(args)
