#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
import shutil
import subprocess
from glob import glob
from re import sub
import sys
try:
    import Tkinter as tk  # Python2
except ImportError:
    import tkinter as tk  # Python3
from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename
from functools import partial


def open_praat_script (args, video_info):

    video_id, aligned_path, queue_path, video_path, out_full_fp, out_flag_fp, full_status, flag_status = video_info[i]

    # Initialize video directory
    if not glob(path.join(video_path, "**", "*.TextGrid"), recursive=True):
        instructions.config(text="Initializing directory...")
        for fn in [fn for fn in listdir(queue_path) if not fn.startswith('.')]:
            name, ext = path.splitext(fn)
            shutil.copy(path.join(aligned_path, video_id, name+'.TextGrid'),
                    path.join(queue_path, name+'.TextGrid'))
    if not (path.exists(out_full_fp) and path.exists(out_flag_fp)):
        with open(out_full_fp, "w") as full_file, open(out_flag_fp, "w") as flag_file:
            print('\nInitialized directory for: {0}'.format(video_id))

    # Start regular process
    global video_script_fp
    video_script_fp = path.join(video_path, '{0}_{1}.praat'.format(mode, video_id))

    path_to_queue = path.join("queue", "").encode('unicode_escape').decode()
    path_to_out_tgs = path.join("textgrids", "").encode('unicode_escape').decode()
    path_to_out_audio = path.join("audio", "").encode('unicode_escape').decode()

    if args.review:
        review_category = review_type.get()
        if review_category == 'Full' and full_status == 0:
            instructions.config(text="No files to be reviewed in: Full")
            return 0
        elif review_category == 'Flagged' and flag_status == 0:
            instructions.config(text="No files to be reviewed in: Flagged")
            return 0

    if path.exists(video_script_fp):
        remove(video_script_fp)

    with open(base_script_fp, "rb") as file:
        # print('\nOpened file '+base_script_fp)
        contents = str(file.read(), 'UTF-8')
        contents = sub(r"replace_me_with_audpath", (path_to_queue), contents)
        contents = sub(r"replace_me_with_tgpath", (path_to_queue), contents)
        contents = sub(r"replace_me_with_out_audpath", (path_to_out_audio), contents)
        contents = sub(r"replace_me_with_out_tgpath", (path_to_out_tgs), contents)
        contents = sub(r"replace_me_with_out_listpath", "", contents)
        if args.review:
            if review_category == 'Flagged':
                contents = sub(r"replace_me_with_out_file", r'flagged-review.txt', contents)
            else:
                contents = sub(r"replace_me_with_out_file", r'full-review.txt', contents)

    with open(video_script_fp, "w") as file:
        file.write(contents)
        # print('Created file '+video_script_fp)

    try:
        subprocess.run(['open', video_script_fp], check=True)
    except FileNotFoundError:
        try:
            # print('Using subprocess.Popen')
            subprocess.Popen(['praat', video_script_fp], shell=True)
        except:
            print('Failed to open script in Praat')

    print('\nLaunched: {0}. {1}'.format(i, video_id))

    instructions.config(text="Ready! Run the script in Praat now.")

def next_video (args, video_info):
    global i

    try:
        remove(video_script_fp)
    except FileNotFoundError:
        print('\nSkipped: {0}. {1}'.format(i, video_info[i][0]))
    except NameError:
        print('\nSkipped: {0}. {1}'.format(i, video_info[i][0]))

    i += 1

    if i >= len(video_info):
        sys.exit('\nNo more videos to process in {0} mode.'.format(mode))

    display.config(text="{0}: {1}".format(video_info[i][0].split('_')[0], video_info[i][0].split('_')[2]))
    if args.review:
        review_type.set("Full")
        instructions.config(text="Select review type: 'Full' or 'Flagged'.\nThen, click 'Open' to start.")
    else:
        instructions.config(text="Click 'Open' to start.")

def quit_program ():
    try:
        remove(video_script_fp)
    except:
        pass
    sys.exit('\nSafely quit program!\n')

