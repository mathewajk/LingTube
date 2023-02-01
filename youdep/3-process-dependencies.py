# process-dependencies.py

# Generate per-sentence dependency measures, including headedness, word order, and
# dependency lengths (true/minimized/random), and basic semantic information 
# (subject, verb, object).

import stanza, json, logging, sys, os, io, random, statistics, argparse, csv
from stanza.utils.conll import CoNLL
from os import path
from glob import glob
import numpy as np


closed_class = ['ADP', 'AUX', 'CCONJ', 'DET', 'NUM', 'PART', 'PRON', 'SCONJ']
closed_rel = ['AUX', 'CASE',  'CC', 'DET', 'EXPL', 'MARK', 'PUNCT']
particles = ['は', 'に', 'で', 'には', 'では', 'が', 'を', 'へ', 'へと', 'と', 'の', 'ね', 'ねぇ', 'ねー', 'よ', 'わ', 'よー', 'よぉ']


""" Word order helper functions """

# Check if the verb has a subject
def has_subj(verb_index, sentence):

    subj = {}

    for tok in sentence:
        if tok[6] == verb_index and tok[7].startswith('nsubj'):
            subj[tok[7]] = int(tok[0])

    return subj

# Check if the verb has an object
def has_obj(verb_index, sentence):

    obj = {}

    for tok in sentence:
        if tok[6] == verb_index and tok[7].startswith('obj'):
            obj[tok[7]] = int(tok[0])

    return obj

# Check if the verb has a complement clause
def has_comp(verb_index, sentence):

    comp = {}

    for tok in sentence:
        if tok[6] == verb_index and (tok[7].startswith('ccomp') or tok[7].startswith('xcomp')):
            comp[tok[7]] = int(tok[0])

    return comp

# Check if the verb is in a V conj V relation
def has_conj(verb_index, sentence):

    conj = {}

    for tok in sentence:
        if tok[6] == verb_index and tok[7].startswith('conj'):
            conj[tok[7]] = int(tok[0])

    return conj

# Check if the verb has an auxiliary dependent
def has_aux(verb_index, sentence):
    aux = {}

    for tok in sentence:
        if tok[6] == verb_index and tok[7].startswith('aux'):
            aux[tok[7]] = int(tok[0])

    return aux

# Determine the order of the sentence in terms of {S, O, V} (or a subset thereof)
def determine_order(subj, obj, verb):

    # No expressed arguments
    if subj == None and obj == None:
        return 'v'

    # Subject only
    elif subj == None:
        if obj < verb:
            return 'ov'
        else:
            return 'vo'

    # Object only
    elif obj == None:
        if subj < verb:
            return 'sv'
        else:
            return 'vs'

    # Transitive; must check all possibilities
    else:
        if subj < obj  and obj  < verb:
            return 'sov'
        if subj < verb and verb < obj:
            return 'svo'
        if verb < subj and subj < obj:
            return 'vso'
        if verb < obj  and obj  < subj:
            return 'vos'
        if obj  < verb and verb < subj:
            return 'ovs'
        if obj  < verb and subj < verb:
            return 'osv'

