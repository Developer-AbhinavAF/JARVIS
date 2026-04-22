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
time.sleep(2)
pyautogui.write("python -m jarvis.main")
pyautogui.press("enter")
time.sleep(2)
# Press 'y' for FULL MODERN GUI MODE (with visualizer and pinkish theme)
pyautogui.write("y")
pyautogui.press("enter")
