from time import time

'''
    This is a TEXT (REPL/console) output class for PrintPY
    It can be adapted for I2C displays etc
'''

# These are the only key sets in the OM we are interested in
# We will always get the 'state' key from serialOM
# All other keys need to be specified below

class outputRRF:
    # ObjectModel keys for each supported mode
    omKeys = {'FFF':['heat','tools','job','boards','network'],
              'CNC':['spindles','tools','move','job','boards','network'],
              'Laser':['move','job','boards','network']}

    def __init__(self, log=None):
        self.log = log
        self.OM = None
        # If running I2C displays etc this should reflect their status
        self.running = True

    def updateModel(self,model):
        # Updates the local model
        self.OM = model
        if model is None:
            return False
        return True

    def showStatus(self):
        if self.OM is None:
            # called while not connected.
            # this could be expanded for microPython memory etc.
            return('No data available')
        # simple info about board and logger
        # needs 'boards' to be in the list of keys above..
        r = 'info: '
        r += self.OM['boards'][0]['firmwareName'] + ' v'
        r += self.OM['boards'][0]['firmwareVersion'] + ' on '
        r += self.OM['boards'][0]['name'] + '\n      Controller is in "'
        r += self.OM['state']['machineMode'] + '" mode\n      '
        r += 'Vin: %.1f' % self.OM['boards'][0]['vIn']['current'] + 'V'
        r += ' | mcu: %.1f' % self.OM['boards'][0]['mcuTemp']['current'] + 'C'
        return r

    def showOutput(self):
        # Shows the results on the console on demand.
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

        if self.OM is None:
            # No data == no viable output
            return('No data available')
        # Construct results string
        r = 'status: ' + self.OM['state']['status']
        r += ' | uptime: ' + dhms(self.OM['state']['upTime'])
        if self.OM['state']['status'] in ['halted','updating','starting']:
            # placeholder for display splash while starting or updating..
            r += ' | please wait'
            return r
        r += self._updateCommon()
        if self.OM['state']['status'] == 'off':
            pass   # Placeholder for display off code etc..
        else:
            r += self._updateJob()
            if self.OM['state']['machineMode'] == 'FFF':
                r += self._updateFFF()
            elif self.OM['state']['machineMode']  == 'CNC':
                r += self._updateAxes()
                r += self._updateCNC()
            elif self.OM['state']['machineMode']  == 'Laser':
                r += self._updateAxes()
                r += self._updateLaser()
        r += self._updateMessages()
        # Return results
        if self.log:
            self.log.write('[' + str(int(time())) + '] ' + r + '\n')
        return r

    def _updateCommon(self):
        # common items to always show
        r = ''
        if len(self.OM['network']['interfaces']) > 0:
            for interface in self.OM['network']['interfaces']:
                r += ' | ' + interface['type'] + ': '
                if interface['state'] != 'active':
                    r += interface['state']
                else:
                    r += interface['actualIP']
        return r

    def _updateJob(self):
        # Job progress
        r = ''
        if self.OM['job']['build']:
            try:
                percent = self.OM['job']['filePosition'] / self.OM['job']['file']['size'] * 100
            except ZeroDivisionError:  # file size can be 0 as the job starts
                percent = 0
            r += ' | progress: ' + "%.1f%%" % percent
        return r

    def _updateAxes(self):
        # Display all configured axes workplace and machine position, plus state.
        ws = self.OM['move']['workplaceNumber']
        r = ' | axes: W' + str(ws + 1)
        m = ''      # machine pos
        offset = False   # workspace offset from Machine Pos?
        if self.OM['move']['axes']:
            for axis in self.OM['move']['axes']:
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
        if self.OM['state']['displayMessage']:
            r += ' | message: ' +  self.OM['state']['displayMessage']
        # M291 messages
        if self.OM['state']['messageBox']:
            if self.OM['state']['messageBox']['mode'] == 0:
                r += ' | info: '
            else:
                r += ' | query: '
            if self.OM['state']['messageBox']['title']:
                r += '== ' + self.OM['state']['messageBox']['title'] + ' == '
            r += self.OM['state']['messageBox']['message']
        return r

    def _updateFFF(self):
        # a local function to return state and temperature details for a heater
        def showHeater(number,name):
            r = ''
            if self.OM['heat']['heaters'][number]['state'] == 'fault':
                r += ' | ' + name + ': FAULT'
            else:
                r += ' | ' + name + ': ' + '%.1f' % self.OM['heat']['heaters'][number]['current']
                if self.OM['heat']['heaters'][number]['state'] == 'active':
                    r += ' (%.1f)' % self.OM['heat']['heaters'][number]['active']
                elif self.OM['heat']['heaters'][number]['state'] == 'standby':
                    r += ' (%.1f)' % self.OM['heat']['heaters'][number]['standby']
            return r

        r = ''
        # For FFF mode we want to show all the Heater states
        # Bed
        if len(self.OM['heat']['bedHeaters']) > 0:
            if self.OM['heat']['bedHeaters'][0] != -1:
                r += showHeater(self.OM['heat']['bedHeaters'][0],'bed')
        # Chamber
        if len(self.OM['heat']['chamberHeaters']) > 0:
            if self.OM['heat']['chamberHeaters'][0] != -1:
                r += showHeater(self.OM['heat']['chamberHeaters'][0],'chamber')
        # Extruders
        if len(self.OM['tools']) > 0:
            for tool in self.OM['tools']:
                if len(tool['heaters']) > 0:
                    r += showHeater(tool['heaters'][0],'e' + str(self.OM['tools'].index(tool)))
        return r

    def _updateCNC(self):
        # a local function to return spindle name + state, direction and speed
        def showSpindle(name,spindle):
            r = ' | ' + name + ': '
            if self.OM['spindles'][spindle]['state'] == 'stopped':
                r += 'stopped'
            elif self.OM['spindles'][spindle]['state'] == 'forward':
                r += '+' + str(self.OM['spindles'][spindle]['current'])
            elif self.OM['spindles'][spindle]['state'] == 'reverse':
                r += '-' + str(self.OM['spindles'][spindle]['current'])
            return r

        # Show details for all configured spindles
        r = ''
        if len(self.OM['tools']) > 0:
            for tool in self.OM['tools']:
                if tool['spindle'] != -1:
                    r += showSpindle(tool['name'],tool['spindle'])
        return r

    def _updateLaser(self):
        # Show laser info; not much to show since there is no seperate laser 'tool' (yet)
        if self.OM['move']['currentMove']['laserPwm'] != None:
            pwm = '%.0f%%' % (self.OM['move']['currentMove']['laserPwm'] * 100)
        else:
            pwm = 'not configured'
        return ' | laser: ' + pwm