# Find constituents and pass to determine_order
def determine_order_from_constituents(verb_index, sentence):

    # Find arguments of verb
    subj_d = has_subj(verb_index, sentence)
    obj_d  = has_obj(verb_index, sentence)
    comp_d = has_comp(verb_index, sentence)
    conj_d = has_conj(verb_index, sentence)

    # Can include cases with AUX for languages like German and Dutch
    # aux_d = has_aux(verb_index, sentence)

    verb_index = int(verb_index) - 1
    info = {'verb': verb_index}
    order_info = {}

    # Check for nominal subject
    if len(subj_d) == 1 and 'nsubj' in subj_d:

        # S, V and O, allowing cases with O and complements
        if len(obj_d) == 1 and 'obj' in obj_d and len(conj_d) == 0:
            info['nsubj'] = subj_d['nsubj']
            info['obj'] = obj_d['obj']

        # S and V, allowing cases with O and complements
        elif len(obj_d) == 0 and len(conj_d) == 0:
            info['nsubj'] = subj_d['nsubj']
            info['obj'] = None

    # Check for object
    elif len(subj_d) == 0:

        # O and V, allowing cases with O and complements
        if len(obj_d) == 1 and 'obj' in obj_d and len(conj_d) == 0:
            info['nsubj'] = None
            info['obj'] = obj_d['obj']

        # V, no complements
        elif len(obj_d) == 0 and len(conj_d) == 0:
            info['nsubj'] = None
            info['obj'] = None

    try:
        info['order'] = determine_order(info['nsubj'], info['obj'], verb_index)
    except KeyError as e:
        print(subj_d, obj_d, comp_d, conj_d)
        print("Sentence does not meet requirements; skipping")
        return None

    order_info.update({'verb': sentence[verb_index][1], 'verb_lemma': sentence[verb_index][2], 'verb_id': sentence[verb_index][0]})


    nsubj, obj = info['nsubj'], info['obj']
    if nsubj != None:
        order_info.update({'subject': sentence[nsubj - 1][1], 'subject_lemma': sentence[nsubj - 1][2], 'subject_id': nsubj})
    else:
        order_info.update({'subject': 'NA', 'subject_lemma': 'NA', 'subject_id': 'NA'})

    if obj != None:
        order_info.update({'object': sentence[obj - 1][1], 'object_lemma': sentence[obj - 1][2], 'object_id': obj})
    else:
        order_info.update({'object': 'NA', 'object_lemma': 'NA', 'object_id': 'NA'})

    order_info.update({'order': info['order']})
    return order_info


""" Dependency length helper functions """

# Create a tree from flat token list
def tree(dependencies):
    nodes={}
    for i in dependencies:
        (parent, rel, child) = i
        nodes[child] = {"parent": parent, "child": child, "relation": rel, "children": []}

    forest = []
    for i in dependencies:
        parent, rel, child = i
        node = nodes[child]

        if rel == 'root' or parent.text == 'ROOT': # this should be the Root Node
            forest.append(node)
        else:
            parent = nodes[parent]
            children = parent['children']
            children.append(node)

    return forest

# Re-flatten a dependency tree
def iter_flatten(iterable):
  it = iter(iterable)
  for e in it:
    if isinstance(e, list):
      for f in iter_flatten(e):
        yield f
    else:
      yield e

# Randomize the sentence while preserving tree structure
def linearize_random(node):

    if not len(node['children']):
        return [(node['parent'], node['relation'], node['child'])]

    else:
        chunk = []
        for child in node['children']: # Randomize each child and append it
            chunk.append(linearize_random(child))
        chunk.append((node['parent'], node['relation'], node['child']))
        random.shuffle(chunk)

        return chunk

# Generate an optimal linearization of a sentence
def linearize_optimal(node, right=True):

    if not len(node['children']):
        return [(node['parent'], node['relation'], node['child'])]

    else:

        sorted_children = node['children']
        sorted_children.sort(key=weight, reverse=True)
        chunk = [(node['parent'], node['relation'], node['child'])]

        root_pos = 0
        for i in range(0, len(sorted_children)):
            weight_cur = weight(sorted_children[i])
            if (i % 2 and right) or (not i % 2 and not right): # Add the largest child to the right of the parent, then swap sides
                chunk.insert(root_pos + 1, linearize_optimal(sorted_children[i], False))
            else: # Add largest child to left of the parent, then swap sides
                chunk.insert(root_pos, linearize_optimal(sorted_children[i], True))
                root_pos = root_pos + 1

        return chunk

def weight(node):
    if not len(node['children']):
        return 1
    return 1 + sum(map(weight, node['children']))

def calculate_deps(dl, dl_no_func, sl, sl_no_func):

    total_dl = sum(dl)
    average_dl = round(total_dl / len(dl), 3)
    average_dl_sl = round(average_dl/sl, 3)

    total_dl_no_func = sum(dl_no_func)
    average_dl_no_func = round(total_dl_no_func / len(dl_no_func), 3)
    average_dl_sl_no_func = round(average_dl_no_func/sl_no_func, 3)

    return {"num_deps": len(dl), "num_deps_no_func": len(dl_no_func), "total_dl": total_dl, "average_dl": average_dl, "average_dl_sl": average_dl_sl, "total_dl_no_func": total_dl_no_func, "average_dl_no_func": average_dl_no_func, "average_dl_sl_no_func": average_dl_sl_no_func}

