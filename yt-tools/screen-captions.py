import argparse
import sys
import re
from os import listdir, makedirs, path
import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher
nlp = spacy.load('en_core_web_sm')

def get_caption_texts (filepath):
    texts = []
    for filename in listdir(filepath):
        name, ext = path.splitext(filename)
        if ext == '.srt':
            try:
                with open(path.join(filepath,filename)) as file:
                    contents = file.read().lower()
                    subs = re.findall(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(\w.*)\n', contents)
                    full_text = ' '.join([line[2] for line in subs])
                    texts.append(full_text)
            except UnicodeDecodeError:
                with open(path.join(filepath,filename), encoding='windows-1252') as file:
                    contents = file.read().lower()
                    subs = re.findall(r'\d+\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(\w.*)\n', contents)
                    full_text = ' '.join([line[2] for line in subs])
                    texts.append(full_text)
    return texts

def get_screening_entities (doc):
    ents = [(ent.text, ent.label_) for ent in doc.ents]
    screening_ents = [ent[0] for ent in ents if ent[1] in ['NORP', 'GPE', 'LANGUAGE', 'LOC']]
    return screening_ents

def get_screening_keywords (doc, keywords):
    keywords = keywords.split(',')
    screening_keywords = [token.text for token in doc if token.text in keywords]
    return screening_keywords

def get_context (doc, target_list, output_type='window', start_NE_num=0, end_NE_num=None, window_size=10):

    matcher = PhraseMatcher(nlp.vocab)
    terms = target_list
    terms.sort()
    print("Here are each of the relevant named entities:")
    for term in terms:
        print('\t* '+term)

    print("\n<Press enter to show concordances, one at a time.\n")
    move_on = input()

    if end_NE_num == None:
        end_NE_num = len(terms)

    for term in terms[start_NE_num:end_NE_num]:
        print("*"+term.upper()+"*")
        term_list = [nlp.make_doc(term)]
        matcher.add("TermList", None, *term_list)

        matches = matcher(doc)
        for i, match in enumerate(matches):
            match_id, start, end = match[0], match[1], match[2]

            if output_type == 'window':
                # # To print 10 words before and after target word:
                span = doc[start-window_size:end+window_size]
                print(i, span.text+'\n')

            elif output_type == 'sent':
                # # To print detected sentences with target words:
                span = doc[start:end]
                print(i, span.sent.text+'\n')

        input()

        matcher.remove("TermList")


def main (args):

    screen_sub_base = path.join('corpus','screening', 'subtitles')
    if args.group:
        screen_sub_base = path.join('corpus','screening', args.group, 'subtitles')

    outfile = path.join(screen_sub_base, 'screened_channels.csv')
    if path.exists(outfile):
        out_df = pd.read_csv(outfile)
    else:
        out_df = pd.DataFrame(columns=['channel', 'subtype', 'language', 'usability', 'from_where', 'ethnicity', 'other_notes'])
        out_df.to_csv(outfile, index=False)

    if args.subtype:
        subtype_list = [args.subtype]
    else:
        subtype_list = ['auto', 'manual']

    for subtype in subtype_list:

        print('\nSUBTITLE TYPE: {0}'.format(subtype))

        screen_sub_dir = path.join(screen_sub_base, subtype)

        if args.language:
            language_list = [args.language]
        else:
            language_list = [lang for lang in listdir(screen_sub_dir)if not lang.startswith('.')]

        for language in language_list:
            lang_sub_dir = path.join(screen_sub_dir, language)

            if args.channel:
                channel_list = [args.channel]
            else:
                channel_list = [channel for channel in listdir(lang_sub_dir)if not channel.startswith('.')]

            for channel in channel_list:
                if channel in out_df['channel'].tolist():
                    continue

                channel_sub_dir = path.join(lang_sub_dir, channel)

                print("\nGathering documents from: {0}".format(channel))
                texts_list = get_caption_texts(channel_sub_dir)
                docs_list = list(nlp.pipe(texts_list))
                entities_list = [get_screening_entities(doc) for doc in docs_list]
                found_entities = [list(set(ent_list)) for ent_list in entities_list]

                if args.keywords:
                    keywords_list = [get_screening_keywords (doc, args.keywords) for doc in docs_list]
                    found_keywords = [list(set(key_list)) for key_list in keywords_list]

                    target_list = [ent_set + key_set for ent_set, key_set in zip(found_entities, found_keywords)]
                else:
                    target_list = found_entities

                if args.filter:
                    filter_words = args.filter.split(',')
                    filter_pass = 0
                    for word in filter_words:
                        for fw in sum(found_entities,[]):
                            filter_pass = re.search(r'\b'+word+r'\b', fw.replace('.',''))
                            if filter_pass:
                                print('Found filter word: {0}'.format(filter_pass.group()))
                                break
                        if filter_pass:
                            break
                    if not filter_pass:
                        continue

                print("\nReady to search concordances.")
                print("Select output_type ('w' for window or 's' for sentence).")

                output_type = input()
                while output_type not in ['w', 's', '']:
                    output_type = input()

                # for testing purposes
                if output_type == '':
                    continue

                for i, doc in enumerate(docs_list):
                    if output_type == 'w':
                        get_context(doc, target_list[i], 'window')
                        print("Repeat with sentences? ('y' or 'n')")
                        while output_type not in ['y', 'n']:
                            output_type = input()
                        if output_type == 'y':
                            get_context(doc, target_list[i], 'sent')
                    elif output_type == 's':
                        get_context(doc, target_list[i], 'sent')
                        print("Repeat with window? ('y' or 'n')")
                        while output_type not in ['y', 'n']:
                            output_type = input()
                        if output_type == 'y':
                            get_context(doc, target_list[i], 'window')

                print("Done! Is the speaker usable? (Y=1, N=0, maybe=0.5)")
                usability = input()
                while usability not in ['1', '0', '0.5']:
                    usability = input()

                print("\nWhere are they from?")
                from_where = input()

                print("\nWhat is their ethnicity?")
                ethnicity = input()

                print("\nAny other notes or comments?")
                other_notes = input()

                out_df = out_df.append({'channel': channel, 'subtype': subtype, 'language': language, 'usability': usability, 'from_where': from_where, 'ethnicity': ethnicity, 'other_notes': other_notes}, ignore_index=True)
                out_df.to_csv(outfile, index=False)

                print("\n<Continue to next channel? Press 'c' or press 'e' to exit.>")
                move_on = input()
                while move_on not in ['e','c']:
                    move_on = input()
                if move_on == 'e':
                    return sys.exit("Safely exited!")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Screen captions for speaker background information.')
    parser.set_defaults(func=None)
    parser.add_argument('--group', '-g', default=None, type=str, help='grouping folder')
    parser.add_argument('--subtype', '-s', default=None, type=str, help='subtitle type (auto, manual)')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--keywords', '-k', default=None, type=str, help='keywords to target in addition to named entities (comma-separated)')
    parser.add_argument('--filter', '-f', default=None, type=str, help='target words to filter by (comma-separated)')

    args = parser.parse_args()

    main(args)
