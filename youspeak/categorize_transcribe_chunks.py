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
import threading
import subprocess
import datetime
import argparse

from math import ceil, log10

idx = 0
df = None
row = None
resp_df = None


# get initial info about annotator
def annotatorinfo():
    global idx
    global df
    global group
    global video_id
    global channel
    global audiodir
    global outdir
    global outfilename
    global resp_df

    showinfo('Window', "Select a metadata file")

    fname = askopenfilename()
    basename = os.path.basename(fname)

    video_id = basename.rsplit('_', 2)[0]
    channel = basename.rsplit('_', 3)[0]
    group = args.group

    print(video_id)

    basedir = os.path.join("corpus", "chunked_audio", group)

    audiodir = os.path.join(basedir, 'audio', 'chunking', channel, video_id)
    logdir = os.path.join(basedir, 'log', 'chunking', channel)
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
                              'id', 'quality', 'unusable_type', 'transcription', 'annotate_date_YYYYMMDD']) # add addtl columns, file_name=None,
        resp_df.to_csv(os.path.join(outdir, outfilename), index=False)

    if len(resp_df['id']) > 0:
        idx = resp_df['id'].max() + 1

    # Annotator name/info
    # TODO: Combine with the original pop-up Window

    # annotate = tk.Toplevel()
    # annotate.title("Annotator information")
    # annotateSize = 220
    #
    # def close_window(annotate):
    #     annotate.destroy()
    #
    # tk.Label(annotate, text="What is your name?").grid(row=0)
    # name = tk.Entry(annotate)
    # def return_name():
    #     global content
    #     content = name.get()
    # name.grid(row=0, column=1)
    #
    #
    # tk.Button(annotate, text="Enter", command=combine_funcs(return_name, partial(close_window, annotate))).grid(row=7,column=1,columnspan=2)



def get_subtitles(args):

    global subtitles

    subtitledir = os.path.join("corpus", "cleaned_subtitles", group)
    try:
        subfile = os.path.join(subtitledir, "manual", args.language, "faves", "corrected", channel, video_id+".txt")

        if not os.path.isfile(subfile):
            subfile = os.path.join(subtitledir, "manual", args.language, "faves", "uncorrected", channel, video_id+".txt")

        subtitles = pd.read_table(subfile, names=["sp_code", "speaker", "start_time", "end_time", "transcription"])
    except:
        try:
            subfile = os.path.join(subtitledir, "auto", args.language, "faves", "corrected", channel, video_id+".txt")

            if not os.path.isfile(subfile):
                subfile = os.path.join(subtitledir, "auto", args.language, "faves", "uncorrected", channel, video_id+".txt")

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
    # mediacat.set(0)
    quality_category.set("0 none")
    unusable_category.set("0 none")
    # topic_category.set("Categorize topic")
    transcript.delete("1.0", "end-1c")

def insert_transcript(subtitles):
    row_timerange = range(row['start_time']-1000, row['end_time']+1000)

    subtitle_match = subtitles[(subtitles["start_time"].isin(row_timerange)) |
                              (subtitles["end_time"].isin(row_timerange))]
    subtitle_text = ' '.join([line for line in subtitle_match["transcription"]])

    # TODO: See if can slice out overlapping parts of the previous transcript from the next line (plus maybe remaining sections of the previous line)

    if idx > 0:
        matched_words = []
        for pre_i in range(1, 4):
            if not idx-pre_i < 0:
                current_words = subtitle_text.strip().split()
                if len(current_words) == 0:
                    break

                previous_line = resp_df.iloc[idx-pre_i]['transcription']

                try:
                    preline_words = previous_line.strip().split()
                    preline_words.reverse()
                    preline_max = len(preline_words)-1
                    print(preline_words)
                    print(preline_max)

                    for preword_i, word in enumerate(preline_words):
                        if word in current_words:
                            word_i = current_words.index(word)
                            if word_i >= 0:
                                matched_words.append(word)
                                print(word, word_i, preword_i)
                                if word_i == 0:
                                    matched_words.reverse()
                                    if len(matched_words) > 1:
                                        matched_string = ' '.join(matched_words)+' '
                                    else:
                                        matched_string = matched_words[0]+' '
                                    print(matched_string)
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
            print('No splitting available.')
        except UnboundLocalError:
            print('No words in current line or previous line.')
        except:
            print('Error, no trimming.')

    print(subtitle_text+'\n')
    transcript.insert("1.0", subtitle_text)


#index and play audio file aloud
def play_audio():

    global row
    global audiofile
    # global subtitles

    row = df.iloc[idx]
    audiofile = os.path.join(audiodir, row['filename'])
    print(idx, row['filename']) # keep us updated about progress in terminal

    if not subtitles.empty:
        insert_transcript(subtitles)

    # t1 = threading.Thread(subprocess.call(["play", audiofile]))
    # t1.start()

    subprocess.call(["play", audiofile])

