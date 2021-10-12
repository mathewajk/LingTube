# Using aligner
**Open up virtual env:**

conda activate aligner

**Close virtual env:**

conda deactivate

---

# Validate

## Structure
mfa validate -t [temp_alignment_folder] corpus_directory dictionary_path [optional_acoustic_model_path]

## Steps
**Type in:**

mfa validate -t corpus/aligned_audio/*GROUP*/mfa_aligner

**Drag in folders:**
* original_corpus(/channel)

**Paste in:**
resources/aligner/english_guava.dict --ignore_acoustics -c -s 7

**Example for copying**
mfa validate -t corpus/aligned_audio/non/mfa_aligner corpus/aligned_audio/non/original_corpus resources/aligner/english_guava.dict --ignore_acoustics -c -s 7

---
# Generate dictionary
## Structure
mfa g2p g2p_model_path input_path output_path

## Steps

**Type in:**
mfa g2p ~/Documents/MFA/pretrained_models/g2p/english_g2p.zip

**Drag in files:**
* mfa_aligner/original_corpus/corpus_data/oovs_found.txt

**Type in:**
* trained_models/dictionary/oovs_guava.dict

**Type in:**
-n 3

**Example for copying**
mfa g2p ~/Documents/MFA/pretrained_models/g2p/english_g2p.zip corpus/aligned_audio/non/mfa_aligner/original_corpus/corpus_data/oovs_found.txt corpus/aligned_audio/non/trained_models/dictionary/oovs_guava_v2.dict
___
# Align

## Structure
mfa align -t [temp_alignment_folder] [corpus_directory] [dictionary_path] [acoustic_model_path] [output_directory]

## Steps
**Type in:**

mfa align -t

**Drag in folders:**
* mfa_aligner
* original_corpus(/channel)

**Paste in:**
resources/aligner/english_guava.dict ~/Documents/MFA/pretrained_models/acoustic/english.zip

**Drag in folders**
* aligned_corpus(/channel)

**Type in flags:**
-c -s 7

**Example for copying**
mfa align -t corpus/aligned_audio/non/mfa_aligner corpus/aligned_audio/non/original_corpus resources/aligner/english_guava.dict ~/Documents/MFA/pretrained_models/acoustic/english.zip corpus/aligned_audio/non/aligned_corpus -c -s 7
