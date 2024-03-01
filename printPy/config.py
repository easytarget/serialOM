'''
    Set the serial device path and baud rate here, etc.
'''

class config():
    '''
        Serial Device Config:
        devices:  (list, strings) devices to try when connecting
                  - a list is used because under linux the /dev/ttyACM* and /dev/ttyUSB*
                    devices can wander between 0 and 1 when the controller reboots.
        baud:     (int) Serial baud rate; should match the setting used in config.g
        quiet:    (bool) suppress info messages
    '''
    devices = ['/dev/ttyACM0','/dev/ttyACM1']
    baud = 57600
    quiet = False

    '''
        Timing and timeout config:
        updateTime:     (int, ms)  Basic time interval between update cycles
        requestTimeout: (int, ms)  maximum time to wait for response after sending request
        rebootDelay:    (int) Countdown in seconds when auto-restarting/rebooting
    '''
    updateTime = 1000
    requestTimeout = updateTime * 0.66
    rebootDelay = 3

    '''
        Logging Config:
        - Replace "None" with "'filename.log'" to enable.
        rawLog:     A raw log of all incoming serial data
        outputLog:  Log file passed to the output module
                    - The example TXT output class will mirror it's output there
    '''
    rawLog = None
    outputLog = None
