import math, time, logging, shutil
import pandas as pd

import xml.etree.ElementTree as ElementTree

from pytube import YouTube, Channel, exceptions, helpers
from os import path, makedirs, remove, rename, listdir
from re import sub, findall
from glob import glob
from csv import DictWriter

from html import unescape

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# TODO: Need to implement robust error handling


class ChannelScraper:

    def __init__(self, url, browser="Firefox", limit=-1, group='_ungrouped', about=False, overwrite=False, screen=False):

        self.url = url
        if self.url[-1] == '/':
            self.url = self.url[:-1]
        self.from_video = False

        if "watch?" in self.url:
            self.from_video = True

        # Default variables
        self.browser       = browser
        self.group         = group
        self.about         = about
        self.overwrite     = overwrite
        self.screen        = screen
        self.limit         = limit


    def init_files(self):

        # If videos need to be screened, save to separate folder
        if self.screen:
            base_path = path.join("corpus", "unscreened_videos")
        else:
            base_path = path.join("corpus", "screened_urls")

        # Generate output directory paths
        out_dirs = {"info_out_dir": path.join(base_path, self.group, "about"),
                     "log_out_dir": path.join(base_path, self.group),
                    "urls_out_dir": path.join(base_path, self.group, "channel_urls")}

        # Make directories if they don't exist
        for key in out_dirs:
            if not path.exists(out_dirs[key]):
                makedirs(out_dirs[key])

        # Generate output filenames
        log_out_fn  = "{0}_videos.txt".format(self.group) # One video log file per group
        info_out_fn = "{0}_{1}_info.txt".format(self.info["SafeChannelName"], self.info["SafeChannelID"])
        urls_out_fn = "{0}_{1}_videos.txt".format(self.info["SafeChannelName"], self.info["SafeChannelID"])

        # Generate output file paths
        self.log_path        = path.join(out_dirs["log_out_dir"], log_out_fn)
        self.info_out_path   = path.join(out_dirs["info_out_dir"], info_out_fn)
        self.urls_out_path   = path.join(out_dirs["urls_out_dir"], urls_out_fn)


    def process(self):
        """Scrape the channel and save
        """

        self.scrape()
        self.init_files() # TODO: Better name?

        # If we are working from a video, log the video URL
        if self.from_video:
            self.log_video()
        self.save()


    def save(self):
        """Save info and (if applicable) list of video URLs as text files
        """

        # Save channel info if it was scraped and file doesn't exist already
        if self.info and not path.isfile(self.info_out_path):
            with open(self.info_out_path, 'w') as info_out:
                for key in self.info.keys():
                    info_out.write("# {0}\n\n".format(key))
                    info_out.write("{0}\n\n".format(self.info[key]))

        # Don't save the links if we didn't scrape anything
        if self.about:
            return

        # TODO: This is a mess.
        previous_urls = []
        if path.isfile(self.urls_out_path):
            with open(self.urls_out_path, 'r') as urls_in:
                previous_urls = [line.split('\t')[0] for line in urls_in]
        previous_urls.append(self.url)

        # Scrape up to LIMIT new video URLs; if no limit, scrape all video URLs
        new_urls = set(self.urls).symmetric_difference(set(previous_urls))

        # Save new video URLs
        url_count = 0
        if new_urls:
            with open(self.urls_out_path, 'a') as urls_out:
                for url in new_urls:

                    formatted_url = "{0}\t{1}\t{2}\n".format(url, self.info["ChannelName"], self.info["SafeChannelID"])
                    urls_out.write(formatted_url)

                    url_count += 1
                    if url_count == self.limit:
                        break


    def scrape_urls(self, channel):
        """Scrape the URLs from a YouTube channel.

        :return : List of videos URLs
        """

        return channel.video_urls


    def scrape_info(self, driver, channel_id, channel_url):
        """Scrape the channel's description.

        :return: A dictionary containing the channel's description, bio, and metadata.
        """

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}
        info.update({"ChannelName": "", "SafeChannelName": "", "Description": "", "Bio": "", "Metadata": ""})

        # Load the about page
        driver.get(channel_url + "/about")

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))

            channel_name = driver.find_element(By.CLASS_NAME, "ytd-channel-name").text

            info["ChannelName"] = channel_name
            info["SafeChannelName"] = sub(punc_and_whitespace, "", channel_name)

        except:
            logging.warning("Could not scrape channel name")

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'description')))
            info["Description"] = driver.find_element(By.ID, "description-container").text
            info["Bio"]         = driver.find_element(By.ID, "bio").text
            info["Metadata"]    = driver.find_element(By.ID, "details-container").find_element(By.TAG_NAME, "table").text
        except:
            logging.warning("Could not scrape about page")

        return info


    def scrape(self):
        """Collect video URLs (if scraping URLs) and about page info from the channel
        """

        # Get the channel's ID and URL from video (if input is a video)
        # Get from input channel URL otherwise
        if self.from_video:
            video = YouTube(self.url)
            channel_id = video.channel_id
            channel_url = 'https://www.youtube.com/channel/' + video.channel_id
        else:
            channel_id = self.url.split('/')[-1]
            channel_url = self.url

        # Gather URLs, unless we only want About page info
        self.urls = None
        if not self.about:
            channel = Channel(channel_url) # Load channel in PyTube
            print('Collecting video URLs from channel {0}'.format(channel.channel_id))
            self.urls = self.scrape_urls(channel)

        # Open a web browser in headless mode and scrape the About page
        if self.browser.lower() == "firefox":
            try:
                options = webdriver.FirefoxOptions()
                options.set_headless()
                with webdriver.Firefox(firefox_options=options) as driver:
                    self.info = self.scrape_info(driver, channel_id, channel_url)
            except FileNotFoundError as e:
                logging.critical("Could not locate geckodriver (Firefox browser)")
        elif self.browser.lower() == "chrome":
            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--window-size=1920x1080")
                with webdriver.Chrome(chrome_options=options) as driver:
                    self.info = self.scrape_info(driver, channel_id, channel_url)
            except FileNotFoundError as e:
                logging.critical("Could not open chromedriver (Chrome browser)")
        else:
            print('ERROR: Invalid browser. Please enter "chrome" or "firefox"')


    def log_video(self):
        """Log the video URL, channel name, and channel ID in LingTube format
        """

        # Grab the previously logged videos
        logged_videos = []
        if path.exists(self.log_path):
            with open(self.log_path, 'r') as log_in:
                logged_videos = [line.split('\t')[0] for line in log_in]

        # Check for overlap and log new URLs
        with open(self.log_path, 'a') as log_out:
            if self.url not in logged_videos:
                formatted_url = "{0}\t{1}\t{2}\n".format(self.url, self.info["ChannelName"], self.info["SafeChannelID"])
                log_out.write(formatted_url)


    def get_info(self):
        return self.info


    def get_links(self):
        return self.urls


    def get_url(self):
        return self.url


