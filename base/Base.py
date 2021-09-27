import math, time, logging
import pandas as pd

import xml.etree.ElementTree as ElementTree

from pytube import YouTube, exceptions, helpers
from os import path, makedirs, remove, rename, listdir
from re import sub, findall
from glob import glob
from csv import DictWriter

from html import unescape

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# TODO: Need to implement robust error handling
# TODO: PyTube now supports channels


class ChannelScraper:

    def __init__(self, url, browser="Firefox", pause_time=1, cutoff=-1, group='', about=False, overwrite=False, screen=False):

        self.url = url
        self.from_video = False

        if "watch?" in self.url:
            self.from_video = True

        # Default variables
        self.video_url     = None
        self.browser       = browser
        self.pause_time    = pause_time
        self.cutoff        = cutoff
        self.group         = group
        self.about         = about
        self.overwrite     = overwrite
        self.screen        = screen


    def init_info(self, driver):
        """Initialize *info* with the channel's ID
        """

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"

        # Remove trailing forward slash
        if self.url[-1] == '/':
            self.url = self.url[:-1]

        if self.from_video:
            driver.get(self.url)

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ytd-channel-name')))

                time.sleep(2)

                channel_url = driver.find_element(By.CLASS_NAME, "ytd-channel-name").find_element(By.TAG_NAME, 'a').get_attribute('href')
                logging.info("Gathering information from channel: " + channel_url)

                # TODO: Not really the safest way to update the URL. Video and channel URL should be kept clearly distinct.
                self.video_url = self.url
                self.url = channel_url

                channel_id = channel_url.split('/')[-1]
                info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

                return info

            except:
                logging.critical("Could not locate channel URL")
                exit(1)

        else:
            # TODO: We are assuming URLs are frmatted correctly
            channel_id = self.url.split('/')[-1]
            info = {"ChannelID": channel_id, "SafeChannelID": sub(punc_and_whitespace, "", channel_id)}

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
        if not self.group:
            info_out_dir = path.join(base_path, "about")
        else:
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
        if self.about:
            return

        # Create URL out path
        if not self.group:
            url_out_dir = path.join(base_path, "channel_urls")
        else:
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
        time.sleep(self.pause_time)

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

        if self.from_video:
            self.log_video()


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
            time.sleep(2)
            info["Description"] = driver.find_element(By.ID, "description-container").text
            info["Bio"]         = driver.find_element(By.ID, "bio").text
            info["Metadata"]    = driver.find_element(By.ID, "details-container").find_element(By.TAG_NAME, "table").text
        except:
            logging.warning("Could not scrape about page")

        return info


    def scrape_about_links(self, driver):

        self.info = self.scrape_info(driver)
        print(self.about)
        if self.about:
            self.links = None
        else:
            self.links = self.scrape_links(driver)


    def scrape(self):
        """Collect video URLs (if scraping URLs) and about page info from the channel
        """

        if self.browser.lower() == "firefox":
            with webdriver.Firefox() as driver:
                self.scrape_about_links(driver)
        else:
            with webdriver.Chrome() as driver:
                self.scrape_about_links(driver)


    def log_video(self):
        """Log the video URL, channel name, and channel ID in LingTube format
        """

        # TODO: Genertion of base_path is redundant given the save() function

        if self.screen:
            base_path = path.join("corpus", "unscreened_urls")
        else:
            base_path = path.join("corpus", "screened_urls")

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


    def get_info(self):
        return self.info


    def get_links(self):
        return self.links


    def get_url(self):
        return self.url


