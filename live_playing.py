import json
from collections import deque

import gpype as gp
import numpy as np
import scipy.signal as sp

from mu_processor import BINS_FILE, C3_CHANNEL, extract_mu_features, assign_bin

KEYS = gp.Constants.Keys
PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT 


class MuPianoNeurofeedback(gp.Node): 
    """
    Continuous sliding-window neurofeedback processor.
    Loads calibrated bin edges and calls `on_bin_change(bin_number)` whenever
    the user's smoothed `c3_mean_abs` state shifts into a new bin (1..8).
    """

    def __init__(
        self,
        channel_labels,
        on_bin_change=None, 
        bins_file=BINS_FILE,
        window_seconds=2.0,
        update_interval_seconds=0.25,
        smoothing_steps=3,
        **kwargs,
    ):
        kwargs.setdefault(
            KEYS.INPUT_PORTS,
            [gp.IPort.Configuration(name=PORT_IN, timing=gp.Constants.Timing.ASYNC)],
        )
        kwargs.setdefault( 
            KEYS.OUTPUT_PORTS,
            [gp.OPort.Configuration(name=PORT_OUT, timing=gp.Constants.Timing.ASYNC)],
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
    