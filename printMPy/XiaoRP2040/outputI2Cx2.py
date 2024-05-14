from time import sleep_ms,ticks_ms,ticks_diff
from machine import Pin,I2C
from ssd1306 import SSD1306_I2C
from sys import path
# fonts
path.append('fonts')
from ezFBfont import ezFBfont
import mPyEZfont_u8g2_spleen_12x24_n
import mPyEZfont_u8g2_spleen_16x32_n
import mPyEZfont_u8g2_helvR10_r
import mPyEZfont_u8g2_helvR24_n
import mPyEZfont_u8g2_helvR12_n

'''
    This is a I2C twin 128x64 OLED display out put class for PrintMPY
        It keeps a 'local' OM so that displays can be refreshed
        independently of the main OM update loop
    See the comments in the printPy 'README.md' for more
'''


class outputRRF:
    '''
        arguments:
            log : log file object or None to disable.

        methods:
            update(model,hostinfo) : Updates the local model copy and
                returns a string with the human-readable machine state info.
                Writes to logfile with timestamp if required.
                hostinfo is optional, it will be prepended if present.
            showStatus(model,hostinfo) : Updates the local model copy and
                returns a 'status' block.
                Aimed at display devices to show extra info when triggered.

        properties:
            omKeys       : see below
            running      : (bool) can be set False if the output device fails
            statusActive : (bool) set True while a status is being displayed
'''

    # ObjectModel keys for each supported mode
    # We will always get the 'state' key from serialOM
    # All other keys need to be specified below
    omKeys = {'FFF':['heat','tools','job','boards','network'],
              'CNC':['spindles','tools','move','job','boards','network'],
              'Laser':['move','job','boards','network']}

    def __init__(self, log=None):
        self._log = log  # Find a way to use this for display debugging
        self._OM = None
        # If running I2C displays etc this should reflect their status
        self.running = True
        self.statusActive = False
        self.statusDuration = 2000     # CONFIG
        self._statusRequested = 0

        # demo only?
        self._begin = ticks_ms()

        # I2C
        I2C0_SDA_PIN = 28
        I2C0_SCL_PIN = 29
        I2C1_SDA_PIN = 6
        I2C1_SCL_PIN = 7
        i2c0=I2C(0,sda=Pin(I2C0_SDA_PIN), scl=Pin(I2C0_SCL_PIN))
        i2c1=I2C(1,sda=Pin(I2C1_SDA_PIN), scl=Pin(I2C1_SCL_PIN))
        self._d0 = SSD1306_I2C(128, 64, i2c0, addr=0x3c)
        self._d1 = SSD1306_I2C(128, 64, i2c1, addr=0x3c)
        self._d0.invert(False)
        self._d1.invert(False)
        self._d0.rotate(1)
        self._d1.rotate(1)
        self._fontSetup(self._d0)
        self._fontSetup(self._d1)
        self._bright(1)
        self._clean()
        self._splash()
        self._active = True

    def _fontSetup(self,d):
        d.heading = ezFBfont(d, mPyEZfont_u8g2_helvR10_r)
        d.tens  = ezFBfont(d, mPyEZfont_u8g2_helvR24_n, halign='right', valign='baseline')
        d.units = ezFBfont(d, mPyEZfont_u8g2_helvR12_n, valign='baseline')


    def _splash(self):
        # Should scroll a 'clean' screen in?
        self._d0.heading.write('serialOM', 63, 0, halign='center')
        self._d1.heading.write('demo', 63, 0, halign='center')
        self._show()

    def _clean(self):
            self._d0.fill_rect(0, 0, 128, 64, 0)
            self._d1.fill_rect(0, 0, 128, 64, 0)

    def _on(self):
        if not self._active:
            self._d0.poweron()
            self._d1.poweron()
            self._active = True

    def _off(self):
        if self._active:
            self._d0.poweroff()
            self._d1.poweroff()
            self._active = False

    def _show(self):
        self._d0.show()
        self._d1.show()

    def _bright(self,bright):
        bright = int(bright * 255)
        self._d0.contrast(bright)
        self._d1.contrast(bright)

    def update(self,model=None, hostInfo=None):
        if self._OM['state']["status"] is not 'off':
            self._on()
            self._clean()
       # Updates the local model, returns the current status text
        if model is not None:
            self._OM = model
        if self._OM is None:
            return('no update data available\n')
        if hostInfo:
            r = hostInfo + ' || ' + self._showModel() + '\n'
        else:
            r = self._showModel() + '\n'
        if self._OM['state']["status"] is not 'off':
            now = int(ticks_diff(ticks_ms(), self._begin))
            secs = int((now / 1000) % 60)
            mins = int((now / 60000) % 60)
            self._d0.heading.write(' ' + self._OM['state']["status"], 0, 0)
            self._d1.heading.write(' Up: ' + str(self._OM['state']["upTime"]), 0, 0)
            self._show()
        else:
            self._off()
        return r

    def showStatus(self, model=None, hostInfo=None):
        # Returns specific status details for the controller and PrintPy
        # this will be expanded for microPython host status. NetWork status
        if ticks_diff(ticks_ms(),self._statusRequested) < self.statusDuration:
            self._statusRequested = ticks_ms()
            return ''
        self._statusRequested = ticks_ms()
        if model is not None:
            self._OM = model
        if self._OM is None:
            # called while not connected.
            return('no data available\n')
        self.statusActive = True
        # simple info about board and logger
        # needs 'boards' to be in the list of keys above..
        r = 'info: '
        r += self._OM['boards'][0]['firmwareName'] + ' v'
        r += self._OM['boards'][0]['firmwareVersion'] + ' on '
        r += self._OM['boards'][0]['name'] + '\n      Controller is in "'
        r += self._OM['state']['machineMode'] + '" mode\n      '
        r += 'Vin: %.1f' % self._OM['boards'][0]['vIn']['current'] + 'V'
        r += ' | mcu: %.1f' % self._OM['boards'][0]['mcuTemp']['current'] + 'C'
        if hostInfo:
            r += '\n' + hostInfo
        # Return results
        self.statusActive = False
        return r + '\n'

    '''
        All the routines below tediously walk/grok the OM and return
        a stringlet with the data they find, this is then concatenated
        into a string that is passed back to the caller.
    '''

    def _showModel(self):
        #  Constructs and returns the model data in human-readable form.
        #  copies to outputLog if one is specified

        def dhms(t):
            # A local function to provide human readable uptime
            d = int(t / 86400)
            h = int((t / 3600) % 24)
            m = int((t / 60) % 60)
            s = int(t % 60)
            if d > 0:
                days = str(d)  + ':'
            else:
                days = ''
            if h > 0 or d > 0:
                hrs = str(h)  + ':'
            else:
                hrs = ''
            mins = "%02.f" % m + ':'
            secs = "%02.f" % s
            return days+hrs+mins+secs

        if self._OM is None:
            # No data == no viable output
            return('No data available')
        # Construct results string
        r = 'status: ' + self._OM['state']['status']
        r += ' | uptime: ' + dhms(self._OM['state']['upTime'])
        if self._OM['state']['status'] in ['halted','updating','starting']:
            # placeholder for display splash while starting or updating..
            r += ' | please wait'
            return r
        r += self._updateCommon()
        if self._OM['state']['status'] == 'off':
            pass   # Placeholder for display off code etc..
        else:
            r += self._updateJob()
            if self._OM['state']['machineMode'] == 'FFF':
                r += self._updateFFF()
            elif self._OM['state']['machineMode']  == 'CNC':
                r += self._updateAxes()
                r += self._updateCNC()
            elif self._OM['state']['machineMode']  == 'Laser':
                r += self._updateAxes()
                r += self._updateLaser()
        r += self._updateMessages()
        # Return results
        return r

    def _updateCommon(self):
        # common items to always show
        r = ''
        if len(self._OM['network']['interfaces']) > 0:
            for interface in self._OM['network']['interfaces']:
                r += ' | ' + interface['type'] + ': '
                if interface['state'] != 'active':
                    r += interface['state']
                else:
                    r += interface['actualIP']
        return r

    def _updateJob(self):
        # Job progress
        r = ''
        if self._OM['job']['build']:
            try:
                percent = self._OM['job']['filePosition'] / self._OM['job']['file']['size'] * 100
            except ZeroDivisionError:  # file size can be 0 as the job starts
                percent = 0
            r += ' | progress: ' + "%.1f%%" % percent
        return r

    def _updateAxes(self):
        # Display all configured axes values (workplace and machine), plus state.
        ws = self._OM['move']['workplaceNumber']
        r = ' | axes: '
        m = ''      # machine pos
        offset = False   # is the workspace offset from machine co-ordinates?
        homed = False   # are any of the axes homed?
        if self._OM['move']['axes']:
            for axis in self._OM['move']['axes']:
                if axis['visible']:
                    if axis['homed']:
                        homed = True
                        r += ' ' + axis['letter'] + ':' + "%.2f" % (axis['machinePosition'] - axis['workplaceOffsets'][ws])
                        m += ' ' + "%.2f" % (axis['machinePosition'])
                        if axis['workplaceOffsets'][ws] != 0:
                            offset = True
                    else:
                        r += ' ' + axis['letter'] + ':?'
                        m += ' ?'
            if homed:
                # Show which workspace we have selected when homed
                r += ' (' + str(ws + 1) + ')'
            if offset:
                # Show machine position if workspace is offset
                r += '(' + m[1:] + ')'
        return r

    def _updateMessages(self):
        # M117 messages
        r = ''
        if self._OM['state']['displayMessage']:
            r += ' | message: ' +  self._OM['state']['displayMessage']
        # M291 messages
        if self._OM['state']['messageBox']:
            if self._OM['state']['messageBox']['mode'] == 0:
                r += ' | info: '
            else:
                r += ' | query: '
            if self._OM['state']['messageBox']['title']:
                r += '== ' + self._OM['state']['messageBox']['title'] + ' == '
            r += self._OM['state']['messageBox']['message']
        return r

    def _updateFFF(self):
        # a local function to return state and temperature details for a heater
        def showHeater(number,name):
            r = ''
            if self._OM['heat']['heaters'][number]['state'] == 'fault':
                r += ' | ' + name + ': FAULT'
            else:
                r += ' | ' + name + ': ' + '%.1f' % self._OM['heat']['heaters'][number]['current']
                if self._OM['heat']['heaters'][number]['state'] == 'active':
                    r += ' (%.1f)' % self._OM['heat']['heaters'][number]['active']
                elif self._OM['heat']['heaters'][number]['state'] == 'standby':
                    r += ' (%.1f)' % self._OM['heat']['heaters'][number]['standby']
            return r

        r = ''
        # For FFF mode we want to show all the Heater states
        # Bed
        if len(self._OM['heat']['bedHeaters']) > 0:
            if self._OM['heat']['bedHeaters'][0] != -1:
                r += showHeater(self._OM['heat']['bedHeaters'][0],'bed')
        # Chamber
        if len(self._OM['heat']['chamberHeaters']) > 0:
            if self._OM['heat']['chamberHeaters'][0] != -1:
                r += showHeater(self._OM['heat']['chamberHeaters'][0],'chamber')
        # Extruders
        if len(self._OM['tools']) > 0:
            for tool in self._OM['tools']:
                if len(tool['heaters']) > 0:
                    r += showHeater(tool['heaters'][0],'e' + str(self._OM['tools'].index(tool)))
        #display
        bed = self._OM['heat']['heaters'][0]['current']
        units=int(bed)
        dec = int((bed - units) * 10)
        self._d1.heading.write('bed', 127, 15, halign='right')
        self._d1.tens.write('{}.'.format(units), 88, 50)
        self._d1.tens.write('°', 88, 50, tkey=0, halign='center')
        self._d1.units.write(' {:01d}'.format(dec), 88, 50)
        e0 = self._OM['heat']['heaters'][1]['current']
        units=int(e0)
        dec = int((e0 - units) * 10)
        self._d0.heading.write('e0', 127, 15, halign='right')
        self._d0.tens.write('{}.'.format(units), 88, 50)
        self._d0.tens.write('°', 88, 50, tkey=0, halign='center')
        self._d0.units.write(' {:01d}'.format(dec), 88, 50)

        return r

    def _updateCNC(self):
        # a local function to return spindle name + state, direction and speed
        def showSpindle(name,spindle):
            r = ' | ' + name + ': '
            if self._OM['spindles'][spindle]['state'] == 'stopped':
                r += 'stopped'
            elif self._OM['spindles'][spindle]['state'] == 'forward':
                r += '+' + str(self._OM['spindles'][spindle]['current'])
            elif self._OM['spindles'][spindle]['state'] == 'reverse':
                r += '-' + str(self._OM['spindles'][spindle]['current'])
            return r

        # Show details for all configured spindles
        r = ''
        if len(self._OM['tools']) > 0:
            for tool in self._OM['tools']:
                if tool['spindle'] != -1:
                    r += showSpindle(tool['name'],tool['spindle'])
        if len(r) == 0:
            r += ' | spindle: not configured'
        return r

    def _updateLaser(self):
        # Show laser info; not much to show since there is no seperate laser 'tool' (yet)
        if self._OM['move']['currentMove']['laserPwm'] is not None:
            pwm = '%.0f%%' % (self._OM['move']['currentMove']['laserPwm'] * 100)
        else:
            pwm = 'not configured'
        return ' | laser: ' + pwm
