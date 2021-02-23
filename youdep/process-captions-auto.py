import re, logging

from sys import argv, stdout, exit
from argparse import ArgumentParser
from os import path, makedirs, getcwd
from glob import glob
from stanza import Pipeline
from random import shuffle
from emoji import get_emoji_regexp


def remove_emoji(text):
    return get_emoji_regexp().sub(u'', text)


def main(args):

    # Get all .srt files for the specified language and channel

    if(args.group):
        captions_fns_auto = glob(path.join("corpus", "raw_subtitles", args.group, args.language, "auto", args.channel, "*.srt"))
        captions_fns_manual = glob(path.join("corpus", "raw_subtitles", args.group, args.language, "manual", args.channel, "*.srt"))
    else:
        captions_fns_auto = glob(path.join("corpus", "raw_subtitles", args.language, "auto", args.channel, "*.srt"))
        captions_fns_manual = glob(path.join("corpus", "raw_subtitles", args.language, "manual", args.channel, "*.srt"))

    if(len(captions_fns_auto) == 0 and len(captions_fns_manual) == 0):
        print("ERROR: No SRT files found. Did you spell the channel name correctly?")
        return

    if len(captions_fns_auto) != 0:
        process_caption_files(args.channel, args.language, captions_fns_auto, args.start, args.end, args.group, auto=True)
    if len(captions_fns_manual) != 0:
        process_caption_files(args.channel, args.language, captions_fns_manual, args.start, args.end, args.group, auto=False)


# Clean up caption files
# Processing differs based on the language specified
def process_caption_files(channel, language, captions_fns, start, end, group=None, auto=False):

    out_path = path.join("corpus", "processed_subtitles", "auto_processed")

    if group:
        out_path = path.join(out_path, group)

    out_path = path.join(out_path, language)

    if auto:
        out_path = path.join(out_path, "auto")
    else:
        out_path = path.join(out_path, "manual")

    out_path = path.join(out_path, channel)

    if not path.exists(out_path):
        makedirs(out_path)

    video_count = 0
    for captions_fn in captions_fns:
        if video_count < start:
            continue
        if end != -1 and video_count > end:
            break

        out_fn = "{0}_processed.txt".format(path.splitext(path.split(captions_fn)[1])[0])

        logging.info("Processing file: {0}".format(captions_fn))
        logging.info("Output file: {0}".format(out_fn))

        with open(captions_fn, "r") as captions_in:

            if language == 'ja':
                processed_captions = list(process_captions_ja(captions_in))
            else:
                processed_captions = list(process_captions(captions_in, channel, language))

            logging.info("Found {0} lines".format(len(processed_captions)))

            if len(processed_captions) != 0:
                with open(path.join(out_path, out_fn + ".srt"), "w") as captions_out:
                    for line in processed_captions:
                        captions_out.write(line + "\n")

            video_count += 1

    logging.info("Processed {0} files".format(video_count))


def process_captions(captions, channel, language):
    for line in captions:

        if line and not re.search("^[0-9]([0-9:,\-\ >])*\n", line):

            line = remove_emoji(line.strip())
            line = line.replace(":D", "")
            line = line.replace(":)", "")

            line = re.sub(r'\([^)]*\)', '', line) # Remove parens
            line = re.sub(r'<[^)]*>', '', line)   # Remove HTML
            line = re.sub("[\\\/\^\_~-♫♡♥♪→↑↖↓←⇓\(\)\[\]☆★♬\n]", "", line)
            line = re.sub("[!?]", ".", line)
            line = re.sub("^( )*\-", "", line)
            ine = re.sub(" \- ", ' ', line)
            line = re.sub("\.\.\.", ".", line)
            line = re.sub("\.\.", ".", line)
            line = line.strip()

            if line:
                if(channel != "AdvokatEgorov"):
                    if(line[-1] != '.' and line[-1] != ','):
                        line += '.'
                no_attr = re.split("[:]", line)
                if len(no_attr) > 1:
                    no_attr = "".join(no_attr[1:])
                    if(language != "ko"):
                        no_attr = no_attr.capitalize()
                    yield (no_attr)
                else:
                    if(language != "ko"):
                        line = line.capitalize()
                    yield line


def process_captions_ja(captions):
    for line in captions:
        if line and not re.search("^[0-9]([0-9:,\-\ >])*\n", line):
                line = line.strip()
                # Remove emoji
                line = remove_emoji(line)

                # Replace all punctuation except commas
                line = re.sub("[！‼？!?.…]", "。", line)
                line = line.replace("～", "") # Re doesn't recognize ～
                line = line.replace("〜", "") # These are two different chars, believe it or not.
                line = line.replace("、、、", "。") # Special case of ellipses

                # Reomove text within matched parentheticals
                parentheses = ["（[^（）]*）", "〔[^〔〕]*〕", "\([^()]*\)", "\[[^\[\]]*\]", "【[^【】)]*】", "＜[^＜＞)]*＞", "｛[｛｝)]*｝"]
                for paren_type in parentheses:
                    line = re.sub(paren_type, "", line)

                # Remove HTML
                line = re.sub(r'<[^)]*>', '', line)

                if not line:
                    #print("Final:   NA")
                    #input()
                    continue

                # Hacky fix for some troublesome whitespace typos
                attr_typos = [(" ：", "："), (" ）","）"), (" )", ")")]
                for typo, correction in attr_typos:
                    line = line.replace(typo, correction)

                # Remove speaker attributions (NOTE: Depends on above fix)
                line_noattr = re.sub("[^\s　。、]+[）\):：;)≫>]", "。", line)

                # Hacky solution for attributions using 「」
                # Do best to prevent accidentally removing content outside 「」or
                # when the 「」 isn't actually an attibution
                if(line_noattr == line):
                    if line[-1] == "」" or (line.find("「") > -1 and line.find("」") == -1):
                        line = re.sub("^[^\s]+「", "。", line).replace("」", "")
                else:
                    line = line_noattr

                # Remove action text
                line = re.sub("[（\(](.*)", "", line)

                # Remove any stray special characters
                line = re.sub("[●<>・･‥／☆\s♫♡♥♪♪→↑↖↓←”✖wｗWｗＷ※⇓⇒()（）【】《》✖「」『』〈〉]*", "", line)

                # Fixes for multiple & initial periods
                line = re.sub("。+", "。", line)
                line = re.sub("^。", "", line)

                if line:
                    if(line[-1] != '。' and line[-1] != '、'):
                        line += '。'
                    yield line
                else:
                    continue


if __name__ == '__main__':

    parser = ArgumentParser(description='Parse dependencies from a set of caption files.')

    parser.add_argument('channel', type=str, help='a friendly name for the channel')
    parser.add_argument('language', type=str, help='language code')
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')

    parser.add_argument('-s', '--start', default=0, type=int, help='video to start from')
    parser.add_argument('-e', '--end', default=-1, type=int, help='video to stop at')

    parser.add_argument('--log', action='store_true', default=False, help='log events to file')

    args = parser.parse_args()

    if args.end != -1 and args.start > args.end:
        parser.print_help()
        print("ERROR: -s/--start: must not exceed end value")
        exit(1)

    if(args.log):
        logging.basicConfig(filename=(args.channel + '_dependencies.log'),level=logging.DEBUG)

    logging.info("Call: {0}".format(args))

    main(args)
