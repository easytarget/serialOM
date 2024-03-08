# This is the microPython port of serialOM

place all the `.py` files in this folder in the root of your microPython device along with `serialOM.py` *and* `compatLib.py` from the repo root folder.

Currently has two working programs:
* `printMPy.py`  : microPython printPy fork
  * Settings are in `config.py`
  * A `lumen` class has been added to handle status LED's. It can also show a RGB 'mood'.
  * The `outputTXT.py` class is identical to the main printPy one, REPL console output and file logging works.
* `microDemo.py` : a re-work of the CPython miniDemo for microPython

Costomisation:
* The `Xiao2024` folder contains the modified output and lumen classes+tools for PrintPy2040
  * The lumen class supports mood display via the on-board Neopixel
  * The output class is a WORK IN PROGRESS (very basic ATM), but wake and status display work.

Development ongoing
* Currently Runs! (XiaoRP2040)
* Documentation in progress.
* This is working towards a output module for [PrintPy2040](https://github.com/easytarget/PrintPy2040)