class MultiChannelScraper:

    def __init__(self, f, browser="Firefox", pause_time=1, cutoff=-1, group='', about=False, overwrite=False, screen=False):

        self.channels = []
        self.f        = f

        # To be passed to ChannelScraper objects
        self.browser       = browser
        self.pause_time    = pause_time
        self.cutoff        = cutoff
        self.group         = group
        self.about         = about
        self.overwrite     = overwrite
        self.screen        = screen


    def process(self):

        try:
            with open(self.f) as file_in:
                for line in file_in:
                    line = line.split('\t')[0]
                    line = sub('[\s\ufeff]+', '', line.strip('/')) # Handle whitespace and Excel nonsense?

                    scraper = ChannelScraper(line, self.browser, self.pause_time, self.cutoff, self.group, self.about, self.overwrite, self.screen)
                    scraper.process()
                    time.sleep(1)

        except FileNotFoundError as e:
            print('Error: File {0} could not be found.'.format(self.channels_f))



class VideoScraper:

    def __init__(self, url, yt_id, log_fp=None, channel_name="", channel_id="", language=None, include_audio=False, include_auto=False, group='', screen=False, convert_srt=False, include_title=False):

        try:
            self.video = YouTube(url)

        except KeyError as e: # Why is ths here?
            logging.warning("ERROR: Could not retrieve URL ({0})".format(self.url))
            exit(1)

        except exceptions.VideoUnavailable as e:
            logging.warning("ERROR: Video unavailable ({0}). Are you using the latest version of PyTube?".format(video_count, url))
            exit(1)


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

        if(self.convert_srt):
            ext = ".srt"
        else:
            ext = ".xml"

        try:
            if self.include_title:
                captions.download(helpers.safe_filename(safe_title), srt=False, output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, self.yt_id))
                caption_fn = "".join(["{0}_{1}_".format(safe_author, self.yt_id), " ", helpers.safe_filename(safe_title), " ({0})".format(captions.code), '.xml'])
            else:
                captions.download(str(self.yt_id), srt=False, output_path=out_path, filename_prefix="{0}_".format(safe_author))
                caption_fn = "".join(["{0}_".format(safe_author), self.yt_id, " ({0})".format(captions.code), '.xml'])


            caption_fn_clean = caption_fn.rsplit(' ',1)[0]+ext

            old_caption_path = path.join(out_path, caption_fn)
            new_caption_path = path.join(out_path, caption_fn_clean)

            if(self.convert_srt):
                with open(old_caption_path, 'r') as xml_in, open(new_caption_path, 'w') as srt_out:
                    xml_string = xml_in.read()
                    srt_string = self.xml_caption_to_srt(xml_string)
                    srt_out.write(srt_string)
                remove(old_caption_path)
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
      root = ElementTree.fromstring(xml_captions)[1]
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
            out_path = path.join("corpus", "unscreened_urls", "audio")
            if self.group:
                out_path = path.join("corpus", "unscreened_urls", self.group, "audio")
        else:
            out_path = path.join("corpus", "raw_audio")
            if self.group:
                out_path = path.join(out_path, self.group)

        punc_and_whitespace = "[\s\_\-\.\?\!,;:'\"\\\/]+"
        if self.channel_name and self.channel_id:
            safe_channel_name = sub(punc_and_whitespace, "", self.channel_name)
            safe_author = "{0}_{1}".format(safe_channel_name, self.channel_id)
        else:
            safe_author = sub(punc_and_whitespace, "", self.video.author)

        out_path = path.join(out_path, safe_author)

        if not path.exists(out_path):
            makedirs(out_path)

        #try:
        if self.include_title:
            audio.download(filename=safe_title + '.mp4', output_path=out_path, filename_prefix="{0}_{1}_".format(safe_author, self.yt_id), skip_existing=True)
        else:
            audio.download(filename=str(self.yt_id) + '.mp4', output_path=out_path, filename_prefix="{0}_".format(safe_author), skip_existing=True)

        #except:
        #    logging.critical("Video {0}: Could not save audio stream for video {0} from channel {1} ({2})".format(self.yt_id, self.video.author, self.video.title))

        # Be polite
        time.sleep(1)


    def get_captions_by_language(self):
        """Filter captions by language and write each caption track to a file. If no language is specified, all caption tracks will be downloaded.

        :return caption_list: list of metadata for all successfully-downloaded caption tracks
        """

        caption_list = []
        for track in self.video.captions:
            if self.language is None or (self.language in track.name and (self.include_auto or "a." not in self.track.code)):

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

        if not self.log_fp:
            if self.group is None:
                log_fn = "{0}_log.csv".format(safe_author)
            else:
                log_fn = "{0}_log.csv".format(self.group)

            self.log_fp = path.join("corpus", "logs")
            if self.screen:
                self.log_fp = path.join("corpus", "unscreened_urls", "logs")

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

        if self.include_audio:
            audio = self.video.streams.filter(mime_type="audio/mp4").first()
            self.write_audio(audio)

        if len(caption_list) or self.include_audio:
            self.write_metadata(caption_list)

        return caption_list


