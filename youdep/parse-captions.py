import stanza, json, argparse, logging
from sys import argv
from glob import glob
from os import path, makedirs, getcwd
from sys import stdout


def main(args):
    subtitles_fns = sorted(glob(path.join("corpus", "processed_subtitles", args.caption_type, args.language, args.channel, "*.srt")))
    if(len(subtitles_fns) == 0):
        print("ERROR: No SRT files found. Did you spell the channel name correctly?")
        return

    nlp = stanza.Pipeline(lang=args.language, use_gpu=True)
    parse_files(nlp, args.channel, args.language, args.caption_type, args.start, args.end, subtitles_fns)


def parse_files(nlp, channel, language, type, start, end, subtitles_fns):

    dep_path = path.join("corpus", "dependency_corpus", type, language, channel)
    if not path.exists(dep_path):
        makedirs(dep_path)

    video_count = 0
    for subtitles_fn in subtitles_fns:
        if video_count < start:
            continue
        if end != -1 and video_count > end:
            break

        logging.info("Processing {1}: {0}".format(subtitles_fn, video_count))
        parse_file(nlp, subtitles_fn, channel, video_count, dep_path)
        video_count += 1

def parse_file(nlp, subtitles_fn, channel, video_id, dep_path):

    dependencies_fn = path.join(dep_path, "{0}_{1}_dependencies.json".format(channel, video_id))

    with open(subtitles_fn, "r") as subtitles_in, open(dependencies_fn, "w") as dependencies_out:

        preprocessed_subtitles = list(subtitles_in)
        logging.info("Found {0} lines".format(len(preprocessed_subtitles)))

        nlp_subtitles = None
        try:
            nlp_subtitles = nlp("".join(preprocessed_subtitles))
            dependencies_json = json.dump(nlp_subtitles.to_dict(), dependencies_out)
        except RecursionError as e:
            logging.warning("Could not parse {0}: recursion depth exceeded".format(video_id))
        except:
            logging.warning("Could not parse {0}: an unexpected error occurred".format(video_id))

    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Parse dependencies from a set of subtitle files.')

    parser.add_argument('channel',  type=str, help='a friendly name for the channel')
    parser.add_argument('language',  type=str, help='language code')
    parser.add_argument('caption_type',  default="auto", type=str, help='the type of caption (auto or other)')

    parser.add_argument('-s', '--start', default=0, type=int, help='video to start from')
    parser.add_argument('-e', '--end', default=-1, type=int, help='video to stop at')

    parser.add_argument('--log',    action='store_true', default=False, help='log events to file')

    args = parser.parse_args()

    if(args.log):
        logging.basicConfig(filename=(args.channel + '_dependencies.log'),level=logging.DEBUG)

    logging.info("Call: {0}".format(args))
    logging.info("BEGIN PARSE\n----------")

    main(args)
