## Example tools:

### `printPY.py`
A test and example for the `serialOM.py' class/library
* This was written as a prototype for the 'heart' of micropython based PrintPy2040
* Output is a seperate python class, easy to adapt for alternate displays
  * By default just an example text/console output class is provided
  * It will be easy to adapt this to display on external devices (eg I2C/SPI displays)
  * Supports multiple machine modes (currently: `FFF`, `CNC` and `Laser`) showing data appropriate to the mode

* Expects to find the `serialOM.py` library in it's parent directory
  * Modify the line at the top of the file to change this path
* Requires Python 3.7+ (ordered dictionaries)
* Requires `pyserial`
  * Install your distros pyserial package: eg: `sudo apt install python-serial`, or `pip install --user pyserial`, or use a virtualenv (advanced users).
  * On linux make sure your user is in the 'dialout' group to access the devices
  * There is no reason why this wont run on Windows, but I have not tried this. You will need a Python 3.7 install with pyserial, and change the device path to the windows equivalent

* Notes:
  * CPython; but I am trying to keep all the logic and data handling simple and low-memory for running on microPython
    * Non micropython standard libs are discouraged unless they have a easy micropython equivalent/local lib
    * All times are in `ms` (micropython uses `int(ms)` for it's timing basics rather than `float(seconds)`)
  * Tested and developed on a RaspberryPI connected to my Duet2 wifi via USB/serial

* See comment in RRFconfigExample.py for configuring connection details
  * Defaults to `/dev/ttyACM[01]`, `57600` baud; use `M575 P0 S2` in your `config.g` if this is not already configured