class MultiVideoScraper:

    def __init__(self, f, log_fp=None, language=None, group=None, screen=None, include_audio=False, include_auto=False, convert_srt=False, resume_from=0, limit_to=-1, overwrite=False):

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
        self.resume_from   = resume_from
        self.limit_to      = limit_to
        self.overwrite     = overwrite

        # Other params
        self.channel_dict = {}
        self.video_count = 0


    def process_videos(self):
        """Download captions, audio (optional), and metadata for a list of videos.
        """

        if not self.log_fp: # No file passed, i.e. not a grouped batch

            if self.group is None:
                log_fn = "{0}_log.csv".format(path.splitext(path.split(self.f)[1])[0])
            else:
                log_fn = "{0}_log.csv".format(self.group)

            log_fp = path.join("corpus", "logs", log_fn)
            if self.screen:
                log_fp = path.join("corpus", "unscreened_urls", "logs", log_fn)

            # Delete previous if overwriting, but only if NOT a batch
            if path.isfile(log_fp) and self.overwrite:
                remove(log_fp)

        if self.screen:
            out_path = path.join("corpus", "unscreened_urls", "subtitles")
            if self.group:
                out_path = path.join("corpus", "unscreened_urls", self.group, "subtitles")
            out_audio_path = None
        else:
            out_path = path.join("corpus", "raw_subtitles")
            out_audio_path = path.join("corpus", "raw_audio")
            if self.group:
                out_path = path.join(out_path, self.group)
                out_audio_path = path.join(out_audio_path, self.group)

        self.video_count = 0
        with open(self.f, "r") as urls_in:

            for line in urls_in:

                self.video_count += 1

                if(self.video_count < self.resume_from):
                    continue

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
                yt_id = sub(punc_and_whitespace, '', findall(r".+watch\?v=(.+)\b", url)[0])

                # Check if yt_id already exists in some file; skip download if so
                if not self.overwrite:
                    files = glob(path.join(out_path, "**", "*{0}*".format(yt_id)), recursive=True)
                    if out_audio_path:
                        audio_files = glob(path.join(out_audio_path, "**", "*{0}*".format(yt_id)), recursive=True)
                        files = files + audio_files
                    if files:
                        continue

                video = VideoScraper(url, yt_id, self.log_fp, channel_name, channel_id, self.language, self.include_audio, self.include_auto, self.group, self.screen, self.convert_srt, self.include_title)
                video.process_video()

                if self.limit_to != -1 and self.video_count == self.resume_from + self.limit_to:
                    print("{0}: Limit reached".format(urls_path))
                    break


