#!/usr/bin/env python3

'''
app to read in and classify chunks of audio

Original by: Meg Cychosz & Ronald Sprouse (UC Berkeley)
Adapted by: Lauretta Cheng (U-M)

'''


try:
    import Tkinter as tk  # Python2
except ImportError:
    import tkinter as tk  # Python3
import pandas as pd
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showinfo
from functools import partial
import sys
import os
import subprocess
import datetime
import argparse

from math import ceil, log10

idx = 0
df = None
row = None
resp_df = None


# Get coding log info
def codinginfo():
    global idx
    global df
    global group
    global video_id
    global channel
    global audiodir
    global outdir
    global outfilename
    global resp_df

    showinfo('Window', "Select a chunking log file")

    fname = askopenfilename()
    basename = os.path.basename(fname)

    video_id = basename.rsplit('_', 2)[0]
    channel = basename.rsplit('_', 3)[0]

    print(video_id)

    basedir = os.path.join("corpus", "chunked_audio")
    if args.group:
        basedir = os.path.join(basedir, args.group)
    print(basedir)

    audiodir = os.path.join(basedir, 'audio', 'chunking', channel, video_id)
    logdir = os.path.join(basedir, 'logs', 'chunking', channel)
    outdir = os.path.join(basedir, 'logs', 'coding', channel)
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    outfilename = video_id+"_coding_responses.csv"

    df = pd.read_csv(fname) # the master config file that won't change

    try:
        resp_df = pd.read_csv(os.path.join(outdir, outfilename)) # if available, open the response df in read mode

    except: # if not, create one
        resp_df = pd.DataFrame(columns=['filename','video_id',
                              'start_time','end_time', 'duration',
                              'id', 'transcription', 'usability', 'bg_music', 'bg_noise', 'other_voice', 'only_music', 'only_noise', 'other_sounds', 'annotator', 'annotate_date_YYYYMMDD']) # add addtl columns, file_name=None,
        resp_df.to_csv(os.path.join(outdir, outfilename), index=False)

    if len(resp_df['id']) > 0:
        idx = resp_df['id'].max() + 1

        if idx > df.index[-1]:
            sys.exit("\nAll audio chunks are validated!")

# Get annotator name/info
def annotatorinfo():
    annotate = tk.Toplevel()
    annotate.title("Annotator information")
    annotateSize = 220

    tk.Label(annotate, text="Enter your name/initials:").grid(row=0)
    name = tk.Entry(annotate)
    def return_name_and_close(annotate):
        global annotator
        annotator = name.get()
        annotate.destroy()
    name.grid(row=0, column=1)

    tk.Button(annotate, text="Enter", command=partial(return_name_and_close, annotate)).grid(row=7,column=1,columnspan=2)

def get_subtitles(args):

    global subtitles

    subtitledir = os.path.join("corpus", "cleaned_subtitles")
    if args.group:
        subtitledir = os.path.join(subtitledir, args.group)
    correct_dir = os.path.join(subtitledir, "corrected")
    manual_dir = os.path.join(subtitledir, "manual")
    auto_dir = os.path.join(subtitledir, "auto")

    if args.language:
        language = args.language
    elif os.path.isdir(correct_dir):
        language_list = os.listdir(correct_dir)
        language = language_list[0]
    elif os.path.isdir(manual_dir):
        language_list = os.listdir(manual_dir)
        language = language_list[0]
    elif os.path.isdir(auto_dir):
        language_list = os.listdir(auto_dir)
        language = language_list[0]

    try:
        subfile = os.path.join(correct_dir, language, "faves", channel, video_id+".txt")

        subtitles = pd.read_table(subfile, names=["sp_code", "speaker", "start_time", "end_time", "transcription"])
    except:
        try:
            subfile = os.path.join(manual_dir, language, "faves", channel, video_id+".txt")

            if not os.path.isfile(subfile):
                subfile = os.path.join(auto_dir, language, "faves", channel, video_id+".txt")

            subtitles = pd.read_table(subfile, names=["sp_code", "speaker", "start_time", "end_time", "transcription"])
        except:
            subtitles = pd.DataFrame()
            print('No transcript file found for this audio file.')

    if not subtitles.empty:
        subtitles['start_time'] = (subtitles['start_time'])*1000
        subtitles['end_time'] = (subtitles['end_time'])*1000


