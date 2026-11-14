import csv
import os

import numpy as np
import scipy.signal as sp

import gpype as gp


KEYS = gp.Constants.Keys
PORT_IN = gp.Constants.Defaults.PORT_IN


# ============================================================
# CONFIGURATION
# ============================================================

MU_LOW = 8.0
MU_HIGH = 12.0

FILTER_ORDER = 4

WINDOW_SECONDS = 0.5

CALIBRATION_SECONDS = 300.0

N_BINS = 8

C3_CHANNEL = "C3"

OUTPUT_FILE = os.path.join(
    "outputs",
    "mu_features.csv"
)


# ============================================================
# REAL-TIME MU PROCESSING SINK
# ============================================================

class MuProcessor(gp.Sink):

    def __init__(
        self,
        channel_labels,
        calibration_seconds=CALIBRATION_SECONDS,
        window_seconds=WINDOW_SECONDS,
        output_file=OUTPUT_FILE,
        **kwargs
    ):

        input_ports = kwargs.pop(
            KEYS.INPUT_PORTS,
            [gp.IPort.Configuration()]
        )

        super().__init__(
            input_ports=input_ports,
            **kwargs
        )

        self.channel_labels = list(channel_labels)

        self.calibration_seconds = calibration_seconds
        self.window_seconds = window_seconds

        self.output_file = output_file

        self.fs = None
        self.window_samples = None

        self.sos = None
        self.zi = None

        self.buffer = None

        self.samples_received = 0
        self.windows_received = 0

        self.calibration_windows = None
        self.calibration_values = {}

        self.bin_edges = {}

        self.calibrated = False

        self.csv_file = None
        self.csv_writer = None

        self.feature_names = [
            "c3_mean_abs",
            "c3_psd",

            "mean_channels_mean_abs",
            "mean_channels_psd",

            "median_channels_mean_abs",
            "median_channels_psd",

            "average_signal_mean_abs",
            "average_signal_psd"
        ]


    # ========================================================
    # SETUP
    # ========================================================

    def setup(self, data, port_context_in):

        context = port_context_in[PORT_IN]

        self.fs = float(
            context[KEYS.SAMPLING_RATE]
        )

        n_channels = len(self.channel_labels)

        if C3_CHANNEL not in self.channel_labels:
            raise ValueError(
                f"{C3_CHANNEL} is not in the channel labels."
            )

        if context.get(KEYS.CHANNEL_COUNT) != n_channels:
            raise ValueError(
                "Channel count does not match channel labels."
            )

        self.c3_index = self.channel_labels.index(C3_CHANNEL)

        self.window_samples = int(
            round(self.fs * self.window_seconds)
        )

        self.calibration_windows = int(
            round(self.calibration_seconds / self.window_seconds)
        )

        # Fourth-order Butterworth mu bandpass.
        # SOS representation is numerically stable.

        self.sos = sp.butter(
            FILTER_ORDER,
            [MU_LOW, MU_HIGH],
            btype="bandpass",
            fs=self.fs,
            output="sos"
        )

        # Preserve filter state between incoming frames.

        self.zi = np.zeros(
            (self.sos.shape[0], 2, n_channels),
            dtype=np.float64
        )

        # Buffer for incomplete 500 ms windows.

        self.buffer = np.empty(
            (0, n_channels),
            dtype=np.float64
        )

        # Calibration storage.

        self.calibration_values = {
            name: [] for name in self.feature_names
        }

        # CSV output.

        os.makedirs(
            os.path.dirname(self.output_file) or ".",
            exist_ok=True
        )

        self.csv_file = open(
            self.output_file,
            "w",
            newline=""
        )

        self.csv_writer = csv.writer(
            self.csv_file
        )

        self.csv_writer.writerow(
            [
                "Time_seconds",
                "Window_number",
                "Calibration",
            ]
            + self.feature_names
            + [
                name + "_bin"
                for name in self.feature_names
            ]
        )

        print("\nMU PROCESSOR INITIALIZED")

        print(f"Sampling rate: {self.fs} Hz")
        print(f"Window length: {self.window_seconds} s")
        print(f"Samples per window: {self.window_samples}")
        print(f"C3 channel index: {self.c3_index}")

        print(
            f"Calibration duration: "
            f"{self.calibration_seconds} seconds"
        )

        return super().setup(data, port_context_in)


    # ========================================================
    # FILTERING
    # ========================================================

    def filter_frame(self, frame):

        filtered, self.zi = sp.sosfilt(
            self.sos,
            frame,
            axis=0,
            zi=self.zi
        )

        return filtered


    # ========================================================
    # FEATURE EXTRACTION
    # ========================================================

    def calculate_features(self, window):

        # window shape:
        # (samples, channels)

        # ----------------------------------------------------
        # 1. Rectified mean amplitude for each channel
        # ----------------------------------------------------

        mean_abs_per_channel = np.mean(
            np.abs(window),
            axis=0
        )

        # ----------------------------------------------------
        # 2. PSD for each channel
        # ----------------------------------------------------

        frequencies, psd = sp.periodogram(
            window,
            fs=self.fs,
            window="hann",
            detrend="constant",
            scaling="density",
            axis=0
        )

        mu_mask = (
            (frequencies >= MU_LOW)
            &
            (frequencies <= MU_HIGH)
        )

        mu_frequencies = frequencies[mu_mask]

        mu_psd = psd[mu_mask, :]

        psd_per_channel = np.trapz(
            mu_psd,
            x=mu_frequencies,
            axis=0
        )

        # ----------------------------------------------------
        # 3. C3 only
        # ----------------------------------------------------

        c3_mean_abs = mean_abs_per_channel[
            self.c3_index
        ]

        c3_psd = psd_per_channel[
            self.c3_index
        ]

        # ----------------------------------------------------
        # 4. Mean of individual channel features
        # ----------------------------------------------------

        mean_channels_mean_abs = np.mean(
            mean_abs_per_channel
        )

        mean_channels_psd = np.mean(
            psd_per_channel
        )

        # ----------------------------------------------------
        # 5. Median of individual channel features
        # ----------------------------------------------------

        median_channels_mean_abs = np.median(
            mean_abs_per_channel
        )

        median_channels_psd = np.median(
            psd_per_channel
        )

        # ----------------------------------------------------
        # 6. Average the filtered signals first
        # ----------------------------------------------------

        average_signal = np.mean(
            window,
            axis=1
        )

        average_signal_mean_abs = np.mean(
            np.abs(average_signal)
        )

        average_frequencies, average_psd = sp.periodogram(
            average_signal,
            fs=self.fs,
            window="hann",
            detrend="constant",
            scaling="density"
        )

        average_mu_mask = (
            (average_frequencies >= MU_LOW)
            &
            (average_frequencies <= MU_HIGH)
        )

        average_signal_psd = np.trapz(
            average_psd[average_mu_mask],
            x=average_frequencies[average_mu_mask]
        )

        # ----------------------------------------------------
        # Return all candidate features
        # ----------------------------------------------------

        return {
            "c3_mean_abs": float(c3_mean_abs),

            "c3_psd": float(c3_psd),

            "mean_channels_mean_abs": float(
                mean_channels_mean_abs
            ),

            "mean_channels_psd": float(
                mean_channels_psd
            ),

            "median_channels_mean_abs": float(
                median_channels_mean_abs
            ),

            "median_channels_psd": float(
                median_channels_psd
            ),

            "average_signal_mean_abs": float(
                average_signal_mean_abs
            ),

            "average_signal_psd": float(
                average_signal_psd
            )
        }


    # ========================================================
    # CALIBRATION
    # ========================================================

    def calibrate(self):

        print("\nCALIBRATION FINISHED")

        for name in self.feature_names:

            values = np.asarray(
                self.calibration_values[name],
                dtype=np.float64
            )

            minimum = np.min(values)
            maximum = np.max(values)

            # Equal-width bins across the calibration range.

            if maximum == minimum:

                epsilon = max(
                    abs(minimum) * 1e-9,
                    1e-12
                )

                minimum -= epsilon
                maximum += epsilon

            edges = np.linspace(
                minimum,
                maximum,
                N_BINS + 1
            )

            self.bin_edges[name] = edges

            print(f"\n{name}")

            print(f"Minimum: {minimum:.8f}")
            print(f"Maximum: {maximum:.8f}")

            print("Bin boundaries:")

            for i in range(N_BINS):

                print(
                    f"Bin {i + 1}: "
                    f"{edges[i]:.8f} - "
                    f"{edges[i + 1]:.8f}"
                )

        self.calibrated = True

        print("\n8-BIN CALIBRATION COMPLETE\n")


    # ========================================================
    # CONVERT FEATURE VALUE INTO BIN 1-8
    # ========================================================

    def get_bin(self, feature_name, value):

        edges = self.bin_edges[feature_name]

        bin_number = np.searchsorted(
            edges[1:-1],
            value,
            side="right"
        ) + 1

        return int(
            np.clip(bin_number, 1, N_BINS)
        )


    # ========================================================
    # PROCESS ONE COMPLETE 500 ms WINDOW
    # ========================================================

    def process_window(self, window):

        features = self.calculate_features(window)

        self.windows_received += 1

        timestamp = (
            self.windows_received
            * self.window_seconds
        )

        # ----------------------------------------------------
        # CALIBRATION PERIOD
        # ----------------------------------------------------

        if not self.calibrated:

            for name in self.feature_names:

                self.calibration_values[name].append(
                    features[name]
                )

            is_calibration = True

            bins = {
                name: ""
                for name in self.feature_names
            }

            if (
                self.windows_received
                >= self.calibration_windows
            ):

                self.calibrate()

        # ----------------------------------------------------
        # FREE-RUNNING PERIOD
        # ----------------------------------------------------

        else:

            is_calibration = False

            bins = {
                name: self.get_bin(
                    name,
                    features[name]
                )
                for name in self.feature_names
            }

            # Print the candidate values and bins.

            print(
                f"\nWindow {self.windows_received}"
            )

            for name in self.feature_names:

                print(
                    f"{name}: "
                    f"{features[name]:.6f} "
                    f"-> bin {bins[name]}"
                )

        # ----------------------------------------------------
        # SAVE RESULTS
        # ----------------------------------------------------

        row = [
            timestamp,
            self.windows_received,
            is_calibration
        ]

        row += [
            features[name]
            for name in self.feature_names
        ]

        row += [
            bins[name]
            for name in self.feature_names
        ]

        self.csv_writer.writerow(row)

        self.csv_file.flush()


    # ========================================================
    # REAL-TIME INPUT
    # ========================================================

    def step(self, data):

        frame = data[PORT_IN]

        # Filter incoming samples continuously.

        filtered = self.filter_frame(frame)

        self.samples_received += len(frame)

        # Add the incoming frame to the buffer.

        self.buffer = np.vstack(
            (self.buffer, filtered)
        )

        # Process every complete 500 ms window.

        while (
            len(self.buffer)
            >= self.window_samples
        ):

            window = self.buffer[
                :self.window_samples
            ]

            self.buffer = self.buffer[
                self.window_samples:
            ]

            self.process_window(window)

        return {}


    # ========================================================
    # SHUTDOWN
    # ========================================================

    def stop(self):

        super().stop()

        if self.csv_file is not None:

            self.csv_file.close()

            self.csv_file = None

        print("\nMU PROCESSOR STOPPED")

        print(
            f"Total samples: {self.samples_received}"
        )

        print(
            f"Total windows: {self.windows_received}"
        )

        print(
            f"Results saved to: {self.output_file}"
        )
