#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path
from glob import glob
import pandas as pd
from re import sub, findall
from statistics import mean

import parselmouth
from parselmouth.praat import call, run_file


def main(args):

    # base paths
    raw_audio_base = path.join("corpus", "raw_audio")
    print(raw_audio_base)
    chunked_audio_base = path.join("corpus", "chunked_audio")
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        raw_audio_base = path.join(raw_audio_base, args.group)
        chunked_audio_base = path.join(chunked_audio_base, args.group)
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    dict_path = path.join(aligned_audio_base, "trained_models", "dictionary")
    dict_fp = path.join(dict_path, "word_list.txt")
    update_fp = path.join(dict_path, "update_list.txt")
    if args.overwrite:
        file = open(dict_fp, "w")
        file.close()

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

            if path.isdir(out_audio_path) and not args.overwrite:
                existing_files = glob(path.join(out_audio_path, "**", "*{0}*".format(video_id)), recursive=True)
                if existing_files:
                    continue


            full_audio_path = path.join(raw_audio_base, "wav", channel_id, video_id+'.wav')
            audio_path = path.join(chunked_audio_base, "audio", "chunking", channel_id, video_id)
            tg_path = path.join(chunked_audio_base, "textgrids", "chunking", channel_id, video_id, video_id+'.TextGrid')
            file_path = path.join(log_path, video_id+'_coding_responses.csv')

            df = pd.read_csv(file_path)
            print('Processing audio chunks from: {0}'.format(video_id))

            # alignment dirs
            pre_align_path = path.join(aligned_audio_base, "original_corpus", channel_id, video_id)
            post_align_path = path.join(aligned_audio_base, "aligned_corpus", channel_id, video_id)
            aligner_path = path.join(aligned_audio_base, "mfa_aligner")
            adjusted_queue_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id, video_id, "queue")
            adjusted_audio_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id, video_id, "audio")
            adjusted_tg_path = path.join(aligned_audio_base, "adjusted_corpus", channel_id, video_id, "textgrids")

            for dir in [dict_path, out_audio_path, out_tg_path, pre_align_path, post_align_path, aligner_path, adjusted_queue_path, adjusted_audio_path, adjusted_tg_path]:
                if not path.exists(dir):
                    makedirs(dir)

            # Start audio-textgrid processing
            original_tg = parselmouth.read(tg_path)
            full_tg = call(original_tg, 'Extract one tier', 1)
            call(full_tg, 'Replace interval texts', 1, 1, 0, '.*', '', 'Regular Expressions')
            # call(full_tg, 'Insert interval tier', 2, 'transcript')

            sil1 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")
            sil2 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")

            loop_start = 0
            # transcript_list = []
            word_list = []

            for i in df['id']:
                row = df.iloc[i]
                if row['usability'] == 1 and not pd.isnull(row['transcription']):

                    # By-timestamp full TextGrid modification
                    if args.full:
                        int_center = mean([int(row['start_time']), int(row['end_time'])])/1000
                        current_int = call(full_tg, 'Get interval at time', 1, int_center)
                        call(full_tg, 'Set interval text', 1, current_int, row['transcription'])

                        if loop_start == 0:
                            # Add transcript start boundary
                            # call(full_tg, 'Insert boundary', 2, call(full_tg, 'Get start time of interval', 1, current_int))
                            loop_start = 1

                            # Save copy to temp MFA pre-alignment dir
                            sound = parselmouth.Sound(full_audio_path)
                            sound.save(path.join(pre_align_path, video_id+'.wav'), "WAV")

                        full_tg.save(path.join(out_tg_path, video_id+'.TextGrid'))
                        full_tg.save(path.join(pre_align_path, video_id+'.TextGrid'))


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

                        # Save copy to temp MFA pre-alignment dir
                        sound.save(path.join(pre_align_path, name+'.wav'), "WAV")
                        textgrid.save(path.join(pre_align_path, name+'.TextGrid'))

                    # Word list creation
                    # transcript_list.append(row['transcription'])

                    punc = "[\.\?\!,;:\"\\\/]+"
                    word_list = word_list + [sub(punc, '', word) for word in row['transcription'].split()]

            # Add transcript end boundary
            # call(full_tg, 'Insert boundary', 2, call(full_tg, 'Get end time of interval', 1, current_int))
            # call(full_tg, 'Set interval text', 2, 2, ' '.join(transcript_list))
            # full_tg.save(path.join(chunked_audio_base, "textgrids", "coding", channel_id, video_id+'.TextGrid'))

            # Add to word list for dictionary generation
            with open(dict_fp, "a+") as word_file, open(update_fp, "a+") as update_file:
                word_file.seek(0)
                word_contents = word_file.read().split('\n')
                for word in set(word_list):
                    if not word in word_contents:
                        update_file.seek(0)
                        update_words = findall(r"\b(.+)\t", update_file.read())
                        if word.isupper() and "-" not in word:
                            if not sub("\-","",word.lower()) in update_words:
                                update_file.write(word.lower()+'\n')
                        word_file.write(word.lower()+'\n')

    out_message = path.join(aligned_audio_base, "adjusted_corpus", "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for aligned audio files (found within the "queue" folder of each video sub-folder) go here.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create MFA-compatible textgrids and move to MFA alignment folder.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: aligned_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--full', '-f', action='store_true', default=False, help='add transcript to full audio and textgrid (not chunked audio)')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
