#!/usr/local/bin/python3
# encoding: utf-8

"""
 * 
 *  mmuGcodeParser
 *
 *  Created by Nikolai Rinas on 12/28/2018
 *  Copyright (c) 2018 Nikolai Rinas. All rights reserved.
 * 
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
  
 *   You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>
 */
"""

import re  # regular expression library for search/replace
import os  # os routines for reading/writing files
import sys  # system library for input/output files

from io import open

""" ---------------------------------------------------------------------
### Constants
"""
VERSION = "v0.1"
MYGCODEMARK = " ; MMUGCODEPARSER " + VERSION
UNLOAD_START_LINE = "unloadStartLine"
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

# For debugging purpose
debug_set = False

# Drop the temperature by 10C during the ramming process. Checking if it might help
ram_temp_diff = 10

# get the input file specified, and turn it into a path variable for the current OS
inpath = sys.argv[1]
outpath = os.path.normpath(os.path.splitext(inpath)[0] + "_adjusted.gcode")

# open the input and output files (one read only, one for writing)
infile = open(inpath, 'r', encoding="utf8")
outfile = open(outpath, 'w', encoding="utf8")

""" ---------------------------------------------------------------
### Compile the regular expressions
"""

# We have to find following spots
# 1. Unload procedure
unloading = r"^T[0-9]?"
# 2. Purge
purge = r"^; CP TOOLCHANGE WIPE"
# 3. Print
printLine = r"^; CP TOOLCHANGE END"
# 4. Before unload
beforeUnload = r"^; CP TOOLCHANGE UNLOAD"
# 5. Target temperature
targetTemp = r"^M104 S([0-9]*)"

# start at TOOLCHANGE START comment. "^" simply indicates "beginning of line"
start = r"^; toolchange #[0-9]*"

# turn those strings into compiled regular expressions so we can search
start_detect = re.compile(start)
purge_detect = re.compile(purge)
print_detect = re.compile(printLine)
unloading_detect = re.compile(unloading)
before_unload_detect = re.compile(beforeUnload)
target_temp_detect = re.compile(targetTemp)


