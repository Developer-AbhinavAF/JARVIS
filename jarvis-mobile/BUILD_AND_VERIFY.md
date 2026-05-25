# Quick Build & Security Verification Guide

## 🏗️ Building the APK

### Prerequisites
- Android Studio installed
- Android SDK 35 or higher
- Gradle synced

### Step 1: Configure Environment
Your `.env` file from `D:\JARVIS\.env` will be used automatically. Make sure it contains API keys.

### Step 2: Build Debug APK
```bash
cd D:\JARVIS\jarvis-mobile
.\scripts\build-debug.ps1
```

**Output**: `app/build/outputs/apk/debug/app-debug.apk`

### Step 3: Install on Phone
```bash
# Option 1: Via ADB (requires phone connected)
.\scripts\build-debug.ps1 -Install

# Option 2: Manual
# Copy app/build/outputs/apk/debug/app-debug.apk to phone
# Open file manager and tap to install
```

## 🔒 Security Verification

### ✅ After Installation on Phone
1. **Check Permissions**: App should ask for:
   - ✅ Microphone (for voice mode)
   - ✅ Camera (for image analysis)
   - ✅ Notifications (for reminders)
   - ❌ Should NOT ask for suspicious/excessive permissions

2. **Check Security Warnings**: 
   - ❌ Should NOT show "app contains known malware"
   - ❌ Should NOT show "unverified app from risky developer"
   - ❌ Should NOT show "virus/security threat detected"

3. **Network Security**:
   - All API calls should use HTTPS
   - No cleartext traffic warnings

### 🔍 Technical Verification (Android Studio)
1. Open **Logcat** in Android Studio
2. Run the app and look for:
   - ✅ No security warnings
   - ✅ Normal app startup logs
   - ✅ Clean TLS handshakes for HTTPS calls

### 📦 Release APK with Signing

#### Step 1: Create Signing Key (First Time Only)
```bash
.\scripts\make-keystore.ps1
```
This creates `jarvis-mobile/keystore.jks` and `keystore.properties`

#### Step 2: Build Release APK
```bash
.\scripts\build-release.ps1
```

**Output**: `app/build/outputs/apk/release/app-release.apk`

#### Step 3: Verify Signing
```bash
jarsigner -verify -verbose app/build/outputs/apk/release/app-release.apk
```

Expected output:
```
- Signed by <key name>
- Digest algorithm: SHA-256
- Signature algorithm: RSA
```

## 🎯 Testing Checklist

After installation, verify:

### Functionality
- [ ] App launches without crashes
- [ ] Home tab shows device info
- [ ] Chat works (requires API keys)
- [ ] Voice mode works (tap Mic button)
- [ ] Tools tab loads action buttons
- [ ] Settings lets you add/edit API keys
- [ ] Dashboard shows phone stats
- [ ] Memory saves notes, todos, reminders

### Visual Appearance
- [ ] Dark theme applied (#050710 background)
- [ ] Pink accent color (#EC4899) on buttons
- [ ] Chat bubbles: Pink for user, Gray for assistant
- [ ] 12dp rounded corners on all elements
- [ ] Text is readable with good contrast
- [ ] No color bleeding or visual glitches

### Security
- [ ] No "Unknown app" warnings during install
- [ ] No "app contains malware" warnings
- [ ] No suspicious permission requests
- [ ] Settings > Apps > JARVIS Mobile shows no warnings

## 🐛 Troubleshooting

### "Build failed" error
```bash
# Clean and rebuild
gradlew clean
gradlew build
```

### "API keys not recognized"
1. Check `D:\JARVIS\.env` exists and has keys
2. Rebuild (keys are embedded at build time)
3. Or import keys in app Settings after installation

### "Cannot install APK"
- Uninstall existing app: `adb uninstall com.jarvis.mobile.debug`
- Try again with: `adb install -r app/build/outputs/apk/debug/app-debug.apk`

### App crashes on launch
1. Check Android logcat in Android Studio
2. Ensure all required permissions are granted
3. Check that API keys are valid

## 📱 Device Requirements
- **Minimum SDK**: Android 8.0 (API 26)
- **Target SDK**: Android 15 (API 35)
- **Architecture**: arm64-v8a, armeabi-v7a
- **RAM**: 2GB minimum
- **Storage**: ~100MB for APK + caches

## 🔗 Useful Commands

```bash
# List connected devices
adb devices

# View app logs in real-time
adb logcat | grep jarvis

# Uninstall app
adb uninstall com.jarvis.mobile.debug

# Check installed version
adb shell dumpsys package com.jarvis.mobile.debug | grep version
```

## 📚 Reference
- [Security Update Doc](./SECURITY_UI_UPDATE.md)
- [Main README](./README.md)
- [APK Build Steps](./APK_BUILD_STEPS.md)

---
*Last updated: 2026-05-25*