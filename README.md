# LingTube
Tools for scraping and doing linguistic analysis with YouTube data.

*[Note: Currently only tested on MacOS and English speech.]*

## Updates
* 08/12/21: Scripts reorganized and renamed (with order); structure and documentation update underway
* 04/06/21: Currently under active development

## Dependencies

Dependencies are provided in the `requirements/` folder. To install all dependencies, run

`pip install -r $FileName`

where $FileName is one of `correct.txt` (if you need only the dependencies for making corrections), `youspeak.txt` (if you need only the YouSpeak pipeline dependencies), `yt-tools.txt` (if you need only the dependencies for scraping YouTube),`text-tools.txt` (if you need only the dependencies for working with caption text), or `full.txt` if you want to install all dependencies. Note, depending on your system, you may need to run `pip3 install` instead of `pip install`.

In addition, this software requires the latest version of Python and TK. If you are on MacOS and using Homebrew, simply run

`brew install python-tk`

to install the version of Python that is bundled with TK. By default, `brew install python` no longer installs TK.

## Components
*Details coming soon!*

* [`base`](#base)
* [`youdep`](#youdep)
* [`youspeak`](#youspeak)

### Base

*Details coming soon!*

<!-- Add details -->

#### 1-scrape-channels.py

This script allows the user to scrape video URLs from a specified channel or list of channels. The user can also input a list of videos in order to scrape the uploading channel's info and/or scrape the remaining videos from their channel.

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

#### 2-scrape-videos.py

##### Usage

```
python3 yt-tools/scrape-videos.py -h
usage: scrape-videos.py [-h] [--language LANGUAGE] [--group NAME] [--overwrite]
                        [--auto] [--audio] [--srt] [--resume N] [--limit N]
                        [--screen] [--clean]
                        urls_in

Download available subtitles and audio from a list of YouTube video urls.

positional arguments:
  urls_in               path to a file or directory containing the URLs to scrape

optional arguments:
  -h, --help            show this help message and exit
  --language LANGUAGE, -l LANGUAGE
                        filter captions by language name (e.g. "Korean"); if
                        unspecified, all captions will be downloaded
  --group NAME, -g NAME
                        a name for the group; if unspecified, channel names will be
                        used
  --overwrite, -o       overwrite logs and files rather than appending
  --auto, -a            include automatically-generated captions
  --audio, -s           download audio
  --srt                 download captions in SRT format
  --resume N, -res N    resume downloading from Nth video or file
  --limit N, -lim N     limit processing to N videos or files
  --screen              downloading files for screening purposes
  --clean               skip scraping and only clean dowloaded caption filenames of
                        langcode
```

### 3-clean-captions.py
#### Usage
```
usage: clean-captions.py [-h] [--group GROUP] [--lang_code LANG_CODE] [--fave]
                         [--text] [--corrected] [--overwrite]

Convert scraped YouTube captions to cleaned transcript format.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: cleaned_subtitles/$group)
  --lang_code LANG_CODE, -l LANG_CODE
                        open captions with a specific a language code (e.g.,
                        "en"); if unspecified, goes through all available
                        language code in subtitle directory
  --fave, -f            additionally output Fave-format file
  --text, -t            additionally output text-only file
  --corrected, -c       only run on corrected subtitles
  --overwrite, -o       overwrite files rather than appending
```

#### 4-correct-captions.py

This script helps to streamline the correction of YouTube captions prior to chunking. It opens each video in a list of videos one-at-a-time in the browser alongside the caption file, which opens in a text editor of the user's choice. Correction progress can be saved such that next time the program is run, the video will open where the user left off last time.

##### Usage

```
python3 yt-tools/correct-captions.py -h
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
### YouDep
*Details coming soon!*

### YouSpeak

*[Note: More details forthcoming!]*

#### Dependencies

Most dependencies are provided in the `requirements/` folder. To install, from the LingTube main directory, run

`pip install -r requirements/youspeak.txt`

For the scripts that rely on [pydub](https://github.com/jiaaro/pydub), you will also need to download `ffmpeg` separately, following the instructions [here](https://github.com/jiaaro/pydub#getting-ffmpeg-set-up).  If you are on MacOS and using Homebrew, you can run

`brew install ffmpeg`

For the scripts requiring `parselmouth-praat`, the Praat application is required. It can be downloaded from the [Praat website](https://www.fon.hum.uva.nl/praat/).  If you are on MacOS and using Homebrew, simply run

`brew install --cask praat`

#### Pipeline Components

Before using scripts under YouSpeak, you should have already run the relevant scripts in `base`. That is, you should have (1) downloaded audio and caption files, and (2) corrected the original captions (though corrections can also be done later). YouSpeak is intended to be run in this order:

1. [`1-convert-audio.py`](#1-convert-audio.py)
2. [`2-chunk-audio.py`](#2-chunk-audio.py)
4. [`3-validate-chunks.py`](#3-validate-chunks.py)
5. [`4-create-textgrids.py`](#4-create-textgrids.py)

After this stage, you can run forced alignment (using the Montreal Forced Aligner or other compatible aligner).

#### 1-convert-audio.py

This script allows the user to convert scraped YouTube audio from MP4 to WAV format, as well as converting from stereo to mono. The default includes mono conversion but the user can specify if they prefer to keep audio as stereo. The script then moves the raw MP4 and converted WAV files to separate folders.

##### Usage

To convert all scraped audio files to mono WAV (in a corpus without group structure):

```
python3 youspeak/1-convert-audio.py
```

To convert all scraped audio files in a group to mono WAV (in a corpus with group structure):

```
python3 youspeak/1-convert-audio.py --group $group_name
```

To convert all scraped audio files in a group to stereo WAV (in a corpus with group structure):

```
python3 youspeak/1-convert-audio.py --group $group_name --stereo
```

##### Examples

`python3 youspeak/1-convert-audio.py -g kor`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `raw_audio`
2. Converts all MP4 files in the `kor` folder to mono WAV files.
3. Moves MP4 files to a folder called `mp4` and the WAV files to a folder called `wav`


#### 2-chunk-audio.py

This script identifies short utterances of speech based on breath breaks in the audio and outputs corresponding Praat TextGrid files. The user can specify whether to process all the audio files in a group, channel, or particular video. Users can also optionally save chunked audio files, either specified during the initial chunking (will be saved while processing the output TextGrid) or when running the script a second time (sound files will be saved based on an input TextGrid).

NOTE: The user can specify whether first-pass chunking is based on voice activity detection (identifying long pauses) or music detection (identifying music vs. speech). Music detection is undergoing updates and not currently recommended for use.


##### Usage

To chunk all audio files and output an annotated TextGrid for each (in a corpus without group structure):

`python3 youspeak/2-chunk-audio.py voice`

To chunk all audio files in a group and output an annotated TextGrid for each (in a corpus with group structure):

`python3 youspeak/2-chunk-audio.py voice --group $group_name`


To chunk all audio files for a particular channel and output an annotated TextGrid for each (in a corpus with group structure):

`python3 youspeak/2-chunk-audio.py voice --group $group_name --channel $channel_name`

To chunk a particular video audio file and output an annotated TextGrid (in a corpus with group structure):

`python3 youspeak/2-chunk-audio.py voice --group $group_name --channel $channel_name --video $video_id`

To chunk all audio files in a group and output (a) an annotated TextGrid for each and (b) separate WAV sound files corresponding to each identified chunk:

`python3 youspeak/2-chunk-audio.py voice --group $group_name --save_sounds`

Alternatively, this same command can be used to save separate WAV sound files based on already existing TextGrids from running `python3 youspeak/2-chunk-audio.py voice --group $group_name` previously. This may be beneficial if the user prefers to check and/or modify the TextGrids prior to extracting utterance-level sound files.

##### Examples

`python3 youspeak/2-chunk-audio.py voice -g kor`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `raw_audio/wav`
2. For each audio file, checks if TextGrids and audio files already exist.

If yes:
3. Skips file.

If no:
3. Runs voice activity detection on each audio file to identify pauses/breath breaks vs. speech.
4. Adds boundaries to a TextGrid per video to identify intervals of "speech" or "silence" and saves this TextGrid under the folder `chunked_audio/kor/textgrids/chunking`

`python3 youspeak/2-chunk-audio.py voice -g kor -s`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `raw_audio/wav`
2. For each audio file, checks if TextGrids already exist.

If yes:
3. Extracts audio per "speech" interval in the TextGrid and saves as WAV files under the folder `chunked_audio/kor/audio/chunking`

If no:
3. Runs voice activity detection on each audio file to identify pauses/breath breaks vs. speech.
4. Adds boundaries to a TextGrid per video to identify intervals of "speech" or "silence" and saves this TextGrid under the folder `chunked_audio/kor/textgrids/chunking`
5. Extracts audio per identified speech chunk and saves as WAV files under the folder `chunked_audio/kor/audio/chunking`

<!-- ```
usage: 2-chunk-audio.py [-h] {voice,music} ...

Chunk WAV audio files into short segments of sound.

positional arguments:
  {voice,music}  use voice activity detection or music detection (beta ver.)
                 for first-pass audio chunking
    voice        use voice activity detection for first-pass audio chunking
                 (see 2-chunk-audio.py voice -h for more help)
    music        (BETA) use music detection for first-pass audio chunking (see
                 2-chunk-audio.py music -h for more help)


                 usage: 2-chunk-audio.py voice [-h] [--group GROUP] [--channel CHANNEL]
                                               [--video VIDEO] [--save_sounds] [--overwrite]

                 optional arguments:
                   -h, --help            show this help message and exit
                   --group GROUP, -g GROUP
                                         name to group files under (create and /or assume files
                                         are located in a subfolder: raw_subtitles/$group)
                   --channel CHANNEL, -ch CHANNEL
                                         run on files for a specific channel name; if
                                         unspecified, goes through all channels in order
                   --video VIDEO, -v VIDEO
                                         run on files for a video id; if unspecified, goes
                                         through all videos in order
                   --save_sounds, -s     save chunked sound files (necessary for using
                                         3-validate-chunks.py); default only saves full
                                         textgrid
                   --overwrite, -o       overwrite files rather than appending



``` -->


#### 3-validate-chunks.py
##### Usage
```
usage: 3-validate-chunks.py [-h] [--group GROUP] [--lang_code LANG_CODE]

Open a GUI for categorizing and transcribing audio chunks.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: chunked_audio/$group)
  --lang_code LANG_CODE, -l LANG_CODE
                        open captions with a specific a language code (e.g.,
                        "en"); if unspecified, uses first available language
                        code in subtitle directory
```

#### 4-create-textgrids.py
##### Usage
```
usage: 4-create-textgrids.py [-h] [--group GROUP] [--channel CHANNEL]
                             [--save_chunks] [--mfa] [--overwrite]

Create MFA-compatible textgrids and move to MFA alignment folder.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: chunked_audio/$group)
  --channel CHANNEL, -ch CHANNEL
                        run on files for a specific channel name; if
                        unspecified, goes through all channels in order
  --save_chunks, -s     save chunked textgrids and sound files; default only
                        saves full textgrid
  --mfa                 copy textgrids and audio into MFA compatible directory
                        structure under aligned_audio/$group; default does not
                        create directory
  --overwrite, -o       overwrite files rather than appending
```
