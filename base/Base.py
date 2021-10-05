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
# TODO: Pytube channel object includes about page ^^;


class ChannelScraper:

    def __init__(self, url, browser="Firefox", limit=-1, group='ungrouped', about=False, overwrite=False, screen=False):

        # Clean URL
        # TODO: URL validation
        self.url = url
        if self.url[-1] == '/':
            self.url = self.url[:-1]

        # Determine if URL is a video or channel link
        self.from_video = True if "watch?" in self.url else False

        # Set other variables
        self.urls          = None
        self.info          = None
        self.browser       = browser
        self.group         = group
        self.about         = about
        self.overwrite     = overwrite
        self.screen        = screen
        self.limit         = limit

    def init_files(self):
        """ Generate directory and file paths and create directores if needed
        """

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
        """Scrape the channel and save URLs to a file
        """

        # Scrape the channel for URLs and about page info
        (name_success, description_success, urls_success) = self.scrape()

        # Create directory structure
        self.init_files()

        # If we are working from a video, log the input URL
        if self.from_video:
            self.log_video()

        # Save scraped URLs and info
        count = self.save(name_success, description_success, urls_success)
        print("Colellected {0} URLs".format(count))


    def save_info(self):
        """Save about page info to info file
        """

        with open(self.info_out_path, 'w') as info_out:
            for key in self.info.keys():
                info_out.write("# {0}\n\n".format(key))
                info_out.write("{0}\n\n".format(self.info[key]))


    def save_new_urls(self, previous_urls):
        """ Save any urls up to LIMIT that don't overlap with previously-saved ones

        :return url_count: The number of URLs saved
        """

        # Scrape up to LIMIT new video URLs; if no limit, scrape all video URLs
        new_urls = set(self.urls).symmetric_difference(set(previous_urls))

        # Quit if there's nothing to save
        if not new_urls:
            logging.warning('No new URLs found')
            return

        # Save new video URLs
        url_count = 0
        with open(self.urls_out_path, 'a') as urls_out:

            for url in new_urls:

                formatted_url = "{0}\t{1}\t{2}\n".format(url, self.info["ChannelName"], self.info["SafeChannelID"])
                urls_out.write(formatted_url)

                url_count += 1
                if url_count == self.limit:
                    break

        return url_count


    def get_previous_urls(self):
        """Read in previously-saved URLs if they exist

        : return previous_urls: List of URLs in the existing output file
        """

        previous_urls = []
        if path.isfile(self.urls_out_path):
            with open(self.urls_out_path, 'r') as urls_in:
                previous_urls = [line.split('\t')[0] for line in urls_in]

        previous_urls.append(self.url)

        return previous_urls


    def save(self, name_success, description_success, urls_success):
        """Save info and (if applicable) list of video URLs as text files

        :return count: Number of URLs saved
        """

        # Save channel info if it was scraped and file doesn't exist already
        if name_success and description_success and not path.isfile(self.info_out_path):
            self.save_info()

        # Don't save the links if we didn't scrape anything
        if urls_success < 1:
            return

        # Get URLs that have already been saved
        previous_urls = self.get_previous_urls()

        # Save only new URLs
        count = self.save_new_urls(previous_urls)

        return count


    def scrape_urls(self, channel_url):
        """Scrape the URLs from a YouTube channel.

        :return channel_urls: List of videos URLs
        :return success: URLs scraped sccessfully
        """

        success = 1

        try:
            channel = Channel(channel_url) # Load channel in PyTube
            return (channel.video_urls, success)
        except:
            success = 0

        return (None, success)


    def set_channel_name(self, driver, info):
        """Scrape the channel's 'human readable' name.

        :return info: A dictionary containing the channel's name.
        :return success: Channel name was scraped successfully
        """

        # Status for scraping channel name
        success = 1

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))

            channel_name = driver.find_element(By.CLASS_NAME, "ytd-channel-name").text

            punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
            info["ChannelName"] = channel_name
            info["SafeChannelName"] = sub(punc_and_whitespace, "", channel_name)

        except:
            logging.warning("Could not scrape channel name")
            success = 0

        return (info, success)


    def set_description(self, driver, info):
        """Scrape the channel's description, bio, and metadata.

        :return info: A dictionary containing the channel's description, bio, etc.
        :return success: About page was scraped successfully
        """

        # Status for scraping data
        success = 1

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'description')))
            info["Description"] = driver.find_element(By.ID, "description-container").text
            info["Bio"]         = driver.find_element(By.ID, "bio").text
            info["Metadata"]    = driver.find_element(By.ID, "details-container").find_element(By.TAG_NAME, "table").text

        except:
            logging.warning("Could not scrape about page")
            success = 0

        return (info, success)


    def set_info(self, driver, channel_id, channel_url):
        """Scrape the channel's about page for the channel's name, description, bio, and metadata.

        :return name_success: Channel name was scraped successfully
        :return description_success: About page was scraped successfully
        """

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}
        info.update({"ChannelName": "", "SafeChannelName": "", "Description": "", "Bio": "", "Metadata": ""})

        # Load the about page
        driver.get(channel_url + "/about")

        # Scrape relevant info
        info_name, name_success              = self.set_channel_name(driver, info)
        info_name_about, description_success = self.set_description(driver, info_name)

        self.info = info_name_about

        return (name_success, description_success)


    def scrape_info(self, channel_id, channel_url):
        """Open a web browser and scrape the channel's about page.

        :return info_name_about: A dictionary containing the channel's name, description, bio, and metadata.
        :return name_success: Channel name was scraped successfully
        :return description_success: About page was scraped successfully
        """

        if self.browser.lower() == "firefox":

            try:
                options = webdriver.FirefoxOptions()
                options.set_headless()
                with webdriver.Firefox(firefox_options=options) as driver:
                    (name_success, description_success) = self.set_info(driver, channel_id, channel_url)

            except FileNotFoundError as e:
                logging.critical('Could not locate geckodriver')

        elif self.browser.lower() == "chrome":

            try:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--window-size=1920x1080")
                with webdriver.Chrome(chrome_options=options) as driver:
                    (name_success, description_success) = self.set_info(driver, channel_id, channel_url)

            except FileNotFoundError as e:
                logging.critical('Could not locate chromedriver')

        else:
            print('ERROR: Invalid browser. Please enter "chrome" or "firefox"')

        return (name_success, description_success)


    def scrape(self):
        """Collect video URLs (if scraping URLs) and about page info from the channel

        :return name_success: Name successfully scraped
        :return description_success: Description, bio, and metadata successfully scraped"
        :return urls_success: URLs successfully scraped"
        """

        # Get the channel's ID and URL from video (if input is a video); from input channel URL otherwise
        if self.from_video:
            video = YouTube(self.url)
            channel_id = video.channel_id
            channel_url = 'https://www.youtube.com/channel/{0}'.format(video.channel_id)
        else:
            channel_id  = self.url.split('/')[-1]
            channel_url = self.url

        # Scrape about page
        print('Collecting about page from channel {0}'.format(channel_id))

        (name_success, description_success) = self.scrape_info(channel_id, channel_url)

        # If about flag is set, stop here
        if self.about:
            return (name_success, description_success, -1)

        # Scrape URLs
        print('Collecting video URLs from channel {0}'.format(channel_id))

        (self.urls, urls_success) = self.scrape_urls(channel_url)

        return (name_success, description_success, urls_success)


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

    def __init__(self, url, yt_id, channel_name="", channel_id="", language=None, include_audio=False, include_auto=False, group='ungrouped', screen=False, convert_srt=False, include_title=False, overwrite=None):

        try:
            self.video = YouTube(url)

        except exceptions.VideoUnavailable as e:
            logging.warning("ERROR: Video unavailable ({0}). Are you using the latest version of PyTube?".format(video_count, url))

        self.url           = url
        self.yt_id         = yt_id
        self.channel_name  = channel_name
        self.channel_id    = channel_id
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.convert_srt   = convert_srt
        self.include_audio = include_audio
        self.include_auto  = include_auto
        self.include_title = include_title
        self.overwrite     = overwrite


    def init_files(self):
        """ Generate necessary file paths and create new directories when needed.
        """

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"

        # Generate safe channel name and video author
        if self.channel_name and self.channel_id:
            self.safe_channel_name = sub(punc_and_whitespace, "", self.channel_name)
            self.safe_author = "{0}_{1}".format(self.safe_channel_name, self.channel_id)
        else:
            self.safe_author = sub(punc_and_whitespace, "", video.author)

        # Sort audio and captions by screening status
        if self.screen:
            captions_out_dir = path.join("corpus", "unscreened_videos", self.group, "subtitles")
            audio_out_dir    = path.join("corpus", "unscreened_videos", self.group, "audio")
            log_out_dir      = path.join("corpus", "unscreened_videos", "logs")
        else:
            captions_out_dir = path.join("corpus", "raw_subtitles", self.group)
            audio_out_dir    = path.join("corpus", "raw_audio", self.group)
            log_out_dir      = path.join("corpus", "logs")

        self.audio_out_dir    = path.join(audio_out_dir, self.safe_author)
        self.captions_out_dir = captions_out_dir

        out_dirs = {"captions": self.captions_out_dir,
                    "audio": self.audio_out_dir,
                    "log": log_out_dir}

        for key in out_dirs:
            if not path.exists(out_dirs[key]):
                makedirs(out_dirs[key])

        log_fn = "{0}_log.csv".format(self.group)
        self.log_out_path = path.join(log_out_dir, log_fn)


    # TODO: Unclear function names
    def convert_and_save_captions(self, old_caption_path, new_caption_path, caption_fn_clean):
        """Convert XML subtitles to SRT format and save the new file. Deletes XML captions.

        :return success: Captions converted successfully
        """

        xml_string = ""
        srt_string = ""

        # Load XML captions
        with open(old_caption_path, 'r') as xml_in:
            xml_string = xml_in.read()

        # Convert XML to SRT
        try:
            srt_string = self.xml_caption_to_srt(xml_string)
        except IndexError as e:
            logging.critical("Could not convert {0} to SRT format".format(caption_fn_clean))
            return 0

        # Save SRT captions
        with open(new_caption_path, 'w') as srt_out:
            srt_out.write(srt_string)
            remove(old_caption_path)

        return 1


    def convert_and_rename_captions(self, caption_fn, captions_out_dir):
        """ Rename caption file to remove language code. Convert to SRT if requested.

        :return success: File renamed and converted successully.
        """

        ext = ".srt" if self.convert_srt else ".xml"

        # Remove language code from filename
        caption_fn_clean = caption_fn.rsplit(' ',1)[0]+ext

        # Generate old and new file path
        old_caption_path = path.join(captions_out_dir, caption_fn)
        new_caption_path = path.join(captions_out_dir, caption_fn_clean)

        if(self.convert_srt):
            return self.convert_and_save_captions(old_caption_path, new_caption_path, caption_fn_clean)

        else:
            rename(old_caption_path, new_caption_path)

        return 1


    def write_captions(self, captions):
        """Write Caption object to a file. If an output folder is not specified, captions will be placed in a folder corresponding to the name of the video's author (i.e. channel).

        :param captions: The Caption track to download

        :return success: 1 if captions were downloaded successfully, 0 otherwise
        """

        safe_title = helpers.safe_filename(self.video.title)
        safe_author = self.safe_author

        # Set up file name components
        if self.include_title:
            prefix = "{0}_{1}_".format(safe_author, self.yt_id)
            base   = safe_title
        else:
            prefix = "{0}_".format(safe_author)
            base   = str(self.yt_id)

        # Build filename for later renaming
        caption_fn = "".join([prefix, base, " ({0})".format(captions.code)])

        # Further subdivide captions by auto and manual
        if "a." in captions.code:
            captions_out_dir = path.join(self.captions_out_dir, "auto", captions.code.split(".")[1])
        else:
            captions_out_dir = path.join(self.captions_out_dir, "manual", captions.code.split(".")[0])

        captions_out_dir = path.join(captions_out_dir, self.safe_author)

        # Download captions in original format if they don't exist or if overwriting
        try:
            captions.download(base, srt=False, output_path=captions_out_dir, filename_prefix=prefix)
        except:
            logging.critical("Video {0}: Could not download captions".format(caption_fn))
            return 0

        # Rename and convert captions
        return self.convert_and_rename_captions(caption_fn+'.xml', captions_out_dir)


    # TOOD: Code adapted from PyTube issue (number?). Check for update to code base
    def xml_caption_to_srt(self, xml_captions: str) -> str:
        """Convert xml caption tracks to "SubRip Subtitle (srt)".

        :param str xml_captions: XML formatted caption track.
        :return str srt_captions: SRT formatted caption track.
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
                    caption = child.text
                else:
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


    # TODO: Copied from PyTube for Reasons
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
        :return success: Audio downloaded successfully
        """

        safe_title = helpers.safe_filename(self.video.title)
        safe_author = self.safe_author

        success = 1

        # Set up filename components
        if self.include_title:
            base = "{0}.mp4".format(safe_title)
            prefix = "{0}_{1}_".format(safe_author, self.yt_id)
        else:
            base = "{0}.mp4".format(self.yt_id)
            prefix = "{0}_".format(safe_author)

        try:
            print(self.overwrite)
            skip = False if self.overwrite != "video" else True
            audio.download(filename=base, output_path=self.audio_out_dir, filename_prefix=prefix, skip_existing=skip)
        except:
            logging.critical("Video {0}: Could not save audio stream for video {0} from channel {1} ({2})".format(self.yt_id, self.video.author, self.video.title))

        # Be polite
        time.sleep(1)

        return success


    def get_captions_by_language(self):
        """Filter captions by language and write each caption track to a file.
        If no language is specified, all caption tracks will be downloaded.

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

        metadata = {
            "yt_id": self.yt_id,
            "author": self.video.author,
            "code": channel_initials,
            "name": self.safe_author,
            "ID": self.channel_id,
            "url": self.url,
            "title": self.video.title,
            "description": '"{0}"'.format(self.video.description.replace('\n', ' ')),
            "keywords": self.video.keywords,
            "length": self.video.length,
            "publish_date": self.video.publish_date,
            "views": self.video.views,
            "rating": self.video.rating,
            "captions": caption_list,
            "scrape_time": time.strftime("%Y-%m-%d_%H:%M:%S"),
            "corrected": 0,
        }

        # Data is ONLY deleted if we SUCCESSFULLY overwrote the video's audio/captions
        if self.overwrite == 'video':
            # Filter log file
            with open(self.log_out_path, 'r') as log_in:
                videos_to_keep = [line for line in log_in if self.yt_id not in line]
            with open(self.log_out_path, 'w') as log_out:
                for video in videos_to_keep:
                    log_out.write(video)

        with open(self.log_out_path, 'a') as log_out:

            log_writer = DictWriter(log_out, fieldnames=["yt_id", "author", "code", "name", "ID", "url", "title", "description", "keywords", "length", "publish_date", "views", "rating", "captions", "scrape_time", "corrected"])

            if(log_out.tell() == 0):
                log_writer.writeheader()

            log_writer.writerow(metadata)


    def process_video(self):
        """Download captions, audio (optional), and metadata for a given video.

        :return caption_dict: list of metadata for all successfully-downloaded caption tracks
        """

        self.init_files()

        audio_success = 0
        caption_list = self.get_captions_by_language()

        if len(caption_list) and self.include_audio:
            try:
                audio = self.video.streams.filter(mime_type="audio/mp4").first()
            except exceptions.VideoUnavailable as e:
                logging.critical("Video unavailable {0}: Are you using the latest version of PyTube?".format(self.url))
            audio_success = self.write_audio(audio)

        if len(caption_list):
            self.write_metadata(caption_list)

        return ((len(caption_list) != 0), audio_success)


class MultiVideoScraper:

    # TODO: Only delete channel folders if overwrite is true!

    def __init__(self, f, language=None, group="ungrouped", screen=False, include_audio=False, include_auto=False, convert_srt=False, limit=-1, overwrite=None):

        # Input params
        self.f             = f
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

        self.init_files()


    def overwrite_channel_data(self):

        # Get channel name and ID from file path
        channel_full = path.split(self.f)[-1].split('_')[:2]
        channel_id = channel_full[1]

        # Generate possible existing audio and caption directories
        chan_audio_out_dir = path.join(self.audio_out_dir, '_'.join(channel_full))
        chan_captions_dirs = glob(path.join(self.captions_out_dir, "*", "*", "*{0}*".format(channel_id)), recursive=True)
        all_chan_dirs = [chan_audio_out_dir] + chan_captions_dirs

        # Delete existing directories
        for dir in all_chan_dirs:
             try:
                 shutil.rmtree(dir)
             except FileNotFoundError as e:
                 pass

        # Filter log file
        with open(self.log_out_path, 'r') as log_in:
            videos_to_keep = [line for line in log_in if channel_id not in line]
        with open(self.log_out_path, 'w') as log_out:
            for video in videos_to_keep:
                log_out.write(video)


    def init_files(self):

        # Sort audio and captions by screening status
        if self.screen:
            self.captions_out_dir = path.join("corpus", "unscreened_videos", self.group, "subtitles")
            self.audio_out_dir    = path.join("corpus", "unscreened_videos", self.group, "audio")
            self.log_out_dir      = path.join("corpus", "unscreened_videos", "logs")
        else:
            self.captions_out_dir = path.join("corpus", "raw_subtitles", self.group)
            self.audio_out_dir    = path.join("corpus", "raw_audio", self.group)
            self.log_out_dir      = path.join("corpus", "logs")

        # Prepare logfile path
        log_fn = "{0}_log.csv".format(self.group)
        self.log_out_path = path.join(self.log_out_dir, log_fn)

        # If overwriting individual channels, do so at this stage
        if self.overwrite == "channel":
            self.overwrite_channel_data()


    def parse_url(self, url_data):

        if len(url_data) == 3:
            return url_data
        elif len(url_data) == 2:
            return (url_data[0], url_data[1], None)
        elif len(url_data) == 1:
            return (url_data[0], None, None)
        else:
            logging.critical("Invalid URL format")
            return (None, None, None)


    def process_url(self, url, yt_id, channel_name, channel_id):

        # Check if yt_id already exists in some file; skip download unless overwriting
        if(self.overwrite != "video"):

            # UNIX paths for captions and audio
            captions_path = path.join(self.captions_out_dir, "**", "*{0}*".format(yt_id))
            audio_path    = path.join(self.audio_out_dir, "**", "*{0}*".format(yt_id))

            # Find all files that match the video ID
            caption_files = glob(captions_path, recursive=True)
            audio_files = glob(audio_path, recursive=True)

            if caption_files + audio_files:
                return 1

        # Scrape audio and captions from video at URL
        video = VideoScraper(url, yt_id, channel_name, channel_id, self.language, self.include_audio, self.include_auto, self.group, self.screen, self.convert_srt, self.include_title, overwrite=self.overwrite)
        caption_status, audio_status = video.process_video()

        # Track completed videos
        self.video_count += 1
        self.caption_success_count += caption_status
        self.audio_success_count += audio_status

        # Stop once #of audio and captins reaches LIMIT, if specified
        if self.limit != -1 and self.caption_success_count >= self.limit and self.audio_success_count >= self.limit:
            return 2

        return 0


    def process_videos(self):
        """Download captions, audio (optional), and metadata for a list of videos.
        """

        self.video_count = 0
        with open(self.f, "r") as urls_in:

            urls = [line.strip('\n').split('\t') for line in urls_in]

        for url in urls:

            # Parse URL, channel name, and channel ID
            (url, channel_name, channel_id) = self.parse_url(url)

            # Skip bad url data
            if url is None:
                continue

            # Check that URL is a valid video link
            try:
                punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
                yt_id = sub(punc_and_whitespace, '', findall(r".+watch\?v=(.+)\b", url)[0])
            except IndexError as e:
                continue

            status = self.process_url(url, yt_id, channel_name, channel_id)
            if status == 1:
                continue
            if status == 2:
                break

        print("Checked {0} videos; located captions for {1} videos and audio for {2} videos.".format(self.video_count, self.caption_success_count, self.audio_success_count))


class BatchVideoScraper:

    def __init__(self, base_fn, language=None, group="ungrouped", screen=None,  include_audio=False, include_auto=False, convert_srt=False, limit=-1, overwrite=None):

        self.base_fn       = base_fn
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.include_audio = include_audio
        self.include_auto  = include_auto
        self.convert_srt   = convert_srt
        self.limit         = limit
        self.overwrite     = overwrite


    def delete_all(self):

        # Sort audio and captions by screening status
        if self.screen:
            captions_out_dir = path.join("corpus", "unscreened_videos", self.group, "subtitles")
            audio_out_dir    = path.join("corpus", "unscreened_videos", self.group, "audio")
            log_out_dir      = path.join("corpus", "unscreened_videos", "logs")
        else:
            captions_out_dir = path.join("corpus", "raw_subtitles", self.group)
            audio_out_dir    = path.join("corpus", "raw_audio", self.group)
            log_out_dir      = path.join("corpus", "logs")

        out_dirs = {"captions": captions_out_dir,
                       "audio": audio_out_dir}


        for key in out_dirs:
            try:
                shutil.rmtree(out_dirs[key])
            except FileNotFoundError as e:
                pass

        log_fn = "{0}_log.csv".format(self.group)
        log_out_path = path.join(log_out_dir, log_fn)

        if path.isfile(log_out_path):
            remove(log_out_path)


    def process_files(self):
        """Download captions, audio (optional), and metadata from a directory of video lists.
        """
        if self.overwrite == "all":
            self.delete_all()

        URL_fns_txt = sorted(glob(path.join(self.base_fn, "*.txt")))
        URL_fns_csv = sorted(glob(path.join(self.base_fn, "*.csv")))
        all_fns = URL_fns_txt + URL_fns_csv

        # Need to make video objs
        for fn in all_fns:
            scraper = MultiVideoScraper(fn, self.language, self.group, self.screen, self.include_audio, self.include_auto, self.convert_srt, self.limit, self.overwrite)
            scraper.process_videos()


class CaptionCleaner:

    def __init__(self, group="_ungrouped", lang_code=None, text=False, overwrite=False):

        self.group     = group
        self.lang_code = lang_code
        self.text      = text
        self.overwrite = overwrite

        self.raw_sub_base = path.join('corpus','raw_subtitles',  self.group)
        self.clean_sub_base = path.join('corpus','cleaned_subtitles', self.group)

        if self.overwrite:
            try:
                shutil.rmtree(self.clean_sub_base)
            except FileNotFoundError as e:
                pass


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

        if path.isdir(cleans_dir):
            existing_files = glob(path.join(cleans_dir, "**", "*{0}*".format(name)), recursive=True)
            if existing_files:
                return 1

        print('Processing transcript {0}: {1}'.format(i+1,fn))

        timed_lines = self.get_timestamped_lines(in_dir, fn, langcode)
        self.write_to_output('cleans', cleans_dir, name, timed_lines)
        if text:
            self.write_to_output('text', text_dir, name, timed_lines)
