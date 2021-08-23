from pytube import YouTube, exceptions, helpers
from os import path, makedirs, remove
from sys import path
from time import sleep
from re import sub

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import logging


# TODO: Need to implement robust error handling

class ChannelScraper:

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


class VideoScraper(ChannelScraper):
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


class MultiChannelScraper:

    def __init__(self, channels_f, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, overwrite=False, screen=False):

        self.channels = []
        self.channels_f = channels_f

        # To be passed to ChannelScraper objects
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

                    channel = ChannelScraper(line, self.browser, self.pause_time, self.cutoff, self.group, self.overwrite, self.screen)
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


class MultiVideoScraper:

    def __init__(self, videos_f, browser="Firefox", pause_time=1, cutoff=-1, group='', ignore_videos=False, screen=False, overwrite=False):

            self.overwrite     = overwrite
            self.videos_f      = videos_f

            # To be passed to VideoScraper objects
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

                # VideoScraper takes a video URL and scrapes the channel data
                # TODO: This isn't very transparent
                channel = VideoScraper(line, self.browser, self.pause_time, self.cutoff, self.group, self.overwrite, self.screen)
                channel.scrape()
                self.channels.append(channel)


class Video:

    def __init__(video, yt_id, channel_name="", channel_id="", group='', screen=False, convert_srt=False, include_title=False):

        try:
            self.video = YouTube(url)

        except KeyError as e: # Why is ths here?
            logging.warning("ERROR: Could not retrieve URL ({0})".format(self.url))
            exit(1)

        except exceptions.VideoUnavailable as e:
            logging.warning("ERROR: Video unavailable ({0}). Are you using the latest version of PyTube?".format(video_count, url))
            exit(1)


        self.yt_id = yt_id
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.group = group
        self.screen = screen
        self.convert_srt = convert_srt
        self.include_title = include_title

    def write_captions(self, captions):
        """Write Caption object to a file. If an output folder is not specified, captions will be placed in a folder corresponding to the name of the video's author (i.e. channel).

        :param captions: The Caption track to download

        :return success: 1 if captions were downloaded successfully, 0 otherwise
        """

        safe_title = helpers.safe_filename(self.video.title)
        out_path = ""

        if self.screen:
            out_path = path.join("corpus", "unscreened_urls", "subtitles")
            if self.group:
                out_path = path.join("corpus", "unscreened_urls", self.group, "subtitles")
        else:
            out_path = path.join("corpus", "raw_subtitles")
            if self.group:
                out_path = path.join(out_path, self.group)

        if "a." in captions.code:
            out_path = path.join(out_path, "auto", captions.code.split(".")[1])
        else:
            out_path = path.join(out_path, "manual", captions.code.split(".")[0])

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        if self.channel_name and self.channel_id:
            safe_channel_name = sub(punc_and_whitespace, "", self.channel_name)
            safe_author = "{0}_{1}".format(safe_channel_name, self.channel_id)
        else:
            safe_author = sub(punc_and_whitespace, "", video.author)

        out_path = path.join(out_path, safe_author)

        if not path.exists(out_path):
            makedirs(out_path)

        try:
            if self.include_title:
                captions.download(helpers.safe_filename(safe_title), srt=self.convert_srt, output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, self.yt_id))
                return 1
            else:
                captions.download(str(self.yt_id), srt=self.convert_srt, output_path=out_path, filename_prefix="{0}_".format(safe_author))
                return 1
        except:
            logging.critical("Video {0}: Could not download caption track for video {0} from channel {1} ({2})".format(self.yt_id, video.author, video.title))
            return 0


    def write_audio(audio, video, yt_id, channel_name="", channel_id="", group=None, screen=None, include_title=False):
        """Write audio Stream object to a file. If an output folder is not specified, audio will be placed in a folder corresponding to the name of the video's author (i.e. channel).

        :param audio: The audio Stream to download
        :param yt_id: YouTube ID string of the video from the url
        :param channel_name: The name of the channel as given on its main page (default "")
        :param channel_id: The name of the channel as it appears in the channel's URL (default "")
        :param group: The folder to output the audio stream to (default None)
        :param include_title: Include video title in audio filename (default True)
        """

        safe_title = helpers.safe_filename(video.title)
        safe_author = helpers.safe_filename(video.author)

        if screen:
            out_path = path.join("corpus", "unscreened_urls", "audio")
            if group:
                out_path = path.join("corpus", "unscreened_urls", group, "audio")
        else:
            out_path = path.join("corpus", "raw_audio")
            if group:
                out_path = path.join(out_path, group)

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        if channel_name and channel_id:
            safe_channel_name = sub(punc_and_whitespace, "", channel_name)
            safe_author = "{0}_{1}".format(safe_channel_name, channel_id)
        else:
            safe_author = sub(punc_and_whitespace, "", video.author)

        out_path = path.join(out_path, safe_author)

        if not path.exists(out_path):
            makedirs(out_path)

        try:
            if include_title:
                audio.download(filename=safe_title + '.mp4', output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, yt_id), skip_existing=True)
            else:
                audio.download(filename=str(yt_id) + '.mp4', output_path=out_path, filename_prefix="{0}_".format(safe_author), skip_existing=True)

        except:
            logging.critical("Video {0}: Could not save audio stream for video {0} from channel {1} ({2})".format(yt_id, video.author, video.title))

        # Be polite
        sleep(1)


    def write_captions_by_language(video, yt_id, channel_name="", channel_id="", language=None, group=None, screen=None, include_auto=False, convert_srt=False, include_title=False):
        """Filter captions by language and write each caption track to a file. If no language is specified, all caption tracks will be downloaded.

        :param video: The YouTube object to download caption tracks from
        :param yt_id: YouTube ID string of the video from the url
        :param channel_name: The name of the channel as given on its main page (default "")
        :param channel_id: The name of the channel as it appears in the channel's URL (default "")
        :param language: The language to download caption tracks for (default None)
        :param group: The folder to output the caption track to (default None)
        :param convert_srt: Convert captions from XML to SRT format (default False)
        :param include_title: Include video title in caption filename (default False)

        :return caption_list: list of metadata for all successfully-downloaded caption tracks
        """

        caption_list = []
        for track in video.captions:
            if language is None or (language in track.name and (include_auto or "a." not in track.code)):

                success = write_captions(track, video, yt_id, channel_name, channel_id, group, screen, convert_srt, include_title)
                if success:
                    caption_list.append((track.code, track.name))

                # Be polite
                sleep(1)

        return caption_list


    def write_metadata(video, yt_id, caption_list, log_writer, url, channel_name="", channel_id=""):
        """Write video metadata to log file.

        :param video: The YouTube object to log
        :param yt_id: YouTube ID string of the video from the url
        :param caption_list: A list of successfully-downloaded captions
        :param log_writer: DictWriter to use for writing metadata
        :param channel_name: The name of the channel as given on its main page (default "")
        :param channel_id: The name of the channel as it appears in the channel's URL (default "")
        """

        channel_initials = "".join( [name[0].upper() for name in video.author.split()] )

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        safe_author = sub(punc_and_whitespace, "", video.author)

        metadata = {
            "yt_id": yt_id,
            "author": video.author,
            "code": channel_initials,
            "name": safe_author,
            "ID": channel_id,
            "url": url,
            "title": video.title,
            "description": video.description.replace('\n', ' '),
            "keywords": video.keywords,
            "length": video.length,
            "publish_date": video.publish_date,
            "views": video.views,
            "rating": video.rating,
            "captions": caption_list,
            "scrape_time": strftime("%Y-%m-%d_%H:%M:%S"),
            "corrected": 0,
        }

        log_writer.writerow(metadata)


    def process_video(video, yt_id, channel_dict, log_writer, channel_name=None, channel_id=None, url=None, language=None, group=None, screen=None, include_audio=False, include_auto=False, convert_srt=False, include_title=False, overwrite=False):
        """Download captions, audio (optional), and metadata for a given video.

        :param video: The YouTube object to process
        :param channel_name: The name of the channel as given on its main page (default None)
        :param channel_id: The name of the channel as it appears in the channel's URL (default None)
        :param channel_id: The url of the video
        :param yt_id: YouTube ID string of the video from the url
        :param language: The language to download caption tracks for (default None)
        :param group: The folder to output the caption track to (default None)
        :param convert_srt: Convert captions from XML to SRT format (default False)
        :param include_title: Include video title in caption filename (default False)

        :return caption_dict: list of metadata for all successfully-downloaded caption tracks
        """

        if video.author not in channel_dict.keys():
            channel_dict.update({video.author: 0})
        channel_dict[video.author] = channel_dict[video.author] + 1

        caption_list = write_captions_by_language(video, yt_id, channel_name, channel_id, language, group, screen, include_auto, convert_srt, include_title)

        if include_audio:
            audio = video.streams.filter(mime_type="audio/mp4").first()
            write_audio(audio, video, yt_id, channel_name, channel_id, group, screen, include_title)

        if len(caption_list):
            write_metadata(video, yt_id, caption_list, log_writer, url, channel_name, channel_id)

        return channel_dict


    def process_videos(urls_path, batch=False, language=None, group=None, screen=None,  include_audio=False, include_auto=False, convert_srt=False, resume_from=0, limit_to=-1, overwrite=False):
        """Download captions, audio (optional), and metadata for a list of videos.

        :param batch: Indicates if a directory or single file is being processed
        :param video: Path to a file containing the list of URLs to process
        :param channel_name: The name of the channel as given on its main page (default None)
        :param channel_id: The name of the channel as it appears in the channel's URL (default None)
        :param language: The language to download caption tracks for (default None)
        :param group: The subfolder to output the caption and audio tracks to (default None)
        :param include_audio: Download audio in addition to captions (default False)
        :param include_auto: Download automatically-generated captions (default False)
        :param convert_srt: Convert captions from XML to SRT format (default False)
        :param resume_from: Start from the Nth entry in the URL list (default 0)
        :param limit_to: Download captions (and audio) from only N files (default -1)
        """

        channel_dict = {}
        video_count = 0

        if group is None:
            log_fn = "{0}_log.csv".format(path.splitext(path.split(urls_path)[1])[0])
        else:
            log_fn = "{0}_log.csv".format(group)

        log_fp = path.join("corpus", "logs", log_fn)
        if screen:
            log_fp = path.join("corpus", "unscreened_urls", "logs", log_fn)

        log_exists = path.exists(log_fp)

        write_type = 'a'
        #if batch and group:
        #    write_type = 'a'
        if overwrite:
            write_type = 'w'

        if screen:
            out_path = path.join("corpus", "unscreened_urls", "subtitles")
            if group:
                out_path = path.join("corpus", "unscreened_urls", group, "subtitles")
            out_audio_path = None
        else:
            out_path = path.join("corpus", "raw_subtitles")
            out_audio_path = path.join("corpus", "raw_audio")
            if group:
                out_path = path.join(out_path, group)
                out_audio_path = path.join(out_audio_path, group)

        with open(urls_path, "r") as urls_in, open(log_fp, write_type) as log_out:

            # Prepare writer for writing video data
            log_writer = DictWriter(log_out, fieldnames=["yt_id", "author", "code", "name", "ID", "url", "title", "description", "keywords", "length", "publish_date", "views", "rating", "captions", "scrape_time", "corrected"])
            if not (batch and group):
                if overwrite or not log_exists:
                    log_writer.writeheader()

            for url_data in urls_in:

                video_count += 1

                if(video_count < resume_from):
                    continue

                url_data = url_data.strip('\n').split('\t')
                # Get URL and title
                if len(url_data) == 3:
                    (url, channel_name, channel_id) = url_data
                elif len(url_data) == 2:
                    url = url_data[0]
                    channel_name=url_data[1]
                    channel_id=None
                elif len(url_data) == 1:
                    url = url_data[0]
                    channel_name=None
                    channel_id=None
                else:
                    logging.critical("Invalid file format")
                    exit(2)

                punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
                yt_id = sub(punc_and_whitespace, '',
                                findall(r".+watch\?v=(.+)\b", url)[0])

                # Check if yt_id already exists in some file; skip download if so

                if not overwrite:
                    files = glob(path.join(out_path, "**", "*{0}*".format(yt_id)), recursive=True)
                    if out_audio_path:
                        audio_files = glob(path.join(out_audio_path, "**", "*{0}*".format(yt_id)), recursive=True)
                        files = files + audio_files
                    if files:
                        continue

                # Try to load the video
                try:
                    video = YouTube(url)
                except KeyError as e:
                    logging.warning("Video {0}: Could not retrieve URL ({1})".format(video_count, url))
                    continue
                except exceptions.VideoUnavailable as e:
                    logging.warning("Video {0}: Video unavailable ({1})".format(video_count, url))
                    continue
                # except:
                #     logging.critical("Video {0}: An unexpected error occured ({1})".format(video_count, url))
                #     continue

                process_video(video, yt_id, channel_dict, log_writer, channel_name, channel_id, url, language, group, screen, include_audio, include_auto, convert_srt, False, overwrite)

                if limit_to != -1 and video_count == resume_from + limit_to:
                    print("{0}: Limit reached".format(urls_path))
                    break


    def process_files(urls_path, language=None, group=None, screen=None, include_audio=False, include_auto=False, convert_srt=False, resume_from=0, limit_to=-1, overwrite=False):
        """Download captions, audio (optional), and metadata from a directoy of video lists.

        :param video: Path to a directory containing a set of list files
        :param channel_name: The name of the channel as given on its main page (default None)
        :param channel_id: The name of the channel as it appears in the channel's URL (default None)
        :param language: The language to download caption tracks for (default None)
        :param group: The subfolder to output the caption and audio tracks to (default None)
        :param include_audio: Download audio in addition to captions (default False)
        :param include_auto: Download automatically-generated captions (default False)
        :param convert_srt: Convert captions from XML to SRT format (default False)
        :param resume_from: Start from the Nth entry in the URL list (default 0)
        :param limit_to: Download captions (and audio) from only N files (default -1)
        """

        URL_fns_txt = sorted(glob(path.join(urls_path, "*.txt")))
        URL_fns_csv = sorted(glob(path.join(urls_path, "*.csv")))

        if group:
            log_fn = "{0}_log.csv".format(group)
            log_fp = path.join("corpus", "logs", log_fn)
            if screen:
                log_fp = path.join("corpus", "unscreened_urls", "logs", log_fn)

            log_exists = path.exists(log_fp)

            write_mode = 'a'
            if overwrite:
                write_mode = 'w'

            with open(log_fp, write_mode) as log_out:
                log_writer = DictWriter(log_out, fieldnames=["yt_id", "author", "code", "name", "ID", "url", "title", "description", "keywords", "length", "publish_date", "views", "rating", "captions", "scrape_time", "corrected"])
                if overwrite or not log_exists:
                    log_writer.writeheader()

        all_fns = URL_fns_txt + URL_fns_csv

        for fn in all_fns:
            process_videos(fn, True, language, group, screen, include_audio, include_auto, convert_srt, resume_from, limit_to, False, overwrite)
