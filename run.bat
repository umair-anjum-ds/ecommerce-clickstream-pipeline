@echo off
REM Windows launcher.
REM   run.bat                              start the web app
REM   run.bat test --quick                 fast checks
REM   run.bat pipeline --input file.csv    analyse a file without the browser
REM If "python" opens the Microsoft Store, install Python from python.org and tick "Add python.exe to PATH".
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py %*
) else (
  python run.py %*
)
exit /b %errorlevel%
