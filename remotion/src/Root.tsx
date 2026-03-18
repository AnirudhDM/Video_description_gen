import React from 'react';
import { Composition } from 'remotion';
import { SceneComponent } from './compositions/garden_tree_equalization';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="garden-tree-equalization"
    component={SceneComponent}
    durationInFrames={3983}
    fps={30}
    width={1280}
    height={720}
    defaultProps={{ audioSrc: "/render_audio.wav" }}
  />
);
