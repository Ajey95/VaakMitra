# SpeakEasy — Android App 🎤⭐

A colorful, animation-rich native **Android** companion app for the SpeakEasy ASD
speech-therapy platform, built for children. It talks to the **same FastAPI backend
and MongoDB Atlas database** as the web app — no backend changes required.

Built with **Kotlin + Jetpack Compose** (Material 3).

## Features
- 🎨 Animated multicolor gradient UI throughout, bouncy buttons, confetti, floating shapes
- 👋 Onboarding → Register / Login (real JWT auth against your backend)
- 🏠 Playful home dashboard with animated stats (stars, sessions, mastered lessons)
- 📚 Lessons fetched live from `/api/therapy/lessons` (Tamil letters & words)
- 🎤 Practice screen: **listen (TTS) → record → AI speech evaluation** via `/api/evaluate/speech`,
  with animated star rewards + confetti; results saved to Atlas via `/api/progress/save`
- 🌬️ Candle-blow mini-game that reacts to real microphone breath (fully on-device)
- 📈 Progress charts and 🏆 unlockable reward badges
- 👤 Profile + logout

## Architecture
- `data/` — Retrofit + Moshi models, API service, `SessionManager` (JWT in DataStore)
- `viewmodel/` — `AuthViewModel`, `AppViewModel` (coroutines + StateFlow)
- `ui/screens/` — one Composable per screen
- `ui/components/` — reusable animated widgets (gradient bg, confetti, buttons, fields)
- `audio/` — `VoiceRecorder` (MediaRecorder: upload + live amplitude)

## Connecting to the backend
The base URL comes from `BuildConfig.BASE_URL` and defaults to **`http://10.0.2.2:8000/`**
— the Android **emulator's** alias for your PC's `localhost`, where FastAPI runs. So:

1. Start the backend on your PC:
   ```powershell
   cd C:\final_year_project\backend
   $env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Run the app on an **emulator** (Android Studio → Device Manager → create/launch a Pixel API 34).

### Running on a physical phone instead
Pass your PC's LAN IP at build time — no source edit needed:
```powershell
.\gradlew assembleDebug -PbackendUrl=http://192.168.1.5:8000/
```
Start the backend with `--host 0.0.0.0` so the phone can reach it. Phone and PC must be
on the same Wi-Fi. (Debug builds permit cleartext to any host; release builds restrict it.)

## Build / Run
```powershell
# from C:\final_year_project\SpeakEasyAndroid
.\gradlew.bat assembleDebug      # builds app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat installDebug       # installs to a running emulator/device
```
Or just open the `SpeakEasyAndroid` folder in **Android Studio** and press ▶.

## Deploy (release build)
```powershell
.\gradlew.bat assembleRelease    # unsigned; configure a signing key for Play Store
```
For the Play Store, generate a keystore and add a `signingConfig` in `app/build.gradle.kts`,
then run `.\gradlew.bat bundleRelease` to produce an `.aab`.

— Team 96, Amrita Vishwa Vidyapeetham
