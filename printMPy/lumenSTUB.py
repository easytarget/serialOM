from machine import Timer
'''
    Lumen (LED Indicator) stubs
    Suitable for a color RGB/NeoPixel with moods
    A mono LED could be used without the mood colors
'''

class lumen:
    moods = {
             'off':(1,1,0), # orange
              'on':(0,1,0), # green
            'busy':(1,1,1), # white
             'job':(1,0,1), # violet
          'paused':(0,0,1), # blue
             'err':(1,0,0), # red
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
            use an interrupt timer to turn off after flash time
            timer features vary by MCU, example here is for RP2040, ymmv
        '''
        def unblink(t):
            # interrupt/schedule target
            #print('TODO: led-off')
            pass # Put code here to turn the LED off

        if mood == 'empty':
            return
        # uncomment timer line below
        #Timer(period=self.flash, mode=Timer.ONE_SHOT, callback=unblink)
        #print('TODO: led-on: "' + mood + '"')
        pass  # Put code here to turn the LED on, if it is RGB use the colors in the mood map.

    def send(self):
        '''
            Use for a seperate 'send heartbeat' led, if available
            cycling on/off every time a request cycle begins
        '''
        self._heartbeat = not self._heartbeat
        if self._heartbeat:
            #print('TODO: heartbeat on')
            pass  # replace with code to turn heartbeat indicator on
        else:
            #print('TODO: heartbeat off')
            pass  # replace with code to turn heartbeat indicator off

    def emote(self,model):
        '''
            Use the model to find our mood by mapping the
            status to colors, crudely.
        '''

        if model is None:
            return('err')
        if 'state' in model.keys():
            status = model['state']['status']
        else:
            return 'err'
        network = False
        if 'network' in model.keys():
            if len(model['network']['interfaces']) > 0:
                for interface in model['network']['interfaces']:
                    if interface['state'] is 'active':
                        network = True
        if model['state']['machineMode'] == '':
           return('err')
        if status in ['disconnected','halted']:
            return('err')
        if status is 'off':
            if network:
                return('off')
            else:
                return('err')
        if status is 'idle':
            if network:
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
