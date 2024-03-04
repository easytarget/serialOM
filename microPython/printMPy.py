from sys import exit
# Import our local classes and config
from serialOM import serialOM
from outputTXT import outputRRF
from config import config

# Common classes between CPython and microPython
from gc import collect
from machine import UART
from time import sleep_ms,ticks_ms,ticks_diff,localtime
from machine import reset
from micropython import mem_info


'''
    PrintMPy is a serialOM.py loop for MicroPython devices.
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
        pp(c,end=' ')
        sleep_ms(1000)
    pp()
    #execv(executable, ['python'] + argv)   #  CPython
    exit()
    reset() # Micropython; reboot module

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
    print('printMPy is starting at: ' + startDate + ' ' + startTime + ' (device localtime)')

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

# Get output/display device, hard fail if not available
pp('starting output')
out = outputRRF(log=outputLog)
if not out.running:
    hardwareFail('Failed to start output device')

# Init RRF USB/serial connection
rrf = UART(config.device)
rrf.init(baudrate=config.baud)
if not rrf:
    hardwareFail('No UART device found')
else:
    print('UART connected')

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
    collect()  # do this before every loop because.. microPython
    begin = ticks_ms()
    # Do a OM update
    haveData = False
    try:
        haveData = OM.update()
    except Exception as e:
        restartNow('Error while fetching machine state\n' + str(e))
    # output the results if successful
    if haveData:
        # pass the results to the output module and print any response
        outputText = out.update(OM.model)
        if outputText:
             print(outputText,end='')
    else:
        pp('Failed to fetch ObjectModel data')
    # check output is running and restart if not
    if not out.running:
        restartNow('Output device has failed')
    #mem_info()
    # Request cycle ended, wait for next
    while ticks_diff(ticks_ms(),begin) < config.updateTime:
        sleep_ms(1)
