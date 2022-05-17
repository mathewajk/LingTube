#!/usr/bin/env python3

import argparse
from os import path, listdir, makedirs, remove
from glob import glob
import pandas as pd
from shutil import rmtree
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
    if sil_intensity < 0:
        sil_intensity = 0
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


def get_num_intervals(textgrid, tier):
    return call(textgrid, 'Get number of intervals', tier)


def get_interval_label(textgrid, tier, interval):
    return call(textgrid,'Get label of interval', tier, interval)


def get_interval_start(textgrid, tier, interval):
    return call(textgrid, 'Get start time of interval', tier, interval)


def get_interval_end(textgrid, tier, interval):
    return call(textgrid, 'Get end time of interval', tier, interval)


def extract_clip(sound, start, end):
    return call(sound, 'Extract part', start, end, 'rectangular', 1.0, True)


def extract_intervals(sound, textgrid, adjustment):

    sound_start = sound.get_start_time()
    sound_end   = sound.get_end_time()

    # Get total number of intervals in textgrid
    num_intervals = get_num_intervals(textgrid, 1)

    # Get label of first interval
    first_interval_label = get_interval_label(textgrid, 1, 1)

    # Create list of speech intervals
    speech_intervals = range(1, num_intervals, 2) if first_interval_label == 'speech' else range(2, num_intervals, 2)

    extracted_clips = []

    for interval in speech_intervals:

        # Get start time and end time of interval
        int_start = get_interval_start(textgrid, 1, interval)
        int_end   = get_interval_end(textgrid, 1, int_num)

        # Widen start and end times by adjustment
        int_start = int_start - adjustment
        int_end = int_end + adjustment

        # Correct for over-adjustment
        if int_start < sound_start:
            int_start = sound_start
        if int_end > sound_end:
            int_end = sound_end

        extracted_clip = extract_clip(sound, int_start, int_end, 'rectangular', 1.0, True)
        extracted_clip.append(extracted_clip)

        # chunk_start_ms = call(extracted_clip, 'Get start time')
        # chunk_end_ms   = call(extracted_clip, 'Get end time')

    return extracted_clips


def extract_intervals_where(sound, textgrid, tier, operator, condition):
    return call([sound, textgrid], 'Extract intervals where', tier, True, operator, condition)


def count_intervals_where(textgrid, tier, operator, condition):
    return call(textgrid, 'Count intervals where', tier, operator, condition)


def set_interval_text(textgrid, tier, interval, label):
    call(textgrid, 'Set interval text', 2, interval, label)


def chunk_sound (sound, sil_duration, threshold_quantile):

    # Detect silences based on threshold
    sil_threshold = get_silence_threshold(sound, threshold_quantile)
    textgrid      = detect_silences(sound, sil_threshold, sil_duration)

    # Count and extract speech intervals
    num_intervals    = count_intervals_where(textgrid, 1, 'is equal to', 'speech')
    extracted_sounds = extract_intervals_where(sound, textgrid, 1, 'is equal to', 'speech')

    return textgrid, extracted_sounds, num_intervals


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


def check_and_overwrite_audio(sound_path, video_id, overwrite):
    # Check overwrite status for audio
    if path.isdir(sound_path) and not overwrite:
        existing_files = glob(path.join(sound_path, "**", "*{0}*".format(video_id)), recursive=True)
        if existing_files:
            return 1

    elif path.isdir(sound_path) and overwrite:
        shutil.rmtree(sound_path)

    return 0


def check_and_overwrite_textgrids(save_sounds, tg_path, tg_fn, overwrite):

    # Check overwrite status for audio
    if not save_sounds:
        if path.exists(tg_fn) and not overwrite:
            return 2
        elif path.exists(tg_fn) and overwrite:
            remove(tg_fn)

    # Make textgrid path
    if not path.exists(tg_path):
        makedirs(tg_path)

    return 0


def make_logs(video_id, log_path, sound_path):

    if not path.exists(log_path):
        makedirs(log_path)

    # Create log file
    log_fn = path.join(log_path, video_id + '_chunking_log.csv')
    output_df = pd.DataFrame(columns=['filename','video_id', 'start_time','end_time', 'duration'])
    output_df.to_csv(log_fn, index=False)

    # Create output directory
    if not path.exists(sound_path):
        makedirs(sound_path)

    return log_fn, output_df


def make_output_paths(chunk_path, channel_id, video_id):
    sound_path = path.join(chunk_path, "audio", "chunking", channel_id, video_id)
    tg_path    = path.join(chunk_path, "textgrids", "chunking", channel_id, video_id)
    log_path   = path.join(chunk_path, "logs", "chunking", channel_id)

    return sound_path, tg_path, log_path


