#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path
from glob import glob
import re
import pandas as pd


def convert_to_seconds (timestamp) :
    """ Translate timestamps to time in seconds (used in get_lines )
    """
    time_components = re.findall(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', timestamp)

    if not len(time_components) == 0:
        hrs, mins, secs, msecs = time_components[0]

        hrs = int(hrs) * (60 * 60) * 1000
        mins = int(mins) * 60 * 1000
        secs = int(secs) * 1000
        msecs = int(msecs)

        time_ms = hrs + mins + secs + msecs
        time_s = float(time_ms)/float(1000)
        return time_s

def clean_text (text,langcode):
    """ Automated cleaning of text.
    """

    if langcode == 'en':

        numbers = {'0': 'zero',
                    '1': 'one',
                    '2': 'two',
                    '3': 'three',
                    '4': 'four',
                    '5': 'five',
                    '6': 'six',
                    '7': 'seven',
                    '8': 'eight',
                    '9': 'nine',
                    '10': 'ten',
                    '11': 'eleven',
                    '12': 'twelve',
                    '13': 'thirteen',
                    '14': 'fourteen',
                    '15': 'fifteen',
                    '16': 'sixteen',
                    '17': 'seventeen',
                    '18': 'eighteen',
                    '19': 'nineteen',
                    '20': 'twenty',
                    '30': 'thirty',
                    '40': 'forty',
                    '50': 'fifty',
                    '60': 'sixty',
                    '70': 'seventy',
                    '80': 'eighty',
                    '90': 'ninety'}

        text = re.sub(r'1\.5', 'one point five', text)
        for per in re.findall(r'\d+%', text):
            text = re.sub(r'%', ' percent', text)

        text = re.sub(r':00', '', text)
        text = re.sub(r':', ' ', text)
        text = re.sub(r'24/7', 'twenty-four seven', text)

        for abb in re.findall(r'(?:^|\s)((?:[a-zA-Z]\.)+)(?:$|\s)', text):
            cap_string = abb.replace('.','').upper()
            text = re.sub(abb, cap_string, text)

        for num in re.findall(r'(?:^|\s)(\d{1,2})(?:$|\s)', text):
            if num in numbers.keys():
                numeral_string = '{0}'.format(num)
                word_string = '{0}'.format(numbers.get(num))
                text = re.sub(numeral_string, word_string, text)
            else:
                ones = numbers.get(num[-1])
                tens = numbers.get("{0}0".format(num[-2]))
                numeral_string = '{0}'.format(num)
                word_string = '{0}-{1}'.format(tens, ones)
                text = re.sub(numeral_string, word_string, text)

    # text = re.sub(r'[\.,"!?:;()]', '', text)
    text = re.sub(r' & ', ' and ', text)

    return text

def get_timestamped_lines (in_dir, fn, langcode):
    """ Extract timestamps and text per caption line
    """
    with open(path.join(in_dir,fn)) as file:
        file_text = file.read()

        # Extract only the relevant parts of each time+text set
        subs = re.findall(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*)\n', file_text)

    timed_lines = []
    for line in subs:
        time_start_s = convert_to_seconds(line[0])
        time_end_s = convert_to_seconds(line[1])
        sub_text = clean_text(line[2], langcode)
        timed_lines.append((time_start_s, time_end_s, sub_text))

    lasti = len(timed_lines)
    corrected_timed_lines = []
    for i in range(0,lasti):
        time_start = timed_lines[i][0]
        sub_text = timed_lines[i][2]
        if i < lasti-1:
            time_end = timed_lines[i+1][0]
        else:
            time_end = timed_lines[i][1]
        corrected_timed_lines.append((time_start, time_end, sub_text))

    return corrected_timed_lines

def write_to_output (file_type, out_dir, name, timed_lines):
    """ Write to files
    :param name: The filename (w/o ext)
    """
    channel_name = name.split('_', 1)[0]

    if not path.exists(out_dir):
        makedirs(out_dir)
    out_file_path = path.join(out_dir, name+'.txt')

    if file_type == 'cleans':
        out_df = pd.DataFrame(columns=['start_time', 'end_time', 'subtitle_text'])
        for line in timed_lines:
            subtitle_row = {"start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
            out_df = out_df.append(subtitle_row, ignore_index=True)
        out_df.to_csv(out_file_path, sep='\t', index=False, header=False)

    elif file_type == 'fave':
        out_df = pd.DataFrame(columns=['speaker_code', 'speaker_name',
                                 'start_time', 'end_time', 'subtitle_text'])
        for line in timed_lines:
            subtitle_row = {"speaker_code": channel_name[:2], "speaker_name": channel_name, "start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
            out_df = out_df.append(subtitle_row, ignore_index=True)
        out_df.to_csv(out_file_path, sep='\t', index=False, header=False)

    elif file_type == 'text':
        all_lines = [line[2] for line in timed_lines]
        all_text = " ".join(all_lines)
        with open(out_file_path, "w") as file:
            file.write(all_text)
    else:
        print('File type is not valid (cleans, fave, text).')

def process_raw_subs (i, fn, langcode, in_dir, cleans_dir, fave_dir, text_dir, fave=False, text=False, overwrite=False):
    name, ext = path.splitext(fn)

    if path.isdir(cleans_dir) and not overwrite:
        existing_files = glob(path.join(cleans_dir, "**", "*{0}*".format(name)), recursive=True)
        if existing_files:
            return 1

    print('Processing transcript {0}: {1}'.format(i+1,fn))

    timed_lines = get_timestamped_lines(in_dir, fn, langcode)
    write_to_output('cleans', cleans_dir, name, timed_lines)
    if fave:
        write_to_output('fave', fave_dir, name, timed_lines)
    if text:
        write_to_output('text', text_dir, name, timed_lines)


# TODO: Make routes for (1) xml files
def main(args):

    raw_sub_base = path.join('corpus','raw_subtitles')
    clean_sub_base = path.join('corpus','cleaned_subtitles')

    if args.group:
        raw_sub_base = path.join(raw_sub_base, args.group)
        clean_sub_base = path.join(clean_sub_base, args.group)

    # TODO: Remove 'corrected' once all legacy dirs are handled
    for sub_type in ['auto', 'manual', 'corrected']:

        print('\nSUBTITLE TYPE: {0}'.format(sub_type))

        raw_sub_dir = path.join(raw_sub_base, sub_type)
        clean_sub_dir = path.join(clean_sub_base, sub_type)

        if args.lang_code:
            lang_code_list = [args.lang_code]
        if path.isdir(raw_sub_dir):
            lang_code_list = [langcode for langcode in listdir(raw_sub_dir) if not langcode.startswith('.')]
        else:
            lang_code_list = []

        for langcode in lang_code_list:
            in_dir = path.join(raw_sub_dir, langcode)
            cleans_dir = path.join(clean_sub_dir, langcode, "cleans")
            fave_dir = path.join(clean_sub_dir, langcode, "faves")
            text_dir = path.join(clean_sub_dir, langcode, "texts")

            if path.isdir(in_dir):
                dir_list = [dir_element for dir_element in listdir(in_dir)]
                if '.DS_Store' in dir_list:
                    dir_list.remove('.DS_Store')
                for i, dir_element in enumerate(dir_list):
                    if path.isdir(path.join(in_dir, dir_element)):
                        # print('\nChannel {0}: {1}'.format(i+1, dir_element))

                        channel_in_dir = path.join(in_dir, dir_element)
                        channel_cleans_dir = path.join(cleans_dir, dir_element)
                        channel_fave_dir = path.join(fave_dir, dir_element)
                        channel_text_dir = path.join(text_dir, dir_element)

                        for j, fn in enumerate(listdir(channel_in_dir)):
                            process_raw_subs(j, fn, langcode, channel_in_dir, channel_cleans_dir,channel_fave_dir, channel_text_dir, args.fave, args.text, args.overwrite)
                    else:
                        process_raw_subs(i, dir_element, langcode, in_dir, cleans_dir, fave_dir, text_dir, args.fave, args.text, args.overwrite)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube captions to cleaned transcript format.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: cleaned_subtitles/$group)')
    parser.add_argument('--lang_code', '-l', default=None, type=str, help='open captions with a specific a language code (e.g., "en"); if unspecified, goes through all available language code in subtitle directory')
    parser.add_argument('--fave', '-f', action='store_true', default=False, help='additionally output Fave-format file')
    parser.add_argument('--text', '-t', action='store_true', default=False, help='additionally output text-only file')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
