#!which python3
# encoding: utf-8

""" 
mmuGcodeParser

Created by Nikolai Rinas on 12/28/2018
Copyright (c) 2018 Nikolai Rinas. All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>
"""

import re  # regular expression library for search/replace
import os  # os routines for reading/writing files
import sys  # system library for input/output files

from io import open

""" 
### ---------------------------------------------------------------
### Constants
### ---------------------------------------------------------------
""" 
VERSION = "v0.3"
MYGCODEMARK = "MMUGCODEPARSER " + VERSION
UNLOAD_START_LINE = "unloadStartLine"
LOAD_START_LINE = "loadStartLine"
DEST_TEMP_LINE = "destTempLine"
DEST_TEMP = "destTemp"
UNLOAD_LINE = "unloadLine"
PURGE_LINE = "purgeLine"
PRINT_LINE = "printLine"
CURR_TEMP = "currTemp"
TRANSITION = "transition"
LOW2HIGH = "Low2High"
HIGH2LOW = "High2Low"
NOTRANSITION = "NoTrans"
ID_LINE = "idLine"
RAM_TEMP = "ramTemp"
PURGE_TEMP = "purgeTemp"
LINE_NUMBERS = "lineNumbers"

""" 
### ---------------------------------------------------------------
### Settings
### ---------------------------------------------------------------
""" 
# For debugging purpose
debug_set = False

# Drop the temperature by 10C during the ramming process. Checking if it might help
ram_temp_diff = 10

# Set this to True if you want to drop the temperature even for the same filament 
ram_temp_diff_wait_for_stabilize = False

# Prefix for output file
outpath_prefix = ""

# Suffix for output file
outpath_suffix = "_adjusted"

# get the input file specified
inpath = sys.argv[1]

# open the input file for reading
infile = open(inpath, 'r', encoding="utf8")

""" 
### ---------------------------------------------------------------
### Compile the regular expressions
### ---------------------------------------------------------------
""" 

# We have to find following spots
# 1. Unload procedure
unloading = r"^T[0-9]?"
# 2. Purge
purge = r"^; CP TOOLCHANGE WIPE"
# 3. Print
printLine = r"^; CP TOOLCHANGE END"
# 4. Before unload/load
beforeUnload = r"^; CP TOOLCHANGE UNLOAD"
beforeLoad = r"^; CP TOOLCHANGE LOAD"
# 5. Target temperature
targetTemp = r"^M104 S([0-9]*)"

# Start at TOOLCHANGE START comment. "^" simply indicates "beginning of line"
start = r"^; toolchange #[0-9]*"

# Regular expressions to find settings

# Printer Start G-Code
mmuGPDebug = r"^; MMUGP Debug"
mmuGPRamTempDiff = r"^; MMUGP Ram Temp Diff ([0-9]*)"
mmuGPRamTempDiffWaitStabilize = r"^; MMUPG Ram Temp Diff Wait For Stabilize"
mmuGPFilenamePrefix = r"^; MMUGP Filename Prefix ?([a-zA-Z_-]*)"
mmuGPFilenameSuffix = r"^; MMUGP Filename Suffix ?([a-zA-Z_-]*)"

# Filament End G-Code
mmuGPRamTemp = r"^; MMUGP Ram Temp ([0-9]*)"
mmuGPPurgeTemp = r"^; MMUGP Purge Temp ([0-9]*)"

# turn those strings into compiled regular expressions so we can search
start_detect = re.compile(start)
purge_detect = re.compile(purge)
print_detect = re.compile(printLine)
unloading_detect = re.compile(unloading)
before_unload_detect = re.compile(beforeUnload)
before_load_detect = re.compile(beforeLoad)
target_temp_detect = re.compile(targetTemp)
mmugp_debug_detect = re.compile(mmuGPDebug)
mmugp_ram_temp_diff_detect = re.compile(mmuGPRamTempDiff)
mmugp_ram_temp_diff_wait_stabilize_detect = re.compile(mmuGPRamTempDiffWaitStabilize)
mmugp_filename_prefix_detect = re.compile(mmuGPFilenamePrefix)
mmugp_filename_suffix_detect = re.compile(mmuGPFilenameSuffix)
mmugp_ram_temp_detect = re.compile(mmuGPRamTemp)
mmugp_purge_temp_detect = re.compile(mmuGPPurgeTemp)

