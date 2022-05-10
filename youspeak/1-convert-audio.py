#!/usr/bin/env python3

import argparse
from shutil import move
from os import listdir, makedirs, path
from pydub import AudioSegment
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import librosa
from panns_inference import AudioTagging, SoundEventDetection, labels


def init_files(audio_path, sed_dir_path, sed_option):

    # Get name of audio file
    fn = path.splitext(path.split(audio_path)[1])[0]

    out_fig_path = None

    # Create output directories
    if sed_option == "fig":
        if not path.exists(path.join(sed_dir_path, "fig")):
            makedirs(path.join(sed_dir_path, "fig"))
        out_fig_path = path.join(sed_dir_path, 'fig', fn + '_sed_results.png')
    else:
        if not path.exists(sed_dir_path):
            makedirs(sed_dir_path)

    # Create results filepath
    out_fn_path = path.join(sed_dir_path, fn + '_sed_results.csv')

    return out_fn_path, out_fig_path


def run_sed_directories(sed, wav_path, sed_path, ix_to_lb, sed_option):
    print('in ' + wav_path)
    for dir_element in listdir(wav_path):
        if dir_element not in ['README.md', '.DS_Store']:
            run_sed_videos(sed, dir_element, wav_path, sed_path, ix_to_lb, sed_option)


def run_sed_videos(sed, dir_element, wav_path, sed_path, ix_to_lb, sed_option):
    print('in ' + dir_element)
    for fn in listdir(path.join(wav_path, dir_element)):

        video_id = path.splitext(fn)[0]
        sed_files = glob(path.join(sed_path, "*", "*{0}*".format(video_id)), recursive=True)

        if sed_files and not args.overwrite:
            continue

        run_sed_video(sed, fn, video_id, wav_path, sed_path, dir_element, ix_to_lb, sed_option)


def run_sed_video(sed, fn, video_id, wav_path, sed_path, dir_element, ix_to_lb, sed_option):
    print('\nCURRENT VIDEO: {0}'.format(video_id))

    audio_path   = path.join(wav_path, dir_element, fn)
    sed_dir_path = path.join(sed_path, dir_element)

    out_fn_path, out_fig_path = init_files(audio_path, sed_dir_path, sed_option)
    framewise_output = run_sed(sed, audio_path)

    calculate_ratios(framewise_output, ix_to_lb, out_fn_path, out_fig_path, sed_option)


def run_sed(sed, audio_path):

    print('------ Accessing audio ------')
    (audio, _) = librosa.core.load(audio_path, sr=32000, mono=True)

    audio = audio[None, :]  # (batch_size, segment_samples)

    framewise_output = sed.inference(audio)

    return framewise_output


def calculate_ratios(framewise_output, ix_to_lb, out_fn_path, out_fig_path, sed_option):

    frame_arrays = framewise_output[0]

    # Get top classes by max probability
    print('------ Collecting framewise data ------')
    classwise_output = np.max(frame_arrays, axis=0) # get max prob per class
    idxes = np.argsort(classwise_output)[::-1] # get indexes of values sorted by min to max, then reverse so that order is max to min

    # Get probability value per frame for each top X class
    frames = [frame_ix for frame_ix in range(len(frame_arrays))]
    seconds = [f/100 for f in frames[::32]]

    type_lines = []
    ratio_lines = []

    out_df  = pd.DataFrame(seconds, columns=['seconds'])
    temp_df = pd.DataFrame()

    figure, axis = plt.subplots(2, sharex=True, sharey=True, figsize=(10,5))

    # Top 10 category data
    idex_slice = idxes[:10]
    for class_ix in idex_slice:
        class_lb = ix_to_lb[class_ix]
        class_probs = [frame_arrays[frame_ix][class_ix] for frame_ix in frames[::32]]

        # Only save top 10 in CSV
        out_df[class_lb] = class_probs

        if sed_option == "fig": # Plot top 10 categories
            line, = axis[0].plot(seconds, class_probs, label=class_lb, linewidth=0.25)
            type_lines.append(line)

    # Convert all categories
    for class_ix in idxes:
        class_lb = ix_to_lb[class_ix]
        class_probs = [frame_arrays[frame_ix][class_ix] for frame_ix in frames[::32]]
        temp_df[class_lb] = class_probs

    # 0-3: speech/speaking
    # 4-5: conversation/monologue
    # 137-282: music
    # 506-514: room/outdoor noise

    # Speech/music/noise ratios
    classes_speech = [ix_to_lb[i] for i in range(0,6)]
    classes_music  = [ix_to_lb[i] for i in range(137,283)]
    classes_noise  = [ix_to_lb[i] for i in range(66,73)] + [ix_to_lb[i] for i in range(508,527)]

    out_df['speech_ratio'] = temp_df[classes_speech].sum(axis=1) / temp_df.sum(axis=1)
    out_df['music_ratio']  = temp_df[classes_music].sum(axis=1)  / temp_df.sum(axis=1)
    out_df['noise_ratio']  = temp_df[classes_noise].sum(axis=1)  / temp_df.sum(axis=1)

    if sed_option == "fig":
        lines, = axis[1].plot(seconds, out_df['speech_ratio'], label='speech_ratio', linewidth=0.25)
        linem, = axis[1].plot(seconds, out_df['music_ratio'], label='music_ratio', linewidth=0.25)
        linen, = axis[1].plot(seconds, out_df['noise_ratio'], label='noise_ratio', linewidth=0.25)

        ratio_lines.append(lines)
        ratio_lines.append(linem)
        ratio_lines.append(linen)

    # Save full dataframe
    print('------ Saving results ------')
    out_df.loc[:,['seconds', 'speech_ratio', 'music_ratio', 'noise_ratio']].to_csv(out_fn_path, index=False)

    # Save plot
    if sed_option == "fig":
        axis[0].legend(handles=type_lines, loc="upper right")
        axis[1].legend(handles=ratio_lines, loc="lower right")
        plt.xlabel('Seconds')
        plt.ylabel('Probability')
        plt.ylim(0, 1.)
        plt.tight_layout()

        print('Save fig to {}'.format(out_fig_path))
        plt.savefig(out_fig_path, dpi=300)

    plt.clf()


