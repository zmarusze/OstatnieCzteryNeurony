import mne
import numpy as np
import gpype as gp

# FixedRateSource is the base class gpype's own Generator / CsvReader use:
# it runs the pacing thread for you (one cycle per sample).
from gpype.backend.sources.base.fixed_rate_source import FixedRateSource

# IMPORT YOUR PROCESSOR HERE
from mu_processing import MuProcessor

# ==========================================
# CONFIGURATION
# ==========================================
CHANNEL_LABELS = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "Oz", "PO8"]
N_EEG_CHANNELS = len(CHANNEL_LABELS)

# MNE returns volts; g.tec amplifiers (and the gpype scope defaults) work in
# microvolts. Set to 1.0 if your MuProcessor expects raw volts.
VOLTS_TO_MICROVOLTS = 1e6

KEYS = gp.Constants.Keys
PORT_IN = gp.Constants.Defaults.PORT_IN
PORT_OUT = gp.Constants.Defaults.PORT_OUT


# ==========================================
# 1. CUSTOM PHYSIONET SOURCE NODE
# ==========================================
class PhysioNetDevice(FixedRateSource):
    """
    Simulates a real EEG device by streaming a PhysioNet recording
    chunk by chunk in real time.

    FixedRateSource runs its pacing thread once per *sample*, while step()
    emits a whole chunk, so decimation_factor must equal chunk_size.
    Otherwise the recording would play chunk_size times too fast.
    """

    def __init__(self, subject=1, run=4, chunk_size=16, **kwargs):
        print(f"Loading PhysioNet Subject {subject}, Run {run}...")

        # Suppress MNE verbosity for clean console
        mne.set_log_level("WARNING")
        file_paths = mne.datasets.eegbci.load_data(subject, [run])

        raw = mne.io.read_raw_edf(file_paths[0], preload=True)
        mne.datasets.eegbci.standardize(raw)

        raw.pick(CHANNEL_LABELS)
        raw.reorder_channels(CHANNEL_LABELS)

        fs = float(raw.info["sfreq"])
        samples = raw.get_data().T * VOLTS_TO_MICROVOLTS
        self._samples = np.ascontiguousarray(samples, dtype=gp.Constants.DATA_TYPE)
        self._position = 0
        self._exhausted = False

        print(
            f"Data loaded! Shape: {self._samples.shape}, "
            f"Sampling Rate: {fs} Hz"
        )

        kwargs.setdefault("output_ports", [gp.OPort.Configuration()])
        super().__init__(
            sampling_rate=fs,
            channel_count=len(CHANNEL_LABELS),
            frame_size=int(chunk_size),
            decimation_factor=int(chunk_size),
            **kwargs,
        )

    @property
    def fs(self) -> float:
        return float(self.config[self.Configuration.Keys.SAMPLING_RATE])

    def setup(self, data, port_context_in):
        # Sampling rate, channel count, frame size and frame rate are
        # declared by FixedRateSource / Source from the constructor
        # arguments. Only the playback position needs resetting here,
        # because setup() runs again on every start.
        self._position = 0
        self._exhausted = False
        return super().setup(data, port_context_in)

    def step(self, data=None):
        # The pacing thread calls this once per sample; only every
        # chunk_size-th call is allowed to emit a chunk.
        if not self.is_decimation_step():
            return None
        if self._exhausted:
            return None

        chunk_size = self.config[self.Configuration.Keys.FRAME_SIZE]
        if isinstance(chunk_size, list):
            chunk_size = chunk_size[0]

        end = self._position + chunk_size
        if end > self._samples.shape[0]:
            # A partial chunk would break the sampling grid, so playback
            # ends on the last whole chunk. (Raising StopIteration here
            # would kill the pacing thread with a traceback instead.)
            self._exhausted = True
            print("\n--- End of PhysioNet playback reached ---")
            return None

        chunk = self._samples[self._position:end, :]
        self._position = end
        return {PORT_OUT: chunk}


