# Chunks WAV file into short segments based on silence/breath breaks

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
    print(sound_start, sound_end)

    total_ints = call(textgrid, 'Get number of intervals', 1)
    first_label = call(textgrid,'Get label of interval', 1, 1)
    print(total_ints)
    print(first_label)

    if first_label == 'speech':
        speech_ints = range(1, total_ints, 2)
    else:
        speech_ints = range(2, total_ints, 2)
    print(speech_ints)

    extracted_sounds = []
    for int_num in speech_ints:
        print(int_num)
        int_start = call(textgrid,'Get start time of interval', 1, int_num)
        int_end = call(textgrid,'Get end time of interval', 1, int_num)
        print(int_start, int_end)

        # Adjust extraction segment
        int_start = int_start - adjustment
        if int_start < sound_start: int_start = sound_start
        int_end = int_end + adjustment
        if int_end > sound_end: int_end = sound_end
        print(int_start, int_end)

        ext_sound = call(sound, 'Extract part', int_start, int_end,
                        'rectangular', 1.0, True)
        extracted_sounds.append(ext_sound)

        chunk_start_ms = call(ext_sound, 'Get start time')
        chunk_end_ms = call(ext_sound, 'Get end time')
        print(chunk_start_ms, chunk_end_ms)

    return extracted_sounds

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

    soundpath = path.join(chunkpath, "wav")
    tgpath = path.join(chunkpath, "tg")
    logpath = path.join(chunkpath, "log")

    name, ext = path.splitext(filename)

    if ext == '.wav':
        if re.match(r".*_\d+$",name):
            # If filenames do not include video titles
            channel = name.rsplit('_',1)[0]
        else:
            # If filenames do include video titles
            channel = name.rsplit('_',2)[0]


        # Create log file
        log_file = path.join(logpath, channel+'_chunk_log.csv')
        if not path.exists(logpath):
            makedirs(logpath)

        output_df = pd.DataFrame(columns=['filename','video_id',
                                          'start_time','end_time', 'duration'])
        output_df.to_csv(log_file, index=False)


        # Create output directory
        outputpath = path.join(soundpath, channel)
        if not path.exists(outputpath):
            makedirs(outputpath)


        # Start audio processing
        print('\nCURRENT FILE: {0}'.format(filename))

        wav_filename = path.join(audiopath, filename)
        sound = parselmouth.Sound(wav_filename).convert_to_mono()


        print('First pass chunking in progress...\n')
        # Use a more conservative 0.5 sec silence to get larger chunks
        sil_duration = 0.5
        sil_threshold = get_silence_threshold(sound, 0.15)
        textgrid = detect_silences(sound, sil_threshold, sil_duration)

        n_ints = call(textgrid,
                            'Count intervals where',
                            1, 'is equal to', 'speech')
        print('Intervals containing speech: {0}'.format(n_ints))

        # Save first-pass TextGrid now for checking
        if not path.exists(path.join(tgpath, channel)):
            makedirs(path.join(tgpath, channel))
        tg_filename = path.join(tgpath, channel, name+'.TextGrid')
        textgrid.save(tg_filename)

        print('Extracting intervals...\n')
        # extracted_sounds_1 = extract_intervals(sound, textgrid, 0.25)
        extracted_sounds_1 = call([sound, textgrid],
                                'Extract intervals where',
                                1, True, 'is equal to', 'speech')

        print('Second pass chunking in progress...\n')
        # Use a more precise 0.25 s silence to get breath breaks
        extracted_sounds_2 = []
        for subsound in extracted_sounds_1:
            duration = subsound.get_total_duration()
            print(duration)

            if duration <= 11:
                log_entry = save_chunks(subsound, outputpath, name)
                output_df = output_df.append(log_entry, ignore_index=True)

            elif duration <= 20:
                extracted_sounds_2.append(subsound)

            else:
                sil_duration = 0.25
                sil_threshold = get_silence_threshold(subsound, 0.15)
                subtextgrid = detect_silences(subsound, sil_threshold, sil_duration)

                n_ints = call(subtextgrid, 'Count intervals where',
                              1, 'is equal to', 'speech')
                # extracted_subsounds = extract_intervals(subsound, subtextgrid, 0.25)
                extracted_subsounds = call([subsound, subtextgrid],
                                        'Extract intervals where',
                                        1, True, 'is equal to', 'speech')

                if n_ints > 1:
                    extracted_sounds_2 = extracted_sounds_2 + extracted_subsounds
                else:
                    extracted_sounds_2.append(extracted_subsounds)


        print('Third pass chunking in progress...\n')
        # Use a more precise 0.1 s silence + 0.05 threshold
        for subsound in extracted_sounds_2:
            duration = subsound.get_total_duration()
            print(duration)

            if duration <= 11:
                log_entry = save_chunks(subsound, outputpath, name)
                output_df = output_df.append(log_entry, ignore_index=True)

            else:
                sil_duration = 0.1
                sil_threshold = get_silence_threshold(subsound, 0.05)
                subtextgrid = detect_silences(subsound, sil_threshold, sil_duration)

                tg_filename = path.join(tgpath, channel, name+'current'+'.TextGrid')
                subtextgrid.save(tg_filename)

                n_ints = call(subtextgrid, 'Count intervals where',
                              1, 'is equal to', 'speech')

                # extracted_subsounds = extract_intervals(subsound, subtextgrid, 0.1)
                extracted_subsounds = call([subsound, subtextgrid],
                                        'Extract intervals where',
                                        1, True, 'is equal to', 'speech')
                print(extracted_subsounds)

                if n_ints == 1:
                    log_entry = save_chunks(subsound, outputpath, name)
                    output_df = output_df.append(log_entry, ignore_index=True)
                    print('saved 1')
                else:
                    for subsound in extracted_subsounds:
                        log_entry = save_chunks(subsound, outputpath, name)
                        output_df = output_df.append(log_entry, ignore_index=True)
                    print('saved multiple')

        output_df = output_df.sort_values(by=["start_time"])
        output_df.to_csv(log_file, mode='a', index=False, header=False)

def main(args):

    audiopath = path.join('corpus','raw_audio', args.group, "wav")
    chunkpath = path.join('corpus','chunked_audio', args.group)

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
