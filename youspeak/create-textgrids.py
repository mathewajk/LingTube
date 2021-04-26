#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path
from glob import glob
import pandas as pd

import parselmouth
from parselmouth.praat import call, run_file


def main(args):

    # base paths
    chunked_audio_base = path.join("corpus", "chunked_audio")
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        chunked_audio_base = path.join(chunked_audio_base, args.group)
        aligned_audio_base = path.join(aligned_audio_base, args.group)

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

            audio_path = path.join(chunked_audio_base, "audio", "chunking", channel_id, video_id)
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

            for dir in [out_audio_path, out_tg_path, pre_align_path, post_align_path, aligner_path, adjusted_queue_path, adjusted_audio_path, adjusted_tg_path]:
                if not path.exists(dir):
                    makedirs(dir)

            # Start audio-textgrid processing
            sil1 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")
            sil2 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")

            for i in df['id']:
                row = df.iloc[i]
                if row['usability'] == 1:
                    if not pd.isnull(row['transcription']):

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

    out_message = path.join(aligned_audio_base, "adjusted_corpus", "README.md")
    with open(out_message, 'w') as file:
        file.write('Channel folders for aligned audio files (found within the "queue" folder of each video sub-folder) go here.')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create MFA-compatible textgrids and move to MFA alignment folder.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: aligned_audio/$group)')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