# Get dependency lengths for sentence
def get_dep_length(sentence_all, sentence_open):

    sl, sl_no_func = 0, 0
    dl, dl_no_func = [], []

    for tok in sentence_all:
        print(tok)
        input()
        if tok[6] == '0': # ROOT
            sl += 1
            dl.append(0)
            continue
        sl += 1
        dl.append((abs(int(tok[6]) - int(tok[0])), tok))

    for tok in sentence_open:
        if tok[6] == '0': # ROOT
            sl_no_func += 1
            dl_no_func.append(0)
            continue
        sl_no_func += 1
        dl_no_func.append((abs(int(tok[6]) - int(tok[0])), tok))

    return calculate_deps(dl, dl_no_func, sl, sl_no_func)

# Calculate dependency lengths using custom indices
def get_dep_length_from_indices(dependency, indices):
    (governor, rel, child) = dependency
    if rel == 'root' or governor.text == 'ROOT':
        #print(child.text, 'root')
        return 0
    else:
        return abs(indices[governor.id] - indices[child.id])

# Get dependencies for a random linearization of the sentence
def get_random_dep_lengths(dependency_tree_all, dependency_tree_open):

    random_indices_all, random_indices_open = {}, {}
    sl, sl_no_func = 0, 0
    dl, dl_no_func = [], []

    # Randomize the tree and save the new indices
    random_dependencies_all =  list(iter_flatten(linearize_random(dependency_tree_all[0])))
    random_dependencies_open =  list(iter_flatten(linearize_random(dependency_tree_open[0])))

    for j in range (0, len(random_dependencies_all)):
        random_indices_all.update({random_dependencies_all[j][2].id: j + 1})
    for j in range (0, len(random_dependencies_open)):
        random_indices_open.update({random_dependencies_open[j][2].id: j + 1})

    # Get dependency lengths
    for random_dep in random_dependencies_all:
        sl += 1
        dl.append(get_dep_length_from_indices(random_dep, random_indices_all))

    for random_dep in random_dependencies_open:
        sl_no_func += 1
        dl_no_func.append(get_dep_length_from_indices(random_dep, random_indices_open))

    return calculate_deps(dl, dl_no_func, sl, sl_no_func)

# Get optimal deps
def get_optimal_dep_length(dependency_tree_all, dependency_tree_open):
    optimal_indices_all, optimal_indices_open = {}, {}
    sl, sl_no_func = 0, 0
    dl, dl_no_func = [], []

    optimal_dependencies_all = list(iter_flatten(linearize_optimal(dependency_tree_all[0])))
    optimal_dependencies_open = list(iter_flatten(linearize_optimal(dependency_tree_open[0])))

    for i in range (0, len(optimal_dependencies_all)):
        optimal_indices_all.update({optimal_dependencies_all[i][2].id: i + 1})
    for i in range (0, len(optimal_dependencies_open)):
        optimal_indices_open.update({optimal_dependencies_open[i][2].id: i + 1})

    # Get dependency lengths
    for optimal_dep in optimal_dependencies_all:
        sl += 1
        dl.append(get_dep_length_from_indices(optimal_dep, optimal_indices_all))

    for optimal_dep in optimal_dependencies_open:
        sl_no_func += 1
        dl_no_func.append(get_dep_length_from_indices(optimal_dep, optimal_indices_open))

    return calculate_deps(dl, dl_no_func, sl, sl_no_func)

""" Headedness """

