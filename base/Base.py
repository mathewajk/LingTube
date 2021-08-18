from sys import path
from pathlib import Path

from time import sleep
from os import path, makedirs, remove
from re import sub
from glob import glob
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ChannelHandler:

    def __init__(self, url, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, screen=False):

        self.url = url

        # Default variables
        self.browser       = browser
        self.pause_time    = pause_time
        self.cutoff        = cutoff
        self.group         = group
        self.ignore_videos = ignore_videos
        self.screen        = screen


    def init_info(self, driver):
        """Initialize *info* with the channel's ID
        """

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"

        # Remove trailing forward slash
        if self.url[-1] == '/':
            self.url = self.url[:-1]

        # TODO: We are assuming URLs are frmatted correctly
        channel_id = self.url.split('/')[-1]
        info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

        logging.info("Gathering videos from channel ID: " + channel_id)

        return info


    def process(self):
        """Scrape the channel and save
        """

        self.scrape()
        self.save()


    def save(self):
        """Save info and (if applicable) list of video URLs as text files
        """

        # If videos need to be screened, save to separate folder
        if self.screen:
            base_path = path.join("corpus", "unscreened_urls")
        else:
            base_path = path.join("corpus", "screened_urls")

        # Create info output path
        info_out_dir = path.join(base_path, self.group, "about")
        if not path.exists(info_out_dir):
            makedirs(info_out_dir)

        # Create filename based on channel name and unique ID
        info_out_fn = "{0}_{1}_info.txt".format(self.info["SafeChannelName"], self.info["SafeChannelID"])
        info_out_fn = path.join(info_out_dir, info_out_fn)

        # Save channel info
        with open(info_out_fn, 'w') as info_out:

            for key in self.info.keys():
                info_out.write("# {0}\n\n".format(key))
                info_out.write("{0}\n\n".format(self.info[key]))

        # Don't save the links if we didn't scrape anything
        if self.ignore_videos:
            return

        # Create URL out path
        url_out_dir = path.join(base_path, self.group, "channel_urls")
        if not path.exists(url_out_dir):
            makedirs(url_out_dir)

        # Create filename based on channel name and unique ID
        videos_out_fn = "{0}_{1}_videos.txt".format(self.info["SafeChannelName"], self.info["SafeChannelID"])
        videos_out_fn = path.join(url_out_dir, videos_out_fn)

        with open(videos_out_fn, 'w') as videos_out:
            for link in self.links:
                videos_out.write("{0}\t{1}\t{2}\n".format(link, self.info["ChannelName"], self.info["SafeChannelID"]))


    def scroll(self, driver):
        """Scroll the channel to load more videos.

        :return continue: 1 if scroll was successful, 0 if page bottom has been reached
        """

        # Get scroll height
        last_height = driver.execute_script('return document.querySelector("#page-manager").scrollHeight')

        # Scroll down to bottom of current view
        driver.execute_script('window.scrollTo(0,document.querySelector("#page-manager").scrollHeight);')

        # Wait to load page
        sleep(self.pause_time)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script('return document.querySelector("#page-manager").scrollHeight')
        if new_height == last_height: # End of list
            return 0
        return 1


    def scrape_links(self, driver):
        """Scrape the URLs from a YouTube channel.

        :return : List of videos URLs
        """

        # Load the page
        driver.get(self.url + "/videos")

        try:
            # Wait for the "items" div to appear
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'items')))
        except:
            logging.warning("Could not locate 'items' div")
        finally:
            # Scroll to the bottom of the page to load videos
            count = 0
            while (self.cutoff == -1 or count < self.cutoff) and self.scroll(driver):
                count += 1
                print("Loading... ({0})".format(count))

            # Gather urls and metadata
            elements = driver.find_elements_by_xpath('//*[@id="video-title"]')
            return [element.get_attribute('href') for element in elements]


    def scrape_info(self, driver):
        """Scrape the channel's description.

        :return: A dictionary containing the channel's description, bio, and metadata.
        """

        info = self.init_info(driver)

        # Load the about page
        driver.get(self.url + "/about")

        info.update({"ChannelName": "", "Description": "", "Bio": "", "Metadata": ""})

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
            logging.warning("Could not scrape about page")

        return info


    def scrape(self):
        """Collect video URLs (if scraping URLs) and about page info from the channel
        """

        if self.browser == "Firefox":

            with webdriver.Firefox() as driver:

                self.info = self.scrape_info(driver)

                if self.ignore_videos:
                    self.links = None
                else:
                    self.links = self.scrape_links(driver)
        else:

            with webdriver.Chrome() as driver:

                self.info.update(self.scrape_info(driver))

                if self.ignore_videos:
                    self.links = None
                else:
                    self.links = self.scrape_links(driver)


    def get_info(self):
        return self.info


    def get_links(self):
        return self.links


    def get_url(self):
        return self.url


