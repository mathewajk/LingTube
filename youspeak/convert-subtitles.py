#!/usr/bin/env python3

import argparse
import os
from os import listdir, makedirs, path
import shutil
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

def clean_text (text):
    """ Automated cleaning of text.
    """
    text = re.sub(r'1\.5', 'one point five', text)
    text = re.sub(r'[\.,"!?:;()]', '', text)
    text = re.sub(r'&', 'and', text)
    # text = re.sub(r'%', 'percent', text)
    numbers = {'1': 'one',
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
                '13': 'thirteen'}

    for numeral, word in numbers.items():
        numeral_string = ' '+ numeral +' '
        word_string = ' '+ word +' '
        text = re.sub(numeral_string, word_string, text)

    return text

def get_timestamped_lines (indir, filename):
    """ XXX
    """
    with open(path.join(indir,filename)) as file:
        subtext = file.read()

        # Extract only the relevant parts of each time+text set
        subs = re.findall(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(\w.*)\n', subtext)

    timed_lines = []
    for line in subs:
        time_start_s = convert_to_seconds(line[0])
        time_end_s = convert_to_seconds(line[1])
        sub_text = clean_text(line[2])
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

def read_timestamped_lines (insubdir, filename):
    """ XXX
    """
    with open(path.join(insubdir, filename)) as file:
        corrected_timed_lines = []
        lines = file.read().split('\n')
        for line in lines:
            if not line == '':
                timestamped_line = tuple(line.split('\t'))
                corrected_timed_lines.append(timestamped_line)

        return corrected_timed_lines

def write_to_output (filetype, outdir, video_id, timed_lines):
    """ XXX
    """
    channel = video_id.rsplit('_', 1)[0]

    if not path.exists(outdir):
        makedirs(outdir)
    output_file = path.join(outdir, video_id+'.txt')

    if filetype == 'cleans':
        output_df = pd.DataFrame(columns=['start_time', 'end_time', 'subtitle_text'])
        for line in timed_lines:
            subtitle_row = {"start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
            output_df = output_df.append(subtitle_row, ignore_index=True)
        output_df.to_csv(output_file, sep='\t', index=False, header=False)

    elif filetype == 'fave':
        output_df = pd.DataFrame(columns=['speaker_code', 'speaker_name',
                                 'start_time', 'end_time', 'subtitle_text'])
        for line in timed_lines:
            subtitle_row = {"speaker_code": channel[:2], "speaker_name": channel, "start_time": line[0], "end_time": line[1], "subtitle_text": line[2]}
            output_df = output_df.append(subtitle_row, ignore_index=True)
        output_df.to_csv(output_file, sep='\t', index=False, header=False)

    elif filetype == 'text':
        all_lines = [line[2] for line in timed_lines]
        all_text = " ".join(all_lines)
        with open(output_file, "w") as file:
            file.write(all_text)
    else:
        print('Filetype not valid.')

def process_raw_subs (i, subfilename, indir, cleansubdir, favedir, textdir):
    print('Processing transcript {0}: {1}'.format(i+1,subfilename))

    name = path.splitext(subfilename)[0] # channel_num
    if not re.match(r".*_\d+$",name):
        # If filenames do include video titles
        name = name.rsplit('_',1)[0]

    channel, vid_num = name.rsplit('_', 1)
    channel = re.sub(r'[^A-Za-z1-9]', '', channel)
    newname = '_'.join([channel, vid_num])

    timed_lines = get_timestamped_lines(indir, subfilename)

    # Write to file
    write_to_output('cleans', cleansubdir, newname, timed_lines)
    write_to_output('fave', favedir, newname, timed_lines)
    write_to_output('text', textdir, newname, timed_lines)


# TODO: Make routes for (1) -t titles in filenames (2) xml files
def main(args):
    # Get paths from args

    for subtype in ['auto', 'manual', 'corrected']:
        if args.corrected and subtype != 'corrected':
                continue

        print('\nSubtitle type: {0}'.format(subtype))

        indir = path.join('corpus','raw_subtitles', args.group, subtype,
                                args.language)

        cleansubdir = path.join('corpus','cleaned_subtitles', args.group,
                                 subtype, args.language, "cleans")
        favedir = path.join("corpus", "cleaned_subtitles", args.group,
                             subtype, args.language, "faves")
        textdir = path.join('corpus','cleaned_subtitles', args.group, subtype, args.language, "texts")

        if path.isdir(indir):
            dir_list = [e for e in listdir(indir)]
            if '.DS_Store' in dir_list:
                dir_list.remove('.DS_Store')
            for i, dir_element in enumerate(dir_list):
                if not dir_element == '.DS_Store':
                    if path.isdir(path.join(indir, dir_element)):
                        print('\nChannel {0}: {1}'.format(i+1, dir_element))

                        indir_ch = path.join(indir, dir_element)
                        cleansubdir_ch = path.join(cleansubdir, dir_element)
                        favedir_ch = path.join(favedir, dir_element)
                        textdir_ch = path.join(textdir, dir_element)

                        for subi, subdir_element in enumerate(listdir(indir_ch)):
                            process_raw_subs(subi, subdir_element, indir_ch, cleansubdir_ch, favedir_ch, textdir_ch)
                    else:
                        process_raw_subs(i, dir_element, indir, cleansubdir, favedir, textdir)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Convert scraped YouTube subtitles to cleaned transcript format.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')
    parser.add_argument('--corrected', '-c', action='store_true', default=False, help='only run on corrected subtitles')

    args = parser.parse_args()

    main(args)