""" 
### ---------------------------------------------------------------
### Functions
### ---------------------------------------------------------------
""" 

def file_write(file, string):
    # print(string)
    file.write(string)

def low2high_handler(p_tool_change, p_line_number):
    """ Basic idea
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
    """

    lv_output = ""
    lv_insert = 0  # 0 = don't insert, +1 = after the line, -1 before the line, -9 = comment out

    if p_tool_change.get(UNLOAD_START_LINE) == p_line_number:
        if RAM_TEMP in p_tool_change and p_tool_change[RAM_TEMP] > 0:
            # If we have a ram temp for this toolchange we set the temp
            lv_output = "M104 S" + str(p_tool_change[RAM_TEMP])
            lv_insert = 1
        elif ram_temp_diff > 0:  # Only if set and no direct ram temp
            # Add temp drop for better tip
            lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
            lv_output = "M104 S" + str(lv_lower_temp)
            lv_insert = 1

    if p_tool_change.get(DEST_TEMP_LINE) == p_line_number:
        # We need to stay cool here
        # remove/comment existing line
        lv_insert = -9

    if p_tool_change.get(UNLOAD_LINE) == p_line_number:
        # set hot (to save some time)
        # insert the destination temp
        lv_output = "M104 S" + p_tool_change[DEST_TEMP]
        lv_insert = -1  # insert before start unloading

    if p_tool_change.get(PURGE_LINE) == p_line_number:
        # We have to wait for destination temp
        lv_output = "M109 S" + p_tool_change[DEST_TEMP]
        lv_insert = 1  # insert after the purge line identificator

    if p_tool_change.get(PRINT_LINE) == p_line_number:
        # We are already hot. Nothing to do here
        pass

    # print(toolChange["id"])
    return lv_output, lv_insert


def high2low_handler(p_tool_change, p_line_number):
    """ Basic idea
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
    """

    lv_output = ""
    lv_insert = 0  # 0 = don't insert, +1 = after the line, -1 before the line, -9 = comment out

    if p_tool_change.get(UNLOAD_START_LINE) == p_line_number:
        if RAM_TEMP in p_tool_change and p_tool_change[RAM_TEMP] > 0:
            # If we have a ram temp for this toolchange we set the temp
            lv_output = "M104 S" + str(p_tool_change[RAM_TEMP])
            lv_insert = 1
        elif ram_temp_diff > 0:  # Only if set and no direct ram temp
            # Add temp drop for better tip
            lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
            lv_output = "M104 S" + str(lv_lower_temp)
            lv_insert = 1  # after the line

    if p_tool_change.get(DEST_TEMP_LINE) == p_line_number:
        # remove/comment existing line
        lv_insert = -9

    if p_tool_change.get(UNLOAD_LINE) == p_line_number:
        # During unloading there is nothing to do
        # In case we are dropping the temp during ramming, we need to bump it up again
        if ram_temp_diff > 0:  # Only if set
            lv_output = "M104 S" + p_tool_change[CURR_TEMP]
            lv_insert = -1  # before the line
        pass

    if p_tool_change.get(PURGE_LINE) == p_line_number:
        # set to cold. We will cool down faster during purging
        lv_output = "M104 S" + p_tool_change[DEST_TEMP]
        lv_insert = 1  # after the line

    if p_tool_change.get(PRINT_LINE) == p_line_number:
        # wait for stable nozzle temp
        lv_output = "M109 S" + p_tool_change[DEST_TEMP]
        lv_insert = -1  # before the line

    # print(toolChange["id"])
    return lv_output, lv_insert


