import gpype as gp

if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    
    source = gp.HybridBlack() 

    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    
    #montage to average
    reref = gp.Reference(reference=None)
    scope = gp.TimeSeriesScope(time_window=10) 
    
    # 5. Connect the pipeline: Hardware -> Filters -> Re-reference -> Scope
    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    p.connect(notch50, reref)
    p.connect(reref, scope)
    
    app.add_widget(scope)
    
    p.start()
    app.run() 
    p.stop()