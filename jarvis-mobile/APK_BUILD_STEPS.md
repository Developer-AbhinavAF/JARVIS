# Build APK Step By Step

Use these steps on Windows from `D:\JARVIS\jarvis-mobile`.

## 1. Install Android Studio

Download Android Studio from the official Android Developers page:

https://developer.android.com/studio

During setup, keep these selected:

- Android SDK
- Android SDK Platform
- Android Virtual Device
- Android SDK Build-Tools

After Android Studio opens, let it finish downloading SDK components.

## 2. Open The Project

1. Open Android Studio.
2. Choose `Open`.
3. Select `D:\JARVIS\jarvis-mobile`.
4. Wait for Gradle sync to finish.

If Android Studio asks to install missing SDK/build tools, accept it.

## 3. Check API Keys

The project reads keys from:

1. `jarvis-mobile/.env`
2. `D:\JARVIS\.env`
3. Values entered later inside app Settings

Your existing root `.env` should already work during the build. To use a mobile-specific file:

1. Copy `.env.example` to `.env`.
2. Paste your keys.
3. Never commit `.env`.

For chat, set at least one:

- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `GROQ_API_KEY2`
- `GROQ_API_KEY3`
- `GROQ_API_KEY4`
- `GEMINI_API_KEY`

For OCR/Vision, set:

- `GEMINI_API_KEY`

For stronger web search, set:

- `TAVILY_API_KEY`

## 4. Build A Debug APK

Debug APK is easiest for personal phone testing.

### Android Studio

1. Click `Build`.
2. Click `Build Bundle(s) / APK(s)`.
3. Click `Build APK(s)`.
4. When the build finishes, click `locate`.

Expected output:

```text
D:\JARVIS\jarvis-mobile\app\build\outputs\apk\debug\app-debug.apk
```

### PowerShell

If Gradle is installed or Android Studio created `gradlew.bat`:

```powershell
cd D:\JARVIS\jarvis-mobile
.\scripts\build-debug.ps1
```

## 5. Install On Your Android Phone

### Method A: Copy APK

1. Copy `app-debug.apk` to your phone.
2. Open it from the phone file manager.
3. Allow install from unknown sources if Android asks.
4. Install and open `JARVIS Mobile`.

### Method B: USB Install

1. Enable Developer Options on phone.
2. Enable USB Debugging.
3. Connect phone by USB.
4. Run:

```powershell
cd D:\JARVIS\jarvis-mobile
.\scripts\build-debug.ps1 -Install
```

## 6. Build A Signed Release APK

Release APK is better for long-term personal use.

1. Create a keystore:

```powershell
cd D:\JARVIS\jarvis-mobile
.\scripts\make-keystore.ps1
```

2. Build release:

```powershell
.\scripts\build-release.ps1
```

Expected output:

```text
D:\JARVIS\jarvis-mobile\app\build\outputs\apk\release\app-release.apk
```

Keep `jarvis-mobile-release.jks` and `keystore.properties` safe. If you lose the keystore, you cannot update an app installed with that same release signature.

Official signing reference:

https://developer.android.com/studio/publish/app-signing

## 7. First Run Checklist

Inside the app:

1. Open `Settings`.
2. Confirm keys show as `set` or masked values.
3. If keys are missing, tap `Import .env Text` and paste your `.env`.
4. Open `Chat` and ask a simple question.
5. Open `Voice`, grant microphone permission, and tap `Listen`.
6. Open `Tools` and test:
   - Weather
   - Daily Brief
   - OCR Image
   - File AI
   - System Stats

## Troubleshooting

### Gradle was not found

Open the folder in Android Studio first. Android Studio usually sets up Gradle for you. If you want CLI-only builds, install Gradle and Android SDK platform tools.

### SDK not found

In Android Studio:

1. Open `Settings`.
2. Go to `Languages & Frameworks > Android SDK`.
3. Install Android SDK Platform 35 or newer build tools available in your SDK manager.

### Chat says no AI key configured

Set `OPENROUTER_API_KEY`, any `GROQ_API_KEY` slot, or `GEMINI_API_KEY` in `.env`, rebuild, or paste the keys in app Settings.

### OCR/Image AI says Gemini key required

Set `GEMINI_API_KEY`.

### App installs but network tools fail

Check phone internet, API key validity, and provider limits.
