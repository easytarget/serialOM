from sys import path
path.insert(0,'..')
# Import our local classes and config
from serialOM import serialOM
from outputTXT import outputRRF
from config import config

# Common classes between CPython and microPython
from gc import collect
from sys import argv
from time import localtime
from serial import Serial
from sys import executable
from os import execv

# local millisecond time functions that mimic micropython time lib
from time import sleep,time
def ticks_ms():
    return int(time() * 1000)
def ticks_diff(first,second):
    # This should 'just work' in CPython3
    # int()'s can be as 'long' as they need to be, with no need for
    # the 'rollover' protection provided by the microPython equivalent
    return int(first-second)
def sleep_ms(ms):
    sleep(ms/1000)

'''
    PrintPy is a serialOM.py demo/example.

    This is intended to be run on a desktop system (CPython, not microPython)
    that connects via serial or USBSerial to a RRF 3.x based controller.

    For requirements and arguments please refer to the  README, the only real
    requirement is py-serial ('pip install --user pyserial' etc..)
'''

# local print function so we can suppress info messages.
def pp(*args, **kwargs):
    if not config.quiet:
        print(*args, **kwargs)

# Do a minimum drama restart/reboot
def restartNow(why):
    pp('Error: ' + why)
    if outputLog:
        outputLog.flush()
    if rawLog:
        rawLog.flush()
    # Countdown and restart
    pp('Restarting in ',end='')
    for c in range(config.rebootDelay,0,-1):
        pp(c,end=' ',flush=True)
        sleep_ms(1000)
    pp()
    execv(executable, ['python'] + argv)   #  CPython
    #reset() # Micropython; reboot module

# Used for critical hardware errors during initialisation on MCU's
# mostly unused in Cpython, instead we soft-fail, restart and try again.
def hardwareFail(why):
    pp('A critical hardware error has occured!')
    pp('- Do a full power off/on cycle and check wiring etc.\n' + why + '\n')
    while True:  # loop forever
        sleep_ms(60000)

'''
    Init
'''

# Basic info
start = localtime()
startDate = str(start[0]) + '-' + str(start[1]) + '-' + str(start[2])
startTime = "%02.f" % start[3] + ':' + "%02.f" % start[4] + ':' + "%02.f" % start[5]
startText = '=== Starting: ' + startDate + ' ' + startTime

if config.quiet:
    print(startText)
else:
    print(argv[0] + ' is starting at: ' + startDate + ' ' + startTime + ' (device localtime)')

# Arguments, optional, #1 is update timer, #2 serial device, #3 baud.
if len(argv) > 1:
    config.updateTime = int(argv[1])
if len(argv) > 2:
    config.devices = [str(argv[2])]
if len(argv) > 3:
    config.baud = int(argv[3])

# Debug Logging
rawLog = None
if config.rawLog:
    try:
        rawLog = open(config.rawLog, "a")
    except Exception as error:
        pp('logging of raw data failed: ', error)
    else:
        pp('raw data being logged to: ', config.rawLog)
        rawLog.write('\n' + startText +  '\n')
outputLog = None
if config.outputLog:
    try:
        outputLog = open(config.outputLog, "a")
    except Exception as error:
        pp('logging of output failed: ', error)
    else:
        pp('output being logged to: ', config.outputLog)
        outputLog.write('\n' + startText + '\n')

# Get output logging/display device, hard fail if not available
pp('starting output')
out = outputRRF(log=outputLog)
if not out.running:
    hardwareFail('Failed to start output device')

# Init RRF USB/serial connection
rrf = None
for device in config.devices:
    try:
        rrf = Serial(device,config.baud)
    except:
        pp('device "' + device + '" not available')
    else:
        pp('device "' + device + '" available')
        sleep_ms(100)   # settle time
        break
if not rrf:
    # Loop looking for a serial device
    restartNow('No USB/serial device found')
else:
    print('connected to: ' + rrf.name + ' @' + str(rrf.baudrate))

# create the OM handler
try:
    OM = serialOM(rrf, out.omKeys, rawLog, config.quiet)
except Exception as e:
    restartNow('Failed to start ObjectModel communications\n' + str(e))

if OM.machineMode == '':
    restartNow('Failed to connect to controller, or unsupported controller mode.')

# Update the display model and show overall Status
print(out.showStatus(OM.model),end='')

'''
    Main loop
'''
while True:
    # check output is running and restart if not
    if not out.running:
        restartNow('Output device has failed')
    begin = ticks_ms()
    haveData = False
    # request a model update and soft fail on errors
    try:
        haveData = OM.update()
    except Exception as e:
        restartNow('Error while fetching ObjectModel data\n' + str(e))
    # output the results if successful
    if haveData:
        # pass the results to the output module and print any response
        outputText = out.update(OM.model)
        if outputText:
             print(outputText,end='')
    else:
        pp('Failed to fetch ObjectModel data')
    # Request cycle ended, wait for next
    while ticks_diff(ticks_ms(),begin) < config.updateTime:
        sleep_ms(1)
