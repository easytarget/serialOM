# `printPY.py`
A test and example for the `serialOM.py' class/library on CPython based systems (eg RasPI)

Output is handled in a seperate class, easy to adapt for alternate displays.
* By default just an example text/console output class logging to the console and an optional logfile is provided.
  * Supports multiple machine modes (currently: `FFF`, `CNC` and `Laser`) showing data appropriate to the mode.
* It will be easy to adapt this to display on external devices (eg I2C/SPI displays)
  * All the hardware functions can remain inside the class itself.
  * The output class can be run on a seperate thread to the main loop.

## Use
```console
$ cd .../serialOM/printPy
$ python printPy [interval_ms [port [baud]]]
```
* See comments in config.py for configuring default connection and other details.
  * Defaults to `/dev/ttyACM[01]`, `57600` baud.
* Use `M575 P0 S2` in your `config.g` if this is not already configured.
* Accepts up to three optional (positional) arguments; `interval_ms` `port` `baud`, where *update_ms* is the main update interval in milliseconds, *port* is the serial port path/name and *baud* is an integer.

### Requirements:
* Expects to find the `serialOM.py` library in it's parent directory.
  * Modify the *path.insert()* line at the top of the file to change this path.
* Requires Python 3.7+ (ordered dictionaries).
* Requires `pyserial`.
  * Install your distros pyserial package: eg: `sudo apt install python-serial`, or `pip install --user pyserial`, or use a virtualenv (advanced users).
  * On linux make sure your user is in the 'dialout' group to access the devices.
  * There is no reason why this wont run on Windows, but I have not tried this. You will need a Python 3.7 install with pyserial, and change the device path to the windows equivalent.

### Notes:
* CPython; but I am trying to keep all the logic and data handling simple and low-memory for running on microPython.
  * Non micropython standard libs are discouraged unless they have a easy micropython equivalent/local lib.
  * All times are in `ms` (micropython uses `int(ms)` for it's timing basics rather than `float(seconds)`).
* Tested and developed on a RaspberryPI connected to my Duet2 wifi via USB/serial.

# output class:
The output class, `outputRRF` is, essentially, very simple.

An example is presented in `outputTXT.py` that can log to the console and to a file with timestamps.

## Init:
```python
from outputXXX import outputRRF
```
.. where `outputXXX` is the output class *source.py*
```python
out =  outputRRF(log=None)
```
At init *outputRRF()* takes one optional argument: `log`; a writeable file handle for an output log (or None to disable).

The class must provide the `out.omKeys` property with the machine modes and keypairs it supports, *printPy* will pass this to *serialOM* (see the serialOM documentation).

Any necesscary hardware setup needs to happen during init, and the `out.running` flag property set if this succeeds.

## Methods and Properties:

*outputRRF* provides two methods:
```python
outputRRF.update(model)
```
Updates the ObjectModel being displayed.
* *model* is an optional parameter
* Returns a string that will be logged to console by printPy
```python
outputRRF.showStatus(model):
```
Shows extended status information in response to a button press or other trigger
* *model* is an optional parameter
* Not really used by the text outputter, aimed at standalone applications like PrintPy2040
* Returns a string that will be logged to console by printPy

There are two public properties:

`out.running` : a simple boolean property that is true if the display is active
`out.statusActive` : a simple boolean property that is true if the display is showing a expanded status screen, typically on a timer.

## Notes:
The output class keeps it's own copy of the OM so that it can rebuild it's display at will (eg for animation), this local copy is only updated when update() or showStatus() are called with the *model* parameter.

The output class is expected to be fully independent of the main *printPy* loop. Responding only to what it sees in the ObjectModel updates it is passed and doing appropriate animations on startup and when *showStatus()* is called.

It should examine the machine status and uptime to decide when to show 'reboot', 'on', 'off', 'timeout' and other informational responses (splash screens). Screensavers and brightness levels should be derived this way too.
