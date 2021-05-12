# YouSpeak Pipeline

Tools for processing audio speech data from YouTube.

*[Note: Currently only tested on MacOS and English speech.]*

## Updates
* 04/06/21: All scripts and documentation currently under active development

## Dependencies

Most dependencies are provided in the `requirements/` folder. To install, from the LingTube main directory, run

`pip install -r requirements/youspeak.txt`

For the scripts that rely on [pydub](https://github.com/jiaaro/pydub), you will also need to download `ffmpeg` separately, following the instructions [here](https://github.com/jiaaro/pydub#getting-ffmpeg-set-up).  If you are on MacOS and using Homebrew, you can run

`brew install ffmpeg`

For the scripts requiring `parselmouth-praat`, the Praat application is required. It can be downloaded from the [Praat website](https://www.fon.hum.uva.nl/praat/).  If you are on MacOS and using Homebrew, simply run

`brew install --cask praat`

## Pipeline Components
*[Note: More details forthcoming!]*

Before using YouSpeak, you should have already (1) downloaded audio and caption files (using `scrape-videos.py` in `yt-tools`). You may have also (2) corrected the original captions (using `correct-captions.py` in `text-tools`), but that can also be done concurrently. YouSpeak is intended to be run in this order:

1. [`convert-audio.py`](#convert-audio.py)
2. [`chunk-audio.py`](#chunk-audio.py)
3. [`clean-captions.py`](#clean-captions.py)
4. [`validate-chunks.py`](#validate-chunks.py)
5. [`create-textgrids.py`](#create-textgrids.py)

At this stage, you can run forced alignment using the Montreal Forced Aligner (or other compatible aligner).

6. [`adjust-textgrids.py`](#adjust-textgrids.py)
7. [`get-vowels.py`](#get-vowels.py)

### convert-audio.py

#### Usage

```
usage: convert-audio.py [-h] [--group GROUP]

Convert scraped YouTube audio from mp4 to WAV format.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: raw_audio/$group)
```

### chunk-audio.py

#### Usage
```
usage: chunk-audio.py [-h] [--group GROUP] [--overwrite]

Chunk WAV audio files into short segments of sound.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: raw_subtitles/$group)
  --overwrite, -o       overwrite files rather than appending
```

### clean-captions.py
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


### validate-chunks.py
#### Usage
```
usage: validate-chunks.py [-h] [--group GROUP] [--lang_code LANG_CODE]

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

### create-textgrids.py
#### Usage
```
usage: create-textgrids.py [-h] [--group GROUP] [--channel CHANNEL]
                           [--overwrite]

Create MFA-compatible textgrids and move to MFA alignment folder.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: aligned_audio/$group)
  --channel CHANNEL, -ch CHANNEL
                        run on files for a specific channel name; if
                        unspecified, goes through all channels in order
  --overwrite, -o       overwrite files rather than appending
```
### adjust-textgrids.py
#### Usage
```
usage: adjust-textgrids.py [-h] [--group GROUP] [--channel CHANNEL] [--review]

Open Praat scripts for adjusting force-aligned textgrids.

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: adjusted_corpus/$group)
  --channel CHANNEL, -ch CHANNEL
                        run on files for a specific channel name; if
                        unspecified, goes through all channels in order
  --review, -r          run in review mode to check adjusted textgrids
```

### get-vowels.py
#### Usage
```
usage: get-vowels.py [-h] [--group GROUP] [--channel CHANNEL]
                     [--vowels VOWELS] [--stress STRESS] [--nucleus] [--onoff]
                     [--steps] [--formants FORMANTS]

Get duration and formants from aligned audio chunks and textgrids
(default=only duration).

optional arguments:
  -h, --help            show this help message and exit
  --group GROUP, -g GROUP
                        name to group files under (create and /or assume files
                        are located in a subfolder: raw_audio/$group)
  --channel CHANNEL, -ch CHANNEL
                        run on files for a specific channel name; if
                        unspecified, goes through all channels in order
  --vowels VOWELS, -vw VOWELS
                        list of vowels to target, comma-separated
  --stress STRESS, -st STRESS
                        list of stress values to target, comma-separated
  --nucleus, -n         extract nucleus midpoint formants
  --onoff, -o           extract onset and offset formants
  --steps, -s           extract formants at 30 steps
  --formants FORMANTS, -f FORMANTS
                        maximum number of formants to extract (default=3)
```
