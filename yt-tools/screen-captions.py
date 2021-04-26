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

    screen_sub_base = path.join('corpus','unscreened_urls', 'subtitles')
    screen_about_dir = path.join('corpus','unscreened_urls', 'about')
    out_fp = path.join(screen_sub_base, 'screened_channels.csv')

    if args.group:
        screen_sub_base = path.join('corpus','unscreened_urls', args.group, 'subtitles')
        screen_about_dir = path.join('corpus','unscreened_urls', args.group, 'about')
        out_fp = path.join(screen_sub_base, '{0}_screened_channels.csv'.format(args.group))

    if path.exists(out_fp):
        out_df = pd.read_csv(out_fp)
    else:
        out_df = pd.DataFrame(columns=['channel', 'sub_type', 'language', 'usability', 'channel_name', 'tag', 'ethnicity', 'from_where', 'url', 'type', 'minutes', 'other_notes'])
        out_df.to_csv(out_fp, index=False)

    if args.sub_type:
        sub_type_list = [args.sub_type]
    else:
        sub_type_list = ['auto', 'manual']

    for sub_type in sub_type_list:

        print('\nSUBTITLE TYPE: {0}'.format(sub_type))

        screen_sub_dir = path.join(screen_sub_base, sub_type)

        if args.language:
            language_list = [args.language]
        else:
            language_list = [lang for lang in listdir(screen_sub_dir)if not lang.startswith('.')]

        for language in language_list:
            lang_sub_dir = path.join(screen_sub_dir, language)

            if args.channel:
                channel_list = [args.channel]
            else:
                channel_list = [channel_id for channel_id in listdir(lang_sub_dir)if not channel_id.startswith('.')]

            for channel_id in channel_list:
                if channel_id in out_df['channel'].tolist():
                    continue

                channel_sub_dir = path.join(lang_sub_dir, channel_id)

                print("\nGathering documents from: {0}".format(channel_id))
                texts_list = get_caption_texts(channel_sub_dir)
                docs_list = list(nlp.pipe(texts_list))
                entities_list = [get_screening_entities(doc) for doc in docs_list]
                found_entities = [list(set(ent_list)) for ent_list in entities_list]

                print(entities_list)
                print(found_entities)

                if args.keywords:
                    keywords_list = [get_screening_keywords (doc, args.keywords) for doc in docs_list]
                    found_keywords = [list(set(key_list)) for key_list in keywords_list]

                    print(found_keywords)

                    target_list = [ent_set + key_set for ent_set, key_set in zip(found_entities, found_keywords)]

                else:
                    target_list = found_entities

                print(target_list)

                if args.filter:
                    filter_words = args.filter.split(',')
                    filter_pass = 0
                    for word in filter_words:
                        for fw in sum(target_list,[]):
                            filter_pass = re.search(r'\b'+word+r'\b', fw.replace('.',''))
                            if filter_pass:
                                print('\n*** FOUND FILTER WORD: {0} ***\n'.format(filter_pass.group()))
                                break
                        if filter_pass:
                            break
                    if not filter_pass:
                        continue

                print('----------ABOUT-----------')
                about_file = path.join(screen_about_dir, "{0}_info.txt".format(channel_id))
                with open(about_file, "r") as file:
                    about_text = file.read().replace('\n',' ')
                    channel_name = re.findall(r"#\s+ChannelName\s+(.*?)\s+#\s+Description", about_text)[0]
                    print("\nCHANNEL NAME: {0}".format(channel_name))
                    description = re.findall(r"#\s+Description\s+(.*?)\s+#\s+Bio", about_text)[0]
                    print("\nCHANNEL DESCRIPTION:\n\n{0}".format(description))
                    metadata = re.findall(r"#\s+Metadata\s+(.*?)\s+#\s+SafeChannelName",  about_text)[0]
                    print("\nCHANNEL METADATA:\n\n{0}".format(metadata))

                print('--------------------------')

                for i, doc in enumerate(docs_list):

                    print("\nReady to search concordances for video {0} of {1}.".format(i+1, len(docs_list)))
                    print("Select output_type ('w' for window or 's' for sentence). To skip, type 'x'.")

                    output_type = input()
                    while output_type not in ['w', 's', 'x']:
                        output_type = input()

                    # for testing purposes
                    if output_type == 'x':
                        continue

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

                    print("Done! Is the speaker usable? (Yes=1; No=0; not enough info=unk; skip=x)")
                    usability = input()
                    # while usability not in ['1', '0', '0.5', 'x']:
                    #     usability = input()

                    if not usability == 'x':
                        print("\nWhere are they from?")
                        from_where = input()

                        print("\nWhat is their ethnicity?")
                        ethnicity = input()

                        print("\nAny other notes or comments?")
                        other_notes = input()

                        # Get log info (url)
                        # TODO: Fix for non-group use case
                        log_fp = path.join('corpus','unscreened_urls', 'logs', "{0}_log.csv".format(channel_id))
                        if args.group:
                            log_fp = path.join('corpus','unscreened_urls', 'logs', "{0}_log.csv".format(args.group))
                        log_df = pd.read_csv(log_fp)

                        channel_name = channel_id.split('_')[0]
                        log_row =  log_df.loc[log_df['name']==channel_name]

                        out_df = out_df.append({'channel': channel_id, 'sub_type': sub_type, 'language': language, 'usability': usability, 'channel_name': channel_name, 'tag': '', 'ethnicity': ethnicity, 'from_where': from_where, 'url': log_row['url'].values[i], 'type': '', 'minutes': int(log_row['length'].values[i]/60), 'other_notes': other_notes}, ignore_index=True, sort=False)
                        out_df.to_csv(out_fp, index=False)

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
    parser.add_argument('--sub_type', '-s', default=None, type=str, help='subtitle type (auto, manual)')
    parser.add_argument('--language', '-l', default=None, type=str, help='language code')
    parser.add_argument('--channel', '-ch', default=None, type=str, help='channel folder')
    parser.add_argument('--keywords', '-k', default=None, type=str, help='keywords to target in addition to named entities (comma-separated)')
    parser.add_argument('--filter', '-f', default=None, type=str, help='target words to filter by (comma-separated)')

    args = parser.parse_args()

    main(args)
