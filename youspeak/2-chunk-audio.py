#!/usr/bin/env python3

import argparse
from os import path, listdir, makedirs, remove
from glob import glob
import pandas as pd
from shutil import rmtree
import parselmouth
from parselmouth.praat import call, run_file
import tempfile
import ffmpeg
import librosa
import torch
from samplecnn import SampleCNN

def get_silence_threshold(sound, lower_quantile):
    """ Calculates silence threshold per sound interval for chunking.

    :param sound: A parselmouth.praat Sound object
    :param lower_quantile: A quantile value (0-1; e.g., 0.5 = median)

    :return sil_threshold: Threshold value to be used for 'To TextGrid (silences)'
    """
    soundint = sound.to_intensity()
    max_intensity = call(soundint, 'Get quantile', 0.0, 0.0, 1)
    sil_intensity = call(soundint, 'Get quantile', 0.0, 0.0, lower_quantile)
    return sil_intensity - max_intensity

def detect_silences(sound, sil_threshold, sil_duration):
    """ Wrapper to run Praat 'To Textgrid (silences)' function.

    :param sound: A parselmouth.praat Sound object (or a list of such objects)
    :param sil_threshold: Silence threshold value (dB) (e.g., -25)
    :param sil_duration: Minimum silence interval duration (s) (e.g., 0.1)

    :return textgrid: (List of) TextGrid object(s) marked with silent/speech intervals
    """
    textgrid = call(sound, 'To TextGrid (silences)', 100, 0.0, sil_threshold, sil_duration, 0.1, 'silence', 'speech')

    return textgrid

def extract_intervals(sound, textgrid, adjustment):
    sound_start = sound.get_start_time()
    sound_end = sound.get_end_time()


    total_ints = call(textgrid, 'Get number of intervals', 1)
    first_label = call(textgrid,'Get label of interval', 1, 1)


    if first_label == 'speech':
        speech_ints = range(1, total_ints, 2)
    else:
        speech_ints = range(2, total_ints, 2)

    extracted_sounds = []
    for int_num in speech_ints:
        int_start = call(textgrid,'Get start time of interval', 1, int_num)
        int_end = call(textgrid,'Get end time of interval', 1, int_num)

        # Adjust extraction segment
        int_start = int_start - adjustment
        if int_start < sound_start: int_start = sound_start
        int_end = int_end + adjustment
        if int_end > sound_end: int_end = sound_end

        ext_sound = call(sound, 'Extract part', int_start, int_end,
                        'rectangular', 1.0, True)
        extracted_sounds.append(ext_sound)

        chunk_start_ms = call(ext_sound, 'Get start time')
        chunk_end_ms = call(ext_sound, 'Get end time')

    return extracted_sounds

def chunk_sound (sound, sil_duration, threshold_quantile):
    sil_threshold = get_silence_threshold(sound, threshold_quantile)
    textgrid = detect_silences(sound, sil_threshold, sil_duration)

    n_ints = call(textgrid, 'Count intervals where',
                        1, 'is equal to', 'speech')

    extracted_sounds = call([sound, textgrid],
                            'Extract intervals where',
                            1, True, 'is equal to', 'speech')

    return textgrid, extracted_sounds, n_ints

def save_chunks(chunk_sound, out_path, video_id):
    """ Saves chunked speech intervals as WAV file.

    :param chunk_sound: A parselmouth.praat Sound object
    # :param adjustment: The padding time on either side of target speech
    :param out_path: The output path of the wav file
    :param video_id: The original soundfile name (w/o ext)

    :return logfile_entry: Row with chunk metadata to be written to log
    """
    chunk_start_ms = int(chunk_sound.get_start_time()*1000)
    chunk_end_ms = int(chunk_sound.get_end_time()*1000)
    chunk_duration = chunk_end_ms - chunk_start_ms

    chunk_fn = '{0}_{1}_{2}.wav'.format(video_id, chunk_start_ms, chunk_end_ms)
    chunk_file_path = path.join(out_path, chunk_fn)
    chunk_sound.save(chunk_file_path, 'WAV')

    return {'filename': chunk_fn, 'video_id': video_id, 'start_time': chunk_start_ms, 'end_time': chunk_end_ms, 'duration': chunk_duration}

