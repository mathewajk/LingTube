#####################################################################
# mp4_to_wav.py
#####################################################################
# Converts raw mp4 files to analyzable WAV files
# To Use: From scripts folder, run script with optional group name
#####################################################################

import argparse
import sys
import shutil
from os import listdir, makedirs, path
from pydub import AudioSegment
import re

####### FUNCTIONS ##################################################

def convertToWav (fileName, name, origPath, wavPath):
		print("Converting {0} to .wav...".format(fileName))
		if re.match(r".*_\d+$",name):
			newName = name
		else:
			newName = name.rsplit('_',1)[0]
		exportName = newName + ".wav"
		filePath = path.join(origPath, fileName)

		if not path.exists(wavPath):
			makedirs(wavPath)
		exportPath = path.join(wavPath, exportName)
		sound = AudioSegment.from_file(filePath,"mp4")
		sound.export(exportPath, format="wav")

def fileConversion (fileName, audPath, wavPath, mp4Path):
	name, ext = path.splitext(fileName)
	if ext == ".mp4":
		print(fileName)
		convertToWav (fileName, name, audPath, wavPath)
	oldLoc = path.join(audPath, fileName)
	newLoc = path.join(mp4Path, fileName)
	if not path.exists(mp4Path):
		makedirs(mp4Path)
	shutil.move(oldLoc, newLoc)

def dirConversion (dirName, audPath, wavPath, mp4Path):
	print(dirName)
	audDirPath = path.join(audPath, dirName)
	wavPath = path.join(wavPath, dirName)
	for fileName in listdir(audDirPath):
		name, ext = path.splitext(fileName)
		if ext == ".mp4":
			print(fileName)
			convertToWav (fileName, name, audDirPath, wavPath)
	if not path.exists(mp4Path):
		makedirs(mp4Path)
	shutil.move(audDirPath, mp4Path)

#####################################################################
# RUN SCRIPT
#####################################################################

def main(args):

	# Get paths
	audPath = path.join('corpus','raw_audio', args.group)
	mp4Path = path.join(audPath, "mp4")
	wavPath = path.join(audPath, "wav")

	# Run mp4 to wav conversion
	for dirItem in listdir(audPath):
		if path.splitext(dirItem)[1] == '.mp4':
			fileConversion(dirItem, audPath, wavPath, mp4Path)
		elif dirItem not in ['mp4', 'wav', '.DS_Store']:
			# If find directories instead of files, move dirs into MP4
			dirConversion (dirItem, audPath, wavPath, mp4Path)

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Convert scraped YouTube audio from mp4 to WAV format.')

	parser.set_defaults(func=None)
	parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')

	args = parser.parse_args()

	main(args)
