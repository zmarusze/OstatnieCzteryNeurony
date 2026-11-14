import mne
import numpy as np
import pandas as pd

file_path = "outputs/bci_synthetic_mu_power_features_20261114_195005_053.edf" 

print(f"Loading {file_path}...")
raw = mne.io.read_raw_edf(file_path, preload=True)
stim_channel = raw.ch_names[-1]

events = mne.find_events(raw, stim_channel=stim_channel)
event_id = {'Rest': 1, 'Right_MI': 2, 'Left_MI': 3}

print("Slicing out the exact epochs...")
epochs = mne.Epochs(raw, events, event_id, tmin=0.5, tmax=4.0, baseline=None, preload=True)
data = epochs.get_data() 
mean_power = np.mean(data, axis=2)

df = pd.DataFrame({
    'Marker_Code': epochs.events[:, 2],  
    'C3_Mu_Power': mean_power[:, 0], # First channel is C3
    'C4_Mu_Power': mean_power[:, 1]  # Second channel is C4
})


label_map = {1: 'Rest', 2: 'Right_MI', 3: 'Left_MI'}
df['Category'] = df['Marker_Code'].map(label_map)

out_file = "outputs/ml_training_dataset.csv"
df.to_csv(out_file, index=False)

print(f"\nSUCCESS! Extracted {len(df)} epochs.")
print(f"Saved your ML categories to {out_file}\n")
print(df.head(10))