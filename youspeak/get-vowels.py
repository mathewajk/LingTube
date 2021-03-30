#!/usr/bin/env python3

import argparse
import os
from os import listdir, makedirs, path
import shutil
import pandas as pd
from numpy import arange

import parselmouth
from parselmouth.praat import call, run_file


# ARPABET
# AA	odd     AA D
# AE	at	AE T
# AH	hut	HH AH T
# AO	ought	AO T
# AW	cow	K AW
# AY	hide	HH AY D
# B 	be	B IY
# CH	cheese	CH IY Z
# D 	dee	D IY
# DH	thee	DH IY
# EH	Ed	EH D
# ER	hurt	HH ER T
# EY	ate	EY T
# F 	fee	F IY
# G 	green	G R IY N
# HH	he	HH IY
# IH	it	IH T
# IY	eat	IY T
# JH	gee	JH IY
# K 	key	K IY
# L 	lee	L IY
# M 	me	M IY
# N 	knee	N IY
# NG	ping	P IH NG
# OW	oat	OW T
# OY	toy	T OY
# P 	pee	P IY
# R 	read	R IY D
# S 	sea	S IY
# SH	she	SH IY
# T 	tea	T IY
# TH	theta	TH EY T AH
# UH	hood	HH UH D
# UW	two	T UW
# V 	vee	V IY
# W 	we	W IY
# Y 	yield	Y IY L D
# Z 	zee	Z IY
# ZH	seizure	S IY ZH ER

# TODO: make classes of sounds, optional flags for all vowels, specific vowel, ignore unstressed vowels, getting pre- and post- sound, ...
# vowels = ['AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW']

# 1 = word tier; 2 = Phone tier

def open_files_in_praat (filename, tgpath, audpath):
    name, ext = path.splitext(filename)
    if ext == '.TextGrid':
        tgfile = path.join(tgpath, filename)
        wavfile = path.join(audpath, name+'.wav')

        sound = parselmouth.Sound(wavfile)
        textgrid = parselmouth.read(tgfile)
        return [sound, textgrid]

def get_formants (sound, int_start, int_dur, proportion_time, max_formant):
    sound_formant = sound.to_formant_burg(0.001, 5.0, 5500.0, 0.025, 50.0)
    timepoint = int_start + (int_dur * proportion_time)

    # get formant values at timepoint in sound
    formant_list = []
    for formant_i in range(1, max_formant+1):
        fn = sound_formant.get_value_at_time(formant_i, timepoint)
        formant_list.append(fn)
    return formant_list

