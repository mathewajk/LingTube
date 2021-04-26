#!/usr/bin/env python3

from sys import argv
from time import sleep, strftime
from os import path, makedirs
from re import sub, findall
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scroll_page(driver, pause_time):
    """Scroll the channel to load more videos.

    :param driver: A WebDriver object
    :param pause_time: Time to wait before scrolling again

    :return continue: 1 if scroll was successful, 0 if page bottom has been reached
    """

    # Get scroll height
    last_height = driver.execute_script('return document.querySelector("#page-manager").scrollHeight')

    # Scroll down to bottom
    driver.execute_script('window.scrollTo(0,document.querySelector("#page-manager").scrollHeight);')

    # Wait to load page
    sleep(pause_time)

    # Calculate new scroll height and compare with last scroll height
    new_height = driver.execute_script('return document.querySelector("#page-manager").scrollHeight')
    if new_height == last_height: # End of list
        return 0
    return 1


def get_links(driver, url, cutoff):
    """Scrape the URLs from a YouTube channel.

    :param driver: A WebDriver object
    :param url: URL of the channel's videos page
    :param cutoff: Limit scrolling to N attempts

    :return continue: 1 if scroll was successful, 0 if page bottom has been reached
    """

    # Load the page
    driver.get(url)

    try:
        # Wait for the "items" div to appear
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'contents')))
    except:
        print("Could not locate 'contents' div")
    finally:
        # Scroll to the bottom of the page to load videos
        count = 0
        while (cutoff == -1 or count < cutoff) and scroll_page(driver, 4):
            count += 1
            print("Loading... ({0})".format(count))

        # Gather urls and metadata
        video_elements = driver.find_elements_by_xpath('//*[@id="video-title"]')
        return [(element.get_attribute('href'), element.get_attribute('aria-label')) for element in video_elements]


def save_videos(links, search_query, exclude_query, group=None):
    """Write a scraped list of video links to a file.

    :param links: A list of video URLs
    :param info: A dictionary containing the channel's name, ID, description, bio, and metadata
    :param group: The folder to output the channel info to (default None)
    """
    search_string = '-'.join(search_query.split())
    current_time = strftime("%Y%m%d%H%M%S")

    videos_out_fn = "{0}_{1}_videos.csv".format(search_string, current_time)
    urls_out_fn = "{0}_{1}_urls.txt".format(search_string, current_time)

    if group:
        full_out_dir = path.join("corpus", "unscreened_urls", group, "search", "info")
        url_out_dir = path.join("corpus", "unscreened_urls", group, "search", "urls")
    else:
        full_out_dir = path.join("corpus", "unscreened_urls", "search", "info")
        url_out_dir = path.join("corpus", "unscreened_urls", "search", "urls")

    if not path.exists(full_out_dir):
        makedirs(full_out_dir)
    if not path.exists(url_out_dir):
        makedirs(url_out_dir)

    videos_out_fn = path.join(full_out_dir, videos_out_fn)
    urls_out_fn = path.join(url_out_dir, urls_out_fn)

    with open(videos_out_fn, 'w') as videos_out, open(urls_out_fn, 'w') as urls_out:

        for (link, video_info) in links:
            if link:
                info_details = findall(r'(.+) by (.+?) (\d.*)', video_info)
                video_title, video_author, video_other  = info_details[0]

                if search_query.lower() in video_title.lower():
                    videos_out.write("{0},{1},{2},{3}\n".format(link, video_author, video_title, video_other))

                    if exclude_query:
                        if not any(term.lower() in video_title.lower() for term in exclude_query.split(',')):
                            urls_out.write("{0}\t{1}\n".format(link, video_author))
                    else:
                        urls_out.write("{0}\t{1}\n".format(link, video_author))

def process_results(search_query, exclude_query=None, cutoff=-1, group=None, driver=None):
    """Process a channel from a URL

    :param url: Channel URL
    :param cutoff: Limit scrolling to N attempts
    :param group:  Folder name to group channels under
    """

    print("Gathering videos from search results for: " + search_query)

    # if exclude_query:
    #     url = "https://www.youtube.com/results?search_query=" + '+'.join(search_query.split()) + '+' + '+'.join(exclude_query.split())
    # else:
    url = "https://www.youtube.com/results?search_query=" + '+'.join(search_query.split())

    if driver:
        sleep(1)
        links = get_links(driver, url, cutoff)
    else:
        with webdriver.Firefox() as driver:
            sleep(1)
            links = get_links(driver, url, cutoff)

    print("Found {0} videos".format(str(len(links))))
    save_videos(links, search_query, exclude_query, group)

def main(args):

    process_results(args.search_query, args.exclude_query, args.cutoff, args.group)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape video URLs from a YouTube search page.')
    parser.add_argument('search_query', type=str, help='search query (e.g., "get to know me")')
    parser.add_argument('--exclude_query', '-ex', metavar='STR', help='string of terms used to exclude from video title', type=str)
    parser.add_argument('--group', '-g', default=None, metavar='NAME', type=str, help='name to group files under (will create a subfolder: unscreened_urls/$group)')
    parser.add_argument('--cutoff', type=int, metavar='N', default=-1, help='maximum number of times to scroll the page')
    parser.set_defaults(func=None)

    args = parser.parse_args()

    main(args)
