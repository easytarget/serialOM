from machine import Timer
'''
    Lumen (LED Indicator) stubs
    Suitable for a color RGB/NeoPixel with moods
    A mono LED could be used without the mood colors
'''

class lumen:
    moods = {
             'off':(1,1,0),
              'on':(0,1,0),
            'busy':(1,1,1),
             'job':(1,0,1),
          'paused':(0,0,1),
             'err':(1,0,0),
             }

    def __init__(self,bright=1,flash=120):
        '''
            start led/neopixel etc
            
            properties:
                self.bright = float(0..1), intensity
                self.flash  = int(), flash duration in ms
        '''
        self.bright = bright
        self.flash = flash
        self._heartbeat = 0
        pass

    def blink(self,mood):
        '''
            flash the mood after an update finishes
            use an interrupt timer
            to turn off after self.flash time
            timer features vary by MCU, example here is for RP2040, ymmv
        '''
        def unblink(t):
            # interrupt/schedule target
            #print('TODO: led-off')
            pass
        
        if mood == 'empty':
            return
        #print('TODO: led-on: "' + mood + '"')
        # uncomment timer line below
        #Timer(period=self.flash, mode=Timer.ONE_SHOT, callback=unblink)
        pass
    
    def send(self):
        '''
            Use for a seperate 'send heartbeat' led, if available
            cycling on/off every time a request cycle begins
        '''
        #print('TODO: send-flash')
        pass
    
    def emote(self,model):
        '''
            Use the model to find our mood by mapping the
            status to colors, crudely.
        '''

        status = model['state']['status']
        wifi = True
        if model is None:
            return('err')
        if model['state']['machineMode'] == '':
           return('err') 
        if status in ['disconnected','halted']:
            return('err')
        if status is 'off':
            if wifi:
                return('off')
            else:
                return('err')
        if status is 'idle':
            if wifi:
                return('on')
            else:
                return('err')
        if status in ['starting','updating','busy','changingTool']:
            return('busy')
        if status in ['pausing','paused','resuming','cancelling']:
            return('paused')
        if status in ['processing','simulating']:
            return('job')
        return 'empty'