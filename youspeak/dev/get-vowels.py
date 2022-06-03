#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
import pandas as pd
from numpy import arange
import chardet

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
    sound_formant = sound.to_formant_burg(0.001, 5.0, formant_ceiling, 0.005, 50.0)
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

                if args.fasttrack:
                    fasttrack_path = path.join(out_data_path, "fasttrack")
                    fasttrack_sounds_path = path.join(out_data_path, "fasttrack", "sounds")
                    # fasttrack_tgs_path = path.join(adjusted_path, video_id, "fasttrack", "textgrids")

                out_error_list = path.join(out_data_path, '{0}_{1}.txt'.format(video_id, "errors"))

                try:
                    if not len(listdir(tg_path)):
                        continue #skip this unadjusted file
                except FileNotFoundError:
                    continue #skip this unadjusted file
            else:
            #if not path.isdir(tg_path) or not [tg for tg in listdir(tg_path) if path.splitext(tg)[1] == '.TextGrid']:
                print('  Using automatic (unadjusted) forced alignment')
                tg_path = path.join(post_align_path, video_id)
                audio_path = path.join(pre_align_path, video_id)
                out_data_path = path.join(acoustic_data_base, "automatic", channel_id)

                if args.fasttrack:
                    fasttrack_path = path.join(out_data_path, "fasttrack")
                    fasttrack_sounds_path = path.join(out_data_path, "fasttrack", "sounds")
                    # fasttrack_tgs_path = path.join(pre_align_path, video_id, "fasttrack", "textgrids")

            # Make folders
            if args.fasttrack:
                for dir in [out_data_path, fasttrack_sounds_path]: #fasttrack_tgs_path
                    if not path.exists(dir):
                        makedirs(dir)
            else:
                if not path.exists(out_data_path):
                    makedirs(out_data_path)

            if args.nucleus:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","nucleus")
            if args.onoff:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","onoff")
            if args.steps:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","steps")
            if args.nucleus or args.onoff or args.steps:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","formants")
            else:
                out_fn = '{0}_{1}_{2}.csv'.format(video_id, "vowel","duration")

            if path.exists(path.join(out_data_path, out_fn)):
                if args.overwrite and not args.fasttrack:
                    print('- Overwriting file: {0}'.format(out_fn))

                    remove(path.join(out_data_path, out_fn))
                elif args.fasttrack:
                    pass
                else:
                    print('- Skipping existing file: {0}'.format(out_fn))
                    continue

            if args.adjusted:
                if path.exists(out_error_list) and args.overwrite:
                    remove(out_error_list)

            # Create output data frame (overwriting existing)
            out_df = pd.DataFrame(columns=['filename', 'label', 'start_time', 'end_time', 'duration', 'pre_phone', 'post_phone', 'word', 'vowel', 'stress', 'diph'])

            if args.fasttrack:
                ft_segment_df = pd.DataFrame(columns=['inputfile', 'outputfile', 'vowel', 'interval', 'duration', 'start', 'end', 'previous_sound', 'next_sound', 'omit', 'stress', 'word', 'word_interval', 'word_start', 'word_end', 'previous_word', 'next_word', 'diphthong', 'number', 'boundaries', 'creak', 'issues', 'flag'])

                ft_file_df = pd.DataFrame(columns=['file', 'label', 'group', 'color', 'number'])

                sil1 = call('Create Sound from formula', "silence", 1, 0, 0.025, 44100, "0")
                sil2 = call('Create Sound from formula', "silence", 1, 0, 0.025, 44100, "0")

                # Read in for reference OR just build in list/dictionary:
                vowelstoextract_df = pd.read_csv('/Users/laurettacheng/Documents/UM/UM_Research/LingTube/youspeak/dev/praat/vowelstoextract_default.csv')

            # TODO: Read in the 'vowel_coding_log.csv'
            if args.adjusted:
                log_path = path.join(adjusted_path, channel_id+"_all", "vowel_coding_log.csv")
                with open(log_path, 'rb') as f:
                    enc = chardet.detect(f.read())  # or readline if the file is large
                log_df = pd.read_csv(log_path, encoding = enc['encoding'])

            files_list = [fn for fn in listdir(tg_path) if not fn.startswith('.') and not fn.endswith('.txt')]
            files_list.sort(key=str.lower)

            for f_i, fn in enumerate(files_list):
                sound, textgrid = open_files_in_praat(fn, tg_path, audio_path)
                sound_name = path.splitext(fn)[0]
                sound_fn = sound_name + ".wav"
                fn_target_label = path.splitext(fn)[0].rsplit('_', 1)[1]

                if args.adjusted:
                    target_point_marker = call(textgrid, "Get time of point", 3, 1)
                    target_int = call(textgrid, "Get interval at time", 2, target_point_marker)
                    target_label = call(textgrid, "Get label of interval", 2, target_int)
                    if not target_label in target_list:
                        continue
                    # TODO: add check in case marked label is wrong/doesn't match expected vowel; write filename to textfile for manual checking
                    if target_label != fn_target_label:
                        with open(out_error_list, 'a+') as file:
                            file.write(fn+'\n')

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

                # Extract segmentation info
                for j, target_vowel in enumerate(extracted_vowels):
                    vowel_sound, int_start, int_end, vowel_label = target_vowel

                    int_vowel = vowel_label[:2]
                    int_stress = vowel_label[-1]
                    if int_vowel in diph:
                        int_diph = 1
                    else:
                        int_diph = 0

                    # Get label timing
                    int_dur =  (int_end - int_start)

                    # Get label word/sound info
                    if args.adjusted:
                        int_i = call(textgrid, "Get interval at time", 2, target_point_marker)
                        int_word_i = call(textgrid, "Get interval at time", 1, target_point_marker)
                        int_word = call(textgrid, 'Get label of interval', 1,
                                int_word_i)
                    else:
                        int_i = call(textgrid, 'Get interval at time', 2, int_start)
                        int_word_i = call(textgrid, 'Get interval at time', 1, int_start)
                        int_word = call(textgrid, 'Get label of interval', 1,
                                int_word_i)


                    # Get pre- and post-context
                    # for Sound
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

                    # for Word
                    try:
                        int_word_pre = call(textgrid, 'Get label of interval', 1, int_word_i-1)
                    except:
                        int_word_pre = None
                    try:
                        int_word_post = call(textgrid, 'Get label of interval', 1, int_word_i+1)
                    except:
                        int_word_post = None


                    # Add info to data output row
                    data_row = {'filename': sound_fn, 'label': vowel_label, 'start_time': int_start, 'end_time': int_end, 'duration': int_dur, 'pre_phone': int_pre, 'post_phone': int_post, 'word': int_word, 'vowel': int_vowel, 'stress': int_stress, 'diph': int_diph}

                    if args.adjusted:
                    # TODO: Read columns, split file column name to remove wav, add order, vowel label, boundaries, creak, and issues column
                        # print(sound_fn)
                        try:
                            v_idx = log_df.file[log_df.file==sound_fn].index[0]
                        except IndexError:
                            continue
                        data_row.update({'number': log_df.order.iloc[v_idx], 'boundaries': log_df.boundaries.iloc[v_idx], 'creak': log_df.creak.iloc[v_idx], 'issues': log_df.issues.iloc[v_idx], 'flag': log_df.flag.iloc[v_idx]})

                    if args.fasttrack:

                        # USE already extracted sound (no need for textgrid)
                        segment_sound = call([sil1, vowel_sound, sil2], 'Concatenate')

                        # extract sound + extra window
                        # tg_window = call(textgrid, 'Extract part', window_start, window_end, False)

                        # save extracted vowels
                        segment_name = '{0}_{1}'.format(sound_name, "target")
                        segment_sound.save(path.join(fasttrack_sounds_path, segment_name+".wav"), "WAV")
                        # tg_window.save(path.join(fasttrack_tgs_path, window_name+'.TextGrid'))

                        # Add all info to segmentation_info.csv
                        ft_data_row = {'inputfile': sound_name, 'outputfile': segment_name, 'vowel': int_vowel, 'interval': int_i, 'duration': int_dur, 'start': int_start, 'end': int_end, 'previous_sound': int_pre, 'next_sound': int_post, 'omit': 0, 'stress': int_stress, 'word': int_word, 'word_interval': int_word_i, 'word_start': "NA", 'word_end': "NA", 'previous_word': int_word_pre, 'next_word': int_word_post, 'diphthong': int_diph, 'number': log_df.order[v_idx], 'boundaries': log_df.boundaries[v_idx], 'creak': log_df.creak[v_idx], 'issues': log_df.issues[v_idx], 'flag': log_df.flag[v_idx]}

                        # write to DataFrame
                        ft_segment_df = ft_segment_df.append(ft_data_row, ignore_index=True, sort=False)

                        # Create file_information.csv
                        vte_idx = vowelstoextract_df.label[vowelstoextract_df.label==int_vowel].index[0]

                        ft_file_row = {'file': segment_name+".wav", 'label': int_vowel, 'group': vowelstoextract_df.group[vte_idx], 'color': vowelstoextract_df.color[vte_idx], 'number': log_df.order[v_idx]}

                        ft_file_df = ft_file_df.append(ft_file_row, ignore_index=True, sort=False)


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

            # Write to file
            if args.fasttrack:
                ft_segment_df.to_csv(path.join(fasttrack_path, "segmentation_information.csv"), index=False)
                # if not (args.stress == 1):
                #     ft_segment_df_stressed = ft_segment_df[ft_segment_df['stress']=='1']
                #     ft_segment_df_stressed.to_csv(path.join(fasttrack_path, "segmentation_information.csv"), index=False)
                ft_file_df.to_csv(path.join(fasttrack_path, "file_information.csv"), index=False)
            else:
                out_df.to_csv(path.join(out_data_path, out_fn), index=False)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get duration and formants from aligned audio chunks and textgrids (default=only duration).')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--adjusted', '-a', action='store_true', default=False, help='use hand-corrected, adjusted textgrids (under adjusted_corpus), identifying target vowel via point markers')
    parser.add_argument('--fasttrack', '-f', action='store_true', default=False, help='(adjusted only) extract adjusted vowels (w/ 25ms buffer) to fasttrack folder')
    parser.add_argument('--vowels', '-vo', help='list of vowels to target, comma-separated', type=str)
    parser.add_argument('--stress', '-st', help='list of stress values to target, comma-separated', type=str)
    parser.add_argument('--nucleus', '-n', action='store_true', default=False, help='extract nucleus midpoint formants (50 for mono; 30 for diph)')
    parser.add_argument('--onoff', '-onf', action='store_true', default=False, help='extract onset and offset formants (25 and 75)')
    parser.add_argument('--steps', '-s', action='store_true', default=False, help='extract formants at 30 steps between 20-80')
    parser.add_argument('--max_formant', '-mf', default=3, type=int, metavar='N', help='maximum number of formants to extract (default=3)')
    parser.add_argument('--formant_ceiling', '-fc', default=5500, type=int, metavar='N', help='formant ceiling value (Hz); typically 5500 for adult women, 5000 for adult men (default=5500)')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
