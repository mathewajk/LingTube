# https://github.com/qiuqiangkong/panns_inference

import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import librosa
import panns_inference
import argparse
from panns_inference import AudioTagging, SoundEventDetection, labels


def main(source):

    # Get index to label dictionary
    print('------ Compiling dictionary ------')
    ix_to_lb = {i : label for i, label in enumerate(labels)}

    # Run SED for audio file
    print('------ Accessing audio ------')
    audio_path = source
    fn = os.path.splitext(os.path.split(source)[1])[0]
    device = 'cpu' # 'cuda' | 'cpu'

    # Prep files
    if not os.path.exists(os.path.join("sed", "fig")):
        os.makedirs(os.path.join("sed", "fig"))

    out_fn_path = os.path.join('sed', fn+'_sed_results.csv')
    out_fig_path = os.path.join('sed', 'fig', fn+'_sed_results.png')

    # TODO: get audio length in seconds

    (audio, _) = librosa.core.load(audio_path, sr=32000, mono=True)
    # duration = librosa.get_duration(y=audio, sr=32000)
    audio = audio[None, :]  # (batch_size, segment_samples)

    print('------ Sound event detection ------')
    sed = SoundEventDetection(checkpoint_path=None, device=device)
    framewise_output = sed.inference(audio)
    frame_arrays = framewise_output[0]

    # Get top classes by max probability
    print('------ Collecting framewise data ------')
    classwise_output = np.max(frame_arrays, axis=0) # get max prob per class
    idxes = np.argsort(classwise_output)[::-1] # get indexes of values sorted by min to max, then reverse so that order is max to min




    # Get probability value per frame for each top X class
    frames = [frame_ix for frame_ix in range(len(frame_arrays))]
    seconds = [f/100 for f in frames[::32]]

    slices = [100, 50, 10, 2]
    lines = []

    out_df = pd.DataFrame(seconds, columns=['seconds'])
    for slice in slices:
        temp_df = pd.DataFrame()
        idex_slice = idxes[:slice]
        for class_ix in idex_slice:
            class_lb = ix_to_lb[class_ix]
            class_probs = [frame_arrays[frame_ix][class_ix] for frame_ix in frames[::32]]
            # Add list as a column to dataframe
            temp_df[class_lb] = class_probs
            if slice == 10:
                out_df[class_lb] = class_probs
            if slice == 2:
                    # Optional: Make plot of SED results and save
                line, = plt.plot(seconds[:320], class_probs[:320], label=class_lb, linewidth=0.25)
                lines.append(line)
        label = 'speech_ratio_{0}'.format(slice)

        if slice == 50:
            out_df[label] = temp_df['Speech'] / temp_df.sum(axis=1)
            line, = plt.plot(seconds[:320], out_df[label][:320], label=label.format(slice), linewidth=0.25)
            lines.append(line)

    # Save full dataframe
    print('------ Save results ------')
    out_df.to_csv(out_fn_path, index=False)

    # Save plot
    plt.legend(handles=lines)
    plt.legend(bbox_to_anchor=(1,1), loc="upper left")
    plt.xlabel('Seconds')
    plt.ylabel('Probability')
    plt.ylim(0, 1.)
    plt.savefig(out_fig_path)
    print('Save fig to {}'.format(out_fig_path))

        # Take statistics/assess thresholds and add to group log
        # TODO: Was there speech? How much time of speech w/o a high threshold of music/noise?


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Analyze sound events.')

    parser.add_argument('source', type=str, help='wav file path')

    # parser.set_defaults(func=None)
    # parser.add_argument('-f', '--file', type=str, help='name to group files under (create and /or assume files are located in a subfolder: raw_audio/$group)')

    args = parser.parse_args()

    main(args.source)
