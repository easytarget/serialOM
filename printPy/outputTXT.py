from time import time

'''
    This is a TEXT (REPL/console) output class for PrintPY
    It can be adapted for I2C displays etc
'''


class outputRRF:
    # ObjectModel keys for each supported mode
    # We will always get the 'state' key from serialOM
    # All other keys need to be specified below
    omKeys = {'FFF':['heat','tools','job','boards','network'],
              'CNC':['spindles','tools','move','job','boards','network'],
              'Laser':['move','job','boards','network']}

    def __init__(self, log=None):
        self._log = log
        self._OM = None
        # If running I2C displays etc this should reflect their status
        self.running = True

    def update(self,model=None):
        # Updates the local model, triggers an output update
        if model is not None:
            self._OM = model
        if self._OM is None:
            # called while not connected.
            return('no update data available\n')
        return self._showModel() + '\n'

    def showStatus(self,model=None):
        # Show specific status details for the controller and PrintPy
        # this could be expanded for microPython memory etc.
        if model is not None:
            self._OM = model
        if self._OM is None:
            # called while not connected.
            return('no data available\n')
        # simple info about board and logger
        # needs 'boards' to be in the list of keys above..
        r = 'info: '
        r += self._OM['boards'][0]['firmwareName'] + ' v'
        r += self._OM['boards'][0]['firmwareVersion'] + ' on '
        r += self._OM['boards'][0]['name'] + '\n      Controller is in "'
        r += self._OM['state']['machineMode'] + '" mode\n      '
        r += 'Vin: %.1f' % self._OM['boards'][0]['vIn']['current'] + 'V'
        r += ' | mcu: %.1f' % self._OM['boards'][0]['mcuTemp']['current'] + 'C'
        # Return results
        if self._log:
            self._log.write('[' + str(int(time())) + '] ' + r + '\n')
        return r + '\n'

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
        if self._log:
            self._log.write('[' + str(int(time())) + '] ' + r + '\n')
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
        # Display all configured axes workplace and machine position, plus state.
        ws = self._OM['move']['workplaceNumber']
        r = ' | axes: W' + str(ws + 1)
        m = ''      # machine pos
        offset = False   # workspace offset from Machine Pos?
        if self._OM['move']['axes']:
            for axis in self._OM['move']['axes']:
                if axis['visible']:
                    if axis['homed']:
                       r += ' ' + axis['letter'] + ':' + "%.2f" % (axis['machinePosition'] - axis['workplaceOffsets'][ws])
                       m += ' ' + "%.2f" % (axis['machinePosition'])
                       if axis['workplaceOffsets'][ws] != 0:
                           offset = True
                    else:
                       r += ' ' + axis['letter'] + ':?'
                       m += ' ?'
            if offset:
                r += ' (' + m[1:] + ')'
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
        return r

    def _updateLaser(self):
        # Show laser info; not much to show since there is no seperate laser 'tool' (yet)
        if self._OM['move']['currentMove']['laserPwm'] is not None:
            pwm = '%.0f%%' % (self._OM['move']['currentMove']['laserPwm'] * 100)
        else:
            pwm = 'not configured'
        return ' | laser: ' + pwm
