# Using aligner
**Open up virtual env:**

conda activate aligner

**Close virtual env:**

conda deactivate

---

# Generate dictionary
## Structure
mfa g2p g2p_model_path input_path output_path

## Steps

**Type in:**
mfa g2p ~/Documents/MFA/pretrained_models/g2p/english_g2p.zip

**Drag in files:**
* trained_models/dictionary/word_list.txt

**Type in:**
* trained_models/dictionary/english.dict

**Type in:**
-n 3
---

# Align

## Structure
mfa align -t [temp_alignment_folder] [corpus_directory] [dictionary_path] [acoustic_model_path] [output_directory]

## Steps
**Type in:**

mfa align -t

**Drag in folders:**
* mfa_aligner
* original_corpus/channel

**Paste in:**
resources/aligner/english_full.dict ~/Documents/MFA/pretrained_models/acoustic/english.zip

**Drag in folders**
* aligned_corpus/channel
