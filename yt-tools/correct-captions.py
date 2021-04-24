#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path
import pandas as pd
import shutil
from re import sub, match
import sys
import webbrowser
import subprocess

try:
    import Tkinter as tk  # Python2
except ImportError:
    import tkinter as tk  # Python3
from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename
from functools import partial


def open_file_in_editor (file):
    if args.editor == 'textedit':
        subprocess.call(['open', '-a', 'TextEdit', file])
    elif args.editor == 'atom':
        subprocess.call(['open', '-a', 'Atom', file])
    else:
        print('This editor is not available. Please choose an available editor: textedit, atom')

def open_video_and_subtitles (args, log_fp, log, display, end_time, complete):
    if i == len(log):
        sys.exit('\nAll videos have been corrected!')
    else:
        row = log.iloc[i]
        timestamp = str(row['corrected'])

        channel_id = "{0}_{1}".format(row['name'], row['ID'])
        video_id = '{0}_{1}'.format(channel_id, row['yt_id'])

        print('\nOpening video {0}: {1} (starting at {2})'.format(i, video_id, timestamp))

        # Clear and configure displays
        complete.set(0)
        display.config(text="Channel: {0}\tCurrent Video: {1}".format(row['name'], row['yt_id']))
        end_time.delete(0, 'end')
        if timestamp == '0':
            end_time.insert(0, '00:00:00')
        else:
            end_time.insert(0, timestamp)

        raw_subtitles_base = path.join('corpus','raw_subtitles')
        if args.group:
            raw_subtitles_base = path.join(raw_subtitles_base, args.group)

        if args.language:
            language = args.language
        elif path.isdir(path.join(raw_subtitles_base, "manual")):
            language_list = listdir(path.join(raw_subtitles_base, "manual"))
            language = language_list[0]
        elif path.isdir(path.join(raw_subtitles_base, "auto")):
            language_list = listdir(path.join(raw_subtitles_base, "auto"))
            language = language_list[0]

        manual_dir = path.join(raw_subtitles_base, "manual", language, channel_id)
        print(manual_dir)
        auto_dir = path.join(raw_subtitles_base, "auto", language, channel_id)
        corrected_dir = path.join(raw_subtitles_base, "corrected", language, channel_id)
        if not path.exists(corrected_dir):
            makedirs(corrected_dir)

        # Open .srt file in Text Editor
        sub_fn = '{0}.srt'.format(video_id)

        try:
            sub_fp = path.join(manual_dir, sub_fn)
            if path.exists(sub_fp):
                corrected_fp = path.join(corrected_dir, sub_fn)
                if not path.exists(corrected_fp):
                    shutil.copyfile(sub_fp, corrected_fp)
                open_file_in_editor(corrected_fp)
            else:
                sub_fp = path.join(auto_dir, sub_fn)
                corrected_fp = path.join(corrected_dir, sub_fn)
                if not path.exists(corrected_fp):
                    shutil.copyfile(sub_fp, corrected_fp)
                open_file_in_editor(corrected_fp)
        except FileNotFoundError:
            print('File does not exist.')

        # Open YouTube video in web browser
        if not timestamp == '0':
            times = timestamp.split(':')
            if len(times) == 3:
                timestamp = int(times[0])*3600 + int(times[1])*60 + int(times[2])
            else:
                timestamp = int(times[0])*60 + int(times[1])

        url = '{0}&t={1}'.format(row['url'], timestamp)
        try:
            webbrowser.open_new(url)
        except:
            print('Could not open URL in browser.')

def save_progress (log_fp, log, end_time, complete):
    global i
    if complete.get() == True:
        log.loc[i, 'corrected'] = 1
        log.to_csv(log_fp, index=False)
        # display.config(text="Saved completion!"")
    elif match(r'\d+:\d+(:\d+)?', end_time.get()):
        log.loc[i, 'corrected'] = end_time.get()
        log.to_csv(log_fp, index=False)
    else:
        print('Error: No time provided or completion not checked.')

