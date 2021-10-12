#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
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

def get_formants (sound, int_start, int_dur, proportion_time, max_formant, formant_ceiling):

    # print("Making formant object")
    sound_formant = sound.to_formant_burg(0.001, 5.0, formant_ceiling, 0.025, 50.0)
    timepoint = int_start + (int_dur * proportion_time)

    # print("Getting formant values")
    formant_list = []
    for formant_i in range(1, max_formant+1):
        formant_n = sound_formant.get_value_at_time(formant_i, timepoint)
        formant_list.append(formant_n)
    return formant_list

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

    if args.group:
        aligned_audio_base = path.join(aligned_audio_base, args.group)
        acoustic_data_base = path.join(acoustic_data_base, args.group)

    if args.channel:
        channel_list = [args.channel]
    else:
        channel_list = [channel_id for channel_id in listdir(path.join(aligned_audio_base, "aligned_corpus")) if not channel_id.startswith('.') and not channel_id.endswith('.txt')]
        channel_list.sort(key=str.lower)


    for ch_i, channel_id in enumerate(channel_list):
        print('\nChannel {0} of {1}: {2} ...'.format(ch_i+1, len(channel_list), channel_id))

        adjusted_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id)
        post_align_path = path.join(aligned_audio_base, "aligned_corpus", channel_id)
        pre_align_path = path.join(aligned_audio_base, "original_corpus", channel_id)

        #video_list = []
        #if path.isdir(adjusted_path):
        if args.adjusted:
            video_list = [video_dir for video_dir in listdir(adjusted_path) if not video_dir.startswith('.') and not video_dir.endswith('.txt')]
        #if len(video_list) == 0:
        else:
            video_list = [video_dir for video_dir in listdir(post_align_path) if not video_dir.startswith('.') and not video_dir.endswith('.txt')]
        video_list.sort(key=str.lower)

        for v_i, video_dir in enumerate(video_list):
            video_id = video_dir # need to fix so things work without an id

            print('* Video {0} of {1}: {2} ...'.format(v_i+1, len(video_list), video_id))

            if args.adjusted:
                tg_path = path.join(adjusted_path, video_id, "textgrids")
                audio_path = path.join(adjusted_path, video_id, "audio")
                out_data_path = path.join(acoustic_data_base, "adjusted", channel_id)
            else:
            #if not path.isdir(tg_path) or not [tg for tg in listdir(tg_path) if path.splitext(tg)[1] == '.TextGrid']:
                print('  Using automatic (unadjusted) forced alignment')
                tg_path = path.join(post_align_path, video_id)
                audio_path = path.join(pre_align_path, video_id)
                out_data_path = path.join(acoustic_data_base, "automatic", channel_id)

            # Make folders
            if not path.exists(out_data_path):
                makedirs(out_data_path)

            if args.nucleus:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","nucleus")
            if args.onoff:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","onoff")
            if args.steps:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","steps")
            if args.nucleus or args.onoff or args.steps:
                '{0}_{1}_{2}.csv'.format(video_id, "vowel","formants")
            else:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","duration")

            if path.exists(path.join(out_data_path, out_fn)):
                if args.overwrite:
                    print('- Overwriting file: {0}'.format(out_fn))

                    remove(path.join(out_data_path, out_fn))
                else:
                    print('- Skipping existing file: {0}'.format(out_fn))
                    continue

            # Create output data frame (overwriting existing)
            out_df = pd.DataFrame(columns=['filename', 'label', 'start_time', 'end_time', 'duration', 'pre_phone', 'post_phone', 'word', 'vowel', 'stress', 'diph'])

            # TODO: Read in the 'vowel_coding_log.csv'
            if args.adjusted:
                log_path = path.join(adjusted_path, video_id, "vowel_coding_log.csv")
                log_df = pd.read_csv(log_path)
            # TODO: Read columns, split file column name to remove wav, add order, vowel label, boundaries, creak, and issues column
            # log_df['file']
            # log_df.iloc[idx]

            files_list = [fn for fn in listdir(tg_path) if not fn.startswith('.') and not fn.endswith('.txt')]
            files_list.sort(key=str.lower)

            for f_i, fn in enumerate(files_list):
                sound, textgrid = open_files_in_praat(fn, tg_path, audio_path)
                sound_fn = path.splitext(fn)[0] + ".wav"

                if args.point_marker:
                    target_int = call(textgrid, "Get interval at time", 2, call(textgrid, "Get time of point", 3, 1))
                    target_label = call(textgrid, "Get label of interval", 2, target_int)
                    # TODO: add check in case marked label is wrong/doesn't match expected vowel; write filename to textfile for manual checking
                    target_start = call(textgrid, "Get start time of interval", 2, target_int)
                    target_end = call(textgrid, "Get end time of interval", 2, target_int)
                    vowel_subsounds = [call(sound, "Extract part", target_start, target_end, "rectangular", 1, True)]
                    extracted_vowels = [(vs, target_start, target_end, target_label) for vs in vowel_subsounds]
                else:
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
                            vowel_sound_list = [(vs,vs.get_start_time(), vs.get_end_time(), target_label) for vs in vowel_subsounds]
                            extracted_vowels = extracted_vowels + vowel_sound_list
                        else:
                            none_vowels.append(target_label)

                    if none_vowels:
                        print('  - Vowels not found: {0}.'.format(none_vowels))

                if not args.adjusted:
                    print('  Number of vowels: {0}'.format(len(extracted_vowels)))
                for j, target_vowel in enumerate(extracted_vowels):
                    vowel_sound, int_start, int_end, vowel_label = target_vowel

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

                    # Get pre- and post-context
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

                    # Add info to data output row
                    data_row = {'filename': sound_fn, 'label': vowel_label, 'start_time': int_start, 'end_time': int_end, 'duration': int_dur, 'pre_phone': int_pre, 'post_phone': int_post, 'word': int_word, 'vowel': int_vowel, 'stress': int_stress, 'diph': int_diph}

                    # Get nucleus formants
                    if args.nucleus:
                        if int_diph == 1:
                            f1, f2, f3 = get_formants(vowel_sound, int_start, int_dur, 0.3, args.max_formant, args.formant_ceiling)
                        else:
                            f1, f2, f3 = get_formants(vowel_sound, int_start, int_dur, 0.5, args.max_formant, args.formant_ceiling)
                        data_row.update({'F1_nuc': f1, 'F2_nuc': f2, 'F3_nuc': f3})

                    if args.onoff:
                        # Get onset formants at 25% into the vowel
                        f1, f2, f3 = get_formants(vowel_sound, int_start, int_dur, 0.25, args.max_formant, args.formant_ceiling)
                        data_row.update({'F1_on': f1, 'F2_on': f2, 'F3_on': f3})

                        # Get offset formants at 75% into the vowel
                        f1, f2, f3 = get_formants(vowel_sound, int_start, int_dur, 0.75, args.max_formant, args.formant_ceiling)
                        data_row.update({'F1_off': f1, 'F2_off': f2, 'F3_off': f3})

                    if args.steps:
                        # Get formants at X steps between Y time and Z time
                        prop_start = 0.2
                        prop_end = 0.8
                        n_steps = 30
                        prop_interval = (prop_end - prop_start)/n_steps

                        for step_i in arange(prop_start, prop_end+prop_interval, prop_interval):
                            prop_step = round(step_i,3)
                            f1, f2, f3 = get_formants(vowel_sound, int_start, int_dur, prop_step, args.max_formant, args.formant_ceiling)
                            data_row.update({'F1_{0}'.format(round(prop_step*100)): f1, 'F2_{0}'.format(round(prop_step*100)): f2, 'F3_{0}'.format(round(prop_step*100)): f3})

                    # write to DataFrame
                    out_df = out_df.append(data_row, ignore_index=True, sort=False)

                    out_df.to_csv(path.join(out_data_path, out_fn), index=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get duration and formants from aligned audio chunks and textgrids (default=only duration).')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--adjusted', '-a', action='store_true', default=False, help='use hand-corrected, adjusted textgrids (under adjusted_corpus)')
    parser.add_argument('--point_marker', '-p', action='store_true', default=False, help='use point marker to identify target vowels')
    parser.add_argument('--vowels', '-vo', help='list of vowels to target, comma-separated', type=str)
    parser.add_argument('--stress', '-st', help='list of stress values to target, comma-separated', type=str)
    parser.add_argument('--nucleus', '-n', action='store_true', default=False, help='extract nucleus midpoint formants')
    parser.add_argument('--onoff', '-onf', action='store_true', default=False, help='extract onset and offset formants')
    parser.add_argument('--steps', '-s', action='store_true', default=False, help='extract formants at 30 steps')
    parser.add_argument('--max_formant', '-mf', default=3, type=int, metavar='N', help='maximum number of formants to extract (default=3)')
    parser.add_argument('--formant_ceiling', '-fc', default=5500, type=int, metavar='N', help='formant ceiling value (Hz); typically 5500 for adult women, 5000 for adult men (default=5500)')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
