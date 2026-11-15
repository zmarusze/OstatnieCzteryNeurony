# 🧠🎹 Heroes of the Brain Hackathon — Ostatnie Cztery Neurony 

### Your brain. Your music. Your instrument.

Welcome to our **Brain (as a) Composer Interface**!

This project explores how brain activity can be translated into music using EEG (electroencephalography) and Brain-Computer Interface (BCI) technology.

Our goal is to make music creation more accessible, particularly for people with motor disabilities. By interpreting EEG signals, the system allows users to interact with a virtual piano through brain activity rather than conventional physical controls.

The project includes three main components:

- **Auditory Artifact Detection (AAD)** — analysis of EEG signals to identify artifacts associated with blinking, jaw activity, and head movement.
- **Motor Imagery Calibration** — a calibration procedure for distinguishing between imagined right-hand movement, imagined left-hand movement, and rest. This includes an integrated PsychoPy experimental procedure.
- **BCI-Controlled Piano** — an interactive musical interface that uses EEG-based control to play piano notes.

---

## 🚀 Getting Started

If you're new to the project, here's how to explore and use it.

### 1. Set up your environment

Start with the 'requirements.txt' file. It contains the dependencies needed to prepare your Python environment.

Make sure to complete the setup before running any of the project scripts.

### 2. Understand the configuration

Before running an experiment, take a look at these two files:

| File | What it does |
|---|---|
| `constants.py` | Contains the main constants and configuration parameters used for EEG signal acquisition. |
| `utils.py` | Provides helper functionality, including the PsychoPy marker-streaming utility used to synchronise experimental events with EEG recordings. |

These files are a good starting point if you want to understand or adapt the project to your own setup.

---

## 🔬 Project Modules

### 1. Auditory Artifact Detection

EEG recordings can contain unwanted signals caused by movements such as blinking, jaw clenching, or moving your head. These artifacts can interfere with the interpretation of brain activity.

Our Auditory Artifact Detection component explores the identification and analysis of these signals.

| File | What it does |
|---|---|
| `evaluate_calibration_on_outsource_data.py` | Evaluates the calibration prototype using external EEG data from PhysioNet. |
| `run_aad.py` | Runs the auditory artifact detection analysis. |

*💡 Fun fact: We weren't planning on doing this analysis but we encountered some problems with our EEG cap, so we decided to use publically available EEG data from PhysioNet. Thankfully, we resolved the problem and now we have an additional cmponent of our project!*

### 2. Motor Imagery Calibration

Motor imagery is the process of imagining a movement without physically performing it. In our project, users are asked to imagine moving their right hand, imagine moving their left hand, or remain at rest.

The calibration procedure provides the basis for interpreting EEG activity during these different conditions.

| File | What it does |
|---|---|
| `run_calibration.py` | Runs the calibration procedure and collects the corresponding EEG data. |
| `pilot_calibration_results.ipynb` | Jupyter Notebook containing the results and analysis of our pilot calibration. |

The calibration procedure also uses PsychoPy to present experimental instructions and cues, while markers identify the different stages of the task.


### 3. BCI-Controlled Piano 🎹

This is the main interactive component of the project: a virtual piano controlled using EEG signals.

The system combines live EEG processing with a musical interface to translate brain activity into piano interactions.

| File | What it does |
|---|---|
| `run_bci_piano.py` | Main entry point for running the BCI-controlled piano. |
| `live_playing.py` | Handles the live processing and interaction logic used during piano control. |
| `piano.py` | Implements the piano interface and its musical functionality. |

Start by exploring the supporting files to understand how the live processing and piano interface work together, then use `run_bci_piano.py` to launch the main application.


---

## 🗂️ Repository Overview

For convenience, here's a quick reference to the main files:

| File | Purpose |
|---|---|
| `constants.py` | EEG acquisition configuration and constants |
| `utils.py` | Shared utilities and PsychoPy marker streaming |
| `evaluate_calibration_on_outsource_data.py` | Calibration evaluation using external EEG data |
| `run_aad.py` | Auditory artifact detection |
| `run_calibration.py` | Motor imagery calibration procedure |
| `pilot_calibration_results.ipynb` | Pilot calibration results and analysis |
| `live_playing.py` | Live BCI processing and interaction |
| `piano.py` | Virtual piano implementation |
| `run_bci_piano.py` | Main BCI piano application |

---

## 🧪 Try It Yourself!

We encourage you to explore the project, experiment with the calibration procedure, and, if you have compatible EEG equipment, record your own brain activity.

A few things to keep in mind:

- Make sure your Python environment is configured before running the scripts.
- Check the acquisition settings in `constant.py` and adapt them to your EEG hardware where necessary.
- Follow the instructions presented by the PsychoPy experiment during calibration.
- EEG recordings can be affected by movement and other artifacts, so try to remain relaxed and minimise unnecessary movement during the experiment.
- The quality of the calibration can influence how well the BCI responds.

And most importantly, have fun!

We hope you'll enjoy discovering how your brain can become a musical instrument. With practice, you might even get better at controlling the piano and playing your own songs — one thought at a time.
