#!/usr/bin/env python3

import argparse
from shutil import move
from os import listdir, makedirs, path
from pydub import AudioSegment

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import librosa
from panns_inference import AudioTagging, SoundEventDetection, labels


def detect_speech(audio_path, orig_path):

        # Get index to label dictionary
        print('------ Compiling dictionary ------')
        ix_to_lb = {i : label for i, label in enumerate(labels)}

        # Run SED for audio file
        print('------ Accessing audio ------')
        fn = path.splitext(path.split(audio_path)[1])[0]
        device = 'cpu' # 'cuda' | 'cpu'

        # Prep files
        if not path.exists(path.join(orig_path, "sed", "fig")):
            makedirs(path.join(orig_path, "sed", "fig"))

        out_fn_path = path.join(orig_path, "sed", fn+'_sed_results.csv')
        out_fig_path = path.join(orig_path, "sed", 'fig', fn+'_sed_results.png')

        # TODO: get audio length in seconds

        (audio, _) = librosa.core.load(audio_path, sr=32000, mono=True)
        # duration = librosa.get_duration(y=audio, sr=32000)
        audio = audio[None, :]  # (batch_size, segment_samples)

        print('------ Sound event detection ------')
        sed = SoundEventDetection(checkpoint_path=None, device=device)
        framewise_output = sed.inference(audio)
        frame_arrays = framewise_output[0]

        # Get top classes by max probability
        print('------ Collecting framewise data ------')
        classwise_output = np.max(frame_arrays, axis=0) # get max prob per class
        idxes = np.argsort(classwise_output)[::-1] # get indexes of values sorted by min to max, then reverse so that order is max to min

        # Get probability value per frame for each top X class
        frames = [frame_ix for frame_ix in range(len(frame_arrays))]
        seconds = [f/100 for f in frames[::32]]

        slices = [100, 50, 10, 2]
        lines = []

        out_df = pd.DataFrame(seconds, columns=['seconds'])
        for slice in slices:
            temp_df = pd.DataFrame()
            idex_slice = idxes[:slice]
            for class_ix in idex_slice:
                class_lb = ix_to_lb[class_ix]
                class_probs = [frame_arrays[frame_ix][class_ix] for frame_ix in frames[::32]]
                # Add list as a column to dataframe
                temp_df[class_lb] = class_probs
                if slice == 10:
                    out_df[class_lb] = class_probs
                if slice == 2:
                        # Optional: Make plot of SED results and save
                    line, = plt.plot(seconds[:320], class_probs[:320], label=class_lb, linewidth=0.25)
                    lines.append(line)
            label = 'speech_ratio_{0}'.format(slice)

            if slice == 50:
                out_df[label] = temp_df['Speech'] / temp_df.sum(axis=1)
                line, = plt.plot(seconds[:320], out_df[label][:320], label=label.format(slice), linewidth=0.25)
                lines.append(line)

        # Save full dataframe
        print('------ Save results ------')
        out_df.to_csv(out_fn_path, index=False)

        # Save plot
        plt.legend(handles=lines)
        plt.legend(bbox_to_anchor=(1,1), loc="upper left")
        plt.xlabel('Seconds')
        plt.ylabel('Probability')
        plt.ylim(0, 1.)
        plt.savefig(out_fig_path)
        print('Save fig to {}'.format(out_fig_path))

        plt.clf()


def convert_to_wav (fn, orig_path, wav_path, mono=False):
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


def convert_and_move_file (fn, orig_path, wav_path, mp4_path, mono=False):
    """ Wrapper to convert mp4 file and move to separate directory.

    :param fn: An mp4 filename (w/ ext)
    :param orig_path: The original path of the mp4 file
    :param wav_path: The output path of the wav file
    :param mp4_path: The output path of the mp4 file
    :param mono: Boolean for converting sound to mono
    """
    name, ext = path.splitext(fn)
    if ext == ".mp4":
        convert_to_wav (fn, orig_path, wav_path, mono)

    if not path.exists(mp4_path):
        makedirs(mp4_path)
    move(path.join(orig_path, fn), path.join(mp4_path, fn))


def convert_and_move_dir (dir_name, orig_path, wav_path, mp4_path, mono, sed):
    """ Wrapper to convert each mp4 file in a channel folder and
    move the entire folder to a separate directory.

    :param dir_name: An sub-directory name (i.e., channel folders)
    :param orig_path: The original path of the sub-directory
    :param wav_path: The output path of the wav sub-directory
    :param mp4_path: The output path of the mp4 sub-directory
    :param mono: Boolean for converting sound to mono
    """
    print('\nCURRENT CHANNEL: {0}'.format(dir_name))

    orig_dir_path = path.join(orig_path, dir_name)
    wav_dir_path = path.join(wav_path, dir_name)

    for fn in listdir(orig_dir_path):
        name, ext = path.splitext(fn)

        if ext == ".mp4":
            convert_to_wav(fn, orig_dir_path, wav_dir_path, mono)

        if sed:
            detect_speech(path.join(wav_dir_path, name+".wav"), orig_path)

    if not path.exists(mp4_path):
        makedirs(mp4_path)
    move(orig_dir_path, mp4_path)


def main(args):

    orig_path = path.join('corpus','raw_audio')
    if args.group:
        orig_path = path.join(orig_path, args.group)
    mp4_path = path.join(orig_path, "mp4")
    wav_path = path.join(orig_path, "wav")

    if args.stereo:
        mono = False
    else:
        mono = True # Convert files to mono

    for dir_element in listdir(orig_path):

        if path.splitext(dir_element)[1] == '.mp4':
            convert_and_move_file(dir_element, orig_path, wav_path, mp4_path, mono)

        elif dir_element not in ['mp4', 'wav', 'sed', '.DS_Store']:
            convert_and_move_dir(dir_element, orig_path, wav_path, mp4_path, mono, args.sed)

    out_message = path.join(wav_path, "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for full audio files (converted to WAV) go here.')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format.')

    parser.set_defaults(func=None)
    parser.add_argument('-g', '--group', default="ungrouped", type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('-s', '--stereo', action='store_true', default=False, help='keep stereo (separate audio channels); else, converts to mono')
    parser.add_argument('-sed', '--sed', action='store_true', default=False, help='use machine learning model to detect sound events')

    args = parser.parse_args()

    main(args)
