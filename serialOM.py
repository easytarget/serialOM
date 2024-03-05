from sys import implementation
from json import loads
from gc import collect
try:
    from time import sleep_ms,ticks_ms,ticks_diff  # microPython
except:
    from compatLib import sleep_ms,ticks_ms,ticks_diff  # CPython
from compatLib import zip_longest
from compatLib import reduce

'''
    General note:
    This class is designd to run on either CPython (with PySerial) or on
    microPython using the machine.UART interface.

    This should be opaque to the user, we select the correct serial vs uart
    functions where this differs (timing options and flushing rx buffer)
'''

class serialOMError(Exception):
    '''
        Our own Exception class, used to handle comms errors and enable
        easy soft-fail on communications failures by the calling program
        testing for 'serialOMError' in a try/except block.
    '''

    def __init__(self, errMsg):
        self.errMsg = errMsg
        super().__init__(self.errMsg)
    def __str__(self):
        return f'{self.errMsg}'

class serialOM:
    '''
        Object Model communications class.
        Provides specific functions used to fetch and process the RRF Object Model
        via a serial/stream interface.

        We make two different types of request on a 'per key' basis:
          Verbose status requests to read the full key.
          Frequent requests that just return the frequently changing key values.
        Verbose requests are more 'expensive' in terms of processor and data use,
        so we only make these when we need to.

        There is a special key returned by M409; `seqs`, which returns an
        incremental count of changes to the 'infrequent' values. This is
        used to trigger verbose updates when necessary for the keys we monitor.

        If either the machine mode changes, or the uptime rolls-back a clean
        and rebuild is done on the local object model copy.

        Serial communications errors will raise a 'serialOMError' exception
        with the original error in it's message body.

        See:
        https://docs.duet3d.com/User_manual/Reference/Gcodes#m409-query-object-model
        https://github.com/Duet3D/RepRapFirmware/wiki/Object-Model-Documentation


        init arguments:
            rrf :           PySerial or micropython UART object
            omKeys:         dict; per-mode lists of keys to sync, see below
            rawLog:         file object; where to write the raw log, or None
            quiet:          bool; suppress messages on startup and when soft errors are encountered

                            omKeys = {'machineMode':['OMkey1','OMkey2',..],etc..}
                                     Empty lists [] are allowed.
                                     At least one machineMode must be specified.

        methods:
            sendGcode(code):         Sends a Gcode to controller and returns immediately.
            getResponse(code,json):  Sends a Gcode and waits for a response.
                                     If 'json' is True it will exit as soon as a json
                                     line is seen, and only returns that line.
                                     Otherwise returns the response as a list of lines until
                                     the read timeout. No response returns an empty list
            update():                Updates local model from the controller
                                     Returns True for success, False if timeouts occurred

        properties:
            msdel:              Dictionary with the fetched model
            machineMode:        The current machine mode, string, or None if no response

        There are a few defaults set below, of note are:
            self._requestTimeout : Absolute maximum time to wait for any response, int(ms)
                                   This defines the maximum blocking time per key! The
                                   total blocking time is the sum total of these
                                   - for a normal update() we always fetch the seqs and state
                                     keys, plus the per mode keys defined in omKeys
            self._depth          : the maximum depth specified for M409 requests, default = all
            self._uartRxBuf      : microPython specific: UART input buffer size, the default
                                   of 512 bytes is probably OK, but increasing is not a bad idea
    '''

    def __init__(self, rrf, omKeys, rawLog=None, quiet=False):
        self._rrf = rrf
        self._uart = False
        self._omKeys = omKeys
        self._rawLog = rawLog
        self._quiet = quiet
        self._requestTimeout = 250
        self._depth = 99
        self._uartRxBuf = 2048
        self._defaultModel = {'state':{'status':'unknown'},'seqs':None}
        self._seqs = {}
        self._seqKeys = ['state']  # we always check 'state'
        for mode in self._omKeys.keys():  # all possible keys
            self._seqKeys = list(set(self._seqKeys) | set(self._omKeys[mode]))
        self._upTime = -1

        # public parameters
        self.model = self._defaultModel
        self.machineMode = ''

        # Main Init
        self._print('serialOM is starting')
        # a list of all possible keys we may need
        # set a non blocking timeout on the serial device
        # default is 1/10 of the request time
        if 'Serial' in str(type(rrf)):
            # PySerial
            rrf.timeout = self._requestTimeout / 10000
            rrf.write_timeout = rrf.timeout
        elif 'UART' in str(type(rrf)):
            # UART (micropython)
            self._uart = True
            rrf.init(timeout = int(self._requestTimeout / 2),
                     timeout_char = int(self._requestTimeout / 2),
                     rxbuf = self._uartRxBuf)
        else:
            self._print('Unable to determine serial stream type to enforce read timeouts!')
            self._print('please ensure these are set for your device to prevent serialOM blocking')
        # start the handler
        self._start()

    def _start(self):
        # Start the serialOM comms
        retries = 10
        while not self._firmwareRequest():
            retries -= 1
            if retries == 0:
                self._print('failed to get a sensible M115 response from controller')
                return False
            self._print('failed..retrying')
            sleep_ms(self._requestTimeout)
        self._print('controller is connected')
        sleep_ms(100)

        # Do initial update to fill local model`
        self._print('making initial data set request')
        if self.update():
            self._print('connected to ObjectModel')
            return True
        else:
            self.model = self._defaultModel
            self.machineMode = ''
            self._print('failed to obtain initial machine state')
            return False

    # To print, or not print, that is the question.
    def _print(self, *args, **kwargs):
        if not self._quiet:
            print(*args, **kwargs)

    def _omRequest(self, OMkey, OMflags):
        '''
            This is the main request send/recieve function, it sends a OM key request to the
            controller and returns True when a valid response was recieved, False otherwise.
        '''
        # Construct the M409 command
        cmd = 'M409 F"' + OMflags + '" K"' + OMkey + '"'
        queryResponse = self.getResponse(cmd, json=True)
        if len(queryResponse) == 0:
            return False
        else:
            return self._updateOM(queryResponse,OMkey)

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
                # invalid JSON, skip line
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
        #print(key,end='')                              # debug
        if key in verboseList:
            #print('*',end='')  # debug
            if not self._omRequest(key,'vnd' + str(self._depth)):
                return False;
        else:
            #print('.',end='')  # debug
            if not self._omRequest(key,'fnd' + str(self._depth)):
                 return False;
        return True

    def _stateRequest(self,verboseSeqs):
        # sends a state request
        # handles machine mode and uptime changes

        def cleanstart(why):
            # clean and reset the local OM and seqs, returns full seqs list
            self.model = self._defaultModel
            self._seqs = {}
            self._print(why)
            return self._seqKeys

        if not self._keyRequest('state',verboseSeqs):
            self._print('state key request failed')
        if self._upTime > self.model['state']['upTime']:
            verboseSeqs = cleanstart('controller restarted')
        if self.machineMode != self.model['state']['machineMode']:
            verboseSeqs = cleanstart('machine mode is: ' +
                                      self.model['state']['machineMode'])
        self.machineMode = self.model['state']['machineMode']
        self._upTime = self.model['state']['upTime']
        return verboseSeqs

    def _seqRequest(self):
        # Send a 'seqs' request to the OM, updates local OM and returns
        # a list of keys where the sequence number has changed
        changed=[]
        if self._seqs == {}:                           # TODO, can put in init
            # no previous data, start from scratch
            for key in self._seqKeys:
                self._seqs[key] = -1
        # get the seqs key, note and record all changes
        #print('Q',end='')                                  # debug
        if self._omRequest('seqs','vnd99'):
            for key in self._seqKeys:
                if self._seqs[key] != self.model['seqs'][key]:
                    changed.append(key)
                    self._seqs[key] = self.model['seqs'][key]
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
                try:
                    json = loads(line)
                except:
                    fwLine = line.strip('\n')
                else:
                    if 'resp' in json.keys():
                        fwLine = json['resp']
                    else:
                        fwLine = str(json)
                self._print('>> ' + fwLine.strip('\n'))
                # A basic test to see if we have an RRF firmware
                # - Ideally expand to add more checks, eg version.
                if 'RepRapFirmware' in line:
                    haveRRF = True
        return haveRRF

    def sendGcode(self, code):
        # send a gcode then block until it is sent, or error
        # begin by absorbing whatever is in our buffer
        try:
            if self._uart:
                waiting = self._rrf.any()
            else:
                waiting = self._rrf.in_waiting
        except Exception as e:
            print(e)
            raise serialOMError('Failed to query length of input buffer : ' + repr(e)) from None
        if waiting > 0:
            try:
                junk = self._rrf.read()
            except Exception as e:
                raise serialOMError('Failed to flush input buffer : ' + repr(e)) from None
            if self._rawLog:
                try:
                    self._rawLog.write(junk.decode('ascii'))
                except:
                    pass  # just silently ignore decode failures here

        # send command
        try:
            self._rrf.write(bytearray(code + "\r\n",'utf-8'))
        except Exception as e:
            raise serialOMError('Gcode serial write failed : ' + repr(e)) from None
        # log what we sent
        if self._rawLog:
            self._rawLog.write("> " + code + "\n")

    def getResponse(self, cmd, json=False):
        '''
            Sends a query and waits for response data,
            returns a list of response lines, or None
            If 'json' is set we exit immediately when
            a potential JSON canidate is seen.
        '''
        # Send the command to RRF
        self.sendGcode(cmd)
        # And wait for a response
        requestTime = ticks_ms()
        response=[]
        # only look for responses within the requestTimeout period
        while (ticks_diff(ticks_ms(),requestTime) < self._requestTimeout):
            try:
                rawLine = self._rrf.readline()
            except Exception as e:
                raise serialOMError('Serial read from controller failed : ' + repr(e)) from None
            if not rawLine:
                continue
            try:
                readLine = rawLine.decode('ascii')
            except:
                self_print('ascii decode failure')
                continue
            if self._rawLog:
                self._rawLog.write(readLine)
            if (readLine[:1] == '{') and (readLine[-2:] == '}\n') and json:
                response.append(readLine)
                break
            if not json:
                response.append(readLine)
        # now have either a 'json-like' string or a timeout, cleanup and return
        collect()
        return response

    def update(self):
        # Do an update cycle; get new data and update local OM
        success = True  # track (soft) failures
        verboseSeqs = self._seqRequest()
        verboseList = self._stateRequest(verboseSeqs)
        if self.machineMode not in self._omKeys.keys():
            self._print('unknown machine mode "' + self.machineMode + '"')
            return False
        for key in self._omKeys[self.machineMode]:
            if not self._keyRequest(key, verboseList):
                success = False
        return success
