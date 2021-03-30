#!/usr/bin/env python3

import argparse
from os import path, listdir, makedirs
import re
import pandas as pd
import parselmouth
from parselmouth.praat import call, run_file


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
    # print(sound_start, sound_end)

    total_ints = call(textgrid, 'Get number of intervals', 1)
    first_label = call(textgrid,'Get label of interval', 1, 1)
    # print(total_ints)
    # print(first_label)

    if first_label == 'speech':
        speech_ints = range(1, total_ints, 2)
    else:
        speech_ints = range(2, total_ints, 2)
    # print(speech_ints)

    extracted_sounds = []
    for int_num in speech_ints:
        # print(int_num)
        int_start = call(textgrid,'Get start time of interval', 1, int_num)
        int_end = call(textgrid,'Get end time of interval', 1, int_num)
        # print(int_start, int_end)

        # Adjust extraction segment
        int_start = int_start - adjustment
        if int_start < sound_start: int_start = sound_start
        int_end = int_end + adjustment
        if int_end > sound_end: int_end = sound_end
        # print(int_start, int_end)

        ext_sound = call(sound, 'Extract part', int_start, int_end,
                        'rectangular', 1.0, True)
        extracted_sounds.append(ext_sound)

        chunk_start_ms = call(ext_sound, 'Get start time')
        chunk_end_ms = call(ext_sound, 'Get end time')
        # print(chunk_start_ms, chunk_end_ms)

    return extracted_sounds

def chunk_sound (sound, sil_duration, threshold_quantile, tgpath, name):
    sil_threshold = get_silence_threshold(sound, threshold_quantile)
    textgrid = detect_silences(sound, sil_threshold, sil_duration)

    n_ints = call(textgrid, 'Count intervals where',
                        1, 'is equal to', 'speech')
    print('Intervals containing speech: {0}'.format(n_ints))

    # Save first-pass TextGrid now for checking
    # TODO: Add folder for different passes
    if not path.exists(tgpath):
        makedirs(tgpath)
    tg_filename = path.join(tgpath, name+'.TextGrid')
    textgrid.save(tg_filename)

    print('Extracting intervals...\n')
    # extracted_sounds_1 = extract_intervals(sound, textgrid, 0.25)
    extracted_sounds = call([sound, textgrid],
                            'Extract intervals where',
                            1, True, 'is equal to', 'speech')

    return extracted_sounds, n_ints

def save_chunks(chunk_sound, outputpath, name):
    """ Saves chunked speech intervals as WAV file.

    :param chunk_sound: A parselmouth.praat Sound object
    # :param adjustment: The padding time on either side of target speech
    :param outputpath: The output path of the wav file
    :param name: The original soundfile name (w/o ext)

    :return logfile_entry: Row with chunk metadata to be written to log
    """
    chunk_start_ms = int(call(chunk_sound, 'Get start time')*1000)
    chunk_end_ms = int(call(chunk_sound, 'Get end time')*1000)
    chunk_duration = chunk_end_ms - chunk_start_ms

    chunk_name = '{0}_{1}_{2}.wav'.format(name, chunk_start_ms, chunk_end_ms)
    chunk_filename = path.join(outputpath, chunk_name)
    chunk_sound.save(chunk_filename, 'WAV')
    print('Saved {0}!'.format(chunk_name))

    return {'filename': chunk_name, 'video_id': name, 'start_time': chunk_start_ms, 'end_time': chunk_end_ms, 'duration': chunk_duration}
    # return '{0}\t{1}\t{2}\t{3}\n'.format(chunk_name, name, chunk_start_ms, chunk_end_ms)

    # TODO: add time before and after each chunk boundary (.25 s?)

