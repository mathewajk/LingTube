# Converts raw YouTube mp4 audio files to analyzable WAV files

import argparse
import sys
import shutil
from os import listdir, makedirs, path
from pydub import AudioSegment
import re

def convert_to_wav (filename, name, origpath, wavpath):
	""" Takes an mp4 file and converts it to WAV format.

	:param filename: An mp4 file (with ext)
    :param name: The extracted mp4 filename identifier (w/o ext)
	:param origpath: The original path of the mp4 file
	:param wavpath: The output path of the wav file
	"""
		print("Converting {0} to .wav...".format(filename))
		if re.match(r".*_\d+$",name):
			# If filenames do not include video titles
			newname = name
		else:
			# If filenames do include video titles
			newname = name.rsplit('_',1)[0]
		exportname = newname + ".wav"
		filepath = path.join(origpath, filename)

		if not path.exists(wavpath):
			makedirs(wavpath)
		exportPath = path.join(wavpath, exportname)
		sound = AudioSegment.from_file(filepath,"mp4")
		sound.export(exportPath, format="wav")

def convert_and_move_file (filename, origpath, wavpath, mp4path):
	""" Wrapper to convert mp4 file and move to separate directory.

	:param filename: An mp4 file
    :param origpath: The original path of the mp4 file
	:param wavpath: The output path of the wav file
	:param mp4path: The output path of the mp4 file
	"""
	name, ext = path.splitext(filename)
	if ext == ".mp4":
		print(filename)
		convert_to_wav (filename, name, origpath, wavpath)

	if not path.exists(mp4path):
		makedirs(mp4path)
	oldlocation = path.join(origpath, filename)
	newlocation = path.join(mp4path, filename)
	shutil.move(oldlocation, newlocation)

def convert_and_move_dir (dirname, origpath, wavpath, mp4path):
	""" Wrapper to convert each mp4 file in a channel folder and
	move the entire folder to a separate directory.

	:param dirname: An sub-directory name (i.e., channel folders)
    :param origpath: The original path of the sub-directory
	:param wavpath: The output path of the wav sub-directory
	:param mp4path: The output path of the mp4 sub-directory
	"""
	print(dirname)
	origdirpath = path.join(origpath, dirname)
	wavdirpath = path.join(wavpath, dirname)
	for filename in listdir(origdirpath):
		name, ext = path.splitext(filename)
		if ext == ".mp4":
			print(filename)
			convert_to_wav(filename, name, origdirpath, wavdirpath)

	if not path.exists(mp4path):
		makedirs(mp4path)
	shutil.move(origdirpath, mp4path)

def main(args):

	origpath = path.join('corpus','raw_audio', args.group)
	mp4path = path.join(origpath, "mp4")
	wavpath = path.join(origpath, "wav")

	for dir_element in listdir(origpath):
		if path.splitext(dir_element)[1] == '.mp4':
			convert_and_move_file(dir_element, origpath, wavpath, mp4path)
		elif dir_element not in ['mp4', 'wav', '.DS_Store']:
			convert_and_move_dir (dir_element, origpath, wavpath, mp4path)

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format.')

	parser.set_defaults(func=None)
	parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')

	args = parser.parse_args()

	main(args)