def save_and_quit(log_fp, log, end_time, complete):
    save_progress (log_fp, log, end_time, complete)
    sys.exit('\nSafely saved progress!')

def next_video (args, log_fp, log, display, end_time, complete):
    save_progress (log_fp, log, end_time, complete)
    global i
    i += 1
    if args.group and args.channel:
        while not log.iloc[i]['name'] == args.channel.split('_')[0]:
            i += 1
            if i >= len(log):
                break
    if i >= len(log):
        sys.exit('\nAll videos have been corrected!')
    else:
        print('Next video: {0}'.format(i))
    open_video_and_subtitles (args, log_fp, log, display, end_time, complete)


def main (args):

    global i

    # Open log file
    if args.group:
        showinfo('Window', "Opening log file for group: {0}".format(args.group))
        log_fn = '{0}_log.csv'.format(args.group)
        log_fp = path.join('corpus', 'logs', log_fn)
    elif args.channel:
        showinfo('Window', "Opening log file for channel: {0}".format(args.channel))
        log_fn = '{0}_log.csv'.format(args.channel)
        log_fp = path.join('corpus', 'logs', log_fn)
    else:
        showinfo('Window', "No group was specified. Select a channel log file from corpus > logs.")
        log_fp = askopenfilename()
        if log_fp == '':
            sys.exit('No file selected. Exiting program now.')

    log = pd.read_csv(log_fp)

    # If column doesn't exist, initialize
    if not 'corrected' in log.columns:
        log = log.assign(corrected = 0)

    # Check rows in need of correction
    i_list = [(i, row['name'], row['yt_id'], row['corrected']) for i, row in log.iterrows() if not str(row['corrected']) == '1']

    if args.group and args.channel:
        i_list = [item for item in i_list if item[1] == args.channel.split('_')[0]]

    print('\nNumber of videos remaining: {0}'.format(len(i_list)))
    for item in i_list:
        print("{0}. {1}: {2} ({3})".format(item[0], item[1], item[2], item[3]))

    # If all files are completed, exit program
    if len(i_list) == 0:
        sys.exit('\nAll videos have been corrected!')
    else:
        i = i_list[0][0]

    # Pop-up Window
    root = tk.Tk()
    root.update()
    root.title("Correct Subtitles")
    frame = tk.Frame(root)
    frame.grid(row=8, column=8, padx=10, pady=10)

    display = tk.Label(frame, text="Channel: {0}\tCurrent Video: {1}".format("None", "None"))
    display.grid(row=0, column=1, columnspan=2)

    tk.Label(frame, text="Leaving off at time:").grid(row=3, column=1)
    end_time = tk.Entry(frame, width=8)
    end_time.delete(0, 'end')
    end_time.insert(0, '00:00:00')
    end_time.grid(row=3, column=2, columnspan=1)

    # Completion checkbox
    tk.Label(frame, text="Complete?").grid(row=4, column=1)
    complete = tk.IntVar()
    tk.Checkbutton(frame, text='Yes', variable=complete, onvalue=1, offvalue=0).grid(row=4, column=2)

    tk.Button(frame, text="   Open   ", command=partial(open_video_and_subtitles, args, log_fp, log, display, end_time, complete), bg="grey").grid(row=1, column=0)
    tk.Button(frame, text=" Save Progress ", command=partial(save_progress, log_fp, log, end_time, complete), bg="grey").grid(row=1, column=1)
    tk.Button(frame, text= "  Save & Quit  ", command=partial(save_and_quit, log_fp, log, end_time, complete), bg="grey").grid(row=1, column=2)
    tk.Button(frame, text="   Next   ", command=partial(next_video, args, log_fp, log, display, end_time, complete), bg="grey").grid(row=1, column=3)


    root.mainloop()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Open text file and YouTube video to aid in correcting captions.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--editor', '-e', default='textedit', type=str, help='preferred text editor')

    args = parser.parse_args()

    main(args)