# Get proportion of head-final dependencies
def head_final(sentence_all, sentence_open):

    dependency_c, dependency_c_no_func, head_final_c, head_final_c_no_func = 0, 0, 0, 0
    head_finality, head_finality_no_func = None, None

    for tok in sentence_all:
        if tok[7].upper() != "ROOT" :
            try:
                if int(tok[6]) > int(tok[0]):
                    head_final_c += 1
            except:
                continue
            dependency_c += 1

    for tok in sentence_open:
        if tok[7].upper() != "ROOT":
            try:
                if int(tok[6]) > int(tok[0]):
                    head_final_c_no_func += 1
            except:
                continue
            dependency_c_no_func += 1

    if dependency_c > 0:
        head_finality = round(head_final_c / dependency_c, 3)
    else:
        head_finality = "NA"

    if dependency_c_no_func > 0:
        head_finality_no_func = round(head_final_c_no_func / dependency_c_no_func, 3)
    else:
        head_finality_no_func = "NA"

    return {"head_finality": head_finality, "head_finality_no_func": head_finality_no_func}


""" Other utilities """

# Return the root, only if it is a verb
def get_root(sentence):
    for tok in sentence:
        if tok[3] == 'VERB' and tok[7] == 'root' and tok[1] not in particles:
            return tok[0]
    return None

def remove_punct_particles(sentence):

    punct_indices = []
    part_indices = []
    clean_sentence = []

    for tok in sentence:
        if tok[3].upper() == 'PUNCT':
            punct_indices.append(int(tok[0]))
        if tok[1] in particles:
            part_indices.append(int(tok[0]))

    for tok in sentence:
        if tok[3].upper() == 'PUNCT' or tok[1] in particles:
            continue

        cur_index = int(tok[0])
        head_index = int(tok[6])
        tok_adjusted = [i for i in tok] # Deep copy

        cur_adjustment = 0
        head_adjustment = 0

        for punct_index in punct_indices:
            if head_index == punct_index:
                continue
            if head_index > punct_index:
                head_adjustment += 1
            if cur_index > punct_index:
                cur_adjustment += 1

        for part_index in part_indices:
            if head_index == part_index:
                continue
            if head_index > part_index:
                head_adjustment += 1
            if cur_index > part_index:
                cur_adjustment += 1

        tok_adjusted[0] = str(cur_index - cur_adjustment)
        tok_adjusted[6] = str(head_index - head_adjustment)
        tok_adjusted[9] = '_'

        clean_sentence.append(tok_adjusted)
    #for tok in clean_sentence:
    #    print(tok)
    #input()
    return clean_sentence

def remove_closed_class(sentence):
    closed_indices = []
    clean_sentence = []

    for tok in sentence:
        if tok[7].upper() in closed_rel or tok[3].upper() in closed_class or sentence[int(tok[6]) - 1][3].upper() in closed_class:
            closed_indices.append(int(tok[0]))

    for tok in sentence:
        if tok[7].upper() in closed_rel or tok[3].upper() in closed_class or sentence[int(tok[6]) - 1][3].upper() in closed_class:
            continue

        cur_index = int(tok[0])
        head_index = int(tok[6])
        tok_adjusted = [i for i in tok] #Deep copy

        cur_adjustment = 0
        head_adjustment = 0

        for closed_index in closed_indices:
            if head_index == closed_index or cur_index == closed_index:
                continue
            if head_index > closed_index:
                head_adjustment += 1
            if cur_index > closed_index:
                cur_adjustment += 1

        tok_adjusted[0] = str(cur_index - cur_adjustment)
        tok_adjusted[6] = str(head_index - head_adjustment)
        tok_adjusted[9] = '_'

        clean_sentence.append(tok_adjusted)

    #for tok in clean_sentence:
    #    print(tok)
    #input()

    return clean_sentence

