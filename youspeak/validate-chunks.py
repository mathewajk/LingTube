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
from os import sep, path, listdir, makedirs
import subprocess
from pydub import AudioSegment
from pydub.playback import play
import datetime
import argparse

idx = 0
df = None
row = None
resp_df = None


# Get coding log info
def codinginfo(args):
    global idx
    global df
    global group
    global video_id
    global channel_id
    global audio_dir
    global out_dir
    global out_fn
    global resp_df

    group = args.group
    if group:
        showinfo('Window', "Select a chunking log file from a channel folder in:\n\n corpus > chunked_audio > {0} > logs > chunking.".format(group))
    else:
        showinfo('Window', "Select a chunking log file from a channel folder in:\n\n corpus > chunked_audio > logs > chunking.")

    log_fp = askopenfilename()
    if log_fp == '':
        sys.exit('\nNo file selected. Exiting program now.')
    log_fp_parts = path.normpath(log_fp).split(sep)

    if not group:
        if not log_fp_parts[-5] == 'chunked_audio' and log_fp_parts[-6] == 'chunked_audio':
            group = log_fp_parts[-5]
            showinfo('Window', '\nNo group was specified but the following group was detected:\n\n{0}\n\nIf this was not intended, re-start the program and select a new chunking log file.'.format(group))
    else:
        if not log_fp_parts[-5] == group:
            showinfo('Window', "File structure does not match the group that was specified:\n\n{0}\n\nPlease re-start the program and specify the correct group or select an acceptable chunking log file.".format(group))
            sys.exit()
    base_fn = path.basename(log_fp)

    video_id = base_fn.split('_chunking')[0]
    channel_id = video_id.rsplit('_', 1)[0]

    base_dir = path.join("corpus", "chunked_audio")
    if group:
        base_dir = path.join(base_dir, group)

    audio_dir = path.join(base_dir, 'audio', 'chunking', channel_id, video_id)
    log_dir = path.join(base_dir, 'logs', 'chunking', channel_id)
    out_dir = path.join(base_dir, 'logs', 'coding', channel_id)
    if not path.exists(out_dir):
        makedirs(out_dir)
    out_fn = video_id+"_coding_responses.csv"

    df = pd.read_csv(log_fp) # the master config file that won't change

    try:
        resp_df = pd.read_csv(path.join(out_dir, out_fn)) # if available, open the response df in read mode

    except: # if not, create one
        resp_df = pd.DataFrame(columns=['filename','video_id',
                              'start_time','end_time', 'duration',
                              'id', 'transcription', 'usability', 'bg_music', 'bg_noise', 'other_voice', 'only_music', 'only_noise', 'other_sounds', 'annotator', 'annotate_date_YYYYMMDD']) # add addtl columns, file_name=None,
        resp_df.to_csv(path.join(out_dir, out_fn), index=False)

    if len(resp_df['id']) > 0:
        idx = resp_df['id'].max() + 1

        if idx > df.index[-1]:
            sys.exit("\nAll audio chunks are validated!")

# Get annotator name/info
def annotatorinfo():
    annotate = tk.Toplevel()
    annotate.title("Annotator information")
    annotateSize = 220

    global annotator
    annotator = None

    tk.Label(annotate, text="Enter your initials:").grid(row=0)
    name = tk.Entry(annotate)
    def return_name_and_close(annotate):
        global annotator
        annotator = name.get()
        annotate.destroy()
    name.grid(row=0, column=1)

    tk.Button(annotate, text="Enter", command=partial(return_name_and_close, annotate)).grid(row=7,column=1,columnspan=2)

def get_subtitles(args):

    global subtitles

    subtitle_dir = path.join("corpus", "cleaned_subtitles")
    if group:
        subtitle_dir = path.join(subtitle_dir, group)
    correct_dir = path.join(subtitle_dir, "corrected")
    manual_dir = path.join(subtitle_dir, "manual")
    auto_dir = path.join(subtitle_dir, "auto")

    if args.lang_code:
        lang_code = args.lang_code
    elif path.isdir(correct_dir):
        lang_code_list = listdir(correct_dir)
        lang_code = lang_code_list[0]
    elif path.isdir(manual_dir):
        lang_code_list = listdir(manual_dir)
        lang_code = lang_code_list[0]
    elif path.isdir(auto_dir):
        lang_code_list = listdir(auto_dir)
        lang_code = lang_code_list[0]

    try:
        subtitle_fp = path.join(correct_dir, lang_code, "cleans", channel_id, video_id+".txt")

        subtitles = pd.read_table(subtitle_fp, names=["start_time", "end_time", "transcription"])
    except:
        try:
            subtitle_fp = path.join(manual_dir, lang_code, "cleans", channel_id, video_id+".txt")

            if not path.isfile(subtitle_fp):
                subtitle_fp = path.join(auto_dir, lang_code, "cleans", channel_id, video_id+".txt")

            subtitles = pd.read_table(subtitle_fp, names=["start_time", "end_time", "transcription"])
        except:
            subtitles = pd.DataFrame()
            print('No subtitle file found for this audio file.')

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

    if not idx == df.index[-1]:
        post_row = df.iloc[idx+1]
        post_subtitle_text = get_transcription(subtitles, post_row)

    # TODO: See if can add remaining sections of the previous line to the next line if not there

    if idx > 0:
        matched_words = []
        for pre_i in range(1, 6):
            if not idx-pre_i < 0:
                current_words = subtitle_text.strip().split()
                previous_line = resp_df.iloc[idx-pre_i]['transcription']
                if len(current_words) == 0 and previous_line != "":
                    try:
                        subtitle_text = pre_subtitle_text.split(previous_line)[-1].strip()
                    except TypeError:
                        break
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

    if not idx == df.index[-1]:
        subtitle_text = '{0} {1}'.format(subtitle_text, post_subtitle_text.strip())
    print(subtitle_text+'\n')
    transcript.insert("1.0", subtitle_text)


#index and play audio file aloud
def play_audio():

    global row
    global audiofile

    if not annotator:
        sys.exit('\nNo annotator initials provided. Please re-start the program and enter your initials in the "Annotator information" pop-up window.')

    row = df.iloc[idx]
    audiofile = path.join(audio_dir, row['filename'])
    print('\nFile number {0}: {1}\n'.format(idx, row['filename'])) # keep us updated about progress in terminal

    if not subtitles.empty:
        insert_transcript(subtitles)

    try: # MacOS compatible
        subprocess.call(["afplay", audiofile])
    except: # Windows compatible with pydub + simpleaudio
        play(AudioSegment.from_wav(audiofile))

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
    resp_df.to_csv(path.join(out_dir, out_fn), index=False)

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
    try: # MacOS compatible
        subprocess.call(["afplay", audiofile])
    except: # Windows compatible with pydub + simpleaudio
        play(AudioSegment.from_wav(audiofile))


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

    codinginfo(args)

    annotatorinfo()

    get_subtitles(args)

    root.mainloop()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Open a GUI for categorizing and transcribing audio chunks.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: chunked_audio/$group)')
    parser.add_argument('--lang_code', '-l', default=None, type=str, help='open captions with a specific a language code (e.g., "en"); if unspecified, uses first available language code in subtitle directory')

    args = parser.parse_args()

    main(args)
