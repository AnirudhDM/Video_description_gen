import {makeScene2D, Rect, Txt, Line, Layout} from '@motion-canvas/2d';
import {all, waitFor, createRef} from '@motion-canvas/core';

const YELLOW = '#CCFF00';
const BG     = '#1a1a2e';
const CARD   = '#16213e';
const BLUE   = '#4FC3F7';
const GREEN  = '#69F0AE';
const ORANGE = '#FFB74D';
const MUTED  = '#666688';
const WHITE  = '#FFFFFF';

// Step timings (offset / dur / ends):
// 0:  0.0       / 13.775 / 15.275
// 1:  15.275    / 12.35  / 29.125
// 2:  29.125    / 15.775 / 46.4
// 3:  46.4      / 16.5   / 64.4
// 4:  64.4      / 16.35  / 82.25
// 5:  82.25     / 15.45  / 99.2
// 6:  99.2      / 13.975 / 114.675
// 7:  114.675   / 14.6   / 130.775

const RX = 160;
const BW = 62, BH = 50;

export default makeScene2D(function* (view) {
  view.fill(BG);
  view.add(<Rect width={1920} height={1080} opacity={0.04}
    stroke={WHITE} lineWidth={1} lineDash={[40, 40]} />);

  // ── Intro ─────────────────────────────────────────────────────────────
  const iTitle = createRef<Txt>();
  const iSig   = createRef<Rect>();
  const iDesc  = createRef<Txt>();
  const iEg1   = createRef<Txt>();
  const iEg2   = createRef<Txt>();
  const iEg3   = createRef<Txt>();

  view.add(<>
    <Txt ref={iTitle} text={'Garden Tree\nEqualization'}
      fontSize={40} fill={YELLOW} fontWeight={700} textAlign={'center'} y={-150} opacity={0} />
    <Rect ref={iSig} width={380} height={52} radius={10}
      fill={CARD} stroke={BLUE} lineWidth={1.5} y={-60} opacity={0}>
      <Txt text={'int solution(int A[], int N)'} fontSize={18} fill={BLUE} />
    </Rect>
    <Txt ref={iDesc} text={'Minimize plant/move actions to\nequalize all section tree counts.'}
      fontSize={20} fill={WHITE} textAlign={'center'} y={30} opacity={0} />
    <Txt ref={iEg1} text={'e.g.  [1,2,2,4]  →  4'} fontSize={16} fill={MUTED} y={100} opacity={0} />
    <Txt ref={iEg2} text={'      [4,2,4,6]  →  2'} fontSize={16} fill={MUTED} y={128} opacity={0} />
    <Txt ref={iEg3} text={'      [1,1,2,1]  →  3'} fontSize={16} fill={MUTED} y={156} opacity={0} />
  </>);

  // ── Layout chrome ──────────────────────────────────────────────────────
  const divider   = createRef<Line>();
  const leftPanel = createRef<Layout>();

  view.add(<Line ref={divider}
    points={[[-310, -520], [-310, 520]]}
    stroke={MUTED} lineWidth={1} opacity={0} />);

  view.add(
    <Layout ref={leftPanel} direction={'column'} gap={14} layout
      x={-620} y={0} alignItems={'start'} opacity={0}>
      <Txt text={'Garden Tree\nEqualization'} fontSize={21} fill={YELLOW} fontWeight={700} />
      <Txt text={'Minimize plant or move actions\nto equalize all N section\ntree counts. No removal allowed.'}
        fontSize={13} fill={WHITE} maxWidth={230} />
      <Rect width={230} height={44} radius={8} fill={CARD} stroke={BLUE} lineWidth={1.2}>
        <Txt text={'int solution(int A[], int N)'} fontSize={11} fill={BLUE} />
      </Rect>
      <Txt text={'[1,2,2,4] → 4'} fontSize={12} fill={MUTED} />
      <Txt text={'[4,2,4,6] → 2'} fontSize={12} fill={MUTED} />
      <Txt text={'[1,1,2,1] → 3'} fontSize={12} fill={MUTED} />
    </Layout>
  );

  // ── Step 1: array A1 + action icons ───────────────────────────────────
  const A1 = [1, 2, 2, 4];
  const a1Boxes = A1.map(() => createRef<Rect>());
  const a1Idxs  = A1.map(() => createRef<Txt>());
  const a1Label  = createRef<Txt>();
  const plantIcon = createRef<Rect>();
  const moveIcon  = createRef<Rect>();

  view.add(<Txt ref={a1Label} text={'A ='} fontSize={16} fill={MUTED}
    x={RX - 185} y={-300} opacity={0} />);
  A1.forEach((v, i) => {
    const x = RX - 100 + i * (BW + 8);
    view.add(<>
      <Rect ref={a1Boxes[i]} x={x} y={-300} width={BW} height={BH} radius={6}
        fill={CARD} stroke={MUTED} lineWidth={1} opacity={0}>
        <Txt text={String(v)} fontSize={22} fill={WHITE} fontWeight={600} />
      </Rect>
      <Txt ref={a1Idxs[i]} x={x} y={-263} text={String(i)} fontSize={12} fill={MUTED} opacity={0} />
    </>);
  });
  view.add(<>
    <Rect ref={plantIcon} x={RX - 60} y={-200} width={160} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={1.5} opacity={0}>
      <Txt text={'+ plant new tree'} fontSize={15} fill={GREEN} />
    </Rect>
    <Rect ref={moveIcon} x={RX + 120} y={-200} width={200} height={38} radius={8}
      fill={CARD} stroke={BLUE} lineWidth={1.5} opacity={0}>
      <Txt text={'↔ move between sections'} fontSize={14} fill={BLUE} />
    </Rect>
  </>);

  // ── Step 2: sum/T chips ────────────────────────────────────────────────
  const sumCard       = createRef<Rect>();
  const tCard         = createRef<Rect>();
  const constraintLbl = createRef<Txt>();

  view.add(<>
    <Rect ref={sumCard} x={RX - 20} y={-200} width={300} height={42} radius={8}
      fill={CARD} stroke={MUTED} lineWidth={1.2} opacity={0}>
      <Txt text={'sum(A) = 9,  N = 4'} fontSize={16} fill={WHITE} />
    </Rect>
    <Rect ref={tCard} x={RX - 20} y={-140} width={300} height={42} radius={8}
      fill={CARD} stroke={YELLOW} lineWidth={1.5} opacity={0}>
      <Txt text={'T = ⌈9 / 4⌉ = 3'} fontSize={16} fill={YELLOW} />
    </Rect>
    <Txt ref={constraintLbl} text={'T ≥ ⌈sum / N⌉  (cannot remove trees)'}
      fontSize={14} fill={BLUE} x={RX - 20} y={-80} opacity={0} />
  </>);

  // ── Step 3: formula ────────────────────────────────────────────────────
  const plantedCard = createRef<Rect>();
  const plantedNote = createRef<Txt>();
  const excessCard  = createRef<Rect>();
  const totalCard   = createRef<Rect>();

  view.add(<>
    <Rect ref={plantedCard} x={RX - 20} y={-120} width={340} height={42} radius={8}
      fill={CARD} stroke={ORANGE} lineWidth={1.5} opacity={0}>
      <Txt text={'planted = N×T − sum(A)'} fontSize={15} fill={ORANGE} />
    </Rect>
    <Txt ref={plantedNote} text={'larger T → more planted → minimize T'}
      fontSize={13} fill={MUTED} x={RX - 20} y={-62} opacity={0} />
    <Rect ref={excessCard} x={RX - 20} y={0} width={360} height={42} radius={8}
      fill={CARD} stroke={ORANGE} lineWidth={1.5} opacity={0}>
      <Txt text={'excess = Σ max(0, A[K] − T)'} fontSize={14} fill={ORANGE} />
    </Rect>
    <Rect ref={totalCard} x={RX - 20} y={70} width={360} height={48} radius={10}
      fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
      <Txt text={'total = excess + planted'} fontSize={18} fill={YELLOW} fontWeight={700} />
    </Rect>
  </>);

  // ── Step 4: example 1 detail ───────────────────────────────────────────
  const ex1Header  = createRef<Txt>();
  const ex1TCard   = createRef<Rect>();
  const ex1ExcCard = createRef<Rect>();
  const ex1PltCard = createRef<Rect>();
  const ex1ResCard = createRef<Rect>();

  view.add(<>
    <Txt ref={ex1Header} text={'Example 1: A = [1, 2, 2, 4]'}
      fontSize={16} fill={WHITE} x={RX - 20} y={-230} opacity={0} />
    <Rect ref={ex1TCard} x={RX - 20} y={-170} width={280} height={38} radius={8}
      fill={CARD} stroke={YELLOW} lineWidth={1.5} opacity={0}>
      <Txt text={'T = ⌈9/4⌉ = 3'} fontSize={15} fill={YELLOW} />
    </Rect>
    <Rect ref={ex1ExcCard} x={RX - 20} y={-118} width={320} height={38} radius={8}
      fill={CARD} stroke={ORANGE} lineWidth={1.5} opacity={0}>
      <Txt text={'excess = max(0, 4−3) = 1'} fontSize={14} fill={ORANGE} />
    </Rect>
    <Rect ref={ex1PltCard} x={RX - 20} y={-66} width={320} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={1.5} opacity={0}>
      <Txt text={'planted = 4×3 − 9 = 3'} fontSize={14} fill={GREEN} />
    </Rect>
    <Rect ref={ex1ResCard} x={RX - 20} y={10} width={240} height={50} radius={10}
      fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
      <Txt text={'return 4'} fontSize={24} fill={YELLOW} fontWeight={700} />
    </Rect>
  </>);

  // ── Step 5: example 2 ─────────────────────────────────────────────────
  const A2 = [4, 2, 4, 6];
  const a2Boxes = A2.map(() => createRef<Rect>());
  const ex2Header  = createRef<Txt>();
  const ex2TCard   = createRef<Rect>();
  const ex2ExcCard = createRef<Rect>();
  const ex2PltCard = createRef<Rect>();
  const ex2ResCard = createRef<Rect>();

  A2.forEach((v, i) => {
    const x = RX - 100 + i * (BW + 8);
    view.add(<Rect ref={a2Boxes[i]} x={x} y={-300} width={BW} height={BH} radius={6}
      fill={CARD} stroke={MUTED} lineWidth={1} opacity={0}>
      <Txt text={String(v)} fontSize={22} fill={WHITE} fontWeight={600} />
    </Rect>);
  });
  view.add(<>
    <Txt ref={ex2Header} text={'Example 2: A = [4, 2, 4, 6]'}
      fontSize={16} fill={WHITE} x={RX - 20} y={-230} opacity={0} />
    <Rect ref={ex2TCard} x={RX - 20} y={-170} width={280} height={38} radius={8}
      fill={CARD} stroke={YELLOW} lineWidth={1.5} opacity={0}>
      <Txt text={'T = 16/4 = 4'} fontSize={15} fill={YELLOW} />
    </Rect>
    <Rect ref={ex2ExcCard} x={RX - 20} y={-118} width={320} height={38} radius={8}
      fill={CARD} stroke={ORANGE} lineWidth={1.5} opacity={0}>
      <Txt text={'excess = max(0, 6−4) = 2'} fontSize={14} fill={ORANGE} />
    </Rect>
    <Rect ref={ex2PltCard} x={RX - 20} y={-66} width={320} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={1.5} opacity={0}>
      <Txt text={'planted = 4×4 − 16 = 0'} fontSize={14} fill={GREEN} />
    </Rect>
    <Rect ref={ex2ResCard} x={RX - 20} y={10} width={240} height={50} radius={10}
      fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
      <Txt text={'return 2'} fontSize={24} fill={YELLOW} fontWeight={700} />
    </Rect>
  </>);

  // ── Step 6: example 3 ─────────────────────────────────────────────────
  const A3 = [1, 1, 2, 1];
  const a3Boxes = A3.map(() => createRef<Rect>());
  const ex3Header  = createRef<Txt>();
  const ex3TCard   = createRef<Rect>();
  const ex3ExcCard = createRef<Rect>();
  const ex3PltCard = createRef<Rect>();
  const ex3ResCard = createRef<Rect>();

  A3.forEach((v, i) => {
    const x = RX - 100 + i * (BW + 8);
    view.add(<Rect ref={a3Boxes[i]} x={x} y={-300} width={BW} height={BH} radius={6}
      fill={CARD} stroke={MUTED} lineWidth={1} opacity={0}>
      <Txt text={String(v)} fontSize={22} fill={WHITE} fontWeight={600} />
    </Rect>);
  });
  view.add(<>
    <Txt ref={ex3Header} text={'Example 3: A = [1, 1, 2, 1]'}
      fontSize={16} fill={WHITE} x={RX - 20} y={-230} opacity={0} />
    <Rect ref={ex3TCard} x={RX - 20} y={-170} width={280} height={38} radius={8}
      fill={CARD} stroke={YELLOW} lineWidth={1.5} opacity={0}>
      <Txt text={'T = ⌈5/4⌉ = 2'} fontSize={15} fill={YELLOW} />
    </Rect>
    <Rect ref={ex3ExcCard} x={RX - 20} y={-118} width={320} height={38} radius={8}
      fill={CARD} stroke={ORANGE} lineWidth={1.5} opacity={0}>
      <Txt text={'excess = 0  (none exceed T=2)'} fontSize={14} fill={ORANGE} />
    </Rect>
    <Rect ref={ex3PltCard} x={RX - 20} y={-66} width={320} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={1.5} opacity={0}>
      <Txt text={'planted = 4×2 − 5 = 3'} fontSize={14} fill={GREEN} />
    </Rect>
    <Rect ref={ex3ResCard} x={RX - 20} y={10} width={240} height={50} radius={10}
      fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
      <Txt text={'return 3'} fontSize={24} fill={YELLOW} fontWeight={700} />
    </Rect>
  </>);

  // ── Step 7: algorithm code ─────────────────────────────────────────────
  const algoLabel = createRef<Txt>();
  const algoCard  = createRef<Rect>();

  view.add(<>
    <Txt ref={algoLabel} text={'O(N) time  ·  O(1) space'}
      fontSize={15} fill={GREEN} x={RX - 20} y={-230} opacity={0} />
    <Rect ref={algoCard} x={RX - 20} y={-50} width={430} height={220} radius={10}
      fill={'#0e1628'} stroke={BLUE} lineWidth={1.5} opacity={0}>
      <Layout direction={'column'} gap={7} padding={18} layout alignItems={'start'}>
        <Txt text={'long sum = 0;'} fontSize={13} fill={MUTED} fontFamily={'monospace'} />
        <Txt text={'for (k=0..N-1) sum += A[k];'} fontSize={13} fill={MUTED} fontFamily={'monospace'} />
        <Txt text={'long T = (sum + N - 1) / N;'} fontSize={13} fill={YELLOW} fontFamily={'monospace'} />
        <Txt text={''} fontSize={5} fill={WHITE} />
        <Txt text={'long excess = 0;'} fontSize={13} fill={MUTED} fontFamily={'monospace'} />
        <Txt text={'for (k=0..N-1)'} fontSize={13} fill={MUTED} fontFamily={'monospace'} />
        <Txt text={'  if (A[k]>T) excess += A[k]-T;'} fontSize={13} fill={ORANGE} fontFamily={'monospace'} />
        <Txt text={''} fontSize={5} fill={WHITE} />
        <Txt text={'return excess + N*T - sum;'} fontSize={14} fill={YELLOW} fontFamily={'monospace'} fontWeight={700} />
      </Layout>
    </Rect>
  </>);

  // ════════════════════════════════════════════════════════════════════════
  // STEP 0 — intro  (dur=13.775)
  // anim=1.6s  fill=12.175s  transition in 1.5s pause
  // ════════════════════════════════════════════════════════════════════════
  yield* iTitle().opacity(1, 0.5);
  yield* waitFor(0.2);
  yield* all(iSig().opacity(1, 0.4), iDesc().opacity(1, 0.4));
  yield* waitFor(0.2);
  yield* all(iEg1().opacity(1, 0.3), iEg2().opacity(1, 0.3), iEg3().opacity(1, 0.3));
  yield* waitFor(12.175);
  yield* all(
    iTitle().opacity(0, 0.3), iSig().opacity(0, 0.3), iDesc().opacity(0, 0.3),
    iEg1().opacity(0, 0.3),   iEg2().opacity(0, 0.3), iEg3().opacity(0, 0.3),
  );
  yield* all(divider().opacity(1, 0.4), leftPanel().opacity(1, 0.4));
  yield* waitFor(0.8);
  // cumulative: 15.275s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 1 — array A + action icons  (dur=12.35)
  // anim=1.8s  fill=10.55s
  // ════════════════════════════════════════════════════════════════════════
  yield* a1Label().opacity(1, 0.3);
  for (let i = 0; i < A1.length; i++) {
    yield* all(a1Boxes[i]().opacity(1, 0.2), a1Idxs[i]().opacity(1, 0.2));
    yield* waitFor(0.1);
  }
  yield* all(plantIcon().opacity(1, 0.3), moveIcon().opacity(1, 0.3));
  yield* waitFor(10.55);
  yield* waitFor(1.5);
  // cumulative: 29.125s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 2 — T = ceil(sum/N)  (dur=15.775)
  // anim=1.0s  fill=14.775s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(plantIcon().opacity(0, 0.2), moveIcon().opacity(0, 0.2));
  yield* all(sumCard().opacity(1, 0.4), tCard().opacity(1, 0.4));
  yield* constraintLbl().opacity(1, 0.4);
  yield* waitFor(14.775);
  yield* waitFor(1.5);
  // cumulative: 46.4s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 3 — formula  (dur=16.5)
  // anim=1.9s  fill=14.6s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(sumCard().opacity(0, 0.3), tCard().opacity(0, 0.3), constraintLbl().opacity(0, 0.3));
  yield* plantedCard().opacity(1, 0.4);
  yield* plantedNote().opacity(1, 0.4);
  yield* excessCard().opacity(1, 0.4);
  yield* totalCard().opacity(1, 0.4);
  yield* waitFor(14.6);
  yield* waitFor(1.5);
  // cumulative: 64.4s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 4 — example 1 detail  (dur=16.35)
  // anim=1.9s  fill=14.45s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    plantedCard().opacity(0, 0.3), plantedNote().opacity(0, 0.3),
    excessCard().opacity(0, 0.3),  totalCard().opacity(0, 0.3),
  );
  yield* ex1Header().opacity(1, 0.3);
  a1Boxes[3]().stroke(ORANGE);
  a1Boxes[3]().fill('#2e1a00');
  yield* ex1TCard().opacity(1, 0.3);
  yield* ex1ExcCard().opacity(1, 0.3);
  yield* ex1PltCard().opacity(1, 0.3);
  yield* ex1ResCard().opacity(1, 0.4);
  yield* waitFor(14.45);
  yield* waitFor(1.5);
  // cumulative: 82.25s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 5 — example 2  (dur=15.45)
  // anim=2.5s  fill=12.95s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    a1Label().opacity(0, 0.3),
    ...a1Boxes.map(r => r().opacity(0, 0.3)),
    ...a1Idxs.map(r => r().opacity(0, 0.3)),
    ex1Header().opacity(0, 0.3), ex1TCard().opacity(0, 0.3),
    ex1ExcCard().opacity(0, 0.3), ex1PltCard().opacity(0, 0.3),
    ex1ResCard().opacity(0, 0.3),
  );
  yield* ex2Header().opacity(1, 0.3);
  for (let i = 0; i < A2.length; i++) {
    yield* a2Boxes[i]().opacity(1, 0.15);
  }
  a2Boxes[3]().stroke(ORANGE);
  a2Boxes[3]().fill('#2e1a00');
  yield* ex2TCard().opacity(1, 0.3);
  yield* ex2ExcCard().opacity(1, 0.3);
  yield* ex2PltCard().opacity(1, 0.3);
  yield* ex2ResCard().opacity(1, 0.4);
  yield* waitFor(12.95);
  yield* waitFor(1.5);
  // cumulative: 99.2s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 6 — example 3  (dur=13.975)
  // anim=2.5s  fill=11.475s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    ...a2Boxes.map(r => r().opacity(0, 0.3)),
    ex2Header().opacity(0, 0.3), ex2TCard().opacity(0, 0.3),
    ex2ExcCard().opacity(0, 0.3), ex2PltCard().opacity(0, 0.3),
    ex2ResCard().opacity(0, 0.3),
  );
  yield* ex3Header().opacity(1, 0.3);
  for (let i = 0; i < A3.length; i++) {
    yield* a3Boxes[i]().opacity(1, 0.15);
  }
  yield* ex3TCard().opacity(1, 0.3);
  yield* ex3ExcCard().opacity(1, 0.3);
  yield* ex3PltCard().opacity(1, 0.3);
  yield* ex3ResCard().opacity(1, 0.4);
  yield* waitFor(11.475);
  yield* waitFor(1.5);
  // cumulative: 114.675s ✓

  // ════════════════════════════════════════════════════════════════════════
  // STEP 7 — algorithm code  (dur=14.6)
  // anim=1.0s  fill=13.6s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    ...a3Boxes.map(r => r().opacity(0, 0.3)),
    ex3Header().opacity(0, 0.3), ex3TCard().opacity(0, 0.3),
    ex3ExcCard().opacity(0, 0.3), ex3PltCard().opacity(0, 0.3),
    ex3ResCard().opacity(0, 0.3),
  );
  yield* algoLabel().opacity(1, 0.3);
  yield* algoCard().opacity(1, 0.4);
  yield* waitFor(13.6);
  yield* waitFor(1.5);
  // cumulative: 130.775s ✓
});
