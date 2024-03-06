# This is the microPython port of serialOM

place all the `.py` files in this folder in the root of your microPython device
along with `serialOM.py` *and* `compatLib.py` from the repo root folder.

Currently has two working programs:
* `printMPy.py`  : microPython printPy fork
  * Settings are in `config.py`
  * The `outputTXT.py` class is identical to the main printPy one, REPL console output and file logging works.
* `microDemo.py` : a re-work of the CPython miniDemo for microPython

Development ongoing
* Currently Runs! (XiaoRP2040)
* Documentation in progress.
* This is working towards a I2C output module for [PrintPy2040](https://github.com/easytarget/PrintPy2040)
