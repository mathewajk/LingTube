import argparse
import os
from os import listdir, makedirs, path
import shutil
import subprocess
import re
import sys
from tkinter.messagebox import showinfo
from tkinter.filedialog import askopenfilename

def main(args):

    mode = 'adjust-alignment'
    if args.review:
        mode = 'review-alignment'

    base_script_fp = path.join("scripts", mode+".praat")
    if not path.exists(base_script_fp):
        showinfo('Window', "Go to LingTube > youspeak and select the following file:\n\n{0}.praat".format(mode))
        script_fp = askopenfilename()
        script_fn = path.basename(script_fp)
        if not path.exists("scripts"):
            makedirs("scripts")
        shutil.copyfile(script_fp,
                        path.join("scripts", script_fn))

    # base paths
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    # Get file info
    if args.channel:
        channel_list = [args.channel]
    else:
        channel_list = [channel for channel in listdir(path.join(aligned_audio_base, "original_corpus")) if not channel.startswith('.')]

    for channel in channel_list:
        originalpath = path.join(aligned_audio_base, "original_corpus", channel)
        alignedpath = path.join(aligned_audio_base, "aligned_corpus", channel)
        adjustedpath = path.join(aligned_audio_base, "adjusted_corpus", channel)

        if args.video:
            video_id = '{0}_{1}'.format(channel, args.video)
            video_list = [video_id]
        else:
            video_list = [video_id for video_id in listdir(originalpath) if not video_id.startswith('.')]

        for video_id in video_list:

            tgdir = path.join(alignedpath, video_id)
            auddir = path.join(adjustedpath, video_id, "queue")
            print(len(listdir(auddir)))
            if not len([fn for fn in listdir(auddir) if not fn.startswith('.')]):
                for fn in listdir(path.join(originalpath, video_id)):
                    if path.splitext(fn)[1]=='.wav':
                        shutil.move(path.join(originalpath, video_id, fn),
                                    path.join(auddir, fn))

            out_auddir = path.join(adjustedpath, video_id, "audio")
            out_tgdir = path.join(adjustedpath, video_id, "textgrids")
            if not args.review:
                # Move audio files to queue if not already there
                if not len([fn for fn in listdir(audio_path) if not fn.startswith('.')]):
                    for fn in listdir(path.join(original_path, video_id)):
                        if path.splitext(fn)[1]=='.wav':
                            shutil.move(path.join(original_path, video_id, fn),
                                        path.join(audio_path, fn))

            scriptname = path.join("scripts", 'adjust-alignment_{0}.praat'.format(video_id))
            path_to_auddir = '../{0}/'.format(auddir)
            path_to_tgdir = '../{0}/'.format(tgdir)
            path_to_out_auddir = '../{0}/'.format(out_auddir)
            path_to_out_tgdir = '../{0}/'.format(out_tgdir)

            if not path.exists(scriptname):
                with open(base_script, "rb") as f:
                    contents = str(f.read(), 'UTF-8')
                    contents = re.sub("replace_me_with_audpath", path_to_auddir, contents)
                    contents = re.sub("replace_me_with_tgpath", path_to_tgdir, contents)
                    contents = re.sub("replace_me_with_out_audpath", path_to_out_auddir, contents)
                    contents = re.sub("replace_me_with_out_tgpath", path_to_out_tgdir, contents)

                with open(scriptname, "w") as f:
                    f.write(contents)

                print('\nCreated copy of adjust-alignment.praat for: {0}'.format(video_id))

            subprocess.run(['open', scriptname], check=True)

            print('\nSuccessfully launched Praat for: {0}'.format(video_id))

            print('\nType "next" to move on to the next video. To quit, type "quit".\n')
            next_video = None
            while next_video not in ['next', 'quit']:
                next_video = input()
                if next_video == 'quit':
                    sys.exit('\nSafely quit program!\n')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Open Praat to adjust textgrids.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--review', '-r', default=None,  action='store_true', help='run in review mode to check adjusted textgrids')

    args = parser.parse_args()

    main(args)
