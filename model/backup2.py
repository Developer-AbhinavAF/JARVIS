import subprocess
import time
import pyautogui as pg
import asyncio
import edge_tts
import pygame
import os

VOICE = "en-IN-PrabhatNeural"

pygame.mixer.init()


async def speak(text):
    filename = "temp.mp3"

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=VOICE
        )

        await communicate.save(filename)

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        pygame.mixer.music.unload()

    finally:
        if os.path.exists(filename):
            os.remove(filename)


async def main():
    await speak("Limit exceeded. doosre GPU mein shift kar raha hun, please kuch der apna haath keyboard aur mouse se door rakhe.")

asyncio.run(main())
chrome_path = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

url = "https://google.com/"

# profile = "Default"      # Ya "Default", "Profile 1", "Profile 2", etc.
profile = "Profile 3"

subprocess.Popen([
    chrome_path,
    f"--profile-directory={profile}",
    url
])

time.sleep(12)
pg.moveTo(430, 62, duration=.2)
time.sleep(2)
pg.write("colab", interval=.01)
time.sleep(.6)
pg.press("enter")
time.sleep(12)
pg.moveTo(700, 500, duration=.2)
pg.scroll(700)
time.sleep(1)
pg.moveTo(333, 175, duration=.2)
time.sleep(3)
pg.click()
time.sleep(22)
pg.hotkey("win", "m")
async def last():
    await speak("Saath dene ke liye dhanyavaad!. shifting complete ho gaya hai. ab aap apna kaam shuru kar sakte hain.")

asyncio.run(last())