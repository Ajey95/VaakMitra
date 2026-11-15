# Asset Placeholder Files

This directory contains all media assets for the SpeakEasy ASD application.

## Directory Structure

```
public/assets/
├── letters/           # Tamil letter images (அ, ஆ, ல, த)
│   ├── a.png         # Letter அ image
│   ├── aa.png        # Letter ஆ image
│   ├── la.png        # Letter ல image
│   └── ta.png        # Letter த image
│
├── words/            # Word images (அம்மா, அப்பா)
│   ├── amma.png      # Mother image
│   └── appa.png      # Father image
│
├── animations/       # Mouth animation GIFs
│   ├── a_mouth.gif
│   ├── aa_mouth.gif
│   ├── la_mouth.gif
│   ├── ta_mouth.gif
│   ├── amma_mouth.gif
│   └── appa_mouth.gif
│
├── sounds/           # Audio files
│   ├── letters/
│   │   ├── a.mp3
│   │   ├── aa.mp3
│   │   ├── la.mp3
│   │   └── ta.mp3
│   ├── words/
│   │   ├── amma.mp3
│   │   └── appa.mp3
│   ├── applause.mp3
│   ├── star_collect.mp3
│   ├── whoosh.mp3
│   └── ding.mp3
│
└── 3d/               # 3D models
    └── candle.glb    # Candle 3D model
```

## Fallback Behavior

All components include fallback mechanisms when assets are missing:

- **Images**: Fall back to emoji placeholders (📝 for letters, 👨 👩 for words)
- **Animations**: Fall back to CSS-animated SVG mouth shapes
- **Sounds**: Silent operation (no error thrown)
- **3D Models**: Fall back to procedural Three.js geometry

## Asset Requirements

### Images (PNG, 1024x1024)
- Transparent background
- High contrast, colorful
- Child-friendly illustrations

### Animations (GIF, 512x512)
- 1-2 second loop
- Clear mouth articulation
- Side profile view

### Audio (MP3, 44.1kHz)
- Clear native speaker pronunciation
- 1-3 seconds duration
- Normalized volume

### 3D Models (GLB)
- Low poly (< 10k vertices)
- PBR materials
- Centered at origin

## Temporary Placeholders

During development, components use:
- Emoji text (⭐ 🎯 📝)
- CSS gradients
- SVG shapes
- Procedural graphics

## Production Assets

Contact the design team for production-ready assets:
- **Designer**: Aditya Sharma
- **Email**: design.team96@amrita.edu