class MultiChannelScraper:

    def __init__(self, source, browser="Firefox", cutoff=-1, group='ungrouped', about=False, overwrite=False, screen=False):

        self.channels = []
        self.source   = source

        # To be passed to ChannelScraper objects
        self.browser       = browser
        self.cutoff        = cutoff
        self.group         = group
        self.about         = about
        self.overwrite     = overwrite
        self.screen        = screen


    def process(self):

        # If overwriting, delete entire group subfolder
        if self.overwrite:

            if self.screen:
                base_path = path.join("corpus", "unscreened_videos")
            else:
                base_path = path.join("corpus", "screened_urls")

            group_dir = path.join(base_path, self.group)
            if path.isdir(group_dir):
                shutil.rmtree(group_dir)

        # Single URL
        if 'http' in self.source:
            scraper = ChannelScraper(self.source, self.browser, self.cutoff, self.group, self.about, self.overwrite, self.screen)
            scraper.process()

        # Multiple URLs
        elif path.isfile(self.source):
            with open(self.source) as file_in:
                for line in file_in:
                    line = line.split('\t')[0]
                    line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?

                    scraper = ChannelScraper(line, self.browser, self.cutoff, self.group, self.about, self.overwrite, self.screen)
                    scraper.process()
                    time.sleep(1)