def none_handler(p_tool_change, p_line_number):
    # Just in case we need to do something at the end
    lv_output = ""
    lv_insert = 0  # 0 = don't insert, +1 = after the line, -1 before the line, -9 = comment out

    if CURR_TEMP in p_tool_change :
        if p_tool_change.get(UNLOAD_START_LINE) == p_line_number:
            if RAM_TEMP in p_tool_change and p_tool_change[RAM_TEMP] > 0:
                # If we have a ram temp for this toolchange we set the temp
                if ram_temp_diff_wait_for_stabilize:
                    lv_output = "M109 S" + str(p_tool_change[RAM_TEMP])
                else:
                    lv_output = "M104 S" + str(p_tool_change[RAM_TEMP])

                lv_insert = 1
            elif ram_temp_diff > 0:  # Only if set and no direct ram temp
                # Add temp drop for better tip
                lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
                if ram_temp_diff_wait_for_stabilize:
                    lv_output = "M109 S" + str(lv_lower_temp)
                else:
                    lv_output = "M104 S" + str(lv_lower_temp)

                lv_output = "M104 S" + str(lv_lower_temp)
                lv_insert = 1  # after the line

        if p_tool_change.get(LOAD_START_LINE) == p_line_number:
            if ram_temp_diff > 0:  # Only if set
                lv_restore_temp = int(p_tool_change[CURR_TEMP])
                # don't wait for stable nozzle temperature
                # (enough time for nozzle to reach correct temp)
                lv_output = "M104 S" + str(lv_restore_temp)
                lv_insert = 1

        if p_tool_change.get(DEST_TEMP_LINE) == p_line_number:
            # nothing to do
            pass

        if p_tool_change.get(UNLOAD_LINE) == p_line_number:
            # nothing to do
            pass

        if p_tool_change.get(PURGE_LINE) == p_line_number:
            # nothing to do
            pass

        if p_tool_change.get(PRINT_LINE) == p_line_number:
            # nothing to do
            pass

    return lv_output, lv_insert

# Progressbar for analyzing input file
progress_unknown_state = -1
def progress_unknown(cur=0, text=""):
    global progress_unknown_state
    progress_unknown_states = "|/-\\"

    if progress_unknown_state == -1:
        progress_unknown_state = 0
        sys.stdout.flush()

    sys.stdout.write("[" + progress_unknown_states[progress_unknown_state:progress_unknown_state+1] + "] " + text + " " + str(cur) + "\r")

    if cur % 1000 == 0:
        progress_unknown_state += 1
        if progress_unknown_state >= len(progress_unknown_states):
            progress_unknown_state = 0

    sys.stdout.flush()

# Progressbar for analyzing tool changes and writing output file
def progress_range(cur, text="", start=1, end=10, maxwidth=50, clearOnEnd=True):
    curPos = int(translate(cur, start, end, start, maxwidth))
    doneLen = curPos - 1
    todoLen = maxwidth - curPos
    
    progressLine = "[%s>%s] %s %d of %d (%d%%)\r" % ("=" * doneLen, " " * todoLen, text, cur, end, int(cur / end * 100))
    sys.stdout.write(progressLine)

    if cur == end:
        sys.stdout.write("%s\r" % (" " * len(progressLine)))

    sys.stdout.flush()

def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

""" 
### ------------------------------------------------------------------------------
### Main process
### ------------------------------------------------------------------------------
"""

""" 
### ----------------------------------------------
### Scan the gcode for tool changes and the values
### ----------------------------------------------
"""

print("Analyzing input file...")