def process_soundfile(fn, audio_path, chunk_path, overwrite=False, save_sounds=False, sed=False):

    video_id, ext = path.splitext(fn)

    # Ignore non-WAV files
    if ext != '.wav': return

    # Creat paths for audio, textgrids, and logs
    channel_id, yt_id = video_id.rsplit('_',1)
    sound_path, tg_path, log_path = make_output_paths(chunk_path, channel_id, video_id)

    # Check overwrite status for audio
    status = check_and_overwrite_audio(sound_path, video_id, overwrite)
    if status: return status

    # Check overwrite status for textgrid
    tg_fn = path.join(tg_path, video_id + '.TextGrid')
    status = check_and_overwrite_textgrids(save_sounds, tg_path, tg_fn, overwrite)
    if status: return status

    # Load sound from WAV file
    wav_fn = path.join(audio_path, fn)
    sound  = parselmouth.Sound(wav_fn).convert_to_mono()

    log_fn, output_df = None, None
    if save_sounds:
        log_fn, output_df = make_logs(video_id, log_path, sound_path)
        if path.exists(tg_fn):
            status = chunk_existing(tg_fn, log_fn, sound, textgrid, sound_path)
            return status

    status = process_audio(sound, video_id, fn, tg_fn, log_fn, output_df, audio_path, sound_path, save_sounds, sed)
    return status


def chunk_existing(tg_fn, log_fn, outputdf, sound, textgrid, sound_path):

    print('Chunking speech from existing TextGrid...')

    textgrid = parselmouth.read(tg_fn)
    extracted_intervals = extract_intervals_where(sound, textgrid, tier, True, 'is equal to', 'speech')

    for interval in extracted_intervals:
        log_entry = save_chunks(interval, sound_path, video_id)
        output_df = output_df.append(log_entry, ignore_index=True)

    output_df = output_df.sort_values(by=["start_time"])
    output_df.to_csv(log_fn, mode='a', index=False, header=False)

    return 3


def process_audio(sound, video_id, fn, tg_fn, log_fn, output_df, audio_path, sound_path, save_sounds, sed):

    # Start audio processing
    print('\nCURRENT FILE: {0}'.format(fn))

    if sed:
        base_textgrid, extracted_sounds_1 = chunk_sed(sed, sound, video_id, audio_path, tg_fn)

    else:
        print('First pass chunking in progress...')
        # Use a more conservative 0.5 sec silence to get larger chunks

        sil_duration = 0.25
        quantile = 0.05
        (base_textgrid, extracted_sounds_1, n_ints) = chunk_sound(sound, sil_duration, quantile)

        while n_ints <= 1:
            quantile += 0.025
            (base_textgrid, extracted_sounds_1, n_ints) = chunk_sound(sound, sil_duration, quantile)

        call(base_textgrid, 'Duplicate tier', 1, 1, 'usable speech')
        call(base_textgrid, 'Replace interval texts', 1, 1, 0, 'silence', '', 'Regular Expressions')

    print('Iterative chunking in progress...')
    counter = -1
    stage = -1
    quantile = 0.025
    sil_duration = 0.3
    duration_cutoff = [5, 7.5, 7.5, 10, 15, 15, -1]

    while len(extracted_sounds_1) > 0:
        counter += 1

        if counter % 5 == 0:
            stage +=1
            print('* Stage: {0}'.format(stage))
            if stage < 3:
                sil_duration -= 0.05
            else:
                sil_duration -= 0.025

        current_cutoff = duration_cutoff[stage]

        new_subsound_list = []
        for i, subsound in enumerate(extracted_sounds_1):
            duration = subsound.get_total_duration()

            if duration <= current_cutoff or stage == 6:

                if save_sounds:
                    log_entry = save_chunks(subsound, sound_path, video_id)
                    output_df = output_df.append(log_entry, ignore_index=True)

                # extracted_sounds_1.remove(subsound)

            elif duration > current_cutoff:

                (subtextgrid, extracted_subsounds, n_ints) = chunk_sound(subsound, sil_duration, quantile)

                if n_ints > 1:
                    # extracted_sounds_1.remove(subsound)
                    # extracted_sounds_1 = extracted_sounds_1 + extracted_subsounds
                    new_subsound_list = new_subsound_list + extracted_subsounds

                    for subsound in extracted_subsounds:
                        subsound_start = subsound.get_start_time()
                        subsound_end = subsound.get_end_time()
                        try:
                            call(base_textgrid, 'Insert boundary', 1, subsound_start)
                        except:
                            pass
                        try:
                            call(base_textgrid, 'Insert boundary', 1, subsound_end)
                        except:
                            pass

                        interval_num = call(base_textgrid, 'Get interval at time', 1, subsound_start)
                        call(base_textgrid, 'Set interval text', 1, interval_num, 'speech')

                elif n_ints == 0:
                    print('No sounds extracted.')
                elif n_ints == 1:
                    # extracted_sounds_1.remove(subsound)
                    # extracted_sounds_1.append(extracted_subsounds)
                    new_subsound_list.append(extracted_subsounds)

        extracted_sounds_1 = new_subsound_list

    if save_sounds:
        output_df = output_df.sort_values(by=["start_time"])
        output_df.to_csv(log_fn, mode='a', index=False, header=False)

    # Save second-pass TextGrid
    base_textgrid.save(tg_fn)


