import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, AbsoluteFill } from 'remotion';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

export const SceneComponent: React.FC<{ audioSrc: string }> = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, fps * 0.5], [0, 1], clamp);
  const subOpacity   = interpolate(frame, [fps * 0.7, fps * 1.2], [0, 1], clamp);

  return (
    <AbsoluteFill style={{ backgroundColor: '#1a1a2e', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24, fontFamily: 'sans-serif' }}>
      <div style={{ opacity: titleOpacity, color: '#CCFF00', fontSize: 48, fontWeight: 700 }}>
        Remotion Test
      </div>
      <div style={{ opacity: subOpacity, color: '#4FC3F7', fontSize: 24 }}>
        Rendering without Puppeteer
      </div>
    </AbsoluteFill>
  );
};
