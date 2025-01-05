pip install pyinstaller

@REM ============ 1. compile without license ==============
@REM pyinstaller --onefile --collect-all selenium --add-data "ui/templates;ui/templates" --add-data "ui/static;ui/static" --add-data "src;src"  --add-data "config.py;." ui/app.py

@REM ============ 2. compile with license ==============
@REM pyinstaller --onefile --collect-all selenium  --collect-submodules ui --add-data "ui/templates;ui/templates" --add-data "ui/static;ui/static" --add-data "src;src"  --add-data "config.py;." license.py

@REM ============ 3. compile with license with icon ==============
pyinstaller --icon=src/img/dice.ico --onefile --collect-all selenium --collect-all selenium_stealth --collect-submodules ui --add-data "ui/templates;ui/templates" --add-data "ui/static;ui/static" --add-data "src;src"  --add-data "config.py;." license.py

@REM ============ 4. compile with license using license.spec==============
@REM pyinstaller license.spec