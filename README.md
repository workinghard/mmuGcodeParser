# mmuGcodeParser
Improves Slic3r gcode for better MMU handling and allows true Multi Material printing.

If you're using Prusa MMU1/MMU2 and Slic3r 1.41 you will encounter an issue if the temperature differ between the used materials.
Slic3r sets the new temperature between toolchanges only once after cooling and before unloading. This causing an issue in the transition from high temp filament to cold because it is being purged with cold temperature. 

## Table of contents
 * [Installation](#installation)
   * [Linux/Mac](#linux/Mac)
   * [Windows](#windows)
 * [Usage](#usage)
 * [How it works](#how-it-works)
 * [Testobject](#testobject)
 * [Roadmap](#roadmap)

## Installation
The python script can be either placed in Slic3r for post processing under "Print Settings" -> "Output options" -> "Post-processing scripts".
Or it can be called manually passing the gcode file as an argument.

### Linux/Mac
Python version 3 is required. Make sure to adjust the path in first line to your installation: '''#!/usr/local/bin/python3'''

### Windows
Extract the zip to any location and use it either in Slic3r or in the command line.  

## Usage
If you maintained the post processing script in Slic3r, you will get in the output folder two files. The original one and with <b>_adjusted.gcode</b> extension. 

## How it works
The logic behind this script is following:

 1. It looks for tool changes and determines the transition (high->low, low->high)
 2. It removes the existing temperature set
 3. Placing the new temperature based on following strategy:
``` 
 Cold (200C) ==> Hot (255C)
 ==========================
 -> Ram/cool
   -> Stay cool, do nothing. If needed, set lower temp but don't wait
 -> Unload filament
   -> Set hot. We can heating up while loading. Save some time
 -> Load filament
   -> Nozzle might still warming up. Load to nozzle for smooth loading process
 -> Purge
   -> Before start purging, wait for destination temp
 -> Print
   -> We are printing with the stabilized temp. No further intervention required

 Hot (255C) ==> Cold (200C)
 ==========================
 -> Ram/cool
   -> We need to stay hot because hot filament is still in the nozzle. If needed, set lower temp but don't wait
 -> Unload
   -> Stay hot, do nothing
 -> Load filament
   -> Stay hot, do nothing. Load to nozzle for smooth loading process
 -> Purge
   -> Before start purging, set cool temp. We can cool down during the purging process
 -> Print
   -> Before start to print, wait for destination temp. Most likely temp will bounce pretty hard
```

## Testobject
I've created a small test object. It can be used to print different material.

### Properties
 * Two windows with one wall thickness
 * Two windows with two wall thickness
 * Two vertical tubes
 * One horizontal tube
 * 100+ tool changes with 0.2 layer height

## Roadmap
This is a first release and a proof of concept. I've printed the test object with PLA base and PETG windows and tubes successfully.
I'm currently using it for any multi material prints as it helps as soon as you use filament with different temperature requirements.

For further discussions please use this official [Prusa forum thread](https://sourceforge.net/projects/linuxconsole/)