class VideoHandler(ChannelHandler):
    """Scrape channel info and videos from a channel based on the URL of a video from that channel.
    """

    def __init__(self, url, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, overwrite=False, screen=False):

        self.overwrite = overwrite
        super().__init__(url, browser, pause_time, cutoff, group, ignore_videos, screen)


    def init_info(self, driver):
        """Initialize *info* with the channel name and ID. For videos, this requires scraping the video's page.
           This function also updates self.url to reflect the URL of the channel.
        """

        driver.get(self.url)

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))

            sleep(2)

            channel_url = driver.find_element(By.CLASS_NAME, "ytd-channel-name").find_element(By.TAG_NAME, 'a').get_attribute('href')
            logging.info("Gathering information from channel: " + channel_url)

            # TODO: Not really the safest way to update the URL. Video and channel URL should be kept clearly distinct.
            self.video_url = self.url
            self.url = channel_url

            punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
            channel_id = channel_url.split('/')[-1]
            info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

            return info

        except:
            logging.critical("Could not locate channel URL")
            exit(1)


    def save(self):
        """Save channel info and scraped videos (if applicable)
        """

        super().save()
        self.log_video()


    def log_video(self):
        """Log the video URL, channel name, and channel ID in LingTube format
        """

        # TODO: Genertion of base_path is redundant given the save() function
        base_path = path.join("corpus", "screened_urls")
        if self.screen:
            base_path = path.join("corpus", "unscreened_urls")

        if self.group:
            videos_out_dir = path.join(base_path, self.group, "urls")
            videos_fn = "{0}.txt".format(self.group)
        else:
            videos_out_dir = path.join(base_path, "urls")
            videos_fn = "{0}.txt".format(self.info["SafeChannelName"])
        if not path.exists(videos_out_dir):
            makedirs(videos_out_dir)

        videos_path = path.join(videos_out_dir, videos_fn)

        if path.isfile(videos_path) and self.overwrite:
            remove(videos_path)

        # Log input video info
        with open(videos_path, 'a') as videos_out:
            videos_out.write("{0}\t{1}\t{2}\n".format(self.video_url, self.info["ChannelName"], self.info["SafeChannelID"]))


class MultiChannelHandler:

    def __init__(self, channels_f, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, overwrite=False, screen=False):

        self.channels = []
        self.channels_f = channels_f

        # To be passed to ChannelHandler objects
        self.browser       = browser
        self.pause_time    = pause_time
        self.cutoff        = cutoff
        self.group         = group
        self.ignore_videos = ignore_videos
        self.overwrite     = overwrite
        self.screen        = screen


    def process(self):

        try:
            with open(self.channels_f) as channels_in:
                for line in channels_in:
                    line = line.split('\t')[0]
                    line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?

                    channel = ChannelHandler(line, self.browser, self.pause_time, self.cutoff, self.group, self.overwrite, self.screen)
                    channel.scrape()
                    self.channels.append(channel)
                    sleep(1)
        except FileNotFoundError as e:
            print('Error: File {0} could not be found.'.format(self.channels_f))


    def save(self):
        """Write channel information and (if scraping) a scraped list of video links to a file.
        """

        for channel in self.channels:
            channel.save()


class MultiVideoHandler:

    def __init__(self, videos_f, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, screen=False, overwrite=False):

            self.overwrite     = overwrite
            self.videos_f      = videos_f

            # To be passed to VideoHandler objects
            self.browser       = browser
            self.pause_time    = pause_time
            self.cutoff        = cutoff
            self.group         = group
            self.ignore_videos = ignore_videos
            self.screen        = screen


    def process(self):

        with open(self.channels_f) as channels_in:

            for line in videos_f:

                line = line.split('\t')[0]
                line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?

                # VideoHandler takes a video URL and scrapes the channel data
                # TODO: This isn't very transparent
                channel = VideoHandler(line, self.browser, self.pause_time, self.cutoff, self.group, self.overwrite, self.screen)
                channel.scrape()
                self.channels.append(channel)