def make_base_tier(base_textgrid, sed_df):

    speech_alpha = 0.2
    music_alpha = 0.2
    noise_alpha = 0.2

    print("CREATING BASE TIER")

    for idx, sec in enumerate(sed_df["seconds"]):

        # Get ratios by second for each sound type
        speech_ratio = sed_df["speech_ratio"][idx]
        noise_ratio  = sed_df["noise_ratio"][idx]
        music_ratio  = sed_df["music_ratio"][idx]

        # If speech_ratio is above alpha, and the other ratios are below alpha, then we are in a speech segment
        # Otherwise, we are in a music/noise segment
        if speech_ratio >= speech_alpha and music_ratio < music_alpha and noise_ratio < noise_alpha:
            current_status = "speech"
        elif speech_ratio < speech_alpha or music_ratio >= music_alpha or noise_ratio >= noise_alpha:
            current_status = "other"

        # Set the interval text to the current status
        call(base_textgrid, 'Set interval text', 1, 1, current_status)

        # If we are at the start of the soundfile, initialize previous_status
        if sec == 0:
            previous_status = current_status

        # Insert boundaries on our speech, music, and noise grids
        try:
            for i in range (2, 5):
                call(base_textgrid, 'Insert boundary', i, sec)
        except:
            pass

        # Set the interval text on each grid
        ratios = [(speech_ratio, speech_alpha), (music_ratio, music_alpha), (noise_ratio, noise_alpha), ]
        for i in range (0, 3):
            # Get/create interval info
            interval = call(base_textgrid, 'Get interval at time', i + 2, sec)
            interval_type = 'speech' if ratios[i][0] >= ratios[i][1] else 'nonspeech'
            interval_label = '{0} ({1})'.format(interval_type, round(ratios[i][0], 3))

            # Update interval text
            set_interval_text(base_textgrid, i + 2, interval, interval_label)

        # If there was a flip, record it
        if not current_status == previous_status:
            status_queue.append((sec, speech_ratio))
        # If there was not a flip (or we flipped back), reset the queue
        else:
            status_queue = []

        # If we have been in a given state for 3 frames, update the status and make a boundary
        if len(status_queue) == 3:

            previous_status = current_status

            # Insert boundary at start of queue
            try:
                call(base_textgrid, 'Insert boundary', 1, status_queue[0][0])
            except:
                pass

            # Label the interview based on current status
            interval = call(base_textgrid, 'Get interval at time', 1, status_queue[0][0])
            call(base_textgrid, 'Set interval text', 1, interval, current_status)

            # Reset queue
            status_queue = []


