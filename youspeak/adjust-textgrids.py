#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
import shutil
import subprocess
from re import sub
import sys
try:
    import Tkinter as tk  # Python2
except ImportError:
    import tkinter as tk  # Python3
from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename

def main(args):

    mode = 'adjust-alignment'
    if args.review:
        mode = 'review-alignment'

    root = tk.Tk()
    root.withdraw()

    script_path = path.join("resources", "scripts")
    base_script_fp = path.join(script_path, mode+".praat")
    if not path.exists(base_script_fp):
        showinfo('Window', "Go to LingTube > youspeak and select the following file:\n\n{0}.praat".format(mode))
        script_fp = askopenfilename()
        script_fn = path.basename(script_fp)
        if not path.exists(script_path):
            makedirs(script_path)
        shutil.copyfile(script_fp,
                        path.join(script_path, script_fn))

    # base paths
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    # Get file info
    if args.channel:
        channel_list = [args.channel]
    else:
        channel_list = [channel_id for channel_id in listdir(path.join(aligned_audio_base, "original_corpus")) if not channel_id.startswith('.')]

    for channel_id in channel_list:
        original_path = path.join(aligned_audio_base, "original_corpus", channel_id)
        aligned_path = path.join(aligned_audio_base, "aligned_corpus", channel_id)
        adjusted_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id)

        video_list = [video_id for video_id in listdir(original_path) if not video_id.startswith('.')]

        for video_id in video_list:

            tg_path = path.join(aligned_path, video_id)
            audio_path = path.join(adjusted_path, video_id, "queue")

            if not args.review:
                # Move audio files to queue if not already there
                if not len([fn for fn in listdir(audio_path) if not fn.startswith('.')]):
                    for fn in listdir(path.join(original_path, video_id)):
                        if path.splitext(fn)[1]=='.wav':
                            shutil.move(path.join(original_path, video_id, fn),
                                        path.join(audio_path, fn))

            out_audio_path = path.join(adjusted_path, video_id, "audio")
            out_tg_path = path.join(adjusted_path, video_id, "textgrids")

            if args.reset:
                for fn in listdir(out_audio_path):
                    shutil.move(path.join(out_audio_path, fn), path.join(audio_path, fn))
                for fn in listdir(out_tg_path):
                    remove(path.join(out_tg_path, fn))
                continue

            if args.move:
                continue

            video_script_fp = path.join(script_path, '{0}_{1}.praat'.format(mode, video_id))

            # TODO: Add compatability with Windows (use '\')
            path_to_audio = '../{0}/'.format(audio_path)
            path_to_tgs = '../{0}/'.format(tg_path)
            path_to_out_audio = '../{0}/'.format(out_audio_path)
            path_to_out_tgs = '../{0}/'.format(out_tg_path)

            if not path.exists(video_script_fp):
                with open(base_script_fp, "rb") as file:
                    contents = str(file.read(), 'UTF-8')
                    contents = sub("replace_me_with_audpath", path_to_audio, contents)
                    contents = sub("replace_me_with_tgpath", path_to_tgs, contents)
                    contents = sub("replace_me_with_out_audpath", path_to_out_audio, contents)
                    contents = sub("replace_me_with_out_tgpath", path_to_out_tgs, contents)

                with open(video_script_fp, "w") as file:
                    file.write(contents)

            subprocess.run(['open', video_script_fp], check=True)

            print('\nSuccessfully launched Praat for: {0}'.format(video_id))
            print('Run the script in Praat now.')

            print('\nType "next" to move on to the next video. To quit, type "quit".\n')
            next_video = None
            while next_video not in ['next', 'quit']:
                next_video = input()
                remove(video_script_fp)
                if next_video == 'quit':
                    sys.exit('\nSafely quit program!\n')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Open Praat scripts for adjusting force-aligned textgrids.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: adjusted_corpus/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--review', '-r', default=None,  action='store_true', help='run in review mode to check adjusted textgrids')
    parser.add_argument('--move', '-m', default=None,  action='store_true', help='run in move mode to only move sound files to queue')
    parser.add_argument('--reset', default=None,  action='store_true', help='run in reset mode to only clear progress (for testing purposes)')

    args = parser.parse_args()

    main(args)
