import gpype as gp


with gp.Pipeline() as p:
    eeg = gp.BCICore()
    markers = gp.LslReceiver(name='PsychoPyMarkers')
    writer = gp.EDFWriter(file_name="bci_session.edf") #let's record this for callibration
    
    p.connect(eeg, writer)
    p.connect(markers, writer)
    
    p.start()
    
    print("g.Pype is recording to EDF+...")
    print("Start your PsychoPy experiment now. Press [ENTER] here when finished to stop.")
    input()