class VideoScraper:

    def __init__(self, url, yt_id, log_fp=None, channel_name="", channel_id="", language=None, include_audio=False, include_auto=False, group='ungrouped', screen=False, convert_srt=False, include_title=False):

        try:
            self.video = YouTube(url)

        except exceptions.VideoUnavailable as e:
            logging.warning("ERROR: Video unavailable ({0}). Are you using the latest version of PyTube?".format(video_count, url))

        self.url           = url
        self.yt_id         = yt_id
        self.log_fp        = log_fp
        self.channel_name  = channel_name
        self.channel_id    = channel_id
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.convert_srt   = convert_srt
        self.include_audio = include_audio
        self.include_auto  = include_auto
        self.include_title = include_title


    def write_captions(self, captions):
        """Write Caption object to a file. If an output folder is not specified, captions will be placed in a folder corresponding to the name of the video's author (i.e. channel).

        :param captions: The Caption track to download

        :return success: 1 if captions were downloaded successfully, 0 otherwise
        """

        safe_title = helpers.safe_filename(self.video.title)
        out_path = ""

        if self.screen:
            out_path = path.join("corpus", "unscreened_videos", self.group, "subtitles")
        else:
            out_path = path.join("corpus", "raw_subtitles", self.group)

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

        if(self.convert_srt):
            ext = ".srt"
        else:
            ext = ".xml"

        try:
            if self.include_title:
                captions.download(helpers.safe_filename(safe_title), srt=False, output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, self.yt_id))
            else:
                captions.download(str(self.yt_id), srt=False, output_path=out_path, filename_prefix="{0}_".format(safe_author))
                caption_fn = "".join(["{0}_".format(safe_author), self.yt_id, " ({0})".format(captions.code), '.xml'])


            caption_fn_clean = caption_fn.rsplit(' ',1)[0]+ext

            old_caption_path = path.join(out_path, caption_fn)
            new_caption_path = path.join(out_path, caption_fn_clean)

            if(self.convert_srt):
                xml_string = ""
                with open(old_caption_path, 'r') as xml_in:
                    xml_string = xml_in.read()
                #try:
                srt_string = self.xml_caption_to_srt(xml_string)
                with open(new_caption_path, 'w') as srt_out:
                    srt_out.write(srt_string)
                remove(old_caption_path)
                #except IndexError as e:
                #    logging.critical("Could not convert {0} to SRT format".format(caption_fn_clean))

            else:
                rename(old_caption_path, new_caption_path)

            return 1

        except KeyError:
            logging.critical("Video {0}: Could not convert caption track for video {0} from channel {1} ({2}) to SRT.".format(self.yt_id, self.video.author, self.video.title))
            return 0


    def xml_caption_to_srt(self, xml_captions: str) -> str:
        """Convert xml caption tracks to "SubRip Subtitle (srt)".

        :param str xml_captions:
        XML formatted caption tracks.
        """

        segments = []
        try:
            root = ElementTree.fromstring(xml_captions)[1]
        except IndexError as e:
            root = ElementTree.fromstring(xml_captions)[0]

        i=0
        for child in list(root):
            if child.tag == 'p':
                caption = ''
                if len(list(child))==0:
                    continue
                for s in list(child):
                    if s.tag == 's':
                        caption += ' ' + s.text
                caption = unescape(caption.replace("\n", " ").replace("  ", " "),)
                try:
                    duration = float(child.attrib["d"])/1000.0
                except KeyError:
                    duration = 0.0
                start = float(child.attrib["t"])/1000.0
                end = start + duration
                sequence_number = i + 1  # convert from 0-indexed to 1.
                line = "{seq}\n{start} --> {end}\n{text}\n".format(
                    seq=sequence_number,
                    start=self.float_to_srt_time_format(start),
                    end=self.float_to_srt_time_format(end),
                    text=caption,
                )
                segments.append(line)
            i += 1
        return "\n".join(segments).strip()


    def float_to_srt_time_format(self, d: float) -> str:
        """Convert decimal durations into proper srt format.

        :rtype: str
        :returns:
            SubRip Subtitle (str) formatted time duration.

        float_to_srt_time_format(3.89) -> '00:00:03,890'
        """
        fraction, whole = math.modf(d)
        time_fmt = time.strftime("%H:%M:%S,", time.gmtime(whole))
        ms = f"{fraction:.3f}".replace("0.", "")
        return time_fmt + ms


    def write_audio(self, audio):
        """Write audio Stream object to a file. If an output folder is not specified, audio will be placed in a folder corresponding to the name of the video's author (i.e. channel).
        """

        safe_title = helpers.safe_filename(self.video.title)
        safe_author = helpers.safe_filename(self.video.author)

        if self.screen:
            out_path = path.join("corpus", "unscreened_videos", self.group, "audio")
        else:
            out_path = path.join("corpus", "raw_audio", self.group)

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"

        if self.channel_name and self.channel_id:
            safe_channel_name = sub(punc_and_whitespace, "", self.channel_name)
            safe_author = "{0}_{1}".format(safe_channel_name, self.channel_id)
        else:
            safe_author = sub(punc_and_whitespace, "", self.video.author)

        out_path = path.join(out_path, safe_author)

        if not path.exists(out_path):
            makedirs(out_path)

        success = 0
        try:
            if self.include_title:
                audio.download(filename=safe_title + '.mp4', output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, self.yt_id), skip_existing=True)
                success = 1
            else:
                audio.download(filename=str(self.yt_id) + '.mp4', output_path=out_path, filename_prefix="{0}_".format(safe_author), skip_existing=True)
                success = 1
        except:
            logging.critical("Video {0}: Could not save audio stream for video {0} from channel {1} ({2})".format(self.yt_id, self.video.author, self.video.title))

        return success

        # Be polite
        time.sleep(1)


    def get_captions_by_language(self):
        """Filter captions by language and write each caption track to a file. If no language is specified, all caption tracks will be downloaded.

        :return caption_list: list of metadata for all successfully-downloaded caption tracks
        """

        caption_list = []
        for track in self.video.captions:
            if (self.language is None or self.language in track.name) and (self.include_auto or "a." not in track.code):

                success = self.write_captions(track)
                if success:
                    caption_list.append((track.code, track.name))

                # Be polite
                time.sleep(1)

        return caption_list


    def write_metadata(self, caption_list):
        """Write video metadata to log file.

        :param caption_list: List of downloaded caption tracks
        """

        channel_initials = "".join( [name[0].upper() for name in self.video.author.split()] )

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        safe_author = sub(punc_and_whitespace, "", self.video.author)

        metadata = {
            "yt_id": self.yt_id,
            "author": self.video.author,
            "code": channel_initials,
            "name": safe_author,
            "ID": self.channel_id,
            "url": self.url,
            "title": self.video.title,
            "description": self.video.description.replace('\n', ' '),
            "keywords": self.video.keywords,
            "length": self.video.length,
            "publish_date": self.video.publish_date,
            "views": self.video.views,
            "rating": self.video.rating,
            "captions": caption_list,
            "scrape_time": time.strftime("%Y-%m-%d_%H:%M:%S"),
            "corrected": 0,
        }

        log_fn = "{0}_log.csv".format(self.group)
        if not self.log_fp:
            self.log_fp = path.join("corpus", "logs")
            if self.screen:
                self.log_fp = path.join("corpus", "unscreened_videos", "logs")

        if not path.exists(self.log_fp):
            makedirs(self.log_fp)

        self.log_fp = path.join(self.log_fp, log_fn)

        with open(self.log_fp, 'a') as log_out:

            log_writer = DictWriter(log_out, fieldnames=["yt_id", "author", "code", "name", "ID", "url", "title", "description", "keywords", "length", "publish_date", "views", "rating", "captions", "scrape_time", "corrected"])

            if(log_out.tell() == 0):
                log_writer.writeheader()

            log_writer.writerow(metadata)


    def process_video(self):
        """Download captions, audio (optional), and metadata for a given video.

        :return caption_dict: list of metadata for all successfully-downloaded caption tracks
        """

        caption_list = self.get_captions_by_language()

        audio_success = 0
        try:
            if len(caption_list) and self.include_audio:
                audio = self.video.streams.filter(mime_type="audio/mp4").first()
                audio_success = self.write_audio(audio)
        except exceptions.VideoUnavailable as e:
            logging.critical("Video unavailable {0}: Are you using the latest version of PyTube?".format(self.url))

        if len(caption_list):
            self.write_metadata(caption_list)

        return ((len(caption_list) != 0), audio_success)


