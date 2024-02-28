from sys import path
path.insert(0,'..')
# Import our local classes and config
from serialOM import serialOM
from outputTXT import outputRRF
from config import config

# Common classes between CPython and microPython
from gc import collect
from sys import argv
'''
    microPython:
    from machine import UART
    from time import sleep_ms,ticks_ms,ticks_diff,localtime
    from machine import reset
'''
from serial import Serial
from timeStubs import sleep_ms,ticks_ms,ticks_diff
from time import localtime
from sys import executable
from os import execv

'''
    PrintPy is a serialOM.py demo/example.

    This is intended to be run on a desktop system (CPython, not microPython)
    that connects via serial or USBserial to a RRF 3.x based controller.

    For requirements and arguments please refer to the  README, the only real
    requirement is py-serial ('pip install --user pyserial' etc..)

    As with serialOM itself there a comments hera about microPython use, iplease
    ignore these since they are reminders for me to use when porting this later
'''

# local print function so we can suppress info messages.
def pp(*args, **kwargs):
    if not config.quiet:
        print(*args, **kwargs)

# Do a minimum drama restart/reboot
def restartNow(why):
    pp('Error: ' + why +'\nRestarting in ',end='')
    # Pause for a few seconds, then restart
    for c in range(config.rebootDelay,0,-1):
        pp(c,end=' ',flush=True)
        sleep_ms(1000)
    pp()
    execv(executable, ['python'] + argv)   #  CPython
    #reset() # Micropython; reboot module

# Used for critical hardware errors during initialisation on MCU's
# Unused in Cpython, instead we soft-fail, restart and try again.
# - in microPython we will be harsher with hardware errors
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
    config.requestTimeout = int(config.updateTime * 0.66)
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

# Get output/display device
pp('starting output')
out = outputRRF(log=outputLog)

# Init RRF USB/serial connection
rrf = None
for device in config.devices:
    try:
        # microPython: replace following with UART init
        #              and we must set blocking timeout here too
        rrf = Serial(device,config.baud)
    except:
        pp('device "' + device + '" not available')
    else:
        pp('device "' + device + '" available')
        sleep_ms(100)   # settle time
        break
if not rrf:
    # Loop looking for a serial device
    # For micropython we should stop here since no UART == a serious fail.
    restartNow('No USB/serial device found')
else:
    print('connected to: ' + rrf.name + ' @' + str(rrf.baudrate))

# create the OM handler
try:
    OM = serialOM(rrf, out.omKeys, config.requestTimeout, rawLog, config.quiet)
except Exception as e:
    restartNow('Failed to start ObjectModel communications\n' + str(e))

if OM.machineMode == '':
    restartNow('Startup error while connecting to controller')

# Update the display model and show overall Status
out.updateModel(OM.model)
print(out.showStatus())

'''
    Main loop
'''
while True:
    collect()  # do this before every loop because.. microPython
    begin = ticks_ms()
    # Do a OM update
    haveData = False
    try:
        haveData = OM.update()
    except Exception as e:
        restartNow('Failed to fetch machine state\n' + str(e))
    # output the results if successful
    if haveData:
        # output the results
        out.updateModel(OM.model)
        print(out.showOutput())
    else:
        pp('Failed to fetch machine state')
    # Request cycle ended, wait for next
    while ticks_diff(ticks_ms(),begin) < config.updateTime:
        sleep_ms(1)