# Music discriminator based on samplecnn-speech-detection
# Copyright (c) 2019 F. Moukayed (Κοτσάμπ)
# https://github.com/fmqa/samplecnn-speech-detection
def detect_music(audiofile, sound, alpha):
    youspeak_path = path.dirname(path.realpath(__file__))
    model_path = path.join(youspeak_path, "models", "model-gztan-speech-music-20000.pth")

    with tempfile.TemporaryDirectory(suffix="-discriminator") as tmpdir:
        textgrid = call(sound, 'To TextGrid', 'music music-by-sec', '')

        # Convert input to proper format (16 kHz, mono)
        output = path.join(tmpdir, "16khz.wav")
        (
            ffmpeg.input(audiofile)
                  .output(output, format="wav", acodec="pcm_s16le", ac=1, ar="16k")
                  .overwrite_output()
                  .run()
        )
        # Instantiate CNN
        net = SampleCNN()
        net.load_state_dict(torch.load(model_path))
        net.eval()
        count_list = []
        with torch.no_grad():
            # Iterate through frames
            for sec, frame in enumerate(map(torch.Tensor, librosa.core.stream(output, 1, 59049, 16000, fill_value=0))):
                y = net(frame.reshape(1, -1))
                y = y.item()

                if sec == 0:
                    if y > args.alpha:
                        y_status = current_status = 'speech'
                    else:
                        y_status = current_status = 'music'
                    call(textgrid, 'Set interval text', 1, 1, current_status)
                elif current_status == 'speech':
                    if y < args.alpha:
                        y_status = 'music'
                    else:
                        y_status = current_status
                elif current_status == 'music':
                    if y > (1 - args.alpha):
                        y_status = 'speech'
                    else:
                        y_status = current_status

                try:
                    call(textgrid, 'Insert boundary', 2, sec)
                except:
                    pass
                interval_num = call(textgrid, 'Get interval at time', 2, sec)
                call(textgrid, 'Set interval text', 2, interval_num, '{0} ({1})'.format('speech' if y > alpha else 'music', round(y,3)))

                if not y_status == current_status:
                    count_list.append((sec, y))
                else:
                    count_list = []

                if len(count_list) == 4:
                    current_status = y_status
                    # print('Insert boundary at time: {0}'.format(count_list[0][0]))
                    try:
                        call(textgrid, 'Insert boundary', 1, count_list[0][0])
                    except:
                        pass
                    interval_num = call(textgrid, 'Get interval at time', 1, count_list[0][0])
                    call(textgrid, 'Set interval text', 1, interval_num, current_status)

        return textgrid