def save_coding():

    quality = quality_category.get() # get the quality classification
    unusable_type = unusable_category.get() # get the unusable classification
    # topic = topic_category.get() # get the topic classification
    # media = mediacat.get() # 0=absent, 1=present
    transcription = transcript.get("1.0", "end-1c") # get the transcription
    annotate_date_YYYYMMDD = datetime.datetime.now() # get current annotation time
    print(quality, unusable_type, transcription, annotate_date_YYYYMMDD) #, content)

    global row
    global resp_df
    global idx

    annotated_row = pd.DataFrame([row]).assign(id=idx, quality=quality, unusable_type=unusable_type, transcription=transcription, annotate_date_YYYYMMDD=annotate_date_YYYYMMDD) #, annotator=content)
    resp_df = resp_df.append(annotated_row, sort=False)
    resp_df.to_csv(os.path.join(outdir, outfilename), index=False)

#go to the next audio file
def next_audio():

    save_coding()

    clear()

    global idx
    idx += 1 # update the global idx
    # print('File #: '.format(idx))

    play_audio()

def save_and_quit():

    save_coding()

    sys.exit('Safely saved progress!')

def repeat():
    subprocess.call(["play", audiofile])


def main(args):
    global quality_category
    global unusable_category
    # global topic_category
    # global mediacat
    global transcript

    root = tk.Tk() # refers to annotation window

    root.update()

    root.title("Categorize")

    frame = tk.Frame(root)
    frame.grid(row=8, column=8, padx=10, pady=10)

    # Row 1
    # tk.Button(frame, text="   Clear   ", command=clear, bg="grey").grid(row=1, column=0)

    tk.Button(frame, text="   Play   ", command=combine_funcs(clear, play_audio), bg="grey").grid(row=1, column=0)

    tk.Button(frame, background="grey", text="   Repeat   ", command=repeat).grid(row=1, column=1)

    tk.Button(frame, text="   Next   ", command=next_audio, bg="grey").grid(row=1, column=2)

    tk.Button(frame, text= "Save & Quit", command=save_and_quit, bg="grey").grid(row=1, column=3)

    # Row 2: Place holder whitespace
    tk.Label(frame, text=" ").grid(row = 2, column = 1)
    tk.Label(frame, text=" ").grid(row = 2, column = 2)
    tk.Label(frame, text=" ").grid(row = 2, column = 3)
    tk.Label(frame, text=" ").grid(row = 2, column = 4)
    tk.Label(frame, text=" ").grid(row = 2, column = 5)

    # Row 3-4
    quality_category = tk.StringVar()
    unusable_category = tk.StringVar()
    # topic_category = tk.StringVar()

    quality_choices = ("0 none","1 usable (speech only)", "2 unusable (other stuff, see below)", "3 partial (some unusable parts)")
    unusable_choices = ("0 none","1 music only", "2 music in background", "3 noise in background", "4 sound effects", "5 other speakers or altered voices (e.g., pitch, speed)", "6 other human vocal sounds (e.g., breaths, laughs, coughs, cut-off word)", "7 other non-human sounds (e.g., memes, city noises)", "8 multiple")
    # topic_choices = ("1 neutral", "2 personal", "3 ethnicity", "4 location/region")

    popupMenu = tk.OptionMenu(frame, quality_category, *quality_choices)
    popupMenu2 = tk.OptionMenu(frame, unusable_category, *unusable_choices)
    # popupMenu2 = tk.OptionMenu(frame, topic_category, *topic_choices)

    popupMenu.grid(row=3, column=1, columnspan=2)
    popupMenu2.grid(row=4, column=1, columnspan=2)

    tk.Label(frame, text="Quality: ").grid(row = 3, column = 0)
    tk.Label(frame, text="Unusable Type: ").grid(row = 4, column = 0)
    # tk.Label(frame, text="Topic: ").grid(row = 4, column = 0)

    # Row 6
    # Comments, testing
    # tk.Label(frame, font=fontStyle, text="Comments about clip?").grid(row=25, column=0)

    transcript = tk.Text(frame,height=5, wrap="word")
    transcript.grid(row=6, column=1, columnspan=3)

    tk.Label(frame, text="Transcribe: ").grid(row = 6, column = 0)
    # testing

    # Placeholder greyspace border
    # tk.Label(root, text=" ").grid(row=8, column=8)

    # Row 8
    # Media checkbox
    # tk.Label(root, text="Media?").grid(row=8, column=4)
    # mediacat = tk.IntVar()
    # tk.Checkbutton(root, text='Yes', variable=mediacat).grid(row=12, column=9)

    clear()

    app = annotatorinfo()

    get_subtitles(args)

    root.mainloop()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Opens a GUI for categorizing and transcribing audio chunks.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')

    args = parser.parse_args()

    main(args)