# walk through each line in the file
myToolChanges = {}  # dictionary with all tool changes
line_number = 1     # index in the loop
toolChangeID = 0    # required to track the current tool change
initTemp = 0        # required to track the current temp
lineCount = 0       # Number of lines in input file
for line in infile:
    progress_unknown(line_number, "Line")

    # Search for the tool change starts
    start_match = start_detect.search(line)
    if start_match is not None:
        start_position_match = re.search(r"[0-9]*\Z", start_match.group(0))
        if start_position_match is not None:
            # create a dictionary
            myToolChange = {}
            switchID = start_position_match.group(0)
            # remember the tool change start position
            myToolChange["id"] = switchID
            myToolChange[ID_LINE] = line_number
            myToolChange[LINE_NUMBERS] = [line_number]

            toolChangeID = switchID  # Remember the last tool change ID for later reference
            # create dictionary entry
            myToolChanges[toolChangeID] = myToolChange

    # Search for the 'before unloading' position
    before_unload_match = before_unload_detect.search(line)
    if before_unload_match is not None:
        if len(myToolChanges) > 0:  # we found at least the start tool change
            # remember the line number
            myToolChanges[toolChangeID][UNLOAD_START_LINE] = line_number
            myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)

    # Search for the 'before loading' position
    before_load_match = before_load_detect.search(line)
    if before_load_match is not None:
        if len(myToolChanges) > 0:  # we found at least the start tool change
            # remember the line number
            myToolChanges[toolChangeID][LOAD_START_LINE] = line_number
            myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)

    # Search for the target temperature
    targetTemp_match = target_temp_detect.search(line)
    if targetTemp_match is not None:
        if len(myToolChanges) > 0:  # we found at least the start tool change
            # print(myToolChanges[toolChangeID])

            if DEST_TEMP_LINE not in myToolChanges[toolChangeID]:
                # determine the temperature value
                tempMatch = re.search(r"S[0-9]*", line)
                temp = tempMatch.group(0).replace("S", "")
                if DEST_TEMP not in myToolChanges[toolChangeID]:  # do not overwrite in case of temp changes
                    # Remember the temperature
                    myToolChanges[toolChangeID][DEST_TEMP] = temp
                    # remember the line number
                    myToolChanges[toolChangeID][DEST_TEMP_LINE] = line_number
                    myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)
        else:
            # Search for the initial Temperature
            if initTemp == 0:
                # We need this value later to determine the transition for the first tool change
                tempMatch = re.search(r"S[0-9]*", line)
                temp = tempMatch.group(0).replace("S", "")
                initTemp = temp

    # Search for the unloading command
    unloading_match = unloading_detect.search(line)
    if unloading_match is not None:
        if len(myToolChanges) > 0:  # we have already at least one entry
            # remember the line number
            myToolChanges[toolChangeID][UNLOAD_LINE] = line_number
            myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)

    # Search for Ram Temp setting
    ram_temp_match = mmugp_ram_temp_detect.search(line)
    if ram_temp_match is not None:
        if len(myToolChanges) > 0 and not RAM_TEMP in myToolChanges[toolChangeID]:
            myToolChanges[toolChangeID][RAM_TEMP] = int(ram_temp_match.group(1))

    # Search for Purge Temp setting
    purge_temp_match = mmugp_purge_temp_detect.search(line)
    if purge_temp_match is not None:
        if len(myToolChanges) > 0 and not PURGE_TEMP in myToolChanges[toolChangeID]:
            myToolChanges[toolChangeID][PURGE_TEMP] = int(purge_temp_match.group(1))

    # Search for the purge command
    purge_match = purge_detect.search(line)
    if purge_match is not None:
        if len(myToolChanges) > 0:  # we have already at least one entry
            # remember the line number
            myToolChanges[toolChangeID][PURGE_LINE] = line_number
            myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)

    # Search for the print command
    print_match = print_detect.search(line)
    if print_match is not None:
        if len(myToolChanges) > 0:  # we have already at least one entry
            # remember the line number
            myToolChanges[toolChangeID][PRINT_LINE] = line_number
            myToolChanges[toolChangeID][LINE_NUMBERS].append(line_number)

    # Search for Debug setting
    debug_match = mmugp_debug_detect.search(line)
    if debug_match is not None:
        debug_set = True

    # Search for Ram Temp Diff setting
    ram_temp_diff_match = mmugp_ram_temp_diff_detect.search(line)
    if ram_temp_diff_match is not None:
        ram_temp_diff = int(ram_temp_diff_match.group(1))

    # Search for Ram Temp Diff Wait For Stabilize setting
    ram_temp_diff_wait_for_stabilize_match = mmugp_ram_temp_diff_wait_stabilize_detect.search(line)
    if ram_temp_diff_wait_for_stabilize_match is not None:
        ram_temp_diff_wait_for_stabilize = True

    # Search for Filename Prefix setting
    filename_prefix_match = mmugp_filename_prefix_detect.search(line)
    if filename_prefix_match is not None:
        outpath_prefix = filename_prefix_match.group(1)

    # Search for Filename Suffix setting
    filename_suffix_match = mmugp_filename_suffix_detect.search(line)
    if filename_suffix_match is not None:
        outpath_suffix = filename_suffix_match.group(1)

    # increment the line number
    line_number = line_number + 1
    lineCount = lineCount + 1

""" 
### -------------------------
### Determine the transitions
### -------------------------
"""

print("Determining tool changes...")

