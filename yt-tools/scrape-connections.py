import argparse
import re
from bs4 import BeautifulSoup
from requests import get
from time import sleep
import pandas as pd
from os import path, makedirs

def scrape_channel_info(channel, channel_set, depth, max_depth):

    sleep(1)

    print("Channel: {0}".format(channel))
    print("Depth: {0}".format(depth))

    if depth == max_depth:
          return channel_set

    channels_page = get("https://www.youtube.com/user/" + channel + "/channels")
    channels_html = BeautifulSoup(channels_page.content, "html.parser")
    if channels_html.get_text() == '404 Not Found':
        channels_page = get("https://www.youtube.com/c/"+ channel +"/channels")
        channels_html = BeautifulSoup(channels_page.content, "html.parser")

    listed_channels = set(re.findall('\"/user/([a-zA-Z0-9]+)\"', str(channels_html)))

    if not listed_channels:
        return channel_set

    channel_set_prev = channel_set
    channel_set.update(listed_channels)

    for new_channel in listed_channels:
        #if new_channel not in channel_set_prev:
        channel_set.update(scrape_channel_info(new_channel, channel_set, depth + 1, max_depth))

    print("Channel set: {0}".format(channel_set))
    return channel_set

def scrape_channel_about(channel):

    about_page = get("https://www.youtube.com/user/" + channel + "/about")
    about_html = BeautifulSoup(about_page.content, "html.parser")
    if about_html.get_text() == '404 Not Found':
        about_page = get("https://www.youtube.com/c/" + channel + "/about")
        about_html = BeautifulSoup(about_page.content, "html.parser")

    try:
        about_title = re.findall('"name":\s+"(.+?)"}', str(about_html))[0]
    except IndexError:
        about_title = None
    try:
        about_text = re.findall('"description":{"simpleText":"(.+?)"},"', str(about_html))[0]
    except IndexError:
        about_text = None

    return {'user': channel, 'author': about_title, 'description': about_text}

def main(args):

    print('\nRunning recursive search for connections...')

    max_depth = args.max_depth
    with open(args.seed_users, 'r') as f:
        seed_list = [line.strip('\n') for line in f.readlines()]

    channel_set_seed = set(seed_list)
    channel_set = set()
    for channel in channel_set_seed:
        channel_set.update(scrape_channel_info(channel, set(), 1, max_depth))
    print(channel_set)

    print('\nScraping connections for about description...')

    if args.group:
        connect_out_dir = path.join("corpus", "unscreened_urls", args.group, "connections")
    else:
        connect_out_dir = path.join("corpus", "unscreened_urls", "connections")
    if not path.exists(connect_out_dir):
        makedirs(connect_out_dir)

    name = path.splitext(path.basename(args.seed_users))[0]
    out_file = path.join(connect_out_dir, name+"_connections.csv")

    out_df = pd.DataFrame(columns=['user', 'author', 'description'])

    for channel in channel_set:
        about_data = scrape_channel_about(channel)
        out_df = out_df.append(about_data, sort=False, ignore_index=True)

    out_df.to_csv(out_file, index=False)

    print('\nSaved output file!')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Scrape connected channel links from YouTube channel and their about pages.')

    parser.add_argument('seed_users', type=str, help='path to a file containing the users to start search from')
    parser.add_argument('--max_depth', '-max', type=int, metavar='N', default=5,  help='maximum depth of recursion (default=5)')
    parser.add_argument('-g', '--group', default=None, type=str, help='name to group files under (will create a subfolder: unscreened_urls/$group)')

    args = parser.parse_args()

    main(args)