class MultiVideoScraper:

    def __init__(self, f, log_fp=None, language=None, group="ungrouped", screen=None, include_audio=False, include_auto=False, convert_srt=False, limit=-1, overwrite=False):

        # Input params
        self.f             = f
        self.log_fp        = log_fp
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.include_audio = include_audio
        self.include_auto  = include_auto
        self.include_title = False
        self.convert_srt   = convert_srt
        self.limit         = limit
        self.overwrite     = overwrite

        # Other params
        self.channel_dict  = {}
        self.video_count   = 0
        self.caption_success_count = 0
        self.audio_success_count = 0


    def process_videos(self):
        """Download captions, audio (optional), and metadata for a list of videos.
        """

        out_audio_path = path.join("corpus", "raw_audio")
        if self.screen:
            out_path = path.join("corpus", "unscreened_videos", self.group, "subtitles")
            out_audio_path = path.join("corpus", "unscreened_videos", self.group, "audio")
        else:
            out_path = path.join("corpus", "raw_subtitles", self.group)
            out_audio_path = path.join(out_audio_path, self.group)

        if not self.log_fp: # No file passed, i.e. not a grouped batch

            log_fn = "{0}_log.csv".format(self.group)
            log_fp = path.join("corpus", "logs", log_fn)
            if self.screen:
                log_fp = path.join("corpus", "unscreened_videos", "logs", log_fn)

            # Delete previous if overwriting, but only if NOT a batch
            if path.isfile(log_fp) and self.overwrite:
                remove(log_fp)

            # Remove old directories if we are overwriting but ONLY if not a batch!!
            if self.overwrite:
                try:
                    shutil.rmtree(out_path)
                except FileNotFoundError as e:
                    pass
                try:
                    shutil.rmtree(out_audio_path)
                except FileNotFoundError as e:
                    pass

        if not path.exists(out_path):
           makedirs(out_path)
        if not path.exists(out_audio_path):
           makedirs(out_audio_path)

        self.video_count = 0
        with open(self.f, "r") as urls_in:

            for line in urls_in:

                url_data = line.strip('\n').split('\t')

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
                try:
                    yt_id = sub(punc_and_whitespace, '', findall(r".+watch\?v=(.+)\b", url)[0])
                except IndexError as e:
                    pass

                # Check if yt_id already exists in some file; skip download if so
                if not self.overwrite:
                    files = glob(path.join(out_path, "**", "*{0}*".format(yt_id)), recursive=True)
                    if out_audio_path:
                        audio_files = glob(path.join(out_audio_path, "**", "*{0}*".format(yt_id)), recursive=True)
                        files = files + audio_files
                    if files:
                        continue

                video = VideoScraper(url, yt_id, self.log_fp, channel_name, channel_id, self.language, self.include_audio, self.include_auto, self.group, self.screen, self.convert_srt, self.include_title)
                caption_status, audio_status = video.process_video()

                self.video_count += 1
                self.caption_success_count += caption_status
                self.audio_success_count += audio_status

                if self.limit != -1 and self.caption_success_count >= self.limit and self.audio_success_count >= self.limit:
                    break

            print("Checked {0} videos; located captions for {1} videos and audio for {2} videos.".format(self.video_count, self.caption_success_count, self.audio_success_count))


