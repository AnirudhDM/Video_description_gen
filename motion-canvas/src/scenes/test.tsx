import {makeScene2D, Rect, Txt} from '@motion-canvas/2d';
import {waitFor, createRef} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  view.fill('#1a1a2e');

  const box = createRef<Rect>();

  view.add(
    <Rect ref={box} width={400} height={200} radius={12} fill={'#16213e'} stroke={'#4FC3F7'} lineWidth={2} opacity={0}>
      <Txt text={'Motion Canvas Test'} fontSize={32} fill={'#CCFF00'} fontWeight={700} />
    </Rect>,
  );

  yield* box().opacity(1, 0.6);
  yield* waitFor(2);
});
