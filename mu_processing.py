import csv
import math
from pathlib import Path

import gpype as gp
import numpy as np
import scipy.signal as sp

KEYS = gp.Constants.Keys
PORT_IN = gp.Constants.Defaults.PORT_IN

MU_LOW, MU_HIGH, FILTER_ORDER = 8.0, 12.0, 4
WINDOW_SECONDS = 4
PRE_TRIGGER_SECS = 0.1  # MUST MATCH TRIGGER IN EEG REMASTER
CALIBRATION_SECONDS = 160.0
N_BINS = 8
C3_CHANNEL = "C3"
OUTPUT_FILE = Path("outputs") / "mu_features.csv"

FEATURE_NAMES = [
    "c3_mean_abs", "c3_psd",
    "mean_channels_mean_abs", "mean_channels_psd",
    "median_channels_mean_abs", "median_channels_psd",
    "average_signal_mean_abs", "average_signal_psd",
]


class MuProcessor(gp.Sink):
    def __init__(
        self,
        channel_labels,
        epoch_labels=None,
        calibration_seconds=CALIBRATION_SECONDS,
        window_seconds=WINDOW_SECONDS,
        pre_trigger_secs=PRE_TRIGGER_SECS,
        output_file=OUTPUT_FILE,
        **kwargs,
    ):
        kwargs.setdefault(
            KEYS.INPUT_PORTS,
            [gp.IPort.Configuration(name=PORT_IN, timing=gp.Constants.Timing.ASYNC)],
        )
        super().__init__(**kwargs)

        self.channel_labels = list(channel_labels)
        self.epoch_labels = epoch_labels
        self.calibration_seconds = calibration_seconds
        self.window_seconds = window_seconds
        self.pre_trigger_secs = pre_trigger_secs
        self.output_file = Path(output_file)

        self.epochs_received = 0
        self.samples_received = 0
        self.calibration_values = {name: [] for name in FEATURE_NAMES}
        self.bin_edges = {}
        self.csv_file = None

    def setup(self, data, port_context_in):
        context = port_context_in[PORT_IN]
        self.fs = float(context[KEYS.SAMPLING_RATE])

        if C3_CHANNEL not in self.channel_labels:
            raise ValueError(f"{C3_CHANNEL} is not in the channel labels.")
        if context.get(KEYS.CHANNEL_COUNT) != len(self.channel_labels):
            raise ValueError("Channel count does not match channel labels.")

        self.c3_index = self.channel_labels.index(C3_CHANNEL)
        self.window_samples = round(self.fs * self.window_seconds)
        self.pre_trigger_samples = round(self.fs * self.pre_trigger_secs)
        self.calibration_epochs = math.ceil(self.calibration_seconds / self.window_seconds)

        self.sos = sp.butter(
            FILTER_ORDER, [MU_LOW, MU_HIGH], btype="bandpass", fs=self.fs, output="sos"
        )

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.csv_file = open(self.output_file, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(
            ["Epoch_number", "Epoch_time_seconds", "Calibration"]
            + FEATURE_NAMES
            + [f"{name}_bin" for name in FEATURE_NAMES]
        )
        metric_headers = [
            col for name in FEATURE_NAMES for col in (name, f"{name}_bin")
        ]
        self.csv_writer.writerow(
            ["Epoch_number", "Label", "Epoch_time_seconds", "Calibration"] + metric_headers
        )
        print(
            f"\nMU PROCESSOR INITIALIZED\n"
            f"Sampling rate: {self.fs} Hz | Channels: {len(self.channel_labels)} | "
            f"C3 index: {self.c3_index}\nPre-trigger removed: {self.pre_trigger_samples} | "
            f"Window: {self.window_seconds}s ({self.window_samples} samples) | "
            f"Calibration epochs: {self.calibration_epochs}"
        )
        return super().setup(data, port_context_in)

    def _band_metrics(self, signal):
        """Returns (mean_abs, mu_band_psd) along axis 0 for 1D or 2D signals."""
        mean_abs = np.mean(np.abs(signal), axis=0)
        freqs, psd = sp.periodogram(
            signal, fs=self.fs, window="hann", detrend="constant", scaling="density", axis=0
        )
        mask = (freqs >= MU_LOW) & (freqs <= MU_HIGH)
        band_psd = np.trapz(psd[mask], x=freqs[mask], axis=0)
        return mean_abs, band_psd

    def calculate_features(self, window):
        ch_abs, ch_psd = self._band_metrics(window)
        avg_abs, avg_psd = self._band_metrics(np.mean(window, axis=1))

        values = [
            ch_abs[self.c3_index], ch_psd[self.c3_index],
            np.mean(ch_abs), np.mean(ch_psd),
            np.median(ch_abs), np.median(ch_psd),
            avg_abs, avg_psd,
        ]
        return dict(zip(FEATURE_NAMES, map(float, values)))

    def calibrate(self):
        print("\nCALIBRATION FINISHED (QUANTILE BINS)")
        quantiles = np.linspace(0, 100, N_BINS + 1)

        for name in FEATURE_NAMES:
            vals = np.asarray(self.calibration_values[name], dtype=np.float64)
            edges = np.percentile(vals, quantiles)

            # Guarantee strictly increasing edges if identical values occur
            edges += np.arange(N_BINS + 1) * 1e-12
            self.bin_edges[name] = edges

            print(f"\n{name} (min={vals.min():.6f}, max={vals.max():.6f})")
            for i in range(N_BINS):
                print(f"  Bin {i + 1}: {edges[i]:.6f} - {edges[i + 1]:.6f}")
        print("\n8-BIN CALIBRATION COMPLETE\n")

    def get_bin(self, name, value):
        idx = np.searchsorted(self.bin_edges[name][1:-1], value, side="right") + 1
        return int(np.clip(idx, 1, N_BINS))

    def _get_epoch_label(self, epoch_num, is_calibration):
        if isinstance(self.epoch_labels, dict):
            return self.epoch_labels.get(epoch_num, "")
        if isinstance(self.epoch_labels, (list, tuple)) and 0 <= epoch_num - 1 < len(self.epoch_labels):
            return self.epoch_labels[epoch_num - 1]
        return "calibration" if is_calibration else "trial"

    def step(self, data):
        epoch = np.asarray(data[PORT_IN], dtype=np.float64)
        if epoch.ndim != 2:
            raise ValueError("Expected an epoch with shape (samples, channels).")
        if epoch.shape[1] != len(self.channel_labels):
            raise ValueError("Epoch channel count does not match channel labels.")

        self.samples_received += len(epoch)
        epoch = epoch[self.pre_trigger_samples :]
        if len(epoch) < self.window_samples:
            raise ValueError(
                f"Epoch is too short: received {len(epoch)} samples, expected {self.window_samples}."
            )

        filtered = sp.sosfiltfilt(self.sos, epoch[: self.window_samples], axis=0)
        features = self.calculate_features(filtered)
        self.epochs_received += 1

        is_calibration = not self.bin_edges
        label = self._get_epoch_label(self.epochs_received, is_calibration)

        if is_calibration:
            for name in FEATURE_NAMES:
                self.calibration_values[name].append(features[name])
            bins = {name: "-" for name in FEATURE_NAMES}
            if self.epochs_received >= self.calibration_epochs:
                self.calibrate()
        else:
            bins = {name: self.get_bin(name, features[name]) for name in FEATURE_NAMES}
            print(f"\nEpoch {self.epochs_received}")
            for name in FEATURE_NAMES:
                print(f"{name}: {features[name]:.6f} -> bin {bins[name]}")
        metric_cells = [
            cell
            for name in FEATURE_NAMES
            for cell in (f"{features[name]:.6f}", bins[name])
        ]
        self.csv_writer.writerow(
            [self.epochs_received, label, self.epochs_received * self.window_seconds, is_calibration]
            + metric_cells
        )
        self.csv_file.flush()
        return {}

    def stop(self):
        super().stop()
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        print(
            f"\nMU PROCESSOR STOPPED\nTotal samples: {self.samples_received}\n"
            f"Total epochs: {self.epochs_received}\nResults saved to: {self.output_file}"
        )