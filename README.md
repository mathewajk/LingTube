# LingTube
LingTube is a suite of tools for scraping and doing linguistic analysis with YouTube data. This pipeline is intended as a resource for language researchers who want to download YouTube video captions and audio for textual or phonetic analysis.

**Disclaimer/Important Note: Scripts have been developed and thoroughly tested only on MacOS. In addition, while scraping will work for captions in any language, processing of captions and audio have only been developed for and tested on English speech at the moment. English captions are currently processed to be compatible with the Montreal Force-Aligner.**

## Changelog
* 10/05/21: All "base" functions moved to Base module
* 08/12/21: Scripts reorganized and renamed (with order); structure and documentation update underway
* 04/06/21: Currently under active development

## Dependencies

Dependencies are provided in the `requirements.txt` file. To install all dependencies, run

`pip install -r requirements.txt`

In addition, this software requires the latest version of Python and TK. If you are on MacOS and using Homebrew, simply run

`brew install python-tk`

to install the version of Python that is bundled with TK. By default, `brew install python` no longer installs TK.

At the moment, LingTube still depends on [Selenium](https://www.selenium.dev/). In order to work with Selenium, you will need to download the appropriate WebDriver, which should be placed in `usr/bin/`:

* For Firefox: [GeckoDriver](https://github.com/mozilla/geckodriver/releases)\n",
* For Chrome: [ChromeDriver](https://github.com/SeleniumHQ/selenium/wiki/ChromeDriver)

For further information, the Selenium documentation can be found [here](https://www.selenium.dev/documentation/en/webdriver/).

For the YouSpeak scripts that rely on [pydub](https://github.com/jiaaro/pydub), you will also need to download `ffmpeg` separately, following the instructions [here](https://github.com/jiaaro/pydub#getting-ffmpeg-set-up).  If you are on MacOS and using Homebrew, you can run

`brew install ffmpeg`

Additionally, for the YouSpeak scripts requiring `parselmouth-praat`, the Praat application is required. It can be downloaded from the [Praat website](https://www.fon.hum.uva.nl/praat/).  If you are on MacOS and using Homebrew, you can run

`brew install --cask praat`



## Components
*Details coming soon!*

* [`base`](#base)
* [`youdep`](#youdep)
* [`youspeak`](#youspeak)

---

### Base

The LingTube base scripts are used first to access YouTube data and pre-process captions prior to more specific processing (via YouDep or YouSpeak pipeline components). Before using the base scripts, you should have identified YouTube channel(s) or video(s) that you intend to scrape. Base is intended to be run in this order:

1. [`1-scrape-channels.py`](#1-scrape-channelspy)
2. [`2-scrape-videos.py`](#2-scrape-videospy)
4. [`3-clean-captions.py`](#3-clean-captionspy)
5. [`4-correct-captions.py`](#4-correct-captionspy)

---

#### 1-scrape-channels.py

This script allows the user to scrape video URLs from a specified channel or list of channels, along with the channel info (e.g., channel name, channel ID, *About* page). The user can also input a video URL or list of video URLs in order to scrape the uploading channel's info and/or scrape additional videos from their channel. This second option also outputs a formatted version of the input video URLs for use in `2-scrape-videos.py` (see below for more info).

**Note: Running the script for the first time sometimes results in a Selenium error. If this happens, run the script again and it should work.**

**Note 2: Sometimes the channel name is missing from the file(names) for the first downloaded file. If this happens, it should work perfectly if you run it a second time (exact same command). If this happens, run the script again after deleting the bad file.**

###### Usage

```
usage: 1-scrape-channels.py [-h] [-g GROUP] [-a] [-lim N] [-b BROWSER] [-o]
                            [-s] source
```

###### Source
To scrape all video URLs from a single channel into an "ungrouped" sub-folder, include a YouTube channel URL as the source:

```
python3 base/1-scrape-channels.py $channel_url
```

To scrape all video URLs from multiple channels at once into an "ungrouped" sub-folder, include a text file containing a list of YouTube channel URLs:
```
python3 base/1-scrape-channels.py $channel_url_list.txt
```

To scrape a single channel or multiple channels from video URL(s) into an "ungrouped" sub-folder, use video URLs instead of channel URLs as in:

```
python3 base/1-scrape-channels.py $video_url
```
and

```
python3 base/1-scrape-channels.py $video_url_list.txt
```

These latter two commands will also output a separate file containing the same video URLs you input formatted with additional columns for the channel name and channel ID.

###### Options

To scrape all video URLs from multiple channels where channel files are grouped under a named group sub-folder, specify a group name with `-g` or `--group`:
```
python3 base/1-scrape-channels.py --group $group_name $channel_url_list.txt
```

To scrape only the channel name/ID and About page info per channel, use the `-a` or `--about` flag. When video URLs are the source, the outputs the formatted video URL list along with the About page info:
```
python3 base/1-scrape-channels.py --about $video_url_list.txt
```

To scrape only a certain number of video URLs per channel, specify a number (*N*) with the `-lim` or `--limit` flag. This can be repeated to add a specified number of video URLs in addition to what has already been scraped:
```
python3 base/1-scrape-channels.py -lim N $channel_url_list.txt
```

To specify a browser to use for scraping (either "Firefox" or "Chrome"), use `-b` or `--browser`. The default browser option is Firefox:
```
python3 base/1-scrape-channels.py -b $browser_name $channel_url_list.txt
```

To completely overwrite the grouping folder containing previously scraped info and video URL files (if group is unspecified, this will be the "ungrouped" folder) with newly scraped data, use the `-o` or `--overwrite` flag. This is useful for testing purposes or if data needs to be completely re-done, but may result in data loss/change if not used carefully:
```
python3 base/1-scrape-channels.py -o $channel_url_list.txt
```

To scrape video URLs and channel info for (manual) screening purposes, you can use the `-s` or `--screen` flag to download data into a separate temporary folder named "unscreened_videos":
```
python3 base/1-scrape-channels.py -s $channel_url_list.txt
```

##### Examples

<!-- https://www.youtube.com/channel/UCgWfS_47YPVbKx5EK4FLm4A = Jenn Im -->

`python3 base/1-scrape-channels.py -lim 10 -g groupA -s channel_urls.txt
`

This call:
1. Takes a file with a list of channel URLs as its input (`channel_urls.txt`)
2. Using the default Firefox browser, scrapes each channel collecting 10 (additional) video URLs and the About page info
3. Groups the resulting video URLs under a subfolder called `groupA`
4. Additionally places the group subfolder under a folder called `unscreened_videos` indicating that the videos need to be checked for usability



`python3 base/1-scrape-channels.py -o -b Chrome video_urls.txt
`

This call:
1. Takes a file with a list of video URLs as its input (`video_urls.txt`)
2. Checks for and deletes the subfolder called `ungrouped` if it exists
3. Using the Chrome browser, scrapes each channel collecting all available video URLs and the About page info
3. Saves the resulting video URLs under a subfolder called `ungrouped`
4. In addition, outputs the list of video URLs with columns for the scraped channel name and ID

---

#### 2-scrape-videos.py

This script allows the user to scrape manual and/or automated captions and audio from a specified file containing list of video URLs. Alternatively the user can specify a directory containing multiple lists of URLs, or the user can specify a group name (i.e., the name of a group sub-folder under `screened_urls`) which will access the `channel_urls` directory, assumed to contain lists of URLs.

**Note: If getting error that you cannot download audio, try upgrading pytube (pip3 install --upgrade pytube).**

##### Usage

###### Source
To scrape all manual video captions from a list of URLs into an "ungrouped" sub-folder, include a text file containing a list of YouTube video URLs:

```
python3 base/2-scrape-videos.py $video_url_list.txt
```

To scrape all manual video captions from multiple lists of URLs at once into an "ungrouped" sub-folder, include a directory containing text files of video URLs:

```
python3 base/2-scrape-videos.py $urls_directory
```

To scrape all manual video captions from multiple lists of URLs via a specific group folder into group sub-folders of the same name, include a group name (specifying -g [see below] is not necessary):

```
python3 base/2-scrape-videos.py $group_name
```


###### Options
To scrape all manual video captions where channel files are grouped under a named group sub-folder, specify a group name with `-g` or `--group`:
```
python3 base/2-scrape-videos.py -g $group_name $video_url_list.txt
```

To scrape all manual video captions only for a particular language, specify a language name (e.g. "English", "Korean") with `-l` or `--language`:
```
python3 base/2-scrape-videos.py -l $language_name $video_url_list.txt
```

To scrape all manual video captions and/or automated captions from a list of URLs, use `-a` or `--auto`:
```
python3 base/2-scrape-videos.py -a $video_url_list.txt
```

To scrape all manual video captions along with corresponding audio tracks from a list of URLs, use `-aud` or `--audio`:
```
python3 base/2-scrape-videos.py -aud $video_url_list.txt
```

To scrape all manual video captions and convert default XML files to SRT files, use `--srt`:
```
python3 base/2-scrape-videos.py --srt $video_url_list.txt
```

To scrape only a maximum number of manual video captions, specify a number (*N*) with the `-lim` or `--limit` flag. This can be repeated to add a specified number of captions in addition to what has already been scraped:
```
python3 base/2-scrape-videos.py -lim N $video_url_list.txt
```

To completely overwrite the grouping folder containing previously scraped video caption and/or audio files (if group is unspecified, this will be the "ungrouped" folder) with newly scraped data, use the `-o` or `--overwrite` flag with the `all` argument:
```
python3 base/2-scrape-videos.py -o all $video_url_list.txt
```

To overwrite only existing channels (for example, when you want to replace the data for some channels, but not overwrite all previously-downloaded channel data), you can use the `channel` argument:

```
python3 base/2-scrape-videos.py -o channel $video_url_list.txt
```

Finally, to overwrite only the specific video data you've already collected (i.e. not *all of* of a group or channel's data), you can use the `video` argument:
```
python3 base/2-scrape-videos.py -o video $video_url_list.txt
```

To scrape video captions and/or audio for screening purposes, you can use the `-s` or `--screen` flag to download data into a separate temporary folder named "unscreened_videos":
```
python3 base/2-scrape-videos.py -s $video_url_list.txt
```

##### Examples

`python3 base/2-scrape-videos.py -g groupA -a -aud --srt -lim 10 video_urls_list.txt
`

This call:
1. Takes a file with a list of video URLs as its input (`video_urls_list.txt`)
2. Scrapes caption files for up to 10 videos that have either auto captions or manual captions (saved under `raw_subtitles\groupA\auto` and `raw_subtitles\groupA\manual`), along with the corresponding audio tracks for those 10 videos (saved under `raw_audio\groupA`)
3. Additionally converts caption files from XML to SRT format

`python3 base/2-scrape-videos.py -aud -l Korean -o groupB
`
This call:
1. Takes a group name as its input (`groupB`)
2. Checks for and deletes the subfolders called `groupB` if it exists in the output folders (`raw_subtitles` and `raw_audio`)
3. For each file in `screened_urls\groupB\channel_urls`, downloads all existing manual Korean caption files in XML format (saved under `raw_subtitles\groupB\manual`), along with the corresponding audio tracks (saved under `raw_audio\groupB`)

---

#### 3-clean-captions.py

This script allows the user to convert scraped YouTube SRT captions to a cleaned transcript text format that has three columns for: (i) start time, (ii) end time, (iii) caption text. (Note that to use this script, you must have downloaded captions as SRT and not XML files.)

##### Usage
To clean all scraped SRT files from an "ungrouped" sub-folder:

```
python3 base/3-clean-captions.py
```

To clean all scraped SRT files from a grouped sub-folder, specify a group name with `-g` or `--group`:

```
python3 base/3-clean-captions.py -g $group_name
```

To clean all scraped SRT files from a particular language, specify a language code (e.g., 'en', 'ko', 'jp') with `-l` or `--language`:

```
python3 base/3-clean-captions.py -l $lang_code
```

To additionally output a text file with only the transcript text, use the `-t` or `--text` flag:

```
python3 base/3-clean-captions.py -t
```

To overwrite all previously cleaned text files with new cleaned files, use the `-o` or `--overwrite` flag. :

```
python3 base/3-clean-captions.py -o
```


##### Examples

`python3 base/3-clean-captions.py -g kor -l ko -t
`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube captions called `raw_subtitles`
2. For each .srt caption file under the `ko` language folder, outputs a reformatted .txt file with start time, end time and transcript text columns under `cleaned_subtitles/kor` (in a folder called `cleans`).
3. Additionally outputs a transcript text-only file (in a folder called `texts`)


---

#### 4-correct-captions.py

This optional script helps to streamline the correction of YouTube captions, if necessary. It opens each video in a list of videos one-at-a-time in the browser alongside the caption file, which opens in a text editor of the user's choice. Correction progress can be saved such that next time the program is run, the video will open where the user left off last time.

##### Usage

To start the program to correct captions in a corpus without group structure (i.e., where channels are listed under an `ungrouped` folder):

```
python3 base/4-correct-captions.py
```

To start the program to correct captions from a particular group, specify a group name with `-g` or `--group`:

```
python3 base/4-correct-captions.py -g $group_name
```

To start the program to correct captions from a particular channel, specify a channel name with `-ch` or `--channel`:

```
python3 base/4-correct-captions.py -ch $channel_name
```

To start the program to correct captions for a particular language, specify a language code (e.g., 'en' for English) with `-l` or `--lang_code`:

```
python3 base/4-correct-captions.py -l $lang_code
```

To start the program to correct captions using a particular text editor, specify an editor ("TextEdit", "Atom", "Notepad") with `-e` or `--editor`:

```
python3 base/4-correct-captions.py -e $editor_name
```

##### Examples

`python3 base/4-correct-captions.py -g kor -ch JennIm -l en
`

This call:
1. Takes a group name and locates the log file under `logs` called `kor_log.csv`.
2. In the log file, identifies only the rows (i.e., videos) corresponding to the channel `JennIm` that have not yet been corrected (`corrected` column is 0).
3. Opens a GUI window that allows the user to open a text file and YouTube video for each uncorrected video (starting from the first).
4. When the user clicks "Open", locates the cleaned caption file under the `kor` (group) and `en` (language code) sub-folders of the `cleaned_subtitles` folder.
5. Makes a copy of the caption file if it doesn't exist and opens the copy in the default text editor (e.g., TextEdit on MacOS).
6. Additionally, opens the video URL (listed in the log file) in the default browser.
7. When the user is finished editing the text file, they either input a stop time or check off a box indicating completion, then choose to save & quit or move on to the next video. This updates the `corrected` column of the log file `kor_log.csv`.


---

### YouDep
*Details coming soon!*

---

### YouSpeak

The YouSpeak scripts are used to process scraped audio for forced alignment; specifically, these scripts (help to) identify usable speech utterances and match them to transcript text. Before using scripts under YouSpeak, you should have already run the relevant scripts in `base`. That is, you should have (1) downloaded audio and caption files, and optionally (2) corrected the original captions (though corrections can also be done after `2-chunk-audio.py` but before `3-validate-chunks.py`). YouSpeak is intended to be run in this order:

1. [`1-convert-audio.py`](#1-convert-audiopy)
2. [`2-chunk-audio.py`](#2-chunk-audiopy)
4. [`3-validate-chunks.py`](#3-validate-chunkspy)
5. [`4-create-textgrids.py`](#4-create-textgridspy)

After this stage, you can run forced alignment (using the Montreal Forced Aligner or other compatible aligner).

---

#### 1-convert-audio.py

This script allows the user to convert scraped YouTube audio from MP4 to WAV format, as well as converting from stereo to mono. The default includes mono conversion but the user can specify if they prefer to keep audio as stereo. The script then moves the raw MP4 and converted WAV files to separate folders.

**Note: We are in the process of overhauling this script to include neural-net based sound event detection for better identification of useable audio.**

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

---
#### 2-chunk-audio.py

This script identifies short utterances of speech based on breath breaks in the audio and outputs corresponding Praat TextGrid files. The user can specify whether to process all the audio files in a group, channel, or particular video. Users can also optionally save chunked audio files, either specified during the initial chunking (will be saved while processing the output TextGrid) or when running the script a second time (sound files will be saved based on an input TextGrid).

NOTE: The user can specify whether first-pass chunking is based on voice activity detection (identifying long pauses) or music detection (identifying music vs. speech). Music detection is undergoing updates and not currently recommended for use.


##### Usage

To chunk all audio files and output an annotated TextGrid for each (in a corpus without group structure):

```
python3 youspeak/2-chunk-audio.py voice
```

To chunk all audio files in a group and output an annotated TextGrid for each (in a corpus with group structure):

```
python3 youspeak/2-chunk-audio.py voice --group $group_name
```


To chunk all audio files for a particular channel and output an annotated TextGrid for each (in a corpus with group structure):

```
python3 youspeak/2-chunk-audio.py voice --group $group_name --channel $channel_name
```

To chunk a particular video audio file and output an annotated TextGrid (in a corpus with group structure):

```
python3 youspeak/2-chunk-audio.py voice --group $group_name --channel $channel_name --video $video_id
```

To chunk all audio files in a group and output (a) an annotated TextGrid for each and (b) separate WAV sound files corresponding to each identified chunk:

```
python3 youspeak/2-chunk-audio.py voice --group $group_name --save_sounds
```

Alternatively, this same command can be used to save separate WAV sound files based on already existing TextGrids from running `python3 youspeak/2-chunk-audio.py voice --group $group_name` previously. This may be beneficial if the user prefers to check and/or modify the TextGrids prior to extracting utterance-level sound files.

##### Examples

`python3 youspeak/2-chunk-audio.py voice -g kor`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `raw_audio/wav`
2. For each audio file, checks if TextGrids and audio files already exist. (If yes, moves onto next file.)
3. If no, runs voice activity detection on each audio file to identify pauses/breath breaks vs. speech.
4. Adds boundaries to a TextGrid per video to identify intervals of "speech" or "silence" and saves this TextGrid under the folder `chunked_audio/kor/textgrids/chunking`

`python3 youspeak/2-chunk-audio.py voice -g kor -s`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `raw_audio`
2. For each audio file, checks if TextGrids already exist. (If yes, extracts audio per "speech" interval in the TextGrid and saves as WAV files under the folder `chunked_audio/kor/audio/chunking`, with a log file in `chunked_audio/kor/logs/chunking`. Then, moves onto next file.)
3. If no, runs voice activity detection on each audio file to identify pauses/breath breaks vs. speech.
4. Adds boundaries to a TextGrid per video to identify intervals of "speech" or "silence" and saves this TextGrid under the folder `chunked_audio/kor/textgrids/chunking`
5. Extracts audio per identified speech chunk and saves as WAV files under the folder `chunked_audio/kor/audio/chunking`, with a log file in `chunked_audio/kor/logs/chunking`

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

---
#### 3-validate-chunks.py

This script opens a GUI for categorizing and transcribing audio chunks, allowing the user to (1) mark audio chunks as usable or not, and (2) check that transcript lines are time-aligned accurately to speech per audio chunk.

##### Usage

To run the GUI when only one transcript (language) is available:
```
python3 youspeak/3-validate-chunks.py voice -g $group_name
```

To run the GUI when needing to specify transcript (language):
```
python3 youspeak/3-validate-chunks.py voice -g $group_name --lang_code $language_code
```

##### Examples

`python3 youspeak/3-validate-chunks.py voice -g kor (-l en)`

This call:
1. Opens up a prompt for user to select a chunking log file from `chunked_audio/kor/logs/chunking`

![3-validate-chunks.py prompt 1](https://github.com/Narquelion/LingTube/blob/main/_docs/screenshots/validate-chunks-1.png)

2. Prompts user to enter initials

![3-validate-chunks.py prompt 2](https://github.com/Narquelion/LingTube/blob/main/_docs/screenshots/validate-chunks-2.png)

3. Allows user to play each audio chunk, which displays the corresponding transcript text, then (a) code the chunk as usable, (b) optionally code the type of issue if unusable, and (c) correct the predicted transcription to match what is heard in the audio clip.

![3-validate-chunks.py prompt 3](https://github.com/Narquelion/LingTube/blob/main/_docs/screenshots/validate-chunks-4.png)

4. Logs progress in a coding log file saved to `chunked_audio/kor/logs/coding`

<!-- Press ‘Play’ to clear all display options\text box and hear the audio clip
Press ‘Repeat’ to only hear the audio clip again, without clearing selections\text
Press ‘Next’ to go to the next clip, which automatically clears selections and plays the clip
If (some parts of) the clip is usable for analysis of English speech sounds, check off the ‘Usable?’ box
Mainly, clear speech with minimal background noise\music, as well as speech in English
If the clip not usable (or it seems usable but has some potential issues), check off all ‘Main Issues’ that apply
For example, music or noise in the background, or other types of sounds interfering with clear speech (see guidelines at lspcheng\GUAva)
In the ‘Transcribe’ text box, fix the predicted transcription to match what is heard, phonetically, in the audio clip.
This can include deleting extra text, adding missing words (including filler words!), or marking notable issues according to the Transcription Guidelines (see guidelines at lspcheng\GUAva)
When finished a session, press ‘Save & Quit’ to save progress and leave the program. -->



<!-- ```
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
``` -->

---
#### 4-create-textgrids.py

This script combines the chunked interval TextGrids from `2-chunk-audio.py` and the usable transcript sections from `3-validate-chunks.py` to create a TextGrid for the full video-length audio file ready for forced alignment. The user can optionally save chunked audio and TextGrids (i.e., per utterance). Additionally, users can optionally copy all relevant audio and textgrid files into a new folder optimized for running forced alignment with the Montreal Forced Aligner.

##### Usage

To create full video-length TextGrids for all files (in a corpus without group structure):

```
python3 youspeak/4-create-textgrids.py
```

To create full-length TextGrids for all files in a group (in a corpus with group structure):

```
python3 youspeak/4-create-textgrids.py --group $group_name
```

To create full video-length TextGrids for a particular channel in a group (in a corpus with group structure):

```
python3 youspeak/4-create-textgrids.py --group $group_name --channel $channel_name
```

To create chunk-length TextGrids for all files in a group:
```
python3 youspeak/4-create-textgrids.py --group $group_name --save_chunks
```

To create video-length TextGrids for all files in a group and copy files to a directory for running the Montreal Forced Aligner:

```
python3 youspeak/4-create-textgrids.py --group $group_name --mfa
```

##### Examples

`python3 youspeak/2-create-textgrids.py -g kor --mfa`

This call:
1. Takes a group name and locates the group folder `kor` under the folder of scraped YouTube audio called `chunked_audio`
2. For each video, adds transcript text to chunked TextGrid for intervals coded as usable (referencing the coding log file).
3. Outputs transcribed video-length TextGrid to `chunked_audio/kor/textgrids/coding`
4. Creates folder structure under `aligned_audio/kor` for running MFA, including an input folder (`original_corpus`), processing folder (`mfa_aligner`), output folder (`aligned_corpus`), and folder for corpus-specific materials like generated pronunciation dictionaries (`trained_models`)
5. Copies TextGrid from `chunked_audio/kor/textgrids/coding` and audio from `raw_audio/kor/.../wav` to  `aligned_audio/kor/original_corpus`

<!-- ```
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
``` -->
