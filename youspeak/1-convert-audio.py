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


def detect_speech(audio_path, sed_dir_path, save_fig):

    # Get index to label dictionary
    print('------ Compiling dictionary ------')
    ix_to_lb = {i : label for i, label in enumerate(labels)}

    # Run SED for audio file
    print('------ Accessing audio ------')
    fn = path.splitext(path.split(audio_path)[1])[0]
    device = 'cpu' # 'cuda' | 'cpu'

    # Prep files
    if(save_fig):
        if not path.exists(path.join(sed_dir_path, "fig")):
            makedirs(path.join(sed_dir_path, "fig"))
        out_fig_path = path.join(sed_dir_path, 'fig', fn+'_sed_results.png')
    else:
        makedirs(sed_dir_path)

    out_fn_path = path.join(sed_dir_path, fn+'_sed_results.csv')

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

        if save_fig: # Plot top 10 categories
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
    classes_noise  = [ix_to_lb[i] for i in range(66,73)] + [ix_to_lb[i] for i in range(506,527)]

    out_df['speech_ratio'] = temp_df[classes_speech].sum(axis=1) / temp_df.sum(axis=1)
    out_df['music_ratio']  = temp_df[classes_music].sum(axis=1)  / temp_df.sum(axis=1)
    out_df['noise_ratio']  = temp_df[classes_noise].sum(axis=1)  / temp_df.sum(axis=1)

    if(save_fig):
        lines, = axis[1].plot(seconds, out_df['speech_ratio'], label='speech_ratio', linewidth=0.25)
        linem, = axis[1].plot(seconds, out_df['music_ratio'], label='music_ratio', linewidth=0.25)
        linen, = axis[1].plot(seconds, out_df['noise_ratio'], label='noise_ratio', linewidth=0.25)

        ratio_lines.append(lines)
        ratio_lines.append(linem)
        ratio_lines.append(linen)

    # Save full dataframe
    print('------ Save results ------')
    out_df.to_csv(out_fn_path, index=False)

    # Save plot
    if(save_fig):
        axis[0].legend(handles=type_lines, loc="upper right")
        axis[1].legend(handles=ratio_lines, loc="lower right")
        plt.xlabel('Seconds')
        plt.ylabel('Probability')
        plt.ylim(0, 1.)
        plt.tight_layout()

        print('Save fig to {}'.format(out_fig_path))
        plt.savefig(out_fig_path, dpi=300)

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

def convert_and_move_dir (dir_name, orig_path, wav_path, mp4_path, sed_path, mono, sed, save_fig):
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
    sed_dir_path = path.join(sed_path, dir_name)

    for fn in listdir(orig_dir_path):
        name, ext = path.splitext(fn)

        if ext == ".mp4":
            convert_to_wav(fn, orig_dir_path, wav_dir_path, mono)

        if sed:
            detect_speech(path.join(wav_dir_path, name+".wav"), sed_dir_path, save_fig)

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

    for dir_element in listdir(orig_path):

        if dir_element not in ['mp4', 'wav', 'sed', '.DS_Store']:
            convert_and_move_dir(dir_element, orig_path, wav_path, mp4_path, sed_path, mono, args.sed, args.fig)

    out_message = path.join(wav_path, "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for full audio files (converted to WAV) go here.')

    if args.sed:
        for dir_element in listdir(wav_path):
            if dir_element not in ['README.md', '.DS_Store']:
                for fn in listdir(path.join(wav_path, dir_element)):
                    video_id = path.splitext(fn)[0]
                    sed_files = glob(path.join(sed_path, "*", "*{0}*".format(video_id)), recursive=True)
                    if not sed_files or args.overwrite:
                        detect_speech(path.join(wav_path, dir_element, fn), path.join(sed_path, dir_element), args.fig)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format.')

    parser.set_defaults(func=None)
    parser.add_argument('-g', '--group',  default="ungrouped", type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('-s', '--stereo', action='store_true', default=False, help='keep stereo (separate audio channels); else, converts to mono')
    parser.add_argument('-sed', '--sed',  action='store_true', default=False, help='use machine learning model to detect sound events')
    parser.add_argument('-f', '--fig',    action='store_true', default=False, help='output screening figure')
    parser.add_argument('-o', '--overwrite', action='store_true', help='overwrite SED results')


    args = parser.parse_args()

    main(args)
