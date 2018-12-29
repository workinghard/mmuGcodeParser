@ECHO OFF
SET filepath=%~f1

IF NOT EXIST "%filepath%" (
    ECHO %~n0: file not found - %filepath% >&2
    EXIT /B 1
)
ECHO Adjusting the gcode file. Please wait ...
C:\<path to python>\python.exe C:\<path to script>\mmuGcodeParser.py %filepath%
