import React from 'react';
import {
  AbsoluteFill, Composition, Img, Sequence, interpolate,
  registerRoot, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import episode from '../episodes/ep01.json';
import visuals from '../episodes/ep01-visuals.json';

const FPS = 24;
const sceneCuts = episode.scenes.map(({start, end}) => ({
  from: Math.round(start * FPS),
  end: Math.round(end * FPS),
}));
const totalFrames = sceneCuts.at(-1).end;
const rain = Array.from({length: 44}, (_, index) => ({
  left: (index * 197) % 1080,
  phase: (index * 307) % 2080,
  speed: 21 + (index % 9) * 3,
  height: 35 + (index % 6) * 11,
}));

function Rain({frame}) {
  return <AbsoluteFill style={{overflow: 'hidden', opacity: 0.32}}>
    {rain.map(({left, phase, speed, height}) => (
      <div key={left} style={{
        position: 'absolute', left, top: (phase + frame * speed) % 2080 - 100,
        height, width: 2, transform: 'rotate(12deg)',
        background: 'linear-gradient(transparent, #a6d2e4)',
      }}/>
    ))}
  </AbsoluteFill>;
}

function Choices() {
  return <div style={{display: 'grid', gap: 18, marginTop: 36}}>
    {visuals.choices.map((choice, index) => (
      <div key={choice} style={{
        background: '#10242b', border: '2px solid #75949a', borderRadius: 20,
        padding: '22px 28px', display: 'flex', alignItems: 'center', gap: 24,
        fontSize: 43, fontWeight: 650,
      }}>
        <span style={{color: '#ffce85'}}>{index === 0 ? 'A' : 'B'}</span>{choice}
      </div>
    ))}
  </div>;
}

function Shot({scene, index, fixture, sceneArt}) {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.045]);
  const reveal = interpolate(frame, [0, 7], [16, 0], {extrapolateRight: 'clamp'});
  const ending = index === visuals.scenes.length - 1;

  return <AbsoluteFill style={{background: '#0a1a22', color: '#f5f7f4', fontFamily: 'Arial, sans-serif'}}>
    {fixture ? (
      <AbsoluteFill style={{
        background: 'radial-gradient(ellipse at 70% 27%, #295363, #0b1a24 72%)',
      }}>
        <div style={{
          position: 'absolute', top: 380, left: 280, width: 520, height: 470,
          border: '5px solid #669fac', borderRadius: 94, transform: 'rotate(-12deg)',
          display: 'grid', placeItems: 'center', color: '#bce6ea', fontSize: 125, fontWeight: 700,
        }}>{index + 1}</div>
      </AbsoluteFill>
    ) : (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: `scale(${scale})`}}>
          <Img src={staticFile(sceneArt?.file ?? visuals.reference)} style={sceneArt?.panel ? {
            position: 'absolute', width: '200%', height: '200%',
            left: `${-100 * sceneArt.panel[0]}%`, top: `${-100 * sceneArt.panel[1]}%`,
          } : {
            width: '100%', height: '100%', objectFit: sceneArt ? 'cover' : 'contain',
            objectPosition: 'center 28%',
          }}/>
        </AbsoluteFill>
      </AbsoluteFill>
    )}
    <Rain frame={frame}/>
    <AbsoluteFill style={{
      background: 'linear-gradient(180deg, #08151add, transparent 23%, transparent 41%, #08151af2 76%, #08151a 100%)',
    }}/>
    <div style={{position: 'absolute', left: 72, right: 72, top: 84, display: 'flex', justifyContent: 'space-between'}}>
      <strong style={{fontSize: 37, letterSpacing: 7}}>DUA JALAN</strong>
      <span style={{fontSize: 28, alignSelf: 'center', color: '#d2dfe0'}}>EPISODE 01</span>
    </div>
    {fixture && <div style={{
      position: 'absolute', top: 161, left: 72, color: '#ffce85',
      fontSize: 26, letterSpacing: 3, fontWeight: 700,
    }}>FIXTURE · UJI RENDER</div>}
    <div style={{
      position: 'absolute', left: 72, right: 72, bottom: 180,
      transform: `translateY(${reveal}px)`, textShadow: '0 4px 24px #08151a',
    }}>
      <div style={{color: scene.accent, fontSize: 28, letterSpacing: 6, fontWeight: 700}}>{scene.label}</div>
      <div style={{fontSize: ending ? 83 : 110, lineHeight: 0.97, fontWeight: 800, whiteSpace: 'pre-line', marginTop: 25}}>
        {scene.headline}
      </div>
      {ending && <Choices/>}
    </div>
  </AbsoluteFill>;
}

function Episode({fixture, sceneArt}) {
  return <AbsoluteFill>
    {visuals.scenes.map((scene, index) => {
      const {from, end} = sceneCuts[index];
      return <Sequence key={scene.label} from={from} durationInFrames={end - from}>
        <Shot scene={scene} index={index} fixture={fixture} sceneArt={sceneArt[index]}/>
      </Sequence>;
    })}
  </AbsoluteFill>;
}

function Root() {
  return <>
    <Composition id="Ep01" component={Episode} durationInFrames={totalFrames}
      fps={FPS} width={1080} height={1920} defaultProps={{fixture: false, sceneArt: []}}/>
    <Composition id="Ep01Fixture" component={Episode} durationInFrames={totalFrames}
      fps={FPS} width={1080} height={1920} defaultProps={{fixture: true, sceneArt: []}}/>
  </>;
}

registerRoot(Root);
