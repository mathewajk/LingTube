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

mfa validate -t /Users/laurettacheng/Documents/UM/UM_Research/anANAs/GUAva/corpus/aligned_audio/*GROUP*/mfa_aligner

**Drag in folders:**
* original_corpus(/channel)

**Paste in:**
resources/aligner/english_guava.dict --ignore_acoustics

**Example for copying**
mfa validate -t ~/Documents/UM/UM_Research/anANAs/GUAva/corpus/aligned_audio/GROUP/mfa_aligner ~/Documents/UM/UM_Research/anANAs/GUAva/corpus/aligned_audio/GROUP/original_corpus resources/aligner/english_guava.dict --ignore_acoustics

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
mfa g2p ~/Documents/MFA/pretrained_models/g2p/english_g2p.zip ~/Documents/UM/UM_Research/anANAs/GUAva/corpus/aligned_audio/eas/mfa_aligner/original_corpus/corpus_data/oovs_found.txt ~/Documents/UM/UM_Research/anANAs/GUAva/corpus/aligned_audio/eas/trained_models/dictionary/oovs_guava.dict
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
mfa align -t corpus/aligned_audio/chi/mfa_aligner corpus/aligned_audio/chi/original_corpus resources/aligner/english_guava.dict ~/Documents/MFA/pretrained_models/acoustic/english.zip corpus/aligned_audio/chi/aligned_corpus -c -s 7