def process_soundfile(fn, audio_path, chunk_path, alpha=0.1, overwrite=False, textgrid_only=False, music_detection=False):

    video_id, ext = path.splitext(fn)

    if ext == '.wav':
        channel_id, yt_id = video_id.rsplit('_',1)

        sound_path = path.join(chunk_path, "audio", "chunking", channel_id, video_id)
        tg_path = path.join(chunk_path, "textgrids", "chunking", channel_id, video_id)
        log_path = path.join(chunk_path, "logs", "chunking", channel_id)

        # Check overwrite status
        if path.isdir(sound_path) and not overwrite:
            existing_files = glob(path.join(sound_path, "**", "*{0}*".format(video_id)), recursive=True)
            if existing_files:
                return 1
        elif path.isdir(sound_path) and overwrite:
            shutil.rmtree(sound_path)

        tg_fn = path.join(tg_path, video_id+'.TextGrid')
        if textgrid_only:
            if path.exists(tg_fn) and not overwrite:
                return 2
            elif path.exists(tg_fn) and overwrite:
                remove(tg_fn)

        # Start process
        if not path.exists(tg_path):
            makedirs(tg_path)

        if not textgrid_only:
            # Create log file
            log_file = path.join(log_path, video_id+'_chunking_log.csv')
            if not path.exists(log_path):
                makedirs(log_path)

            output_df = pd.DataFrame(columns=['filename','video_id',
                                              'start_time','end_time', 'duration'])
            output_df.to_csv(log_file, index=False)

            # Create output directory
            if not path.exists(sound_path):
                makedirs(sound_path)

        # Start audio processing
        print('\nCURRENT FILE: {0}'.format(fn))

        wav_fn = path.join(audio_path, fn)
        sound = parselmouth.Sound(wav_fn).convert_to_mono()

        if path.exists(tg_fn):
            print('Chunking speech from existing TextGrid...')
            textgrid = parselmouth.read(tg_fn)
            extracted_sounds = call([sound, textgrid],
                                    'Extract intervals where',
                                    1, True, 'is equal to', 'speech')
            for subsound in extracted_sounds:
                log_entry = save_chunks(subsound, sound_path, video_id)
                output_df = output_df.append(log_entry, ignore_index=True)
            output_df = output_df.sort_values(by=["start_time"])
            output_df.to_csv(log_file, mode='a', index=False, header=False)
            return 3

        if music_detection:
            print('Music detection in progress...')
            base_textgrid = detect_music(wav_fn, sound, alpha)
            #base_textgrid.save(path.join(tg_path, video_id+'_music.TextGrid'))

            n_ints = call(base_textgrid, 'Count intervals where',
                                1, 'is equal to', 'speech')

            extracted_speech = call([sound, base_textgrid],
                                    'Extract intervals where',
                                    1, True, 'is equal to', 'speech')

            call(base_textgrid, 'Duplicate tier', 1, 1, 'speech')
            call(base_textgrid, 'Replace interval texts', 1, 1, 0, 'speech', '', 'literals')

            if n_ints <=1:
                extracted_sounds_1 = [extracted_speech]
            else:
                extracted_sounds_1 = extracted_speech

        else:
            print('First pass chunking in progress...')
            # Use a more conservative 0.5 sec silence to get larger chunks

            sil_duration = 0.25
            quantile = 0.05
            (base_textgrid, extracted_sounds_1, n_ints) = chunk_sound(sound, sil_duration, quantile)

            while n_ints <= 1:
                quantile += 0.025
                (base_textgrid, extracted_sounds_1, n_ints) = chunk_sound(sound, sil_duration, quantile)

            call(base_textgrid, 'Duplicate tier', 1, 1, 'speech')
            call(base_textgrid, 'Replace interval texts', 1, 1, 0, 'silence', '', 'Regular Expressions')

        print('Iterative chunking in progress...')
        counter = -1
        stage = -1
        quantile = 0.025
        sil_duration = 0.3
        duration_cutoff = [5, 7.5, 7.5, 10, 15, 15, -1]

        while len(extracted_sounds_1) > 0:
            counter += 1

            # TESTER
            # call(base_textgrid, 'Duplicate tier', 1, 1, 'silences-{0}'.format(counter))
            # call(base_textgrid, 'Replace interval texts', 1, 1, 0, '.*', '', 'Regular Expressions')
            # base_textgrid.save(tg_fn)

            if counter % 5 == 0:
                stage +=1
                print('* Stage: {0}'.format(stage))
                if stage < 3:
                    sil_duration -= 0.05
                else:
                    sil_duration -= 0.025

            current_cutoff = duration_cutoff[stage]

            # TESTER
            # print('Counter: {0}'.format(counter))
            # print('Duration: {0}'.format(sil_duration))

            for subsound in extracted_sounds_1:
                duration = subsound.get_total_duration()

                if duration <= current_cutoff or stage == 6:
                    if not textgrid_only:
                        log_entry = save_chunks(subsound, sound_path, video_id)
                        output_df = output_df.append(log_entry, ignore_index=True)

                    extracted_sounds_1.remove(subsound)

                else:
                    (subtextgrid, extracted_subsounds, n_ints) = chunk_sound(subsound, sil_duration, quantile)

                    if n_ints > 1:
                        extracted_sounds_1.remove(subsound)
                        extracted_sounds_1 = extracted_sounds_1 + extracted_subsounds

                        for subsound in extracted_subsounds:
                            subsound_start = subsound.get_start_time()
                            subsound_end = subsound.get_end_time()
                            try:
                                call(base_textgrid, 'Insert boundary', 1, subsound_start)
                                # print(subsound_start)
                            except:
                                pass
                                # print('\nNo boundary inserted at time {0}.'.format(subsound_start))
                            try:
                                call(base_textgrid, 'Insert boundary', 1, subsound_end)
                                # print(subsound_end)
                            except:
                                pass
                                # print('\nNo boundary inserted at time {0}.'.format(subsound_end))

                            interval_num = call(base_textgrid, 'Get interval at time', 1, subsound_start)
                            call(base_textgrid, 'Set interval text', 1, interval_num, 'speech')

                            # TESTER
                            # base_textgrid.save(tg_fn)

                    elif n_ints == 0:
                        print('No sounds extracted.')
                    elif n_ints == 1:
                        extracted_sounds_1.remove(subsound)
                        extracted_sounds_1.append(extracted_subsounds)

        if not textgrid_only:
            output_df = output_df.sort_values(by=["start_time"])
            output_df.to_csv(log_file, mode='a', index=False, header=False)

        # Save second-pass TextGrid
        base_textgrid.save(tg_fn)

