from machine import Pin
'''
    Set the serial device path and baud rate here, etc.
'''

class config():
    '''
        Serial Device Config:
        device:   (int) UART device (0 or 1)
        baud:     (int) Serial baud rate; should match the setting used in config.g
        quiet:    (bool) suppress info messages
    '''
    device = 0
    baud = 57600
    quiet = False

    '''
        Timing and timeout config:
        updateTime:     (int, ms)  Basic time interval between update cycles
        rebootDelay:    (int) Countdown in seconds when auto-restarting/rebooting printPy
    '''
    updateTime = 1000
    rebootDelay = 3

    '''
        Logging Config:
        - Replace "None" with "'filename.log'" to enable.
        rawLog:     A raw log of all incoming serial data
        outputLog:  Log file passed to the output module
                    - The example TXT output class will mirror it's output there

        WARNING: log files will fill rapidly (MB/Hr for the raw log)
                 use with caution on microPython devices.
    '''
    rawLog = None
    outputLog = None

    '''
        Hardware config:
        button:     Status button pin object, (or None)
                        eg: button = Pin(2, Pin.IN, Pin.PULL_UP)
                        see the micropython 'machine.Pin()' docs
        buttonDown: Pin value when button depressed
        buttonTm:   debounce time (ms); keep this as low as practical
        buttonLong: long press time (ms) for WiFi toggle, 0 to disable
    '''
    button = None
    buttonDown = 0
    buttonTm = 50
    buttonLong = 500