class BatchVideoScraper:

    def __init__(self, base_fn, batch=False, language=None, group=None, screen=None,  include_audio=False, include_auto=False, convert_srt=False, resume_from=0, limit_to=-1, overwrite=False):

        self.base_fn       = base_fn
        self.batch         = batch
        self.language      = language
        self.group         = group
        self.screen        = screen
        self.include_audio = include_audio
        self.convert_srt   = convert_srt
        self.resume_from   = resume_from
        self.limit_to      = limit_to
        self.overwrite     = overwrite


    def process_files():
        """Download captions, audio (optional), and metadata from a directory of video lists.
        """

        URL_fns_txt = sorted(glob(path.join(self.base_fn, "*.txt")))
        URL_fns_csv = sorted(glob(path.join(self.base_fn, "*.csv")))

        log_fp = None
        if self.group:
            log_fn = "{0}_log.csv".format(self.group)
            log_fp = path.join("corpus", "logs", log_fn)
            if self.screen:
                log_fp = path.join("corpus", "unscreened_urls", "logs", log_fn)

            if path.isfile(log_fp) and self.overwrite:
                path.remove(log_fp)


        all_fns = URL_fns_txt + URL_fns_csv

        # Need to make video objs
        for fn in all_fns:
            scraper = MultiVideoScraper(fn, log_fp, self.language, self.group, self.screen, self.include_audio, self.include_auto, self.convert_srt, self.resume_from, self.limit_to, self.overwrite)


class CaptionCleaner:

    def __init__(self, group=None, lang_code=None, fave=False, text=False, overwrite=False):

        self.group     = group
        self.lang_code = lang_code
        self.fave      = fave
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
                fave_dir = path.join(clean_sub_dir, langcode, "faves")
                text_dir = path.join(clean_sub_dir, langcode, "texts")

                if path.isdir(in_dir):
                    dir_list = [dir_element for dir_element in listdir(in_dir)]
                    if '.DS_Store' in dir_list:
                        dir_list.remove('.DS_Store')
                    for i, dir_element in enumerate(dir_list):
                        if path.isdir(path.join(in_dir, dir_element)):

                            channel_in_dir = path.join(in_dir, dir_element)
                            channel_cleans_dir = path.join(cleans_dir, dir_element)
                            channel_fave_dir = path.join(fave_dir, dir_element)
                            channel_text_dir = path.join(text_dir, dir_element)

                            channel_dir_list = [dir_element for dir_element in listdir(channel_in_dir)]
                            if '.DS_Store' in channel_dir_list:
                                channel_dir_list.remove('.DS_Store')
                            for j, fn in enumerate(channel_dir_list):
                                self.clean_captions(j, fn, langcode, channel_in_dir, channel_cleans_dir,channel_fave_dir, channel_text_dir, self.fave, self.text, self.overwrite)
                        else:
                            self.clean_captions(i, dir_element, langcode, in_dir, cleans_dir, fave_dir, text_dir, self.fave, self.text, self.overwrite)

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
            time_start_s = convert_to_seconds(line[0])
            time_end_s = convert_to_seconds(line[1])
            sub_text = clean_text(line[2], langcode)
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

        elif file_type == 'fave':
            out_df = pd.DataFrame(columns=['speaker_code', 'speaker_name',
                                     'start_time', 'end_time', 'subtitle_text'])
            for line in timed_lines:
                subtitle_row = {"speaker_code": channel_name[:2], "speaker_name": channel_name, "start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
                out_df = out_df.append(subtitle_row, ignore_index=True)
            out_df.to_csv(out_file_path, sep='\t', index=False, header=False)

        elif file_type == 'text':
            all_lines = [line[2] for line in timed_lines]
            all_text = " ".join(all_lines)
            with open(out_file_path, "w") as file:
                file.write(all_text)
        else:
            print('File type is not valid (cleans, fave, text).')

    def clean_captions(self, i, fn, langcode, in_dir, cleans_dir, fave_dir, text_dir, fave=False, text=False, overwrite=False):
        name, ext = path.splitext(fn)

        if path.isdir(cleans_dir) and not overwrite:
            existing_files = glob(path.join(cleans_dir, "**", "*{0}*".format(name)), recursive=True)
            if existing_files:
                return 1

        print('Processing transcript {0}: {1}'.format(i+1,fn))

        timed_lines = self.get_timestamped_lines(in_dir, fn, langcode)
        self.write_to_output('cleans', cleans_dir, name, timed_lines)
        if fave:
            self.write_to_output('fave', fave_dir, name, timed_lines)
        if text:
            self.write_to_output('text', text_dir, name, timed_lines)