def process_videos(group, channel, video, textgrid_only, overwrite, music_detection, alpha):

    chunk_path = path.join('corpus','chunked_audio')
    audio_path = path.join('corpus','raw_audio', "wav")
    if group:
        chunk_path = path.join('corpus','chunked_audio', group)
        audio_path = path.join('corpus','raw_audio', group, "wav")

    if video:
        fn = video+'.wav'
        channel_id = video.rsplit('_',1)[0]
        channel_audio_path = path.join(audio_path, channel_id)
        process_soundfile(fn, channel_audio_path, chunk_path, alpha, overwrite, textgrid_only, music_detection)

    elif channel and not video:
        channel_list = [channel]
    elif not channel and not video:
        channel_list = [dir_element for dir_element in listdir(audio_path) if path.isdir(path.join(audio_path, dir_element))]

    if not video:
        for channel_id in channel_list:
            channel_audio_path = path.join(audio_path, channel_id)
            for fn in listdir(channel_audio_path):
                process_soundfile(fn, channel_audio_path, chunk_path, alpha, overwrite, textgrid_only, music_detection)

    out_message = path.join(chunk_path, "audio", "chunking", "README.md")
    if path.exists(path.join(chunk_path, "audio", "chunking")) and not path.exists(out_message):
        with open(out_message, 'w') as file:
            file.write('Channel folders for chunked audio files (with sub-folders for each original video source) go here.')

def chunk_voice(args):
    """Wrapper for chunking with voice activity detection"""
    music_detection = False
    alpha = None
    process_videos(args.group, args.channel, args.video, args.textgrid_only, args.overwrite, music_detection, alpha)

def chunk_music(args):
    """Wrapper for chunking with music detection"""
    music_detection = True
    alpha = args.alpha
    process_videos(args.group, args.channel, args.video, args.textgrid_only, args.overwrite, music_detection, alpha)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Chunk WAV audio files into short segments of sound.')
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(help='use voice activity detection or music detection (beta ver.) for first-pass audio chunking')

    voice_parser = subparsers.add_parser('voice', help='use voice activity detection for first-pass audio chunking (see 2-chunk-audio.py voice -h for more help)')
    voice_parser.set_defaults(func=chunk_voice)
    voice_parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_subtitles/$group)')
    voice_parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    voice_parser.add_argument('--video', '-v', default=None, type=str, help='run on files for a video id; if unspecified, goes through all videos in order')
    voice_parser.add_argument('--textgrid_only', '-tg', action='store_true', default=False, help='only output textgrid with detected speech; no chunked sound files will be saved')
    voice_parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    music_parser = subparsers.add_parser('music', help='(BETA) use music detection for first-pass audio chunking (see 2-chunk-audio.py music -h for more help)')
    music_parser.set_defaults(func=chunk_music)
    music_parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_subtitles/$group)')
    music_parser.add_argument('--channel', '-ch', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    music_parser.add_argument('--video', '-v', default=None, type=str, help='run on files for a video id; if unspecified, goes through all videos in order')
    music_parser.add_argument('--textgrid_only', '-tg', action='store_true', default=False, help='only output textgrid with detected speech; no chunked sound files will be saved')
    music_parser.add_argument('--alpha', '-a', default=0.1, type=float, help='Cutoff point to detect as music  (0-1), where 0=music and 1=speech')
    music_parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    if(args.func == None):
        parser.print_help()
        exit(2)

    args.func(args)