def convert_to_wav (fn, orig_path, wav_path, video_id, mono=False):
    """ Takes an mp4 file and converts it to WAV format.

    :param fn: The mp4 filename (w/ ext)
    :param orig_path: The original path of the mp4 file
    :param wav_path: The output path of the wav file
    :param mono: Boolean for converting sound to mono
    """
    print("Converting {0} to .wav...".format(fn))

    name, ext = path.splitext(fn)
    file_path = path.join(orig_path,  name + ".mp4")
    sound = AudioSegment.from_file(file_path, "mp4")
    if mono == True:
        sound = sound.set_channels(1)

    if not path.exists(wav_path):
        makedirs(wav_path)
    out_file_path = path.join(wav_path, name + ".wav")
    sound.export(out_file_path, format="wav")


def convert_and_move_dir (sed, dir_element, orig_path, wav_path, mp4_path, sed_path, mono, ix_to_lb, sed_option):
    """ Wrapper to convert each mp4 file in a channel folder and
    move the entire folder to a separate directory.

    :param dir_name: An sub-directory name (i.e., channel folders)
    :param orig_path: The original path of the sub-directory
    :param wav_path: The output path of the wav sub-directory
    :param mp4_path: The output path of the mp4 sub-directory
    :param mono: Boolean for converting sound to mono
    """

    print('\nCURRENT CHANNEL: {0}'.format(dir_element))

    orig_dir_path = path.join(orig_path, dir_element)
    wav_dir_path = path.join(wav_path, dir_element)
    sed_dir_path = path.join(sed_path, dir_element)

    for fn in listdir(orig_dir_path):
        video_id, ext = path.splitext(fn)

        if ext == ".mp4":
            convert_to_wav(fn, orig_dir_path, wav_dir_path, video_id, mono)

        if sed:
            wav_path = path.join(wav_dir_path, video_id + ".wav")
            run_sed_video(fn, video_id, wav_path, dir_element, ix_to_lb, sed_option)

    if not path.exists(mp4_path):
        makedirs(mp4_path)

    move(orig_dir_path, mp4_path)


def main(args):

    orig_path = path.join('corpus','raw_audio')

    if args.group:
        orig_path = path.join(orig_path, args.group)

    mp4_path = path.join(orig_path, "mp4")
    wav_path = path.join(orig_path, "wav")
    sed_path = path.join(orig_path, "sed")

    if args.stereo:
        mono = False
    else:
        mono = True # Convert files to mono

    if args.sed:
        device = 'cpu' # 'cuda' | 'cpu'

        print('------ Compiling dictionary ------')
        ix_to_lb = {i : label for i, label in enumerate(labels)}

        print('------ Load sound event detection ------')
        sed = SoundEventDetection(checkpoint_path=None, device=device)
    else:
        ix_to_lb = None
        sed = None

    for dir_element in listdir(orig_path):

        if dir_element not in ['mp4', 'wav', 'sed', '.DS_Store', 'archive']:
            convert_and_move_dir(sed, dir_element, orig_path, wav_path, mp4_path, sed_path, mono, ix_to_lb, args.sed)

    out_message = path.join(wav_path, "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for full audio files (converted to WAV) go here.')

    if args.sed:
        run_sed_directories(sed, wav_path, sed_path, ix_to_lb, args.sed)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format; optionally perform sound event detection to tag for speech, music and noise.')

    parser.set_defaults(func=None)
    parser.add_argument('-g', '--group',  default="ungrouped", type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('-s', '--stereo', action='store_true', default=False, help='keep stereo (separate audio channels); else, convert to mono')
    parser.add_argument('-d', '--sed', default=None, choices = ["csv", "fig"], type=str, help='use machine learning model to detect sound events and output CSV of speech, music and noise data ("csv"), or output CSV with figure of the top sound events and speech, music and noise proportions ("fig")')
    parser.add_argument('-o', '--overwrite', action='store_true', help='overwrite SED results')


    args = parser.parse_args()

    main(args)