def process_soundfile(filename, audiopath, chunkpath):

    name, ext = path.splitext(filename)

    if ext == '.wav':
        if not re.match(r".*_\d+$",name):
            # If filenames do include video titles
            video_id = name.rsplit('_',1)[0]
            channel = video_id.rsplit('_',1)[0]
        else:
            video_id = name
            channel = video_id.rsplit('_',1)[0]

        soundpath = path.join(chunkpath, "audio", "chunking", channel, video_id)
        tgpath = path.join(chunkpath, "textgrids", "chunking", channel, video_id)
        logpath = path.join(chunkpath, "logs", "chunking", channel)

        # Create log file
        log_file = path.join(logpath, video_id+'_chunking_log.csv')
        if not path.exists(logpath):
            makedirs(logpath)

        output_df = pd.DataFrame(columns=['filename','video_id',
                                          'start_time','end_time', 'duration'])
        output_df.to_csv(log_file, index=False)


        # Create output directory
        if not path.exists(soundpath):
            makedirs(soundpath)


        # Start audio processing
        print('\nCURRENT FILE: {0}'.format(filename))

        wav_filename = path.join(audiopath, filename)
        sound = parselmouth.Sound(wav_filename).convert_to_mono()


        print('First pass chunking in progress...\n')
        # Use a more conservative 0.5 sec silence to get larger chunks

        sil_duration = 0.25
        quantile = 0.05
        (extracted_sounds_1, n_ints) = chunk_sound(sound, sil_duration, quantile, tgpath, video_id)

        while n_ints <= 1:
            # sil_duration -= 0.025
            quantile += 0.025
            extracted_sounds_1 = chunk_sound(sound, sil_duration, quantile, tgpath, video_id)
            # input()

        print('Second pass chunking in progress...\n')
        counter = -1
        sil_duration = 0.1
        quantile = 0.025
        while len(extracted_sounds_1) > 0:
            counter += 1
            # print('Counter: {0}'.format(counter))
            # print(len(extracted_sounds_1))

            if counter > 0 and counter % 1 == 0:
                if not counter % 5 == 0:
                    sil_duration += 0.05
                    # print('Duration: {0}'.format(sil_duration))
                    # input()
            if counter > 0 and counter % 5 == 0:
                sil_duration = 0.1
                # print('Duration: {0}'.format(sil_duration))
                # quantile += 0.025
                # print('Quantile: {0}'.format(quantile))
                # input()

            for subsound in extracted_sounds_1:
                duration = subsound.get_total_duration()
                print(counter, duration)
                if duration <= 10:
                    log_entry = save_chunks(subsound, soundpath, video_id)
                    output_df = output_df.append(log_entry, ignore_index=True)
                    extracted_sounds_1.remove(subsound)
                    # input()
                else:
                    n_ints = -1
                    sub_quantile = 0.025
                    while n_ints <= 1:
                        (extracted_subsounds, n_ints) = chunk_sound (subsound, sil_duration, sub_quantile, tgpath, video_id)

                        if n_ints > 1:
                            extracted_sounds_1.remove(subsound)
                            for s in extracted_subsounds:
                                duration = s.get_total_duration()
                                print(counter, duration)
                            extracted_sounds_1 = extracted_sounds_1 + extracted_subsounds
                            # input()
                            break
                        else:
                            sub_quantile += 0.025

        output_df = output_df.sort_values(by=["start_time"])
        output_df.to_csv(log_file, mode='a', index=False, header=False)

def main(args):

    chunkpath = path.join('corpus','chunked_audio')

    if args.group:
        chunkpath = path.join('corpus','chunked_audio', args.group)
        audiopath = path.join('corpus','raw_audio', args.group, "wav")
    else:
        audiopath = path.join('corpus','raw_audio', "wav")

    for dir_element in listdir(audiopath):

        if path.isdir(path.join(audiopath, dir_element)):
            channel_audiopath = path.join(audiopath, dir_element)
            for filename in listdir(channel_audiopath):
                process_soundfile(filename, channel_audiopath, chunkpath)
        else:
            process_soundfile(dir_element, audiopath, chunkpath)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Chunk WAV audio files into short segments of sound.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')

    args = parser.parse_args()

    main(args)
