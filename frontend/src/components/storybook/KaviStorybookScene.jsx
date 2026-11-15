import { AmbientEffects, CelebrationLayer } from '../interactive/SceneEffects'

export default function KaviStorybookScene({
  pageIndex = 0,
  mood = 'idle',
  message = '',
  audioLevel = 0,
  motionLevel = 'full',
  walkingProgress = 0,
  picture,
  pictureAlt = 'கவி உங்களுடன் கதைப் பயணம் செல்லத் தயாராக இருக்கிறான்',
  effectProfile = { ambient: true, particles: 0, travel: false, durationMs: 0 },
}) {
  const safeAudioLevel = Math.max(0, Math.min(1, audioLevel))
  const safeWalkingProgress = Math.max(0, Math.min(1, walkingProgress))

  return (
    <figure
      className="storybook-scene kavi-story-scene kavi-picture-scene"
      data-testid="kavi-picture-scene"
      data-page={pageIndex + 1}
      data-mood={mood}
      data-motion={motionLevel}
      style={{ '--kavi-audio': safeAudioLevel, '--kavi-walk': safeWalkingProgress }}
    >
      <img
        key={picture}
        data-testid="kavi-story-picture"
        src={picture}
        alt={pictureAlt}
        draggable="false"
      />
      <figcaption className="sr-only">{message || pictureAlt}</figcaption>
      <AmbientEffects variant="river" enabled={effectProfile.ambient} />
      <div className="kavi-river-effects" aria-hidden="true">
        <i className="kavi-water-glint" />
        <i className="kavi-lotus" />
        <i className="kavi-stone" />
        <i className="kavi-dragonfly" />
      </div>
      {mood === 'encourage' ? <div className="kavi-retry-cue" aria-hidden="true"><i /><i /></div> : null}
      {mood === 'celebrate' ? (
        <div className="kavi-crossing-celebration" aria-hidden="true"><i className="kavi-rainbow" /></div>
      ) : null}
      <CelebrationLayer variant="river-stars" state={mood} effectProfile={mood === 'celebrate' ? effectProfile : { ...effectProfile, particles: 0 }} />
      <div className="kavi-picture-cue" data-mood={mood} aria-hidden="true">
        <span className="kavi-picture-cue__ring" />
        <span className="kavi-picture-cue__sparkle">✦</span>
        <span className="kavi-picture-cue__sparkle">✦</span>
      </div>
    </figure>
  )
}