# Determine the transitions for the tool changes
lastTemp = initTemp
currentToolChange = 0
for toolChange in myToolChanges:
    currentToolChange += 1
    progress_range(currentToolChange, "Toolchange", 1, len(myToolChanges))

    # Last tool change is unloading only
    #  Special handler required in case we need to do something there
    if DEST_TEMP in myToolChanges[toolChange]:
        if myToolChanges[toolChange][DEST_TEMP] == "0":
            myToolChanges[toolChange][TRANSITION] = NOTRANSITION
        elif lastTemp > myToolChanges[toolChange][DEST_TEMP]:
            # Transition from higher value to lower value
            myToolChanges[toolChange][TRANSITION] = HIGH2LOW
        elif lastTemp == myToolChanges[toolChange][DEST_TEMP]:
            # If there is no difference in temperature, no transition is required
            myToolChanges[toolChange][TRANSITION] = NOTRANSITION
        else:
            # Transition from lower to higher value
            myToolChanges[toolChange][TRANSITION] = LOW2HIGH

        # Save current temperature. Needed for first tool change
        myToolChanges[toolChange][CURR_TEMP] = lastTemp
        # Remember the last temperature
        lastTemp = myToolChanges[toolChange][DEST_TEMP]
    else:
        myToolChanges[toolChange][TRANSITION] = NOTRANSITION
        if RAM_TEMP in myToolChanges[toolChange]:
            myToolChanges[toolChange][CURR_TEMP] = lastTemp

""" 
### ----------------------
### Update the gcode file
### ----------------------
"""

print("Writing output file...")

# First we build our new filename
directory, filename = os.path.split(inpath)
basename = os.path.splitext(filename)[0]

newname = outpath_prefix + basename + outpath_suffix + ".gcode"
outpath = os.path.normpath(os.path.join(directory, newname))
outfile = open(outpath, 'w', encoding="utf8")

# Here we have all the data to make our decisions and updating the gcode file
# Modify the file
line_number = 1
# Go back to the fist position in the input file
infile.seek(0)
for line in infile:
    progress_range(line_number, "Line", 1, lineCount)

    output = ""  # reset the output
    action = 0   # reset the insert position

    # Check our dictionary if we have an entry for this line
    for toolChange in myToolChanges:
        if line_number in myToolChanges[toolChange][LINE_NUMBERS]:
            if myToolChanges[toolChange][TRANSITION] == LOW2HIGH:
                # Calling handler for the lower to higher value transition
                output, action = low2high_handler(myToolChanges[toolChange], line_number)
            elif myToolChanges[toolChange][TRANSITION] == HIGH2LOW:
                # Calling handler for the higher to lower value transition
                output, action = high2low_handler(myToolChanges[toolChange], line_number)
            elif myToolChanges[toolChange][TRANSITION] == NOTRANSITION:
                # Calling handler for no transition case
                output, action = none_handler(myToolChanges[toolChange], line_number)

            # Nothing todo anymore
            break

    # Perform the action determined for this line
    if action == 1:  # insert after this line
        file_write(outfile, line)
        file_write(outfile, output + " ; " + MYGCODEMARK + "\n")

    if action == -1:  # insert before this line
        file_write(outfile, output + " ; " + MYGCODEMARK + "\n")
        file_write(outfile, line)

    if action == -9:  # comment out the line
        file_write(outfile, ";" + line)

    if action == 0:  # leave the line untouched
        file_write(outfile, line)
        # pass

    # increase line index
    line_number = line_number + 1

# Print a nice summery at the end of the file
if debug_set is True:
    file_write(outfile, "; Debug information: " + MYGCODEMARK + "\n")
    file_write(outfile, "; Settings: \n")
    file_write(outfile, ";\tDebug: " + str(debug_set) + "\n")
    file_write(outfile, ";\tOutput Prefix: " + outpath_prefix + "\n")
    file_write(outfile, ";\tOutput Suffix: " + outpath_suffix + "\n")
    file_write(outfile, ";\tRam Temp Difference: " + str(ram_temp_diff) + "\n")
    file_write(outfile, ";\tRam Temp Difference Wait for Stabilize: " + str(ram_temp_diff_wait_for_stabilize) + "\n")

    file_write(outfile, "; Tool Changes: \n")
    for toolChange in myToolChanges:
        myToolChanges[toolChange].pop(LINE_NUMBERS, None)
        file_write(outfile, ";\t" + str(myToolChanges[toolChange]) + "\n")

print("Done")