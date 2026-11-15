import { getPippinExpression } from '../../features/pippin/pippinExpression'

export default function PippinStorybook({ mood = 'idle', audioLevel = 0, motionLevel = 'full', message = '' }) {
  const expression = getPippinExpression(mood, audioLevel)
  return (
    <div className="pippin-story-scene" data-testid="pippin-storybook" data-motion={motionLevel}>
      <svg
        data-testid="pippin-story-svg"
        data-mood={mood}
        viewBox="0 0 640 520"
        role="img"
        aria-labelledby="pippin-svg-title pippin-svg-desc"
        style={{ '--pippin-audio': Math.max(0, Math.min(1, audioLevel)) }}
      >
        <title id="pippin-svg-title">Smiling kitten Pippin / சிரிக்கும் குட்டிப் பூனை பிப்பின்</title>
        <desc id="pippin-svg-desc">{message || 'Pippin is ready to listen / பிப்பின் உங்களைக் கேட்கத் தயாராக இருக்கிறது.'}</desc>
        <defs>
          <linearGradient id="pippin-room" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#fff4e7" /><stop offset="1" stopColor="#e8f8ff" /></linearGradient>
          <filter id="pippin-shadow"><feDropShadow dx="0" dy="9" stdDeviation="8" floodColor="#694f4b" floodOpacity=".18" /></filter>
        </defs>
        <rect width="640" height="520" rx="40" fill="url(#pippin-room)" />
        <path d="M0 398Q160 350 322 401T640 390V520H0Z" fill="#b7e2c5" />
        <g className="pippin-stars" data-active={['dance', 'sing', 'repeating'].includes(mood) ? 'true' : 'false'} aria-hidden="true">
          <path d="M100 118v30m-15-15h30M520 92v34m-17-17h34M542 225v24m-12-12h24" />
        </g>
        <g className="pippin-character" filter="url(#pippin-shadow)">
          <ellipse cx="314" cy="438" rx="137" ry="22" fill="#55434d" opacity=".13" />
          <g data-testid="pippin-tail" data-state={expression.tail} className="pippin-tail">
            <path d="M410 369q112 21 103-76-4-45-43-36-26 6-11 31" fill="none" stroke="#f4a66f" strokeWidth="40" strokeLinecap="round" />
            <path d="M410 369q112 21 103-76-4-45-43-36-26 6-11 31" fill="none" stroke="#774e45" strokeWidth="7" strokeLinecap="round" />
          </g>
          <g data-testid="pippin-body" data-state={expression.body} className="pippin-body">
            <ellipse cx="315" cy="349" rx="119" ry="103" fill="#f4a66f" stroke="#774e45" strokeWidth="8" />
            <path d="M232 287q83 64 168 0v35q-85 58-168 0z" fill="#65c4bc" stroke="#356f70" strokeWidth="7" />
            <path d="M293 317l22 36 23-36" fill="#ffd65b" stroke="#8d6634" strokeWidth="6" strokeLinejoin="round" />
          </g>
          <g className="pippin-head">
            <g data-testid="pippin-ears" data-state={expression.ears} className="pippin-ears">
              <path d="M206 154l20-88 74 56m124 32-19-88-76 56" fill="#f4a66f" stroke="#774e45" strokeWidth="8" strokeLinejoin="round" />
              <path d="M226 101l-5 46 39-25m145-21 5 46-40-25" fill="#ffc1b0" />
            </g>
            <ellipse cx="315" cy="204" rx="120" ry="104" fill="#f8b27c" stroke="#774e45" strokeWidth="8" />
            <path d="M278 126q38 25 75 0M254 142l-30-21m151 21 30-21" fill="none" stroke="#fff0d6" strokeWidth="13" strokeLinecap="round" />
          </g>
          <g data-testid="pippin-eyes" data-state={expression.blink} className="pippin-eyes">
            <ellipse cx="273" cy="192" rx="24" ry="29" fill="#fffdf7" /><ellipse cx="356" cy="192" rx="24" ry="29" fill="#fffdf7" />
            <ellipse cx="278" cy="198" rx="10" ry="15" fill="#4d704d" /><ellipse cx="361" cy="198" rx="10" ry="15" fill="#4d704d" />
            <circle cx="281" cy="193" r="4" fill="#fff" /><circle cx="364" cy="193" r="4" fill="#fff" />
            <path className="pippin-eyelids" d="M250 177q23-20 46 0M333 177q23-20 46 0" fill="none" stroke="#774e45" strokeWidth="8" strokeLinecap="round" />
          </g>
          <g className="pippin-cheeks" data-state={expression.face} aria-hidden="true">
            <ellipse cx="245" cy="235" rx="17" ry="9" fill="#ef8290" opacity=".38" />
            <ellipse cx="385" cy="235" rx="17" ry="9" fill="#ef8290" opacity=".38" />
          </g>
          <path d="M302 226q13-10 26 0l-13 12z" fill="#d96f79" stroke="#774e45" strokeWidth="5" strokeLinejoin="round" />
          <g data-testid="pippin-mouth" data-state={expression.face} className="pippin-mouth">
            <path className="pippin-smile" d="M315 238q-2 21-25 18m25-18q2 21 25 18" fill="none" stroke="#774e45" strokeWidth="7" strokeLinecap="round" />
            <ellipse className="pippin-talk-mouth" cx="315" cy="256" rx="20" ry="13" fill="#75404c" />
          </g>
          <g className="pippin-whiskers" stroke="#774e45" strokeWidth="5" strokeLinecap="round">
            <path d="M245 236l-69-13m69 31-71 13m211-31 69-13m-69 31 71 13" />
          </g>
          <g data-testid="pippin-paws" data-state={expression.paws} className="pippin-paws">
            <path d="M242 385q-8 42 9 55h54l4-64m78 9q8 42-9 55h-54l-4-64" fill="#f0a06a" stroke="#774e45" strokeWidth="8" strokeLinejoin="round" />
          </g>
        </g>
        <g className="pippin-notes" data-active={mood === 'sing' ? 'true' : 'false'} aria-hidden="true" fill="#7058c9">
          <text x="100" y="240" fontSize="54">♪</text><text x="495" y="185" fontSize="66">♫</text>
        </g>
      </svg>
    </div>
  )
}