def chunk_sed(sed, sound, video_id, audio_path, tg_fn):

    print('Accessing SED data...')

    raw_path_parts = path.normpath(audio_path).split(path.sep)
    raw_path_parts[3] = "sed"

    sed_path = path.join(*raw_path_parts)
    file_path = path.join(sed_path, video_id + '_sed_results.csv')

    sed_df = pd.read_csv(file_path)

    # Initialize textgrid
    base_textgrid = call(sound, "To TextGrid", "speech sounds music noise", "")

    make_base_tier(base_textgrid, sed_df)

    interval_window = []

    print("Identifying overlapping speech and other...")

    # Insert tier
    call(base_textgrid, "Insert interval tier", 1, "identified overlaps")

    n_ints = call(base_textgrid, "Get number of intervals", 2)
    for int_i in range(1,n_ints+1):

        int_start = call(base_textgrid, "Get start time of interval", 2, int_i)
        int_end = call(base_textgrid, "Get end time of interval", 2, int_i)
        int_duration = int_end-int_start

        if int_duration <= 15:
            if not interval_window:
                interval_window.append((int_i, int_start, int_end))
            elif interval_window[-1][0] == int_i - 1:
                interval_window.append((int_i, int_start, int_end))
            else:   # if not sequential, this is our new first interval (not sure if this code is ever reached)
                interval_window = [(int_i, int_start, int_end)]

        if int_duration > 15 or int_i == n_ints: # if we are in a long interval
              if len(interval_window) >= 6:
                  try:
                      call(base_textgrid, "Insert boundary", 1, interval_window[0][1])
                  except:
                      pass
                  try:
                      call(base_textgrid, "Insert boundary", 1, interval_window[-1][2])
                  except:
                      pass
                  call(base_textgrid, 'Set interval text', 1, call(base_textgrid, 'Get interval at time', 1, interval_window[0][1]), "overlap")
              interval_window = [] # else, just reset


    print("CREATE USABLE TIER")
    # ADD USABLE/UNUSABLE TIER
    call(base_textgrid, "Insert interval tier", 1, "identified usable")
    n_ints = call(base_textgrid, "Get number of intervals", 3)
    new_intervals = []

    # FINDING INTERVALS ================================
    for int_i in range(1, n_ints + 1):

        int_label = call(base_textgrid, "Get label of interval", 3, int_i)
        int_start = call(base_textgrid, "Get start time of interval", 3, int_i)
        int_end   = call(base_textgrid, "Get end time of interval", 3, int_i)

        # Returns "" if the segment is unlabeled, i.e. not flagged as "speech and other"
        # This is usable speech in the strict sense
        is_speech_other = call(base_textgrid, "Get label of interval", 2, call(base_textgrid, 'Get interval at time', 2, int_start))

        if int_label == "speech" and not is_speech_other:
            new_start = int_start - 1
            if new_start < 0:
                new_start = 0
            new_end = int_end + 1
            if new_end > sound.get_total_duration():
                new_end = sound.get_total_duration()

            new_intervals.append(("usable", new_start, new_end))

        elif sed == "any" and is_speech_other:
            start =  call(base_textgrid, "Get start time of interval", 2, call(base_textgrid, 'Get interval at time', 2, int_start)) - 1
            end   =  call(base_textgrid, "Get end time of interval", 2, call(base_textgrid, 'Get interval at time', 2, int_start)) + 1
            new_start = start - 1
            if new_start < 0:
                new_start = 0
            new_end = end + 1
            if new_end > sound.get_total_duration():
                new_end = sound.get_total_duration()
            new_intervals.append(("usable", new_start, new_end))

    # COMBINE SAME TYPES

    combined_intervals = []

    prev_start = new_intervals[0][1]
    prev_end = new_intervals[0][2]

    if len(new_intervals) == 1:

        start = new_intervals[0][1]
        end   = new_intervals[0][2]

        start_index = call(base_textgrid, 'Get interval at time', 3, start)
        end_index = call(base_textgrid, 'Get interval at time', 3, end)

        print(end - start + 1)
        print( end_index - start_index)

        ratio = (end_index - start_index) / ((end - start) + 1) / sound.get_total_duration() * 100

        print("FLIP RATIO: {0:.3f}".format(ratio))

        combined_intervals = [("usable ({0:.3f})".format(ratio), start, end)]

    print("COMBINING INTERVALS")
    # COMBINING INTERVALS  ================================
    num_ints = 1
    print(len(new_intervals))
    for i, interval in enumerate(new_intervals[1:]):

        current_start = interval[1]
        current_end   = interval[2]
        num_ints += 1
        if current_start > prev_end:

            start_index = call(base_textgrid, 'Get interval at time', 3, prev_start)
            end_index = call(base_textgrid, 'Get interval at time', 3, prev_end)

            print(prev_end - prev_start + 1)
            print(end_index - start_index)

            ratio = (end_index - start_index) / ((prev_end - prev_start) + 1) / sound.get_total_duration() * 100

            print("FLIP RATIO: {0:.3f}".format(ratio))

            combined_intervals.append(("usable ({0:.3f})".format(ratio), prev_start, prev_end))

            prev_start = current_start

        prev_end = current_end

        if i == len(new_intervals[1:])-1:
            start_index = call(base_textgrid, 'Get interval at time', 3, prev_start)
            end_index = call(base_textgrid, 'Get interval at time', 3, prev_end)

            print(prev_start, prev_end)
            print(start_index, end_index)

            ratio = (end_index - start_index) / ((prev_end - prev_start) + 1) / sound.get_total_duration() * 100

            print("FLIP RATIO: {0:.3f}".format(ratio))

            combined_intervals.append(("usable ({0:.3f})".format(ratio), prev_start, prev_end))

    # CREATING INTERVALS  ================================
    for interval in combined_intervals:
        try:
            call(base_textgrid, "Insert boundary", 1, interval[1])
        except:
            pass
        try:
            call(base_textgrid, "Insert boundary", 1, interval[2])
        except:
            pass
        call(base_textgrid, 'Set interval text', 1, call(base_textgrid, 'Get interval at time', 1, interval[1]), interval[0])

    base_textgrid.save(tg_fn)

    # TODO: Account for the case of no usable sections in the entire sound

    n_ints = call(base_textgrid, 'Count intervals where',
                        1, 'contains', 'usable')

    extracted_sounds_1 = call([sound, base_textgrid],
                            'Extract intervals where',
                            1, True, 'contains', 'usable')
    if n_ints <= 1:
        extracted_sounds_1 = [extracted_sounds_1]

    call(base_textgrid, 'Duplicate tier', 1, 1, 'usable speech')
    call(base_textgrid, 'Replace interval texts', 1, 1, 0, 'usable', '', 'literals')

    print("Number of usable chunks: {}".format(n_ints))

    call(base_textgrid, "Insert interval tier", 1, "flip ratio")
    interval = call(base_textgrid, "Get interval at time", 1, 0.001)
    n_ints  = call(base_textgrid, 'Get number of intervals', 4)
    print("FLIP: {0:.3f}".format(n_ints / sound.get_total_duration()))
    call(base_textgrid, "Set interval text", 1, interval, "{0:.3f}".format(n_ints / sound.get_total_duration()))

    return base_textgrid, extracted_sounds_1


