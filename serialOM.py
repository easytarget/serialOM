from json import loads
from timeStubs import sleep_ms,ticks_ms,ticks_diff  # CPython
#from time import sleep_ms,ticks_ms,ticks_diff  # microPython
# - these CPython standard libs will need to be provided locally for microPython
from itertools import zip_longest
from functools import reduce

'''
    General note:
    This class was developed with an eye to providing microPython compatibility
    There are a lot of microPython related comments in here, ignore them for now.
'''

class serialOMError(Exception):
    '''
        Our own Exception class, used to handle comms errors and enable
        easy soft-fail on communications errors since the calling program
        can test for 'serialOMError' in a try/except block.
    '''

    def __init__(self, errMsg):
        self.errMsg = errMsg
        super().__init__(self.errMsg)
    def __str__(self):
        # we could test for the exact error here but not worth it imho
        return f'{self.errMsg}'

class serialOM:
    '''
        Object Model communications tools class provides a class with
        specific functions used to fetch and process the RRF Object Model
        via a serial/stream interface.

        We make two different types of request on a 'per key' basis:
          Verbose status requests to read the full key
          Frequent requests that just return the frequently changing key values
        Verbose requests are more 'expensive' in terms of processor and data use,
        so we only make these when we need to.

        There is a special key returned by M409; `seqs`, which returns an
        incremental count of changes to the values /not/ returned with the
        frequent update requests. This is used to trigger verbose updates
        when necessary for all the keys we monitor.

        If either the machine mode changes, or the uptime rolls-back a clean
        and rebuild is done on the local object model copy

        Serial communications errors will raise a 'serialOMError' exception
        with the original error in it's message body.

        See:
        https://docs.duet3d.com/User_manual/Reference/Gcodes#m409-query-object-model
        https://github.com/Duet3D/RepRapFirmware/wiki/Object-Model-Documentation


        arguments:
            rrf :           Serial stream or similar
            omKeys:         Dictionary with a per-mode list of keys to sync
            requestTimeout: Timeout for response after sending a request (ms)
            rawLog:         File object for the raw log, or None
            quiet:          Print messages on startup and when soft errors are encountered

        provides:
            sendGcode(code):    Sends a Gcode to controller
            getResponse(code):  Sends a Gcode and returns the response as a list of lines
            update():           Updates local model from the controller

    '''

    def __init__(self, rrf, omKeys, requestTimeout=500, rawLog=None, quiet=False):
        self.rrf = rrf
        self.omKeys = omKeys
        self.requestTimeout = requestTimeout
        self.rawLog = rawLog
        self.quiet = quiet
        self.defaultModel = {'state':{'status':'unknown'},'seqs':None}
        self.model = self.defaultModel
        self.seqs = {}
        self.machineMode = ''
        self.upTime = -1
        self.jsonChars = bytearray(range(0x20,0x7F)).decode('ascii')
        self.seqKeys = ['state']  # we always check 'state'
        for mode in omKeys.keys():
            self.seqKeys = list(set(self.seqKeys) | set(omKeys[mode]))

        # Main Init
        self._print('serialOM is starting')
        # we want this to be set; a non blocking timeout
        rrf.timeout = requestTimeout / 2500
        rrf.write_timeout = rrf.timeout
        # check for a valid response to a firmware version query
        self._print('checking for connected RRF controller')
        retries = 10
        while not self._firmwareRequest():
            retries -= 1
            if retries == 0:
                self._print('failed to get a sensible M115 response from controller')
                return
            self._print('failed..retrying')
            sleep_ms(self.requestTimeout)
        self._print('controller is connected')
        sleep_ms(self.requestTimeout)
        # Do initial update to fill local model`
        self._print('making initial data set request')
        if self.update():
            self._print('connected to ObjectModel')
        if self.machineMode == '':
            self._print('failed to obtain initial machine state')


    # To print, or not print, that is the question.
    def _print(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    # Handle a request cycle to the OM
    def _omRequest(self, OMkey, OMflags):
        '''
            This is the main request send/recieve function, it sends a OM key request to the
            controller and returns True when a valid response was recieved, False otherwise.
        '''
        # Construct the M409 command
        cmd = 'M409 F"' + OMflags + '" K"' + OMkey + '"'
        queryResponse = self.getResponse(cmd)
        jsonResponse = self._onlyJson(queryResponse)
        if len(jsonResponse) == 0:
            return False
        else:
            return self._updateOM(jsonResponse,OMkey)

    def _onlyJson(self,queryResponse):
        # return JSON candidates from the query response
        if len(queryResponse) == 0:
            return []
        jsonResponse = []
        nest = 0
        for line in queryResponse:
            json = ''
            for char in line or '':
                if char == '{':
                    nest += 1
                if nest > 0 :
                    json += char
                if char == '}':
                    nest -= 1
                    if nest <0:
                        break
                    elif nest == 0:
                        jsonResponse.append(json)
                        json = ''
        return jsonResponse

    def _updateOM(self,response,OMkey):
        # Merge or replace the local OM copy with results from the query

        def merge(a, b):
            # A Local function for recursive/iterative merge of dict/list structures.
            # https://stackoverflow.com/questions/19378143/python-merging-two-arbitrary-data-structures#1
            if isinstance(a, dict) and isinstance(b, dict):
                d = dict(a)
                d.update({k: merge(a.get(k, None), b[k]) for k in b})
                return d
            if isinstance(a, list) and isinstance(b, list):
                return [merge(x, y) for x, y in zip_longest(a, b)]
            return a if b is None else b

        # Process Json candidate lines
        success = False
        for line in response:
            # Load as a json data structure
            try:
                payload = loads(line)
            except:
                # invalid JSON, print and skip to next line
                self._print('invalid JSON:',line)
                continue
            # Update local OM data
            if 'key' not in payload.keys():
                # Valid JSON but no 'key' data in it
                continue
            elif payload['key'] != OMkey:
                # Valid JSON but not for the key we requested
                continue
            elif 'result' not in payload.keys():
                # Valid JSON but no 'result' data in it
                continue
            # We have a result, store it
            if 'f' in payload['flags']:
                # Frequent updates just refresh the existing key as needed
                if payload['result'] != None:
                    self.model[payload['key']] = merge(self.model[payload['key']],payload['result'])
                # M409 may legitimately return an empty key when getting frequent data
                success = True
            else:
                # Verbose output replaces the existing key if a result is supplied
                if payload['result'] != None:
                    self.model[payload['key']] = payload['result']
                    success = True
        return success

    def _keyRequest(self,key,verboseList):
        # Do an individual key request using the correct verbosity
        if key in verboseList:
            #print('*',end='')  # debug
            if not self._omRequest(key,'vnd99'):
                return False;
        else:
            #print('.',end='')  # debug
            if not self._omRequest(key,'fnd99'):
                 return False;
        return True

    def _stateRequest(self,verboseSeqs):
        # sends a state request
        # handles machine mode and uptime changes

        def cleanstart():
            # clean and reset the local OM and seqs, returns full seqs list
            self.model = self.defaultModel
            self.seqs = {}
            return self.seqKeys

        if not self._keyRequest('state',verboseSeqs):
            self._print('"state" key request failed')
            return False
        verboseList = verboseSeqs
        if self.machineMode != self.model['state']['machineMode']:
            verboseList = cleanstart()
        elif self.upTime > self.model['state']['upTime']:
            verboseList = cleanstart()
        self.upTime = self.model['state']['upTime']
        self.machineMode = self.model['state']['machineMode']
        return verboseList

    def _seqRequest(self):
        # Send a 'seqs' request to the OM, updates local OM and returns
        # a list of keys where the sequence number has changed
        changed=[]
        if self.seqs == {}:
            # no previous data, start from scratch
            for key in self.seqKeys:
                self.seqs[key] = -1
        # get the seqs key, note and record all changes
        if self._omRequest('seqs','vnd99'):
            for key in self.seqKeys:
                if self.seqs[key] != self.model['seqs'][key]:
                    changed.append(key)
                    self.seqs[key] = self.model['seqs'][key]
        else:
            self._print('sequence key request failed')
        return changed

    def _firmwareRequest(self):
        # Use M115 to (re-establish comms and verify firmware
        # Send the M115 info request and look for a sensible reply
        self._print('> M115')
        response = self.getResponse('M115')
        haveRRF = False
        if len(response) > 0:
            for line in response:
                self._print('>> ' + line)
                # A basic test to see if we have an RRF firmware
                # - Ideally expand to add more checks, eg version.
                if 'RepRapFirmware' in line:
                    haveRRF = True
        return haveRRF

    def sendGcode(self, code):
        # send a gcode then block until it is sent, or error
        # first, absorb whatever is in our buffer
        try:
            waiting = self.rrf.in_waiting     # CPython, microPython use 'any()'
        except Exception as e:
            raise serialOMError('Failed to query length of input buffer : ' + str(e)) from None
        if waiting > 0:
            try:
                junk = self.rrf.read().decode('ascii')
            except Exception as e:
                raise serialOMError('Failed to flush input buffer : ' + str(e)) from None
            else:
                if self.rawLog:
                    self.rawLog.write(junk)
        # send command
        try:
            self.rrf.write(bytearray(code + "\r\n",'utf-8'))
        except Exception as e:
            raise serialOMError('Gcode serial write failed : ' + str(e)) from None
        try:
            self.rrf.flush()
        except Exception as e:
            raise serialOMError('Gcode serial write buffer flush failed : ' + str(e)) from None
        # log what we sent
        if self.rawLog:
            self.rawLog.write("\n> " + code + "\n")

    def getResponse(self, cmd):
        '''
            Sends a query and waits for response data,
            returns a list of response lines, or None
        '''
        # Send the command to RRF
        self.sendGcode(cmd)
        # And wait for a response
        requestTime = ticks_ms()
        queryResponse = []
        line = ''
        # only look for responses within the requestTimeout period
        while (ticks_diff(ticks_ms(),requestTime) < self.requestTimeout):
            # Read a character, tolerate and ignore decoder errors
            try:
                char = self.rrf.read(1).decode('ascii')
            except UnicodeDecodeError:
                char = None
            except Exception as e:
                raise serialOMError('Serial/UART failed: Cannot read from controller : ' + str(e)) from None
            if self.rawLog and char:
                self.rawLog.write(char)
            # store valid characters
            if char in self.jsonChars:
                line += char
            elif char == '\n':
                queryResponse.append(line)
                # if we see 'ok' at the line end break immediately from wait loop
                if (line[-2:] == 'ok'):
                    break
                line = ''
        return queryResponse

    def update(self):
        # Do an update cycle; get new data and update local OM
        success = True  # track (soft) failures
        verboseSeqs = self._seqRequest()
        verboseList = self._stateRequest(verboseSeqs)
        for key in self.omKeys[self.machineMode]:
            if not self._keyRequest(key, verboseList):
                success = False
        return success
