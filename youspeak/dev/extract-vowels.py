#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
from shutil import rmtree, copy
import pandas as pd
from numpy import arange

import parselmouth
from parselmouth.praat import call

# NOTE: 1 = word tier; 2 = Phone tier

def open_files_in_praat (fn, tg_path, audio_path):
    name, ext = path.splitext(fn)
    if ext == '.TextGrid':
        tg_fp = path.join(tg_path, fn)
        wav_fp = path.join(audio_path, name+'.wav')

        sound = parselmouth.Sound(wav_fp)
        textgrid = parselmouth.read(tg_fp)
        return [sound, textgrid]


def main(args):

    # Vowel target lists
    monoph = ['AA', 'AE', 'AH', 'AO', 'EH', 'ER', 'IH', 'IY', 'UH', 'UW']
    diph = ['AW', 'AY', 'EY', 'OW', 'OY']
    if args.vowels:
        vowel_list = [v for v in args.vowels.split(',')]
    else:
        vowel_list = monoph + diph

    target_list = []
    if args.stress:
        stress_list = [s for s in args.stress.split(',')]
    else:
        stress_list = [1,2,0]
    for s in stress_list:
        target_list = target_list + [v+str(s) for v in vowel_list]

    # Base paths
    aligned_audio_base = path.join("corpus", "aligned_audio")
    acoustic_data_base = path.join("corpus", "acoustic_data")

    if not args.group == None:
        aligned_audio_base = path.join(aligned_audio_base, args.group)
        acoustic_data_base = path.join(acoustic_data_base, args.group)

    if not args.channel == None:
        channel_list = [args.channel]
    else:
        channel_list = [channel_id for channel_id in listdir(path.join(aligned_audio_base, "aligned_corpus")) if not channel_id.startswith('.') and not channel_id.endswith('.txt')]
        channel_list.sort(key=str.lower)

    for ch_i, channel_id in enumerate(channel_list):
        print('\nChannel {0} of {1}: {2} ...'.format(ch_i+1, len(channel_list), channel_id))

        channel_j = 0

        adjusted_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id)
        post_align_path = path.join(aligned_audio_base, "aligned_corpus", channel_id)
        pre_align_path = path.join(aligned_audio_base, "original_corpus", channel_id)


        video_list = [video_id for video_id in listdir(post_align_path) if not video_id.startswith('.') and not video_id.endswith('.txt')]


        for v_i, video_id in enumerate(video_list):
            print('* Video {0} of {1}: {2} ...'.format(v_i+1, len(video_list), video_id))

            video_j = 0

            tg_path = path.join(post_align_path, video_id)
            audio_path = path.join(pre_align_path, video_id)

            # create vowel output path
            out_path = path.join(adjusted_path, channel_id+"_all")
            out_tg_path = path.join(out_path, "textgrids")
            out_audio_path = path.join(out_path, "audio")
            out_vowel_path = path.join(out_path, "queue")

            if path.exists(out_vowel_path):
                if channel_j == 0:
                    if args.overwrite:
                        rmtree(out_vowel_path)
                    else:
                        print('- Extracted vowels already exist.'.format(channel_id))
                        continue

            for dir in [out_tg_path, out_audio_path, out_vowel_path]:
                if not path.exists(dir):
                    makedirs(dir)

            # add code-vowels praat script to directory
            copy(path.join(path.dirname(path.realpath(__file__)), "praat", "code-vowels.praat"), out_path)
            ##########################

            file_list = [fn for fn in listdir(tg_path) if not fn.startswith('.') and not fn.endswith('.txt')]
            file_list.sort()

            for f_i, fn in enumerate(file_list):
                sound, textgrid = open_files_in_praat(fn, tg_path, audio_path)

                none_vowels = []
                extracted_vowels = []
                for target_label in target_list:
                    vowel_count = call(textgrid,'Count intervals where',
                                   2, 'is equal to', target_label)
                    if vowel_count > 0:
                        vowel_subsounds = call([sound, textgrid],
                                                'Extract intervals where',
                                                2, True, 'is equal to', target_label)
                        if not isinstance(vowel_subsounds, list): # check if list
                            vowel_subsounds = [vowel_subsounds]
                        vowel_sound_list = [(vs, vs.get_start_time(), vs.get_end_time(), target_label) for vs in vowel_subsounds]
                        extracted_vowels = extracted_vowels + vowel_sound_list
                    else:
                        none_vowels.append(target_label)

                ##########################
                extracted_vowels.sort(key=lambda a: a[1]) # sort by start time
                ##########################

                if none_vowels:
                    print('  - Vowels not found: {0}.'.format(none_vowels))

                print('  Number of vowels: {0}'.format(len(extracted_vowels)))
                for file_j, target_vowel in enumerate(extracted_vowels):
                    # print("File j: {}".format(file_j))

                    vowel_sound, int_start, int_end, vowel_label = target_vowel
                    j = channel_j + video_j + file_j + 1
                    # print("Total channel j: {}".format(j))

                    int_vowel = vowel_label[:2]
                    int_stress = vowel_label[-1]
                    if vowel_label in diph:
                        int_diph = 1
                    else:
                        int_diph = 0

                    # Get label timing
                    int_dur =  (int_end - int_start)

                    # Get label word/sound info
                    int_word = call(textgrid, 'Get label of interval', 1,
                                call(textgrid, 'Get interval at time', 1, int_start))
                    int_i = call(textgrid, 'Get interval at time', 2, int_start)

                    ##########################
                    # TODO: if less/more than start/end time, change value
                    window_start = int_start-0.1
                    window_end = int_end+0.1

                    # extract sound + extra window
                    sound_window = call(sound, 'Extract part', window_start, window_end, 'rectangular', 1, False)
                    tg_window = call(textgrid, 'Extract part', window_start, window_end, False)

                    int_start_ms = int(int_start*1000)
                    int_start_ms = int(int_end*1000)

                    # save extracted vowels
                    window_name = '{0}_{1}_{2}_{3}_{4}'.format(video_id, '{:04d}'.format(j), int_start_ms, int_start_ms, vowel_label)

                    # save to different folder based on (personalized) criteria
                    coding_vowels = ['OW1', 'UW1', 'EY1', 'IY1', 'AE1', 'AA1', 'AO1']
                    if j <= 250 or vowel_label in coding_vowels:
                        sound_window.save(path.join(out_vowel_path, window_name+'.wav'), "WAV")
                        tg_window.save(path.join(out_vowel_path, window_name+'.TextGrid'))
                    else:
                        if not path.exists(path.join(out_vowel_path, 'extra')):
                            makedirs(path.join(out_vowel_path, 'extra'))

                        sound_window.save(path.join(out_vowel_path, 'extra', window_name+'.wav'), "WAV")
                        tg_window.save(path.join(out_vowel_path, 'extra', window_name+'.TextGrid'))

                video_j = video_j + file_j
                # print("Updated Video j: {}".format(video_j))
                # input()

            channel_j = j
            # print("Updated Channel j: {}".format(channel_j))
            # input()


                    ##########################

                    # # Get pre- and post-context
                    # try:
                    #     int_pre = call(textgrid, 'Get label of interval', 2, int_i-1)
                    #     if int_pre == 'sp':
                    #         int_pre = ''
                    # except:
                    #     int_pre = None
                    # try:
                    #     int_post = call(textgrid, 'Get label of interval', 2, int_i+1)
                    #     if int_post == 'sp':
                    #         int_post = ''
                    # except:
                    #     int_post = None

                    # # Add info to data output row
                    # data_row = {'channel': channel_id, 'video_id': video_id, 'filename': fn, 'label': vowel_label, 'start_time': int_start, 'end_time': int_end, 'duration': int_dur, 'pre_phone': int_pre, 'post_phone': int_post, 'word': int_word, 'vowel': int_vowel, 'stress': int_stress, 'diph': int_diph, 'wavfile': window_name+'.WAV', 'tgfile': window_name+'.TextGrid', 'index': '{:04d}'.format(j+1)}

                    ##########################
                    # deleted formant content
                    ##########################

                    # # write to DataFrame
                    # out_df = out_df.append(data_row, ignore_index=True, sort=False)
                    #
                    # out_df.to_csv(path.join(adjusted_path, video_id, out_fn), index=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get duration and formants from aligned audio chunks and textgrids (default=only duration).')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--vowels', '-vo', help='list of vowels to target, comma-separated', type=str)
    parser.add_argument('--stress', '-st', help='list of stress values to target, comma-separated', type=str)
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    # TODO: Add overwrite

    args = parser.parse_args()

    main(args)