def main(args):
    # base paths
    aligned_audio_base = path.join("corpus", "aligned_audio")
    acoustic_data_base = path.join("corpus", "acoustic_data")

    if not args.group == None:
        aligned_audio_base = path.join(aligned_audio_base, args.group)
        acoustic_data_base = path.join(acoustic_data_base, args.group)

    if not args.channel == None:
        channel_list = [args.channel]
    else:
        channel_list = [channel for channel in listdir(path.join(aligned_audio_base, "aligned_corpus")) if not channel.startswith('.')]

    for ch_i, channel in enumerate(channel_list):
        print('\nChannel {0} of {1}: {2} ...'.format(ch_i+1, len(channel_list), channel))

        postalignpath = path.join(aligned_audio_base, "aligned_corpus", channel)
        prealignpath = path.join(aligned_audio_base, "original_corpus", channel)

        if not args.video == None:
            video_id = '{0}_{1}'.format(channel, args.video)
            video_list = [video_id]
        else:
            video_list = [video_id for video_id in listdir(postalignpath) if not video_id.startswith('.')]

        for v_i, video_id in enumerate(video_list):
            print('\nVideo {0} of {1}: {2} ...'.format(v_i+1, len(video_list), video_id))

            tgpath = path.join(postalignpath, video_id)
            audpath = path.join(prealignpath, video_id)

            out_tgpath = path.join(acoustic_data_base, "textgrids", channel, video_id)
            out_audpath = path.join(acoustic_data_base, "audio", channel, video_id)
            out_datapath = path.join(acoustic_data_base, "vowels", channel)

            # Make folders and copy files
            for dir in [out_audpath, out_tgpath, out_datapath]:
                if not path.exists(dir):
                    makedirs(dir)
            for tgfilename in listdir(tgpath):
                name, ext = path.splitext(tgfilename)
                wavfilename = name+'.wav'
                shutil.copyfile(path.join(tgpath, tgfilename),
                         path.join(out_tgpath, tgfilename))
                shutil.copyfile(path.join(audpath, wavfilename),
                         path.join(out_audpath, wavfilename))

            # Create output data frame (overwriting existing)
            out_df = pd.DataFrame(columns=['channel', 'video_id', 'filename', 'label', 'start_time', 'end_time', 'duration', 'pre_phone', 'post_phone', 'word', 'vowel', 'stress', 'diph'])
            out_df.to_csv(os.path.join(out_datapath, video_id+"_vowels.csv"), index=False)

            for file_i, filename in enumerate(listdir(tgpath)):
                print('Processing file {0} of {1}: {2} ...'.format(file_i+1, len(listdir(tgpath)), filename))
                sound, textgrid = open_files_in_praat(filename,
                                                      tgpath, audpath)

                # def get_formants(textgrid, max_step, max_formant, vowels)
                monoph = ['AA', 'AE', 'AH', 'AO', 'EH', 'ER', 'IH', 'IY', 'UH', 'UW']
                diph = ['AW', 'AY', 'EY', 'OW', 'OY']

                # Get all times of all (relevant) intervals (e.g., vowels)
                n_ints = call(textgrid, 'Get number of intervals', 2)
                for int_i in range(1, n_ints+1):

                    # Get labels
                    int_lab = call(textgrid, 'Get label of interval', 2, int_i)
                    try:
                        int_pre = call(textgrid, 'Get label of interval', 2, int_i-1)
                        if int_pre == 'sp':
                            int_pre = ''
                    except:
                        int_pre = None
                    try:
                        int_post = call(textgrid, 'Get label of interval', 2, int_i+1)
                        if int_post == 'sp':
                            int_post = ''
                    except:
                        int_post = None

                    if int_lab[:2] in monoph or int_lab[:2] in diph:

                        # Get label timing
                        int_start = call(textgrid, 'Get start time of interval', 2, int_i)
                        int_end = call(textgrid, 'Get end time of interval', 2, int_i)
                        int_dur =  (int_end - int_start)

                        # Get label word/sound info
                        int_vowel = int_lab[:2]
                        int_stress = int_lab[-1]
                        int_word = call(textgrid, 'Get label of interval', 1,
                                    call(textgrid, 'Get interval at time', 1, int_start))
                        # print(int_word)

                        if int_vowel in diph:
                            int_diph = 1
                        else:
                            int_diph = 0

                        # Add info to data output row
                        data_row = {'channel': channel, 'video_id': video_id, 'filename': filename, 'label': int_lab, 'start_time': int_start, 'end_time': int_end, 'duration': int_dur, 'pre_phone': int_pre, 'post_phone': int_post, 'word': int_word, 'vowel': int_vowel, 'stress': int_stress, 'diph': int_diph}

                        # Get nucleus formants
                        if args.nucleus:
                            if int_diph == 1:
                                f1, f2, f3 = get_formants(sound, int_start, int_dur, 0.3, 3)
                            else:
                                f1, f2, f3 = get_formants(sound, int_start, int_dur, 0.5, 3)
                            data_row.update({'F1_nuc': f1, 'F2_nuc': f2, 'F3_nuc': f3})

                        if args.onoff:
                            # Get onset formants at 25% into the vowel
                            f1, f2, f3 = get_formants(sound, int_start, int_dur, 0.25, 3)
                            data_row.update({'F1_on': f1, 'F2_on': f2, 'F3_on': f3})

                            # Get offset formants at 75% into the vowel
                            f1, f2, f3 = get_formants(sound, int_start, int_dur, 0.75, 3)
                            data_row.update({'F1_off': f1, 'F2_off': f2, 'F3_off': f3})

                        if args.steps:
                            # Get formants at X steps between Y time and Z time
                            prop_start = 0.2
                            prop_end = 0.8
                            n_steps = 30
                            prop_interval = (prop_end - prop_start)/n_steps

                            for step_i in arange(prop_start, prop_end+prop_interval, prop_interval):
                                prop_step = round(step_i,3)
                                f1, f2, f3 = get_formants(sound, int_start, int_dur, prop_step, 3)
                                data_row.update({'F1_{0}'.format(round(prop_step*100)): f1, 'F2_{0}'.format(round(prop_step*100)): f2, 'F3_{0}'.format(round(prop_step*100)): f3})

                        # print(data_row)

                        # write to DataFrame
                        out_df = out_df.append(data_row, ignore_index=True, sort=False)

                        # save dataframe
                        out_df.to_csv(os.path.join(out_datapath, video_id+"_vowels.csv"), index=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get formants from aligned audio chunks and textgrids.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--video', '-v', default=None, type=str, help='video number')
    parser.add_argument('--formants', '-f', default=3, type=int, help='maximum number of formants to extract (default=3)')
    parser.add_argument('--nucleus', '-n', action='store_true', default=False, help='extract nucleus midpoint formants')
    parser.add_argument('--onoff', '-o', action='store_true', default=False, help='extract onset and offset formants')
    parser.add_argument('--steps', '-s', action='store_true', default=False, help='extract formants at 30 steps')

    args = parser.parse_args()

    main(args)
