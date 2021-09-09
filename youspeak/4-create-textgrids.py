#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path
from shutil import rmtree, copy
from glob import glob
import pandas as pd
from re import sub, findall
from statistics import mean

import parselmouth
from parselmouth.praat import call, run_file


def main(args):
    mfa_only = 0

    # base paths
    raw_audio_base = path.join("corpus", "raw_audio")
    chunked_audio_base = path.join("corpus", "chunked_audio")
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        raw_audio_base = path.join(raw_audio_base, args.group)
        chunked_audio_base = path.join(chunked_audio_base, args.group)
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    dict_path = path.join(aligned_audio_base, "trained_models", "dictionary")

    # Get file info
    if args.channel:
        channel_list = [args.channel]
    else:
        channel_list = [channel_id for channel_id in listdir(path.join(chunked_audio_base, "logs", "coding")) if not channel_id.startswith('.')]

    for channel_id in channel_list:
        log_path = path.join(chunked_audio_base, "logs", "coding", channel_id)

        video_list = [fn.split('_coding')[0] for fn in listdir(log_path) if not fn.startswith('.')]

        for video_id in video_list:
            # output dirs
            out_audio_path = path.join(chunked_audio_base, "audio", "coding", channel_id, video_id)
            out_tg_path = path.join(chunked_audio_base, "textgrids", "coding", channel_id, video_id)

            # alignment dirs
            pre_align_path = path.join(aligned_audio_base, "original_corpus", channel_id, video_id)
            post_align_path = path.join(aligned_audio_base, "aligned_corpus", channel_id, video_id)
            aligner_path = path.join(aligned_audio_base, "mfa_aligner")

            if args.overwrite:
                if path.isdir(out_audio_path):
                    rmtree(out_audio_path)
                if path.isdir(out_tg_path):
                    rmtree(out_tg_path)
                if path.isdir(pre_align_path):
                    rmtree(pre_align_path)
                print("Overwriting audio and textgrid files for: {0}".format(video_id))
            else:
                if path.isdir(out_audio_path):
                    existing_audio = glob(path.join(out_audio_path, "**", "*{0}*".format(video_id)), recursive=True)
                else:
                    existing_audio = []
                if path.isdir(out_tg_path):
                    existing_tgs = glob(path.join(out_tg_path, "**", "*{0}*".format(video_id)), recursive=True)
                else:
                    existing_tgs = []
                existing_files = existing_audio + existing_tgs
                if existing_files:
                    if args.mfa:
                        print('Copying existing files to MFA compatible directory for: {0}'.format(video_id))
                        mfa_only = 1
                    else:
                        print("Audio and/or textgrid files exist. Skipping {0}".format(video_id))
                        continue

            # Get files
            full_audio_path = path.join(raw_audio_base, "wav", channel_id, video_id+'.wav')
            audio_path = path.join(chunked_audio_base, "audio", "chunking", channel_id, video_id)
            tg_path = path.join(chunked_audio_base, "textgrids", "chunking", channel_id, video_id, video_id+'.TextGrid')

            if not path.exists(out_tg_path):
                makedirs(out_tg_path)
            if args.save_chunks:
                if not path.exists(out_audio_path):
                    makedirs(out_audio_path)
            if args.mfa:
                for dir in [dict_path, pre_align_path, post_align_path, aligner_path]:
                    if not path.exists(dir):
                        makedirs(dir)

            if mfa_only == 1:
                if existing_tgs:
                    for fn in existing_tgs:
                        copy(fn, pre_align_path)
                if existing_audio:
                    for fn in existing_audio:
                        copy(fn, pre_align_path)
                else:
                    copy(full_audio_path, pre_align_path)
                continue

            file_path = path.join(log_path, video_id+'_coding_responses.csv')
            df = pd.read_csv(file_path)
            print('Processing audio chunks from: {0}'.format(video_id))

            # Start audio-textgrid processing
            original_tg = parselmouth.read(tg_path)
            full_tg = call(original_tg, 'Extract one tier', 1)
            call(full_tg, 'Replace interval texts', 1, 1, 0, '.*', '', 'Regular Expressions')
            call(full_tg, 'Set tier name', 1, 'sentence') # for Darla compatibility

            if args.save_chunks:
                sil1 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")
                sil2 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")

            loop_start = 0

            for i in df['id']:
                row = df.iloc[i]
                if row['usability'] == 1 and not pd.isnull(row['transcription']):

                    # By-timestamp full TextGrid modification
                    if not args.save_chunks:
                        int_center = mean([int(row['start_time']), int(row['end_time'])])/1000
                        current_int = call(full_tg, 'Get interval at time', 1, int_center)
                        call(full_tg, 'Set interval text', 1, current_int, row['transcription'])

                        # Save to local dir
                        full_tg.save(path.join(out_tg_path, video_id+'.TextGrid'))

                        if args.mfa:
                            # Save copy to temp MFA pre-alignment dir
                            full_tg.save(path.join(pre_align_path, video_id+'.TextGrid'))

                            if loop_start == 0:
                                sound = parselmouth.Sound(full_audio_path)
                                sound.save(path.join(pre_align_path, video_id+'.wav'), "WAV")
                                loop_start = 1


                    # By-WAV file TextGrid creation
                    else:
                        name, ext = path.splitext(row['filename'])
                        wav_fn = path.join(audio_path, row['filename'])

                        sound = parselmouth.Sound(wav_fn)
                        sound = call([sil1, sound, sil2], 'Concatenate')
                        sound_start = sound.get_start_time()
                        sound_end = sound.get_end_time()

                        textgrid = call(sound, 'To TextGrid', 'utterance', '')
                        # tiers = call(textgrid, 'Get number of tiers')
                        call(textgrid, 'Insert boundary', 1, sound_start+0.25)
                        call(textgrid, 'Insert boundary', 1, sound_end-0.25)
                        call(textgrid, 'Set interval text', 1, 2, row['transcription'])

                        # Save to local dir
                        sound.save(path.join(out_audio_path, name+'.wav'), "WAV")
                        textgrid.save(path.join(out_tg_path, name+'.TextGrid'))

                        if args.mfa:
                            # Save copy to temp MFA pre-alignment dir
                            sound.save(path.join(pre_align_path, name+'.wav'), "WAV")
                            textgrid.save(path.join(pre_align_path, name+'.TextGrid'))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create MFA-compatible textgrids and move to MFA alignment folder.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: chunked_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--save_chunks', '-s', action='store_true', default=False, help='save chunked textgrids and sound files; default only saves full textgrid')
    parser.add_argument('--mfa', action='store_true', default=False, help='copy textgrids and audio into MFA compatible directory structure under aligned_audio/$group; default does not create directory')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
