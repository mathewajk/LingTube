# LingTube
Tools for scraping and doing linguistic analysis with YouTube data.

## Updates
* Currently under active development

## Dependencies

Dependencies are provided in the `requirements/` folder. To install all dependencies, run

`pip install -r $FileName`

where $FileName is one of `correcting.txt` (if you need only the dependencies for making corrections), `youspeak.txt` (if you need only the YouSpeak pipeline dependencies), `yt-tools.txt` (if you need only the depenedencies for scraping YouTube), or `full.txt` if you want to install all dependencies. Note, depending on your system, you may need to run `pip3 install` instead of `pip install`.

In addition, this software requires the latest version of Python and TK. If you are on MacOS and using Homebrew, simply run

`brew install python-tk`

to install the version of Python that is bundled with TK. By default, `brew install python` no longer installs TK.

## Components
*Details coming soon!*

* `youdep`
* `youspeak`

### yt-tools

#### correct-captions.py


This script helps to streamline the correction of YouTube captions prior to chunking. It opens each video in a list of videos one-at-a-time in the browser alongside the caption file, which opens in a text editor of the user's choice. Correction progress can be saved such that next time the program is run, the video will open where the user left off last time.

##### Usage

```
python3 /Users/narquelion/Documents/research/git-projects/LingTube/yt-tools/correct-captions.py -h
usage: correct-captions.py [-h] [--group GROUP] [--lang_code LANG_CODE]
                           [--channel CHANNEL] [--editor EDITOR]

Open captions text file and YouTube video in browser to aid in correcting captions,
based on a log file in corpus/logs. If group is specified, uses
corpus/logs/$group_log.csv. If no group is specified, ask user to navigate to and
select a log file.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files are
                        located in a subfolder: raw_subtitles/$group)
  --lang_code LANG_CODE, -l LANG_CODE
                        open captions with a specific a language code (e.g., "en");
                        if unspecified, uses first available language code in
                        subtitle directory
  --channel CHANNEL, -ch CHANNEL
                        run on files for a specific channel name; if unspecified,
                        goes through all channels in order
  --editor EDITOR, -e EDITOR
                        opens text file in a specified text editor: TextEdit, Atom,
                        Notepad++ (default=TextEdit)
```

#### scrape-channels.py

This script allows the user to scrape video URLs from a specified channel or list of channels. The user can also input a list of videos in order to scrape the uploading channel's infor and/or scrape the remaining videos from their channel.

##### Usage

General usage:

```
python3 yt-tools/scrape-channels.py -h
usage: scrape-channels.py [-h] {single,multi,video} ...

Scrape video URLs from a YouTube channel.

positional arguments:
  {single,multi,video}  process one channel, a list of channels, or a list of
                        videos
    single              process a single channel (see scrape_channels.py single
                        -h for more help)
    multi               process a list of channels (see scrape_channels.py
                        multi -h for more help)
    video               process channels from a list of videos (see
                        scrape_channels.py video -h for more help)

optional arguments:
  -h, --help            show this help message and exit
```

Scraping a single channel with the `single` argument:

```
python3 yt-tools/scrape-channels.py single -h
usage: scrape-channels.py single [-h] [-g NAME] [--cutoff CUTOFF] [--overwrite]
                                 [--screen] [-l]
                                 channel

positional arguments:
  channel               URL pointing to the channel's main page, e.g.
                        https://www.youtube.com/c/ChannelNameHere

optional arguments:
  -h, --help            show this help message and exit
  -g NAME, --group NAME
                        grouping for the output files (will create a subfolder:
                        screened_urls/$group)
  --cutoff CUTOFF       maximum number of times to scroll the page when
                        scraping
  --overwrite, -o       overwrite files rather than appending
  --screen              download files for screening purposes
  -l, --log             log events to file
```

Scraping multiple channels with the `multi` argument:

```
python3 yt-tools/scrape-channels.py multi -h
usage: scrape-channels.py multi [-h] [-g NAME] [--cutoff CUTOFF] [--overwrite]
                                [--screen] [-l]
                                file

positional arguments:
  file                  file containing a newline-separated list of channel
                        URLs (e.g. https://www.youtube.com/c/Channel1NameHere\n
                        https://www.youtube.com/c/Channel2NameHere\n)

optional arguments:
  -h, --help            show this help message and exit
  -g NAME, --group NAME
                        grouping for the output files (will create a subfolder:
                        screened_urls/$group)
  --cutoff CUTOFF       maximum number of times to scroll the page when
                        scraping
  --overwrite, -o       overwrite files rather than appending
  --screen              download files for screening purposes
  -l, --log             log events to file
```

Scraping channels based on a list of videos with the `video` argument:

```
python3 yt-tools/scrape-channels.py video -h
usage: scrape-channels.py video [-h] [-n] [-g NAME] [--cutoff CUTOFF]
                                [--overwrite] [--screen] [-l]
                                file

positional arguments:
  file                  file containing a newline-separated list of video URLs

optional arguments:
  -h, --help            show this help message and exit
  -n, --noscrape        don't scrape the channel; only gather about info
  -g NAME, --group NAME
                        grouping for the output files (will create a subfolder:
                        screened_urls/$group)
  --cutoff CUTOFF       maximum number of times to scroll the page when
                        scraping
  --overwrite, -o       overwrite files rather than appending
  --screen              download files for screening purposes
  -l, --log             log events to file
```

##### Examples

`python3 yt-tools/scrape-channels.py -h -g cali-tw --cutoff 10 --screen multi urls.txt`

This call:
1. Takes a file with a list of channel URLs as its input (`urls.txt`)
2. Scrapes each channel, scrolling the list of videos up to 10 times
3. Groups the resulting video URLs under a subfolder called `cali-tw`
4. Additionally groups them under a folder called `unscreened_videos` indicating that the videos need to be checked for usability
