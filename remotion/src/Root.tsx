import React from 'react';
import { Composition } from 'remotion';
import { SceneComponent } from './compositions/test';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="test"
    component={SceneComponent}
    durationInFrames={90}
    fps={30}
    width={1280}
    height={720}
    defaultProps={{ audioSrc: '' }}
  />
);
