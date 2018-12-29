@ECHO OFF
SET filepath=%~f1

IF NOT EXIST "%filepath%" (
    ECHO %~n0: file not found - %filepath% >&2
    EXIT /B 1
)
ECHO Adjusting the gcode file. Please wait ...
C:\Users\nikol01\AppData\Local\Continuum\anaconda3\python.exe C:\Users\nikol01\ownCloud\PycharmProjects\MMUGcodeParser\mmuGcodeParser.py %filepath%