def process_videos(group, channel, video, save_sounds, overwrite, sed):

    chunk_path = path.join('corpus','chunked_audio')
    audio_path = path.join('corpus','raw_audio', "wav")
    if group:
        chunk_path = path.join('corpus','chunked_audio', group)
        audio_path = path.join('corpus','raw_audio', group, "wav")

    if video:
        fn = video+'.wav'
        channel_id = video.rsplit('_',1)[0]
        channel_audio_path = path.join(audio_path, channel_id)
        process_soundfile(fn, channel_audio_path, chunk_path, overwrite, save_sounds, sed)

    elif channel and not video:
        channel_list = [channel]
    elif not channel and not video:
        channel_list = [dir_element for dir_element in listdir(audio_path) if path.isdir(path.join(audio_path, dir_element))]

    if not video:
        for channel_id in channel_list:
            channel_audio_path = path.join(audio_path, channel_id)
            for fn in listdir(channel_audio_path):
                process_soundfile(fn, channel_audio_path, chunk_path, overwrite, save_sounds, sed)

    out_message = path.join(chunk_path, "audio", "chunking", "README.md")
    if path.exists(path.join(chunk_path, "audio", "chunking")) and not path.exists(out_message):
        with open(out_message, 'w') as file:
            file.write('Channel folders for chunked audio files (with sub-folders for each original video source) go here.')


def chunk_voice(args):
    """Wrapper for chunking with voice activity detection"""
    process_videos(args.group, args.channel, args.video, args.save_sounds, args.overwrite, args.sed)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Chunk WAV audio files into short segments of sound.')
    parser.set_defaults(func=None)
    parser.set_defaults(func=chunk_voice)
    parser.add_argument('-g', '--group', default="ungrouped", type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_subtitles/$group)')
    parser.add_argument('-ch', '--channel', default=None, type=str, help='run on files for a specific channel name; if unspecified, goes through all channels in order')
    parser.add_argument('-v', '--video', default=None, type=str, help='run on files for a video id; if unspecified, goes through all videos in order')
    parser.add_argument('-d', '--sed', default=None, choices = ["only", "any"], type=str, help='use detected sound events (SED) for chunking and classify chunks as usable if it includes (1) only speech alone, without overlapping music/noise, or (2) any speech, even overlapping with music/noise; else, uses voice activity detection (VAD) of speech vs. silence for chunking')
    parser.add_argument('-s', '--save_sounds', action='store_true', default=False, help='save chunked sound files (necessary for using 3-validate-chunks.py); else, only saves full textgrid')
    parser.add_argument('-o', '--overwrite', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    if(args.func == None):
        parser.print_help()
        exit(2)

    args.func(args)
