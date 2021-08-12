#!/usr/bin/env python3

import argparse
from shutil import move
from os import listdir, makedirs, path
from pydub import AudioSegment

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

def convert_and_move_dir (dir_name, orig_path, wav_path, mp4_path, mono):
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

    if not path.exists(mp4_path):
        makedirs(mp4_path)
    move(orig_dir_path, mp4_path)

def main(args):

    orig_path = path.join('corpus','raw_audio')
    if args.group:
        orig_path = path.join(orig_path, args.group)
    mp4_path = path.join(orig_path, "mp4")
    wav_path = path.join(orig_path, "wav")

    # TODO: Legacy mono option
    mono = True # Convert files to mono

    for dir_element in listdir(orig_path):

        if path.splitext(dir_element)[1] == '.mp4':
            convert_and_move_file(dir_element, orig_path, wav_path, mp4_path, mono)

        elif dir_element not in ['mp4', 'wav', '.DS_Store']:
            convert_and_move_dir(dir_element, orig_path, wav_path, mp4_path, mono)

    out_message = path.join(wav_path, "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for full audio files (converted to mono WAV) go here.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')

    args = parser.parse_args()

    main(args)