class BatchVideoScraper:

    def __init__(self, base_fn, language=None, group="ungrouped", screen=None,  include_audio=False, include_auto=False, convert_srt=False, limit=-1, overwrite=False):

        self.base_fn       = base_fn
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.include_audio = include_audio
        self.include_auto  = include_auto
        self.convert_srt   = convert_srt
        self.limit         = limit
        self.overwrite     = overwrite


    def process_files(self):
        """Download captions, audio (optional), and metadata from a directory of video lists.
        """

        URL_fns_txt = sorted(glob(path.join(self.base_fn, "*.txt")))
        URL_fns_csv = sorted(glob(path.join(self.base_fn, "*.csv")))

        out_audio_path = path.join("corpus", "raw_audio")
        if self.screen:
            out_path = path.join("corpus", "unscreened_videos", self.group, "subtitles")
            out_audio_path = path.join(out_audio_path, self.group)
        else:
            out_path = path.join("corpus", "raw_subtitles", self.group)
            out_audio_path = path.join(out_audio_path, self.group)

        if self.overwrite:
            try:
                shutil.rmtree(out_path)
            except FileNotFoundError as e:
                pass
            try:
                shutil.rmtree(out_audio_path)
            except FileNotFoundError as e:
                pass

        if not path.exists(out_path):
           makedirs(out_path)
        if not path.exists(out_audio_path):
           makedirs(out_audio_path)

        log_fn = "{0}_log.csv".format(self.group)
        log_path = path.join("corpus", "logs")
        if self.screen:
            log_fp = path.join("corpus", "unscreened_videos", "logs")
        log_fp = path.join(log_path, log_fn)

        if path.isfile(log_fp) and self.overwrite:
            remove(log_fp)

        all_fns = URL_fns_txt + URL_fns_csv

        # Need to make video objs
        for fn in all_fns:
            scraper = MultiVideoScraper(fn, log_path, self.language, self.group, self.screen, self.include_audio, self.include_auto, self.convert_srt, self.limit, self.overwrite)
            scraper.process_videos()


