#!/usr/bin/env python3

import argparse
from os import listdir, makedirs, path, remove
import re
import shutil

# TODO: Add language flag; make compatible for other languages

def main(args):

    aligned_audio_base = path.join("corpus", "aligned_audio")

    if args.group:
        aligned_audio_base = path.join(aligned_audio_base, args.group)

    dict_path = path.join(aligned_audio_base, "trained_models", "dictionary")
    aligner_resources_path = path.join("resources", "aligner")

    # update_fn = path.join(dict_path, "update_list.txt")
    raw_dict_fn = path.join(dict_path, "english.dict")
    clean_dict_fn = path.join(dict_path, "english_clean.dict")

    full_update_fn = path.join(aligner_resources_path, "update_list_full.txt")
    full_dict_fn = path.join(aligner_resources_path, "english_full.dict")

    if args.overwrite and path.exists(clean_dict_fn):
        remove(clean_dict_fn)
    if not path.exists(clean_dict_fn):
        shutil.copy(raw_dict_fn, clean_dict_fn)

    with open(full_update_fn, "r") as update_file, open(raw_dict_fn, "r") as raw_dict, open(clean_dict_fn, "r") as clean_dict:
        # update_file.seek(0)
        raw_lines = raw_dict.readlines()
        clean_lines = clean_dict.readlines()
        update_contents = update_file.read()

        rm_entries = re.findall(r"([a-z]+\t.+) \-", update_contents)
        add_entries = re.findall(r"([a-z]+\t.+) \+", update_contents)


    with open(raw_dict_fn, "w+") as raw_dict, open(clean_dict_fn, "w+") as clean_dict:
        print('Processing group dictionary...')
        for rm_entry in rm_entries:
            if rm_entry+"\n" in raw_lines or rm_entry+"\n" in clean_lines:
                print('- {0}'.format(rm_entry))
                try:
                    raw_lines.remove(rm_entry+"\n")
                except ValueError:
                    pass
                try:
                    clean_lines.remove(rm_entry+"\n")
                except ValueError:
                    pass
        for add_entry in add_entries:
            if not (add_entry+"\n" in raw_lines or add_entry+"\n" in clean_lines):
                print('+ {0}'.format(add_entry))
                if not add_entry+"\n" in raw_lines:
                    raw_lines.append(add_entry+"\n")
                if not add_entry+"\n" in clean_lines:
                    clean_lines.append(add_entry+"\n")
        for line in raw_lines:
            raw_dict.write(line)
            if not line in clean_lines:
                clean_lines.append(line)
                print(line)
        clean_lines.sort()
        for line in clean_lines:
            clean_dict.write(line)


    with open(full_dict_fn, "w+") as full_dict:
        print('Processing full dictionary...')
        full_lines = full_dict.readlines()
        for rm_entry in rm_entries:
            if rm_entry+"\n" in full_lines:
                print('- {0}'.format(rm_entry))
                try:
                    full_lines.remove(rm_entry+"\n")
                except ValueError:
                    pass
        for line in full_lines:
            full_dict.write(line)
        for line in clean_lines:
            if not line in full_lines:
                full_dict.write(line)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Process MFA-compatible dictionaries.')

    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='name to group files under (create and /or assume files are located in a subfolder: aligned_audio/$group)')
    parser.add_argument('--overwrite', '-o', action='store_true', default=False, help='overwrite files rather than appending')

    args = parser.parse_args()

    main(args)