def main(args):

    global mode
    global script_path
    global base_script_fp

    mode = 'adjust-alignment'
    if args.review:
        mode = 'review-alignment'

    if args.reset:
        print('\n------ RESET MODE ---------')
        print('\n**WARNING: This is a destructive operation. All progress will be lost.**')

    root = tk.Tk()
    root.withdraw()

    script_path = path.join("resources", "scripts")
    base_script_fp = path.join(script_path, mode+".praat")
    if not path.exists(base_script_fp):
        showinfo('Window', "Go to LingTube > youspeak > praat. Select the following file:\n\n{0}.praat".format(mode))
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

    video_info = []
    for channel_id in channel_list:
        original_path = path.join(aligned_audio_base, "original_corpus", channel_id)
        aligned_path = path.join(aligned_audio_base, "aligned_corpus", channel_id)
        adjusted_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id)

        video_list = [video_id for video_id in listdir(original_path) if not video_id.startswith('.')]

        for video_id in video_list:

            queue_path = path.join(adjusted_path, video_id, "queue")
            out_audio_path = path.join(adjusted_path, video_id, "audio")
            out_tg_path = path.join(adjusted_path, video_id, "textgrids")

            video_path = path.join(adjusted_path, video_id)
            out_full_fp = path.join(video_path,  "full-review.txt")
            out_flag_fp = path.join(video_path, "flagged-review.txt")

            full_status = 0
            flag_status = 0

            if not args.review:
                # Move files to queue if both queue and outdir are empty
                if not len([fn for fn in listdir(queue_path) if not fn.startswith('.')]) and not len([fn for fn in listdir(out_audio_path) if not fn.startswith('.')]):
                    for fn in listdir(path.join(original_path, video_id)):
                        name, ext = path.splitext(fn)
                        if ext =='.wav':
                            shutil.move(path.join(original_path, video_id, fn),
                                        path.join(queue_path, fn))
                    print("Moved aligned files to queue for: {0}".format(video_id))

                # Move all files in outdir back to queue (i.e,, regardless of status, revert to full queue, empty outdir)
                if args.reset:
                    print("\nReset files back to queue and delete review files for:\n\n{0}? (y/n)".format(video_id))
                    reset_files = None
                    while reset_files not in ['y', 'n']:
                        reset_files = input()
                    if reset_files == 'y':
                        for fn in listdir(out_audio_path):
                            shutil.move(path.join(out_audio_path, fn), path.join(queue_path, fn))
                        for fn in listdir(out_tg_path):
                            if path.splitext(fn)[-1] == '.TextGrid':
                                remove(path.join(out_tg_path, fn))
                        for fn in listdir(queue_path):
                            if path.splitext(fn)[-1] == '.TextGrid':
                                remove(path.join(queue_path, fn))
                        try:
                            remove(out_full_fp)
                        except:
                            pass
                        try:
                            remove(out_flag_fp)
                        except:
                            pass
                        print('Reset complete!')
                    else:
                        print('No reset.')
                    print('\n----------------------------')

                # Skip adding video to list if in adjust mode when queue is empty but outdir is full (not empty)
                if not len([fn for fn in listdir(queue_path) if not fn.startswith('.')]) and len([fn for fn in listdir(out_audio_path) if not fn.startswith('.')]):
                    continue

            elif args.review:
                if args.reset:
                    print('No resetting available when in review mode.')
                if path.exists(out_full_fp) and path.exists(out_flag_fp):
                    with open(out_full_fp, "r") as full_file, open(out_flag_fp, "r") as flag_file:
                        if len(full_file.read()):
                            full_status = 1
                        if len(flag_file.read()):
                            flag_status = 1

                # Skip adding video to list in review mode if both review list files are empty
                if full_status == 0 and flag_status == 0:
                    continue

            video_info.append((video_id, aligned_path,  queue_path, video_path, out_full_fp, out_flag_fp, full_status, flag_status))

    # If all files are completed, exit program
    if len(video_info) == 0:
        sys.exit('\nNo more videos to process in {0} mode.'.format(mode))
    else:
        print('\nNumber of videos remaining: {0}'.format(len(video_info)))
        for idx, info in enumerate(video_info):
            print('{0}. {1}'.format(idx, info[0]))

        global i
        i = 0


    # Pop-up Window
    root.deiconify()
    root.update()
    root.title("Adjust TextGrids")
    frame = tk.Frame(root)
    frame.grid(row=8, column=8, padx=10, pady=10)

    global display
    display = tk.Label(frame, text="")
    display.grid(row=0, column=0, columnspan=3)
    display.config(text="{0}: {1}".format(video_info[i][0].split('_')[0], video_info[i][0].split('_')[2]))

    tk.Button(frame, text= "  Quit  ", command=quit_program, bg="grey").grid(row=1, column=0)
    tk.Button(frame, text="   Open   ", command=partial(open_praat_script, args, video_info), bg="grey").grid(row=1, column=1)
    tk.Button(frame, text="   Next   ", command=partial(next_video, args, video_info), bg="grey").grid(row=1, column=2)

    if args.review:
        global review_type
        # tk.Label(frame, text="Review Type: ").grid(row = 2, column = 0)
        review_type = tk.StringVar()
        review_choices = {"Full", "Flagged"}
        review_type.set("Full")
        dropdown = tk.OptionMenu(frame, review_type, *review_choices)
        dropdown.grid(row=2, column=1, columnspan=1, sticky='S')

    # tk.Label(frame, text="...").grid(row = 3, column = 0, columnspan=3)

    global instructions
    instructions = tk.Label(frame, text="")
    instructions.grid(row=4, column=0, columnspan=3)
    if args.review:
        instructions.config(text="Select review type: 'Full' or 'Flagged'.\nThen, click 'Open' to start.")
    else:
        instructions.config(text="Click 'Open' to start.")

    root.mainloop()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Open Praat scripts for adjusting and reviewing force-aligned textgrids.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: adjusted_corpus/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--review', '-r', default=None,  action='store_true', help='run in review mode to check adjusted textgrids')
    parser.add_argument('--reset', default=None,  action='store_true', help='run in reset mode to only clear progress (for testing purposes)')

    args = parser.parse_args()

    main(args)
