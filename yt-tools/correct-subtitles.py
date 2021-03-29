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
from tkinter.filedialog import askopenfilename
from functools import partial


def open_file_in_editor (file):
    if args.editor == 'textedit':
        subprocess.call(['open', '-a', 'TextEdit', file])
    elif args.editor == 'atom':
        subprocess.call(['open', '-a', 'Atom', file])
    else:
        print('This editor is not available. Please choose an available editor: textedit, atom')

def open_video_and_subtitles (args, logfile, log, display, end_time, complete):
    if i == len(log):
        sys.exit('\nAll videos have been corrected!')
    else:
        row = log.iloc[i]
        timestamp = str(row['corrected'])

        channel = sub(r"[\s\_\-\.\?\!,;:'\"\\\/]+", "", row['author'])
        video_id = '{0}_{1}'.format(channel, row['position'])

        print('\nOpening video {0}: {1} (starting at {2})'.format(i+1, video_id, timestamp))

        # Clear and configure displays
        complete.set(0)
        display.config(text="Current Video: {0}".format(video_id))
        end_time.delete(0, 'end')
        if timestamp == '0':
            end_time.insert(0, '00:00:00')
        else:
            end_time.insert(0, timestamp)

        raw_subtitles_base = path.join('corpus','raw_subtitles')
        if args.group:
            raw_subtitles_base = path.join(raw_subtitles_base, args.group)

        manual_dir = path.join(raw_subtitles_base, "manual", args.language, channel)
        auto_dir = path.join(raw_subtitles_base, "auto", args.language, channel)
        corrected_dir = path.join(raw_subtitles_base, "corrected", args.language, channel)
        if not path.exists(corrected_dir):
            makedirs(corrected_dir)

        # Open .srt file in Text Editor
        subfilename = '{0}.srt'.format(video_id)

        try:
            subfile = path.join(manual_dir, subfilename)
            if path.exists(subfile):
                correctfile = path.join(corrected_dir, subfilename)
                if not path.exists(correctfile):
                    shutil.copyfile(subfile, correctfile)
                open_file_in_editor(correctfile)
            else:
                subfile = path.join(auto_dir, subfilename)
                correctfile = path.join(corrected_dir, subfilename)
                if not path.exists(correctfile):
                    shutil.copyfile(subfile, correctfile)
                open_file_in_editor(correctfile)
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

def save_progress (logfile, log, end_time, complete):
    global i
    if complete.get() == True:
        log.loc[i, 'corrected'] = 1
        log.to_csv(logfile, index=False)
        # display.config(text="Saved completion!"")
    elif match(r'\d+:\d+(:\d+)?', end_time.get()):
        log.loc[i, 'corrected'] = end_time.get()
        log.to_csv(logfile, index=False)
    else:
        print('Error: No time provided or completion not checked.')

def save_and_quit(logfile, log, end_time, complete):
    save_progress (logfile, log, end_time, complete)
    sys.exit('\nSafely saved progress!')

def next_video (args, logfile, log, display, end_time, complete):
    save_progress (logfile, log, end_time, complete)
    global i
    i += 1
    if i >= len(log):
        sys.exit('\nAll videos have been corrected!')
    else:
        print('Next video: {0}'.format(i))
    open_video_and_subtitles (args, logfile, log, display, end_time, complete)


def main (args):

    global i

    # Open log file
    if args.group:
        logfilename = '{0}_log.csv'.format(args.group)
        logfile = path.join('corpus', 'logs', logfilename)
    else:
        logfile = askopenfilename()

    log = pd.read_csv(logfile)

    # If column doesn't exist, initialize
    if not 'corrected' in log.columns:
        log = log.assign(corrected = 0)

    # Check rows in need of correction
    i_list = [(i, row['author'], row['corrected']) for i, row in log.iterrows() if not str(row['corrected']) == '1']
    print('\nNumber of videos remaining: {0}'.format(len(i_list)))
    print(i_list)

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

    display = tk.Label(frame, text="Current Video: {0}".format("None"))
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

    tk.Button(frame, text="   Open   ", command=partial(open_video_and_subtitles, args, logfile, log, display, end_time, complete), bg="grey").grid(row=1, column=0)
    tk.Button(frame, text=" Save Progress ", command=partial(save_progress, logfile, log, end_time, complete), bg="grey").grid(row=1, column=1)
    tk.Button(frame, text= "  Save & Quit  ", command=partial(save_and_quit, logfile, log, end_time, complete), bg="grey").grid(row=1, column=2)
    tk.Button(frame, text="   Next   ", command=partial(next_video, args, logfile, log, display, end_time, complete), bg="grey").grid(row=1, column=3)


    root.mainloop()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create MFA-compatible textgrids and move to MFA alignment folder.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--video', '-v', default=None, type=str, help='video number')
    parser.add_argument('--editor', '-e', default='textedit', type=str, help='preferred text editor')

    args = parser.parse_args()

    main(args)