# need to give multiple commands to button below
def combine_funcs(*funcs):
    def combined_func(*args, **kwargs):
        for f in funcs:
            f(*args, **kwargs)
    return combined_func

# clear _category and media selection
def clear():
    usable.set(0)
    bg_music.set(0)
    bg_music.set(0)
    other_voice.set(0)
    only_music.set(0)
    only_noise.set(0)
    other_sounds.set(0)
    transcript.delete("1.0", "end-1c")


def get_transcription (subtitles, row):
    row_timerange = range(row['start_time']-1000, row['end_time']+1000)
    subtitle_match = subtitles[(subtitles["start_time"].isin(row_timerange)) |
                              (subtitles["end_time"].isin(row_timerange))]
    subtitle_text = ' '.join([line for line in subtitle_match["transcription"]])
    return subtitle_text

def insert_transcript (subtitles):
    row = df.iloc[idx]
    pre_row = df.iloc[idx-1]
    subtitle_text = get_transcription(subtitles, row)
    pre_subtitle_text = get_transcription(subtitles, pre_row)

    # TODO: See if can add remaining sections of the previous line to the next line if not there

    if idx > 0:
        matched_words = []
        for pre_i in range(1, 6):
            if not idx-pre_i < 0:
                current_words = subtitle_text.strip().split()
                previous_line = resp_df.iloc[idx-pre_i]['transcription']
                if len(current_words) == 0:
                    subtitle_text = pre_subtitle_text.split(previous_line)[-1].strip()
                    break

                try:
                    preline_words = previous_line.strip().split()
                    preline_words.reverse()
                    preline_max = len(preline_words)-1
                    # print(preline_words)
                    # print(preline_max)

                    for preword_i, word in enumerate(preline_words):
                        if word in current_words:
                            word_i = current_words.index(word)
                            if word_i >= 0:
                                matched_words.append(word)
                                # print(word, word_i, preword_i)
                                if word_i == 0:
                                    matched_words.reverse()
                                    if len(matched_words) > 1:
                                        matched_string = ' '.join(matched_words)+' '
                                    else:
                                        matched_string = matched_words[0]+' '
                                    # print(matched_string)
                                    break
                                elif preword_i == preline_max:
                                    break
                    if word_i == 0:
                        break
                except:
                    break
        try:
            subtitle_text = subtitle_text.split(matched_string, 1)[1]
        except IndexError:
            print('No splitting available.\n')
        except UnboundLocalError:
            print('No words in current line or previous line.\n')
        except:
            print('Error, no trimming.\n')

    print(subtitle_text+'\n')
    transcript.insert("1.0", subtitle_text)


#index and play audio file aloud
def play_audio():

    global row
    global audiofile
    # global subtitles

    row = df.iloc[idx]
    audiofile = os.path.join(audiodir, row['filename'])
    print('\nFile number {0}: {1}\n'.format(idx, row['filename'])) # keep us updated about progress in terminal

    if not subtitles.empty:
        insert_transcript(subtitles)

    subprocess.call(["afplay", audiofile])

def save_coding():

    usability = usable.get() # 0=absent, 1=present
    issue_bg_music = bg_music.get()
    issue_bg_noise = bg_noise.get()
    issue_other_voice = other_voice.get()
    issue_only_music = only_music.get()
    issue_only_noise = only_noise.get()
    issue_other_sounds = other_sounds.get()
    transcription = transcript.get("1.0", "end-1c") # get the transcription
    annotate_date_YYYYMMDD = datetime.datetime.now() # get annotation time
    print('\n{0} + {1}\n{2}\n{3}\n'.format(usability, transcription, annotate_date_YYYYMMDD, annotator)) #, content)

    global row
    global resp_df
    global idx

    annotated_row = pd.DataFrame([row]).assign(id=idx, transcription=transcription, usability=usability, bg_music=issue_bg_music, bg_noise=issue_bg_noise, other_voice=issue_other_voice, only_music=issue_only_music, only_noise=issue_only_noise, other_sounds=issue_other_sounds, annotator=annotator, annotate_date_YYYYMMDD=annotate_date_YYYYMMDD)
    resp_df = resp_df.append(annotated_row, sort=False)
    resp_df.to_csv(os.path.join(outdir, outfilename), index=False)

