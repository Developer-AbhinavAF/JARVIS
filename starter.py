# windsurf ai don't touch it, it is temporary

import os
import time
import pyautogui
import webbrowser

os.system('start cmd /k "d: & cd /"')
time.sleep(1)
pyautogui.write(".\.venv\Scripts\Activate.ps1")
pyautogui.press("enter")
pyautogui.write("cd JARVIS/jarvis-desktop/backend", interval=0.01)
time.sleep(.5)
pyautogui.press("enter")
time.sleep(.4)
pyautogui.write("python app.py")
pyautogui.press("enter")
time.sleep(6)
# Press 'y' for FULL MODERN GUI MODE (with visualizer and pinkish theme)
pyautogui.hotkey("ctrl", "shift", "d")
time.sleep(.5)
pyautogui.write("d:")
pyautogui.press("enter")
time.sleep(.5)
pyautogui.write("cd JARVIS/jarvis-desktop/frontend")
pyautogui.press("enter")
time.sleep(.5)
pyautogui.write("npm run dev")
pyautogui.press("enter")
# After npm run dev, add this:
time.sleep(8)
pyautogui.hotkey("ctrl", "shift", "d")  # New terminal
time.sleep(.5)
pyautogui.write("d:")
pyautogui.press("enter")
time.sleep(.5)
pyautogui.write("cd JARVIS/jarvis-desktop")
pyautogui.press("enter")
time.sleep(.5)
pyautogui.write("npm run electron:dev")
pyautogui.press("enter")
time.sleep(5)
webbrowser.open("http://localhost:3000")
