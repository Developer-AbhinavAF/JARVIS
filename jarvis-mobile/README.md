# JARVIS Mobile

Standalone lightweight Android version of `jarvis-desktop`.

This app does not call `localhost`, FastAPI, Electron, Python, or the desktop app. It uses Android-native UI, Android speech recognition/TTS, local storage, reminders, phone stats, and direct HTTP calls to the same external APIs configured by the desktop `.env`.

## What is included

- Chat assistant with OpenRouter, four Groq key slots, or Gemini fallback.
- Speech mode with Android speech recognition and TextToSpeech.
- Weather, forecast, news, stocks, crypto, YouTube, Tavily/search, translation, image generation, QR, Wikipedia, dictionary, books, anime, space news, countries, holidays, GitHub, Reddit, recipes, movies, games, quotes, jokes, facts, geocode, currency, podcast search, API tester, JSON formatter, and ping.
- Image Vision/OCR through Gemini Vision.
- File AI for text-like files such as txt, md, json, csv, and logs.
- Local notes, todos, chat history, reminders, logs, and Android dashboard stats.
- Settings screen for importing or editing API keys on the phone.

Desktop-only actions such as PC process control, terminal execution, silent screenshots, and screen recording are represented with Android-safe equivalents or clear permission-aware messages. The app remains independent and phone-safe.

## API keys

The Android build reads keys in this order:

1. Values saved inside the app Settings screen.
2. `jarvis-mobile/.env`
3. `D:\JARVIS\.env`

That means your existing desktop env is used during build, but the phone app does not need `jarvis-desktop` to run.

To keep secrets out of git, `.env` is ignored. Use `.env.example` as the template.

## Build

Open `D:\JARVIS\jarvis-mobile` in Android Studio and run the `app` configuration.

For full click-by-click APK instructions, see `APK_BUILD_STEPS.md`.

CLI build, after installing Android SDK and Gradle:

```powershell
cd D:\JARVIS\jarvis-mobile
.\scripts\build-debug.ps1
```

Install on a connected phone:

```powershell
.\scripts\build-debug.ps1 -Install
```

The debug APK will be created at:

```text
D:\JARVIS\jarvis-mobile\app\build\outputs\apk\debug\app-debug.apk
```

Copy that APK to your Android phone and install it, or use Android Studio/adb.

Signed release helpers are included:

```powershell
.\scripts\make-keystore.ps1
.\scripts\build-release.ps1
```

## Notes

- `GEMINI_API_KEY` is required for image Vision/OCR.
- `OPENROUTER_API_KEY`, any `GROQ_API_KEY` slot, or `GEMINI_API_KEY` is required for chat.
- `TAVILY_API_KEY` enables stronger web search. Without it, the app falls back to DuckDuckGo instant answers.
- Games now use CheapShark without a key.
- Some APIs are keyless, but weather, news, stocks, YouTube, SerpAPI, Tavily, TMDB, and Resend need their matching keys.
- API keys embedded at build time are present inside the APK. For private use this may be acceptable; for publishing, use a backend or enter keys only on-device.