def extract_features(writer, language, corpus, sentence_list):

    id = 0

    for sentence in sentence_list:

        data = {}
        root = get_root(sentence)

        # First sanity check: is there a verbal root?
        if root == None:
            continue

        sentence_all, sentence_open = remove_punct_particles(sentence), remove_closed_class(sentence)

        # Convert back to stanza for later tree creation (lazy)
        try:
            document_all  = stanza.Document(CoNLL.convert_conll([sentence_all]))
            document_open = stanza.Document(CoNLL.convert_conll([sentence_open]))
        except:
            print("WARNING: Could not parse {0}".format(id))
            continue

        try:
            dependency_tree_all  = tree(document_all.sentences[0].dependencies)
            dependency_tree_open = tree(document_open.sentences[0].dependencies)
        except:
            print("WARNING: Could not create tree for {0}".format(id))
            continue

        # Second sanity check: can we make a tree?
        if len(dependency_tree_all) == 0 or len(dependency_tree_open) == 0 :
            print(root)
            text = []
            for tok in sentence:
                text.append(tok[1])
                text.append(tok[7])
            print(text)
            print("WARNING: Dependencies empty! (sentence {0})".format(id))
            id += 1
            continue

        # Third sanity check: does it meet order_info requirements?
        root = get_root(sentence_all) # Retrieve new verb index
        order_info = determine_order_from_constituents(root, sentence_all)
        if(order_info == None):
            continue

        data.update({"language": language, "corpus": corpus, "id": "{0}_{1}".format(corpus, id), "original_length": len(sentence)})
        data.update(order_info)
        data.update(head_final(sentence_all, sentence_open))

        observed_data = data
        observed_data.update({"baseline": "observed"})
        observed_data.update(get_dep_length(sentence_all, sentence_open))

        optimal_data = data
        optimal_data.update({"baseline": "optimal"})
        optimal_data.update(get_optimal_dep_length(dependency_tree_all, dependency_tree_open))

        writer.writerow(observed_data)
        writer.writerow(optimal_data)
        #print(observed_data)

        for i in range(0, 10):
            random_data = data
            random_data.update({"baseline": "random"})
            random_data.update(get_random_dep_lengths(dependency_tree_all, dependency_tree_open))

            writer.writerow(random_data)
            #print(random_data)

        id += 1


""" Data utilities """

def read_sentences(json_data):

    # Convert sentences from Stanza format to CoNLLu format
    conll_sentences = stanza.utils.conll.CoNLL.convert_dict(json_data)
    return [sent for sent in conll_sentences]

def read_files(fns, statsf, language, corpus, type):

    all_sentences = []

    for fn in fns:

        with open(fn, 'r') as corpus_in:

            if type == "json": # Each file is one Document
                try:
                    json_data = json.load(corpus_in)
                    all_sentences += read_sentences(json_data)
                except json.decoder.JSONDecodeError:
                    logging.info("Could not decode JSON. Is it empty?")
            else: # Each line is one document
                for line in corpus_in:
                    try:
                        all_sentences += read_sentences(json.loads(line))
                    except json.decoder.JSONDecodeError:
                        logging.info("Could not decode JSON. Is it empty?")

    with open(statsf, 'w') as csvfile:
        fieldnames = ["language", "corpus", "baseline", "id", "original_length", "order", "verb", "verb_lemma", "verb_id", "subject", "subject_lemma", "subject_id", "object", "object_lemma", "object_id", "head_finality", "head_finality_no_func", "num_deps", "total_dl", "average_dl", "average_dl_sl", "num_deps_no_func", "total_dl_no_func", "average_dl_no_func", "average_dl_sl_no_func"]
        writer =  csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        extract_features(writer, language, corpus, all_sentences)

def main(args):

    type = "json"
    fns = sorted(glob(path.join(args.corpus, "*.json")))

    if(len(fns) == 0):

        fns = sorted(glob(path.join(args.corpus, "*.jsonl")))

        if(len(fns) == 0):
            logging.error("No JSON(L) files found. Did you specify the correct path?")
            return 1
        else:
            type = "jsonl"

    read_files(fns, args.statsf, args.lang, args.name, type)



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Analyze data from Stanza-formatted JSON and JSONL dependency parse files.')

    parser.add_argument('-c', '--corpus', type = str, help = 'path to data')
    parser.add_argument('-l', '--lang', type = str, help = 'language')
    parser.add_argument('-n', '--name', type = str, help = 'corpus name')
    parser.add_argument('-o', '--statsf', type = str, help = 'stats output file')
    parser.add_argument('--log',    action='store_true', default=False, help='log events to file')

    args = parser.parse_args()

    if(args.log):
        logging.basicConfig(filename=(args.channel + '_dependencies.log'),level=logging.DEBUG)

    main(args)
