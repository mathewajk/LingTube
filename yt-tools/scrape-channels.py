#!/usr/bin/env python3

from sys import argv
from time import sleep
from os import path, makedirs
from re import sub
from glob import glob
import logging, argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scroll_channel(driver, pause_time):
    """Scroll the channel to load more videos.

    :param driver: A WebDriver object
    :param pause_time: Time to wait before scrolling again

    :return continue: 1 if scroll was successful, 0 if page bottom has been reached
    """

    # Get scroll height
    last_height = driver.execute_script('return document.querySelector("#page-manager").scrollHeight')

    # Scroll down to bottom of current view
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

    :return : List of videos URLs
    """

    # Load the page
    driver.get(url)

    try:
        # Wait for the "items" div to appear
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'items')))
    except:
        logging.warning("Could not locate 'items' div")
    finally:
        # Scroll to the bottom of the page to load videos
        count = 0
        while (cutoff == -1 or count < cutoff) and scroll_channel(driver, 4):
            count += 1
            print("Loading... ({0})".format(count))

        # Gather urls and metadata
        elements = driver.find_elements_by_xpath('//*[@id="video-title"]')
        return [element.get_attribute('href') for element in elements]


def save_info_and_videos(links, info, group=None, noscrape=False, screen=False):
    """Write channel information and (if scraping) a scraped list of video links to a file.

    :param links: A list of video URLs
    :param info: A dictionary containing the channel's name, ID, description, bio, and metadata
    :param group: The folder to output the channel info to (default None)
    :param noscrape: Whether or not video links were scraped\
    :param screen: Whether or not videos are being saved for screening
    """

    # Create output paths
    base_path = path.join("corpus", "screened_urls")
    if screen: # If videos need to be screened, save to separate folder
        base_path = path.join("corpus", "unscreened_urls")

    # Group output under shared folder if necessary
    if group:
        url_out_dir = path.join(base_path, group, "channel_urls")
        info_out_dir = path.join(base_path, group, "about")
    else:
        url_out_dir = path.join(base_path, "channel_urls")
        info_out_dir = path.join(base_path, "about")

    if not path.exists(info_out_dir):
        makedirs(info_out_dir)

    # Create filename based on channel name and unique ID
    info_out_fn = "{0}_{1}_info.txt".format(info["SafeChannelName"], info["SafeChannelID"])
    info_out_fn = path.join(info_out_dir, info_out_fn)

    # Save channel info
    with open(info_out_fn, 'w') as info_out:

        for key in info.keys():
            info_out.write("# {0}\n\n".format(key))
            info_out.write("{0}\n\n".format(info[key]))

    # Don't save the links if we didn't scrape anything
    if noscrape:
        return

    if not path.exists(url_out_dir):
        makedirs(url_out_dir)

    videos_out_fn = "{0}_{1}_videos.txt".format(safe_channel_name, info["SafeChannelID"])

    videos_out_fn = path.join(url_out_dir, videos_out_fn)

    with open(videos_out_fn, 'w') as videos_out:

        for link in links:
            videos_out.write("{0}\t{1}\t{2}\n".format(link, info["ChannelName"], info["SafeChannelID"]))

def get_info(driver, url):
    """Scrape the channel's description.

    :param driver: A WebDriver object
    :param url: URL of the channel's videos page
    """

    # Load the about page
    driver.get(url)

    info = {"ChannelName": "", "Description": "", "Bio": "", "Metadata": ""}

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        channel_name = driver.find_element(By.CLASS_NAME, "ytd-channel-name").text

        info["ChannelName"] = channel_name
        info["SafeChannelName"] = sub(punc_and_whitespace, "", channel_name)

    except:
        logging.warning("Could not scrape channel name")

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'description')))

        info["Description"] = driver.find_element(By.ID, "description").text
        info["Bio"]         = driver.find_element(By.ID, "bio").text
        info["Metadata"]    = driver.find_element(By.ID, "details-container").find_element(By.TAG_NAME, "table").text

    except:
        logging.warning("Could not scrape About page")

    return info


def process_channel(url, cutoff=-1, group=None, driver=None, noscrape=False, screen=False):
    """Process a channel from a URL

    :param url: Channel URL
    :param cutoff: Limit scrolling to N attempts
    :param group:  Folder name to group channels under
    """

    punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
    channel_id = url.split('/')[-1]
    info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

    logging.info("Gathering videos from channel ID: " + channel_id)

    # Run the webdriver
    # TODO: Repetitive for legacy reasons
    if driver:
        info.update(get_info(driver, url + "/about"))
        sleep(1)

        links = get_links(driver, url + "/videos", cutoff)
    else:
        with webdriver.Firefox() as driver:

            info.update(get_info(driver, url + "/about"))
            sleep(1)

            links = get_links(driver, url + "/videos", cutoff)

    logging.info("Found {0} videos".format(str(len(links))))
    save_info_and_videos(links, info, group, noscrape, screen)


def process_video(url, videos_path, cutoff=-1, group=None, driver=None, noscrape=False, screen=False, overwrite=False):
    """Process a video from a URL

    :param url: Video URL
    :param cutoff: Limit scrolling to N attempts
    :param group:  Folder name to group channels under
    """

    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))
        channel_url = driver.find_element(By.CLASS_NAME, "ytd-channel-name").find_element(By.TAG_NAME, 'a').get_attribute('href')
        logging.info("Gathering information from channel: " + channel_url)
    except:
        return

    punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
    channel_id = channel_url.split('/')[-1]
    info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

    # Run the webdriver
    # TODO: Repetitive for legacy reasons
    if driver:
        info.update(get_info(driver, channel_url + "/about"))
        sleep(1)

        if not noscrape:
            links = get_links(driver, channel_url + "/videos", cutoff)
            logging.info("Found {0} videos".format(str(len(links))))
        else:
            links = []

    else:
        with webdriver.Firefox() as driver:

            info.update(get_info(driver, channel_url + "/about"))
            sleep(1)

            if not noscrape:
                links = get_links(driver, channel_url + "/videos", cutoff)
                logging.info("Found {0} videos".format(str(len(links))))
            else:
                links = []

    save_info_and_videos(links, info, group, noscrape, screen)

    # Log input video info
    with open(videos_path, 'a') as videos_out:
        videos_out.write("{0}\t{1}\t{2}\n".format(url, info["ChannelName"], info["SafeChannelID"]))


def process_channels(channels_fn, cutoff=-1, group=None, noscrape=False, screen=False):
    """Process a list of channels from a file

    :param channels_fn: The file to open
    :param cutoff: Limit scrolling to N attempts
    :param group:  Folder name to group channels under
    """

    with open(channels_fn, 'r') as channels_in:
        with webdriver.Firefox() as driver:
            for line in channels_in:
                line = line.split('\t')[0]
                line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?
                process_channel(line, cutoff, group, driver, noscrape)
                sleep(1)


def process_videos(channels_fn, cutoff=-1, group=None, noscrape=False, screen=False, overwrite=False):
    """Process a list of videos from a file

    :param channels_fn: The file to open
    :param cutoff: Limit scrolling to N attempts
    :param group:  Folder name to group channels under
    """

    base_path = path.join("corpus", "screened_urls")
    if screen:
        base_path = path.join("corpus", "unscreened_urls")

    if group:
        videos_out_dir = path.join(base_path, group, "urls")
        videos_fn = "{0}.txt".format(group)
    else:
        videos_out_dir = path.join(base_path, "urls")
        videos_fn = "{0}.txt".format(info["SafeChannelName"])
    if not path.exists(videos_out_dir):
        makedirs(videos_out_dir)

    videos_path = path.join(videos_out_dir, videos_fn)

    write_mode = 'a'
    if overwrite:
        write_mode = 'w'

    videos_out = open(videos_path, write_mode)
    videos_out.close()

    with open(channels_fn, 'r') as channels_in:
        with webdriver.Firefox() as driver:
            for line in channels_in:
                line = line.split('\t')[0]
                line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?
                process_video(line, videos_path, cutoff, group, driver, noscrape, screen, overwrite)
                sleep(1)


def handle_single(args):
    """Wrapper for scraping a single channel"""
    process_channel(args.channel, args.cutoff, args.group, False, args.screen)


def handle_multiple(args):
    """Wrapper for scraping multiple channels"""
    process_channels(args.file, args.cutoff, args.group, False, args.screen)


def handle_video(args):
    """Wrapper for scraping multiple videos"""
    process_videos(args.file, args.cutoff, args.group, args.noscrape, args.screen, args.overwrite)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape video URLs from a YouTube channel.')
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(help='process one channel, a list of channels, or a list of videos')

    channel_parser = subparsers.add_parser('single', help='process a single channel (see scrape_channels.py single -h for more help)')
    channel_parser.set_defaults(func=handle_single)
    channel_parser.add_argument('channel', type=str, help='URL pointing to the channel\'s main page, e.g. https://www.youtube.com/c/ChannelNameHere')
    channel_parser.add_argument('-g', '--group', default=None, metavar='NAME', type=str, help='grouping for the output files (will create a subfolder: screened_urls/$group)')
    channel_parser.add_argument('--cutoff', type=int, default=-1, help='maximum number of times to scroll the page when scraping')
    channel_parser.add_argument('--screen',         action='store_true', default=False, help='download files for screening purposes')
    channel_parser.add_argument('-l', '--log', action='store_true', default=False, help='log events to file')

    list_parser = subparsers.add_parser('multi', help='process a list of channels (see scrape_channels.py multi -h for more help)')
    list_parser.set_defaults(func=handle_multiple)
    list_parser.add_argument('file', type=str, help='file containing a newline-separated list of channel URLs (e.g. https://www.youtube.com/c/Channel1NameHere\\n https://www.youtube.com/c/Channel2NameHere\\n)')
    list_parser.add_argument('-g', '--group', default=None, metavar='NAME', type=str, help='grouping for the output files (will create a subfolder: screened_urls/$group)')
    list_parser.add_argument('--cutoff', type=int, default=-1, help='maximum number of times to scroll the page when scraping')
    list_parser.add_argument('--screen',         action='store_true', default=False, help='download files for screening purposes')
    list_parser.add_argument('-l', '--log', action='store_true', default=False, help='log events to file')

    video_parser = subparsers.add_parser('video', help='process channels from a list of videos (see scrape_channels.py video -h for more help)')
    video_parser.set_defaults(func=handle_video)
    video_parser.add_argument('file', type=str, help='file containing a newline-separated list of video URLs')
    video_parser.add_argument('-n', '--noscrape', action='store_true', default=False, help='don\'t scrape the channel; only gather about info')
    video_parser.add_argument('-g', '--group', default=None, metavar='NAME', type=str, help='grouping for the output files (will create a subfolder: screened_urls/$group)')
    video_parser.add_argument('--cutoff', type=int, default=-1, help='maximum number of times to scroll the page when scraping')
    video_parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')
    video_parser.add_argument('--screen',         action='store_true', default=False, help='download files for screening purposes')
    video_parser.add_argument('-l', '--log', action='store_true', default=False, help='log events to file')

    args = parser.parse_args()

    if(args.log):
        logging.basicConfig(filename=(args.channel + '_scrape.log'), level=logging.DEBUG)

    logging.info("Call: {0}".format(args))
    logging.info("BEGIN YT SCRAPE\n----------")

    if(args.func == None):
        parser.print_help()
        exit(2)

    args.func(args)
