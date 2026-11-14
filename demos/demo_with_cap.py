import gpype as gp

if __name__ == "__main__":
    app = gp.MainApp()
    p = gp.Pipeline()
    
    # Connect to the Unicorn amplifier via Bluetooth
    source = gp.HybridBlack() 
    
    # Create a visualization scope
    scope = gp.TimeSeriesScope(time_window=10) 
    
    p.connect(source, scope)
    app.add_widget(scope)
    
    p.start()
    app.run() 
    p.stop()