# ==========================================
# 2. CUSTOM CONTINUOUS EPOCH NODE
# ==========================================
class ContinuousEpoch(gp.IONode):
    """
    Buffers continuous data and outputs a fixed-size epoch of
    ``window_seconds`` every ``step_seconds``.

    Declares its output frame size (window) and decimation factor (step)
    the same way gpype's FFT node does, so downstream nodes see the real
    epoch shape and rate. The sampling rate must be given up front because
    gpype fixes the frame size at construction time.
    """

    def __init__(self, sampling_rate, window_seconds=4.1, step_seconds=4.1,
                 **kwargs):
        self._window_samples = int(round(window_seconds * sampling_rate))
        self._step_samples = int(round(step_seconds * sampling_rate))
        if self._window_samples < 1 or self._step_samples < 1:
            raise ValueError("window_seconds and step_seconds must span at "
                             "least one sample.")

        # frame_size is a derived value; drop it if a serialized document
        # passes it back in.
        kwargs.pop(KEYS.FRAME_SIZE, None)

        # Epochs are discrete events, not a continuous stream, so the output
        # port is ASYNC (same as gp.Trigger). A node with an ASYNC input,
        # such as MuProcessor, refuses to connect to a SYNC port.
        kwargs.setdefault(
            KEYS.OUTPUT_PORTS,
            [gp.OPort.Configuration(timing=gp.Constants.Timing.ASYNC)],
        )

        super().__init__(frame_size=self._window_samples, **kwargs)
        self._sampling_rate = float(sampling_rate)
        self._buf = None
        self._filled = 0
        self._since_last = 0

    def setup(self, data, port_context_in):
        port_context_out = super().setup(data, port_context_in)

        fs_in = float(port_context_in[PORT_IN][KEYS.SAMPLING_RATE])
        if abs(fs_in - self._sampling_rate) > 1e-6:
            raise ValueError(
                f"ContinuousEpoch was built for {self._sampling_rate} Hz "
                f"but its input runs at {fs_in} Hz."
            )

        frame_size_in = port_context_in[PORT_IN][KEYS.FRAME_SIZE]
        if frame_size_in > self._step_samples:
            raise ValueError(
                f"Input frames carry {frame_size_in} samples but the epoch "
                f"step is only {self._step_samples}; a cycle can emit at "
                f"most one epoch."
            )

        channel_count = port_context_out[PORT_OUT][KEYS.CHANNEL_COUNT]
        self._buf = np.zeros((self._window_samples, channel_count),
                             dtype=gp.Constants.DATA_TYPE)
        self._filled = 0
        self._since_last = 0

        out = port_context_out[PORT_OUT]
        out[KEYS.FRAME_SIZE] = self._window_samples
        out[gp.OPort.Configuration.Keys.TIMING] = gp.Constants.Timing.ASYNC
        # Epochs have no fixed frame rate; drop the one inherited from the
        # continuous input.
        out.pop(KEYS.FRAME_RATE, None)
        return port_context_out

    def step(self, data):
        block = data[PORT_IN]
        rows = block.shape[0]
        window = self._buf.shape[0]

        # Rolling buffer, oldest sample first.
        if rows >= window:
            self._buf[:] = block[-window:]
        elif rows:
            self._buf[:-rows] = self._buf[rows:]
            self._buf[-rows:] = block

        self._filled = min(window, self._filled + rows)
        self._since_last += rows

        # Wait until a full window exists, then emit once per step
        # (counted in samples, not cycles).
        if self._filled < window or self._since_last < self._step_samples:
            return None
        self._since_last -= self._step_samples

        # Copy: the buffer is reused immediately.
        return {PORT_OUT: self._buf.copy()}


# ==========================================
# 3. MAIN PIPELINE
# ==========================================
if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()

    # 1. Source (PhysioNet Dataset)
    device = PhysioNetDevice(subject=1, run=4, chunk_size=16)
    labeler = gp.ChannelLabeler(labels=CHANNEL_LABELS)

    # 2. Preprocessing
    bandpass = gp.Bandpass(f_lo=1, f_hi=40)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)

    # 3. Epoching (output an epoch every 4.1 seconds)
    window = ContinuousEpoch(
        sampling_rate=device.fs, window_seconds=4.1, step_seconds=4.1
    )

    # 4. Your MuProcessor (Imported!)
    mu_processor = MuProcessor(
        channel_labels=CHANNEL_LABELS,
        pre_trigger_secs=0.1,
        window_seconds=4.0,
        calibration_seconds=60.0,  # Kept at 60s so it finishes before the 120s dataset ends!
    )

    # 5. Visualization Scope
    scope = gp.TimeSeriesScope(name="PhysioNet EEG Playback", time_window=10)

    # --- Connections ---
    p.connect(device, labeler)
    p.connect(labeler, bandpass)
    p.connect(bandpass, notch50)

    # Split the clean data: send to scope AND to our windowing node
    p.connect(notch50, scope)

    p.connect(notch50, window)
    p.connect(window, mu_processor)

    app.add_widget(scope)

    print("\nPipeline initialized! Starting playback and calibration...")

    try:
        p.start()
        app.run()
    except KeyboardInterrupt:
        print("\nManually interrupted.")
    finally:
        p.stop()