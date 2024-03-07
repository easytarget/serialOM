from machine import Timer
'''
    Lumen (LED Indicator) stubs
    Suitable for a color RGB/NeoPixel with moods
    A mono LED could be used without the mood colors
'''

class lumen:
    def __init__(self,bright=1,flash=120):
        '''
            start led/neopixel etc

            properties:
                self.bright = float(0..1), intensity
                self.flash  = int(), flash duration in ms
        '''
        self._moods = {'off':(255,255,0),
                        'on':(0,255,0),
                      'busy':(255,255,255),
                       'job':(255,0,255),
                    'paused':(0,0,255),
                       'err':(255,0,0)}
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
            #print('TODO: led-off')
            pass  # Put code here to turn the LED off

        if mood == 'empty':
            return
        #print('TODO: led-on: "' + mood + '"')
        pass  # Put code here to turn the LED on, if it is RGB use the colors in the mood map.
        # start a timer to turn the LED off again
        Timer(period=self.flash, mode=Timer.ONE_SHOT, callback=unblink)

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

        status = model['state']['status']
        wifi = False
        if len(model['network']['interfaces']) > 0:
            for interface in model['network']['interfaces']:
                if interface['type'] is 'wifi' and interface['state'] is 'active':
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
