#!/usr/bin/env python3

import argparse
import os
from os import listdir, makedirs, path
import shutil
import pandas as pd

import parselmouth
from parselmouth.praat import call, run_file


def main(args):

    # base paths
    chunked_audio_base = path.join("corpus", "chunked_audio")
    aligned_audio_base = path.join("corpus", "aligned_audio")

    if not args.group == None:
        chunked_audio_base = path.join(chunked_audio_base, args.group)
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    # Get file info
    if not args.channel == None:
        channel_list = [args.channel]
    else:
        channel_list = [channel for channel in listdir(path.join(chunked_audio_base, "logs", "coding")) if not channel.startswith('.')]

    for channel in channel_list:
        logpath = path.join(chunked_audio_base, "logs", "coding", channel)

        if not args.video == None:
            video_id = '{0}_{1}'.format(channel, args.video)
            video_list = [video_id]
            # print(video_list)
        else:
            video_list = [fname.split('_coding')[0] for fname in listdir(logpath) if not fname.startswith('.')]
            # print(video_list)

        for video_id in video_list:
            audpath = path.join(chunked_audio_base, "audio", "chunking", channel, video_id)
            fname = path.join(logpath, video_id+'_coding_responses.csv')

            df = pd.read_csv(fname)
            print('Processing audio chunks from: {0}'.format(video_id))

            # output dirs
            out_audpath = path.join(chunked_audio_base, "audio", "coding", channel, video_id)
            out_tgpath = path.join(chunked_audio_base, "textgrids", "coding", channel, video_id)

            # alignment dirs
            prealignpath = path.join(aligned_audio_base, "original_corpus", channel, video_id)
            postalignpath = path.join(aligned_audio_base, "aligned_corpus", channel, video_id)
            alignerpath = path.join(aligned_audio_base, "mfa_aligner")

            for dir in [out_audpath, out_tgpath, prealignpath, postalignpath, alignerpath]:
                if not path.exists(dir):
                    makedirs(dir)

            # Start audio-textgrid processing
            sil1 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")
            sil2 = call('Create Sound from formula', "silence", 1, 0, 0.25, 44100, "0")

            for i in df['id']:
                row = df.iloc[i]
                if row['quality'][0] == '1':
                    if not pd.isnull(row['transcription']):

                        name, ext = path.splitext(row['filename'])
                        wav_filename = path.join(audpath, row['filename'])

                        sound = parselmouth.Sound(wav_filename)
                        sound = call([sil1, sound, sil2], 'Concatenate')
                        sound_start = sound.get_start_time()
                        sound_end = sound.get_end_time()

                        textgrid = call(sound, 'To TextGrid', 'utterance', '')
                        # tiers = call(textgrid, 'Get number of tiers')
                        call(textgrid, 'Insert boundary', 1, sound_start+0.25)
                        call(textgrid, 'Insert boundary', 1, sound_end-0.25)
                        call(textgrid, 'Set interval text', 1, 2, row['transcription'])

                        # Save to local dir
                        sound.save(path.join(out_audpath, name+'.wav'), "WAV")
                        textgrid.save(path.join(out_tgpath, name+'.TextGrid'))

                        # Save copy to temp MFA pre-alignment dir
                        sound.save(path.join(prealignpath, name+'.wav'), "WAV")
                        textgrid.save(path.join(prealignpath, name+'.TextGrid'))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Create MFA-compatible textgrids and move to MFA alignment folder.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--video', '-v', default=None, type=str, help='video number')

    args = parser.parse_args()

    main(args)