class CaptionCleaner:

    def __init__(self, group="_ungrouped", lang_code=None, text=False, overwrite=False):

        self.group     = group
        self.lang_code = lang_code
        self.text      = text
        self.overwrite = overwrite

        self.raw_sub_base = path.join('corpus','raw_subtitles')
        self.clean_sub_base = path.join('corpus','cleaned_subtitles')

        if self.group:
            self.raw_sub_base = path.join(self.raw_sub_base, self.group)
            self.clean_sub_base = path.join(self.clean_sub_base, self.group)

    def process_captions(self):

        for sub_type in ['auto', 'manual']:

            raw_sub_dir = path.join(self.raw_sub_base, sub_type)
            clean_sub_dir = path.join(self.clean_sub_base, sub_type)

            if self.lang_code:
                lang_code_list = [self.lang_code]
            elif path.isdir(raw_sub_dir):
                lang_code_list = [langcode for langcode in listdir(raw_sub_dir) if not langcode.startswith('.')]
            else:
                lang_code_list = []

            for langcode in lang_code_list:

                in_dir = path.join(raw_sub_dir, langcode)
                cleans_dir = path.join(clean_sub_dir, langcode, "cleans")
                text_dir = path.join(clean_sub_dir, langcode, "texts")

                if path.isdir(in_dir):
                    dir_list = [dir_element for dir_element in listdir(in_dir)]
                    if '.DS_Store' in dir_list:
                        dir_list.remove('.DS_Store')
                    for i, dir_element in enumerate(dir_list):
                        if path.isdir(path.join(in_dir, dir_element)):

                            channel_in_dir = path.join(in_dir, dir_element)
                            channel_cleans_dir = path.join(cleans_dir, dir_element)
                            channel_text_dir = path.join(text_dir, dir_element)

                            channel_dir_list = [dir_element for dir_element in listdir(channel_in_dir)]
                            if '.DS_Store' in channel_dir_list:
                                channel_dir_list.remove('.DS_Store')
                            for j, fn in enumerate(channel_dir_list):
                                self.clean_captions(j, fn, langcode, channel_in_dir, channel_cleans_dir, channel_text_dir, self.text, self.overwrite)
                        else:
                            self.clean_captions(i, dir_element, langcode, in_dir, cleans_dir, text_dir, self.text, self.overwrite)

    def convert_to_seconds(self, timestamp):
        """ Translate timestamps to time in seconds (used in get_lines )
        """
        time_components = findall(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', timestamp)

        if not len(time_components) == 0:
            hrs, mins, secs, msecs = time_components[0]

            hrs = int(hrs) * (60 * 60) * 1000
            mins = int(mins) * 60 * 1000
            secs = int(secs) * 1000
            msecs = int(msecs)

            time_ms = hrs + mins + secs + msecs
            time_s = float(time_ms)/float(1000)
            return time_s

    def clean_text(self, text, langcode):
        """ Automated cleaning of text.
        """

        if langcode == 'en':

            numbers = {'0': 'zero',
                        '1': 'one',
                        '2': 'two',
                        '3': 'three',
                        '4': 'four',
                        '5': 'five',
                        '6': 'six',
                        '7': 'seven',
                        '8': 'eight',
                        '9': 'nine',
                        '10': 'ten',
                        '11': 'eleven',
                        '12': 'twelve',
                        '13': 'thirteen',
                        '14': 'fourteen',
                        '15': 'fifteen',
                        '16': 'sixteen',
                        '17': 'seventeen',
                        '18': 'eighteen',
                        '19': 'nineteen',
                        '20': 'twenty',
                        '30': 'thirty',
                        '40': 'forty',
                        '50': 'fifty',
                        '60': 'sixty',
                        '70': 'seventy',
                        '80': 'eighty',
                        '90': 'ninety'}

            text = sub(r'1\.5', 'one point five', text)
            for val, per in findall(r'(\d+)(%)', text):
                text = sub(val+per, val+' percent', text)

            text = sub(r':00', '', text)
            text = sub(r':', ' ', text)
            for i in range(2):
                for pre, hyp, post in findall(r'([a-zA-Z]+)(\-)([a-zA-Z]+)', text):
                    text = sub(pre+hyp+post, pre+' '+post, text)
            text = sub(r'24/7', 'twenty-four seven', text)

            for abb in findall(r'(?:^|\s)((?:[a-zA-Z]\.)+)(?:$|\s)', text):
                cap_string = abb.replace('.','').upper()
                text = sub(abb, cap_string, text)

            for num in findall(r'(?:^|\s)(\d{1,2})(?:$|\s)', text):
                if num in numbers.keys():
                    numeral_string = '{0}'.format(num)
                    word_string = '{0}'.format(numbers.get(num))
                    text = sub(numeral_string, word_string, text)
                else:
                    ones = numbers.get(num[-1])
                    tens = numbers.get("{0}0".format(num[-2]))
                    numeral_string = '{0}'.format(num)
                    word_string = '{0} {1}'.format(tens, ones)
                    text = sub(numeral_string, word_string, text)

        # text = sub(r'[\.,"!?:;()]', '', text)
        text = sub(r' & ', ' and ', text)

        return text

    def get_timestamped_lines(self, in_dir, fn, langcode):
        """ Extract timestamps and text per caption line
        """
        with open(path.join(in_dir,fn)) as file:
            file_text = file.read()

            # Extract only the relevant parts of each time+text set
            subs = findall(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*)\n', file_text)

        timed_lines = []
        for line in subs:
            time_start_s = self.convert_to_seconds(line[0])
            time_end_s = self.convert_to_seconds(line[1])
            sub_text = self.clean_text(line[2], langcode)
            timed_lines.append((time_start_s, time_end_s, sub_text))

        lasti = len(timed_lines)
        corrected_timed_lines = []
        for i in range(0,lasti):
            time_start = timed_lines[i][0]
            sub_text = timed_lines[i][2]
            if i < lasti-1:
                time_end = timed_lines[i+1][0]
            else:
                time_end = timed_lines[i][1]
            corrected_timed_lines.append((time_start, time_end, sub_text))

        return corrected_timed_lines

    def write_to_output(self, file_type, out_dir, name, timed_lines):
        """ Write to files
        :param name: The filename (w/o ext)
        """
        channel_name = name.split('_', 1)[0]

        if not path.exists(out_dir):
            makedirs(out_dir)
        out_file_path = path.join(out_dir, name+'.txt')

        if file_type == 'cleans':
            out_df = pd.DataFrame(columns=['start_time', 'end_time', 'subtitle_text'])
            for line in timed_lines:
                subtitle_row = {"start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
                out_df = out_df.append(subtitle_row, ignore_index=True)
            out_df.to_csv(out_file_path, sep='\t', index=False, header=False)

        elif file_type == 'text':
            all_lines = [line[2] for line in timed_lines]
            all_text = " ".join(all_lines)
            with open(out_file_path, "w") as file:
                file.write(all_text)
        else:
            print('File type is not valid (cleans, text).')

    def clean_captions(self, i, fn, langcode, in_dir, cleans_dir, text_dir, text=False, overwrite=False):
        name, ext = path.splitext(fn)

        if path.isdir(cleans_dir) and not overwrite:
            existing_files = glob(path.join(cleans_dir, "**", "*{0}*".format(name)), recursive=True)
            if existing_files:
                return 1

        print('Processing transcript {0}: {1}'.format(i+1,fn))

        timed_lines = self.get_timestamped_lines(in_dir, fn, langcode)
        self.write_to_output('cleans', cleans_dir, name, timed_lines)
        if text:
            self.write_to_output('text', text_dir, name, timed_lines)
