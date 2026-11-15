import json
from collections import deque

import gpype as gp
import numpy as np
import scipy.signal as sp

from mu_calibration import BINS_FILE, C3_CHANNEL, extract_mu_features, assign_bin #type:ignore

KEYS = gp.Constants.Keys
PORT_IN = gp.Constants.Defaults.PORT_IN

class MuPianoNeurofeedback(gp.Sink): 
    """
    Continuous sliding-window neurofeedback processor.
    Loads calibrated bin edges and calls `on_bin_change(bin_number)` whenever
    the user's smoothed state shifts into a new bin (1..8).
    """

    def __init__(
        self,
        channel_labels,
        on_bin_change=None, 
        bins_file=BINS_FILE,
        feature_name="c3_mean_abs", 
        window_seconds=2.0,
        update_interval_seconds=0.25,
        smoothing_steps=3,
        **kwargs):

        kwargs.setdefault(
            KEYS.INPUT_PORTS,
            [gp.IPort.Configuration(name=PORT_IN, timing=gp.Constants.Timing.SYNC)], #type:ignore
)
        super().__init__(**kwargs)

        self.channel_labels = list(channel_labels)
        self.on_bin_change = on_bin_change 
        self.feature_name = feature_name
        self.window_seconds = window_seconds
        self.update_interval_seconds = update_interval_seconds
        self.smoothing_steps = smoothing_steps

        with open(bins_file, "r") as f:
            calib = json.load(f)

        self.mu_low = calib["mu_low"]
        self.mu_high = calib["mu_high"]
        self.filter_order = calib["filter_order"]
        self.n_bins = calib["n_bins"]
        self.edges = calib["bin_edges"][feature_name]

        self.recent_bins = deque(maxlen=smoothing_steps)
        self.current_bin = None
        self.samples_since_eval = 0
        self.buffer_filled = 0

    def setup(self, data, port_context_in):
        """Initializes the sliding window buffer and filter based on the sampling rate."""
        context = port_context_in[PORT_IN]
        self.fs = float(context[KEYS.SAMPLING_RATE])

        if C3_CHANNEL not in self.channel_labels:
            raise ValueError(f"{C3_CHANNEL} not found in channel labels.")
        
        self.c3_index = self.channel_labels.index(C3_CHANNEL)
        self.window_samples = round(self.fs * self.window_seconds)
        self.update_samples = round(self.fs * self.update_interval_seconds)

        self.buffer = np.zeros((self.window_samples, len(self.channel_labels)), dtype=np.float64)
        self.sos = sp.butter(self.filter_order, [self.mu_low, self.mu_high], btype="bandpass", fs=self.fs, output="sos")

        print(f"\n[NEUROFEEDBACK INITIALIZED]")
        print(f"Tracking: {self.feature_name}")
        print(f"Window: {self.window_seconds}s | Updating every: {self.update_interval_seconds}s")
        print(f"Smoothing steps: {self.smoothing_steps}\n")

        return super().setup(data, port_context_in)

    def step(self, data):
        """Processes incoming continuous data, manages the sliding window, and emits bins."""
        new_samples = np.asarray(data[PORT_IN], dtype=np.float64)
        n_new = len(new_samples)
        
        if n_new == 0:
            return {}

        if n_new >= self.window_samples:
            self.buffer = new_samples[-self.window_samples:]
            self.buffer_filled = self.window_samples
        else:
            self.buffer[:-n_new] = self.buffer[n_new:]
            self.buffer[-n_new:] = new_samples
            self.buffer_filled = min(self.window_samples, self.buffer_filled + n_new)

        self.samples_since_eval += n_new

        if self.buffer_filled >= self.window_samples and self.samples_since_eval >= self.update_samples:
            
            filtered = sp.sosfiltfilt(self.sos, self.buffer, axis=0)
            features = extract_mu_features(filtered, self.fs, self.c3_index)
            feature_val = features.get(self.feature_name)
            
            if feature_val is not None:
                raw_bin = assign_bin(self.edges, feature_val, n_bins=self.n_bins)
                self.recent_bins.append(raw_bin)
                
                smoothed_bin = int(np.median(self.recent_bins))
                if smoothed_bin != self.current_bin:
                    self.current_bin = smoothed_bin
                    print(f"--> [MU SHIFT] New Bin: {self.current_bin}") 
                    
                    if self.on_bin_change is not None:
                        self.on_bin_change(self.current_bin)
            
            self.samples_since_eval %= self.update_samples 

        return {}