"""---------------------------------------------------------------------- 
### Functions
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
    if p_tool_change[p_line_number] == UNLOAD_START_LINE:
        # Add temp drop for better tip
        if ram_temp_diff > 0:  # Only if set
            lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
            lv_output = "M104 S" + str(lv_lower_temp)
            lv_insert = 1

    if p_tool_change[p_line_number] == DEST_TEMP_LINE:
        # We need to stay cool here
        # remove/comment existing line
        lv_insert = -9

    if p_tool_change[p_line_number] == UNLOAD_LINE:
        # set hot (to save some time)
        # insert the destination temp
        lv_output = "M104 S" + p_tool_change[DEST_TEMP]
        lv_insert = -1  # insert before start unloading

    if p_tool_change[p_line_number] == PURGE_LINE:
        # We have to wait for destination temp
        lv_output = "M109 S" + p_tool_change[DEST_TEMP]
        lv_insert = 1  # insert after the purge line identificator

    if p_tool_change[p_line_number] == PRINT_LINE:
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
    if p_tool_change[p_line_number] == UNLOAD_START_LINE:
        if ram_temp_diff > 0:  # Only if set
            # Add temp drop for better tip
            lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
            lv_output = "M104 S" + str(lv_lower_temp)
            lv_insert = 1  # after the line

    if p_tool_change[p_line_number] == DEST_TEMP_LINE:
        # remove/comment existing line
        lv_insert = -9

    if p_tool_change[p_line_number] == UNLOAD_LINE:
        # During unloading there is nothing to do
        # In case we are dropping the temp during ramming, we need to bump it up again
        if ram_temp_diff > 0:  # Only if set
            lv_output = "M104 S" + p_tool_change[CURR_TEMP]
            lv_insert = -1  # before the line
        pass

    if p_tool_change[p_line_number] == PURGE_LINE:
        # set to cold. We will cool down faster during purging
        lv_output = "M104 S" + p_tool_change[DEST_TEMP]
        lv_insert = 1  # after the line

    if p_tool_change[p_line_number] == PRINT_LINE:
        # wait for stable nozzle temp
        lv_output = "M109 S" + p_tool_change[DEST_TEMP]
        lv_insert = -1  # before the line

    # print(toolChange["id"])
    return lv_output, lv_insert


def none_handler(p_tool_change, p_line_number):
    # Just in case we need to do something at the end
    lv_output = ""
    lv_insert = 0  # 0 = don't insert, +1 = after the line, -1 before the line, -9 = comment out
    if p_tool_change[p_line_number] == UNLOAD_START_LINE:
        if ram_temp_diff > 0:  # Only if set
            # Add temp drop for better tip
            lv_lower_temp = int(p_tool_change[CURR_TEMP]) - ram_temp_diff
            lv_output = "M104 S" + str(lv_lower_temp)
            lv_insert = 1  # after the line

    if p_tool_change[p_line_number] == DEST_TEMP_LINE:
        # nothing to do
        pass

    if p_tool_change[p_line_number] == UNLOAD_LINE:
        # nothing to do
        pass

    if p_tool_change[p_line_number] == PURGE_LINE:
        # nothing to do
        pass

    if p_tool_change[p_line_number] == PRINT_LINE:
        # nothing to do
        pass

    # print(toolChange["id"])
    return lv_output, lv_insert


""" ------------------------------------------------------------------------------
### Main process
"""


""" ----------------------------------------------
### Scan the gcode for tool changes and the values
"""
# walk through each line in the file
myToolChanges = {}  # dictionary with all tool changes
line_number = 1     # index in the loop
toolChangeID = 0    # required to track the current tool change
initTemp = 0        # required to track the current temp
for line in infile:

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
            myToolChange[line_number] = ID_LINE
            toolChangeID = switchID  # Remember the last tool change ID for later reference
            # create dictionary entry
            myToolChanges[toolChangeID] = myToolChange

    # Search for the 'before loading' position
    before_unload_match = before_unload_detect.search(line)
    if before_unload_match is not None:
        if len(myToolChanges) > 0:  # we found at least the start tool change
            # remember the line number
            myToolChanges[toolChangeID][line_number] = UNLOAD_START_LINE

    # Search for the target temperature
    targetTemp_match = target_temp_detect.search(line)
    if targetTemp_match is not None:
        if len(myToolChanges) > 0:  # we found at least the start tool change
            if DEST_TEMP_LINE not in myToolChanges[toolChangeID]:
                # determine the temperature value
                tempMatch = re.search(r"S[0-9]*", line)
                temp = tempMatch.group(0).replace("S", "")
                if DEST_TEMP not in myToolChanges[toolChangeID]:  # do not overwrite in case of temp changes
                    # Remember the temperature
                    myToolChanges[toolChangeID][DEST_TEMP] = temp
                    # remember the line number
                    myToolChanges[toolChangeID][line_number] = DEST_TEMP_LINE
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
            myToolChanges[toolChangeID][line_number] = UNLOAD_LINE

    # Search for the purge command
    purge_match = purge_detect.search(line)
    if purge_match is not None:
        if len(myToolChanges) > 0:  # we have already at least one entry
            # remember the line number
            myToolChanges[toolChangeID][line_number] = PURGE_LINE

    # Search for the print command
    print_match = print_detect.search(line)
    if print_match is not None:
        if len(myToolChanges) > 0:  # we have already at least one entry
            # remember the line number
            myToolChanges[toolChangeID][line_number] = PRINT_LINE

    # increment the line number
    line_number = line_number + 1

""" -------------------------
### Determine the transitions  
"""

# Determine the transitions for the tool changes
lastTemp = initTemp
for toolChange in myToolChanges:
    # Last tool change is unloading only
    #  Special handler required in case we need to do something there
    if myToolChanges[toolChange][DEST_TEMP] == "0":
        myToolChanges[toolChange][TRANSITION] = NOTRANSITION
    else:
        if lastTemp > myToolChanges[toolChange][DEST_TEMP]:
            # Transition from higher value to lower value
            myToolChanges[toolChange][TRANSITION] = HIGH2LOW
        else:
            if lastTemp == myToolChanges[toolChange][DEST_TEMP]:
                # If there is no difference in temperature, no transition is required
                myToolChanges[toolChange][TRANSITION] = NOTRANSITION
            else:
                # Transition from lower to higher value
                myToolChanges[toolChange][TRANSITION] = LOW2HIGH

    # Save current temperature. Needed for first tool change
    myToolChanges[toolChange][CURR_TEMP] = lastTemp
    # Remember the last temperature
    lastTemp = myToolChanges[toolChange][DEST_TEMP]

""" ----------------------
### Update the gcode file
"""
# Here we have all the data to make our decisions and updating the gcode file
# Modify the file
line_number = 1
# Go back to the fist position in the input file
infile.seek(0)
for line in infile:
    output = ""  # reset the output
    action = 0   # reset the insert position

    # Check our dictionary if we have an entry for this line
    for toolChange in myToolChanges:
        if line_number in myToolChanges[toolChange]:
            if myToolChanges[toolChange][TRANSITION] == LOW2HIGH:
                # Calling handler for the lower to higher value transition
                output, action = low2high_handler(myToolChanges[toolChange], line_number)
            if myToolChanges[toolChange][TRANSITION] == HIGH2LOW:
                # Calling handler for the higher to lower value transition
                output, action = high2low_handler(myToolChanges[toolChange], line_number)
            if myToolChanges[toolChange][TRANSITION] == NOTRANSITION:
                # Calling handler for no transition case
                output, action = none_handler(myToolChanges[toolChange], line_number)

    # Perform the action determined for this line
    if action == 1:  # insert after this line
        file_write(outfile, line)
        file_write(outfile, output + MYGCODEMARK + "\n")

    if action == -1:  # insert before this line
        file_write(outfile, output + MYGCODEMARK + "\n")
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
    for toolChange in myToolChanges:
        file_write(outfile, "; " + str(myToolChanges[toolChange]) + "\n")
    file_write(outfile, ';;;;"Prusa PLA MMU2";')

# print(myToolChanges)
# end
