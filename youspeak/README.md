# YouSpeak Pipeline

Tools for processing audio speech data from YouTube.

*[Note: Currently only compatible with OS and tested on English speech.]*

## Updates
* 04/06/21: All scripts and documentation currently under active development

## Dependencies
*[Note: To be updated]*

The following dependencies are required to run the scripts in this pipeline: `argparse`, `pydub`, `pandas`, `parselmouth`, `tkinter`, `numpy`


## Pipeline Components
*[Note: More details forthcoming!]*

Before using YouSpeak, you should have already (1) downloaded audio and subtitle files (using `scrape-videos.py` in `yt-tools`), and optionally (2) corrected the original captions (using `correct-subtitles.py` in `yt-tools`). YouSpeak is intended to be run in this order:

1. `convert-audio.py`
2. `chunk-audio.py`
3. `clean-captions.py`
4. `validate-chunks.py`
5. `create-textgrids.py`

At this stage, you can run forced alignment using the Montreal Forced Aligner (or other compatible aligner).

6. `adjust-textgrids.py`
6. `get-vowels.py`

## Usage
*[Note: Details forthcoming!]*
