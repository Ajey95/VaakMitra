# TalkingPet

TalkingPet is an original, standalone talking-cat experience for the final-year project. Pippin listens in supported browsers, repeats the phrase using the browser speech engine, and provides a typed fallback when microphone recognition is unavailable.

## Run locally

```powershell
cd C:\final_year_project\TalkingPet
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) in Chrome or Edge. Allow microphone access, tap the microphone, and speak. If speech recognition is unavailable, type a phrase and press **Repeat**.

## Verify and build

```powershell
npm test -- --run
npm run build
```

The app is frontend-only and can be deployed as a static Vite site. The character and interface are original project assets; this folder does not include third-party Talking Tom branding or assets.
