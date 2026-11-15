import gpype as gp

if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    
    # create a data source and a visualization scope
    source = gp.Generator(signal_frequency=4, signal_amplitude=25, noise_amplitude=25) 
    scope = gp.TimeSeriesScope(time_window=10) 
    
    p.connect(source, scope)
    app.add_widget(scope)
    p.start()
    app.run() 
    p.stop()