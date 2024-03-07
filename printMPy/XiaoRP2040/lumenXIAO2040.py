from machine import Timer,Pin
from neopixel import NeoPixel
'''
    Lumen (LED Indicator) for the Seeedstudio XIAO RP2040
    Drives the onboard NeoPixel with moods
    The additional RGB 'user' led is cycled RGB to indocate send events
'''

class lumen:
    def __init__(self,bright=1,flash=66):
        '''
            start led/neopixel etc

            properties:
                self.bright = float(0..1), intensity
                self.flash  = int(), flash duration in ms
        '''
        self.bright = bright
        self.flash = flash
        self._moods = {'off':(255,128,0),
                        'on':(0,255,0),
                      'busy':(255,255,255),
                       'job':(255,0,255),
                    'paused':(0,0,255),
                       'err':(255,0,0)}

        # Neopixel
        self._pixelVcc = Pin(11,Pin.OUT)   # Power on pin 11
        self._pixelVcc.value(1)            # turn on immediately
        self._pixel = NeoPixel(Pin(12),1)  # data on pin 12
        self._pixel[0]=(0,0,0)
        self._pixel.write()

        # RGB mini status Led, default off
        self._rgbR = Pin(17,Pin.OUT)
        self._rgbG = Pin(16,Pin.OUT)
        self._rgbB = Pin(25,Pin.OUT)
        self._rgbstate = (True,False,False)
        self._setRGB()   # start off

    def _setRGB(self,state=(False,False,False)):
        # sets onboard rgb status led
        self._rgbR.value(not state[0])   # pins are inverted
        self._rgbG.value(not state[1])
        self._rgbB.value(not state[2])

    def blink(self,mood):
        '''
            flash the mood after an update finishes
            use an interrupt timer
            to turn off after self.flash time
            timer features vary by MCU, example here is for RP2040, ymmv
        '''
        def unblink(t):
            # called by timer
            self._pixel[0] = (0,0,0)
            self._pixel.write()

        if mood == 'empty':
            return

        neo = self._moods[mood]
        self._pixel[0] = (int(neo[0]*self.bright),
                          int(neo[1]*self.bright),
                          int(neo[2]*self.bright))
        self._pixel.write()
        Timer(period=self.flash, mode=Timer.ONE_SHOT, callback=unblink)

    def send(self):
        '''
            Use for a seperate 'send heartbeat' led using the spare 'USER' led of the Xiao
            cycling RGB every time a request cycle begins
        '''
        self._setRGB(self._rgbstate)         # Rotate the onboard RGB
        self._rgbstate = (self._rgbstate[2],self._rgbstate[0],self._rgbstate[1])


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