#go to the next audio file
def next_audio():

    save_coding()

    clear()

    global idx
    idx += 1 # update the global idx

    if idx > df.index[-1]:

        total_min = round((df['duration'].sum()/1000)/60, 2)
        validated_min = round((resp_df['duration'].sum()/1000)/60, 2)
        print('\nValidated {0} min out of {1} min.'.format(validated_min, total_min))

        sys.exit("\nAll audio chunks are validated!")

    play_audio()

def save_and_quit():

    save_coding()

    total_min = ((df['duration'].sum()/1000)/60)
    validated_min = ((resp_df['duration'].sum()/1000)/60)
    print('Validated {0} min out of {1} min'.format(validated_min, total_min))

    sys.exit('\nSafely saved progress!')

def repeat():
    subprocess.call(["afplay", audiofile])


def main(args):
    global usable
    global bg_music
    global bg_noise
    global other_voice
    global only_music
    global only_noise
    global other_sounds
    global mainissue
    global transcript

    root = tk.Tk() # refers to annotation window

    root.update()

    root.title("Categorize")

    frame = tk.Frame(root)
    frame.grid(row=8, column=8, padx=10, pady=10)

    # Row 1
    tk.Button(frame, text="   Play   ", command=combine_funcs(clear, play_audio), bg="grey").grid(row=1, column=1, sticky='E')

    tk.Button(frame, background="grey", text="   Repeat   ", command=repeat).grid(row=1, column=3)

    tk.Button(frame, text="   Next   ", command=next_audio, bg="grey").grid(row=1, column=4)

    tk.Button(frame, text= "   Save & Quit   ", command=save_and_quit, bg="grey").grid(row=1, column=5)

    # Row 2: Place holder whitespace
    tk.Label(frame, text=" ").grid(row = 2, column = 0)
    tk.Label(frame, text=" ").grid(row = 2, column = 1)
    tk.Label(frame, text=" ").grid(row = 2, column = 2)
    tk.Label(frame, text=" ").grid(row = 2, column = 3)
    tk.Label(frame, text=" ").grid(row = 2, column = 4)
    tk.Label(frame, text=" ").grid(row = 2, column = 5)

    # Row 3-4

    tk.Label(frame, text="Usable?").grid(row=3, column=1, sticky='E')
    usable = tk.IntVar()
    tk.Checkbutton(frame, text='Yes', variable=usable).grid(row=3, column=3, sticky='W')

    tk.Label(frame, text="Main Issue(s)").grid(row=4, column=1, sticky='E')

    bg_music = tk.IntVar()
    tk.Checkbutton(frame, text='Speech + music', variable=bg_music).grid(row=4, column=3, sticky='W')
    bg_noise = tk.IntVar()
    tk.Checkbutton(frame, text='Speech + noise', variable=bg_noise).grid(row=4, column=4, sticky='W')
    other_voice = tk.IntVar()
    tk.Checkbutton(frame, text='Other / altered voice', variable=other_voice).grid(row=4, column=5, sticky='W')

    only_music = tk.IntVar()
    tk.Checkbutton(frame, text='Music only', variable=only_music).grid(row=5, column=3, sticky='W')
    only_noise = tk.IntVar()
    tk.Checkbutton(frame, text='Noise only', variable=only_noise).grid(row=5, column=4, sticky='W')
    other_sounds = tk.IntVar()
    tk.Checkbutton(frame, text='Other sounds', variable=other_sounds).grid(row=5, column=5, sticky='W')

    # Row 6
    # Comments, testing
    # tk.Label(frame, text="Comments about clip?").grid(row=25, column=0)

    tk.Label(frame, text="Transcribe: ").grid(row = 8, column = 1)
    transcript = tk.Text(frame,height=7, wrap="word")
    transcript.grid(row=8, column=2, columnspan=4)

    clear()

    codinginfo()

    annotatorinfo()

    get_subtitles(args)

    root.mainloop()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Opens a GUI for categorizing and transcribing audio chunks.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')

    args = parser.parse_args()

    main(args)
