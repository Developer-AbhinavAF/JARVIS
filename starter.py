# windsurf ai don't touch it, it is temporary

import os
import time
import pyautogui

os.system('start cmd /k "d: & cd /"')
time.sleep(1)
pyautogui.write("cd JARVIS", interval=0.01)
time.sleep(.6)
pyautogui.press("enter")
pyautogui.write(".\.venv\Scripts\Activate.ps1")
pyautogui.press("enter")
time.sleep(1.4)
pyautogui.write("python -m jarvis.main")
pyautogui.press("enter")
time.sleep(2)
# Press 'g' for GUI mode
pyautogui.write("g")
pyautogui.press("enter")
