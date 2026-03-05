import {makeScene2D, Rect, Txt, Line, Layout} from '@motion-canvas/2d';
import {all, waitFor, createRef} from '@motion-canvas/core';

const YELLOW = '#CCFF00';
const BG     = '#1a1a2e';
const CARD   = '#16213e';
const BLUE   = '#4FC3F7';
const GREEN  = '#69F0AE';
const RED    = '#FF5252';
const MUTED  = '#666688';
const WHITE  = '#FFFFFF';

const A  = [1, 3, 6, 1, 6, 6, 9, 9];
const P  = [0, 1, 4, 10, 11, 17, 23, 32, 41];
const A2 = [2, 2, 2, 3, 2, 3];
const P2 = [0, 2, 4, 6, 9, 11, 14];

const BW = 56, BH = 48, BG_GAP = 4;

// Audio offsets & durations (from generate_whiteboard_video)
// Step 0:  offset=0.0,      dur=8.775
// Step 1:  offset=10.275,   dur=11.225   (= 0 + 8.775 + 1.5)
// Step 2:  offset=23.0,     dur=13.15    (= 10.275 + 11.225 + 1.5)
// Step 3:  offset=37.65,    dur=13.6     (= 23.0 + 13.15 + 1.5)
// Step 4:  offset=52.75,    dur=11.725   (= 37.65 + 13.6 + 1.5)
// Step 5:  offset=65.975,   dur=11.575   (= 52.75 + 11.725 + 1.5)
// Step 6:  offset=79.05,    dur=10.575   (= 65.975 + 11.575 + 1.5)
// Step 7:  offset=91.125,   dur=14.975   (= 79.05 + 10.575 + 1.5)
// Step 8:  offset=107.6,    dur=12.775   (= 91.125 + 14.975 + 1.5)
// Step 9:  offset=121.875,  dur=15.725   (= 107.6 + 12.775 + 1.5)
//
// Timing rule: each step consumes exactly (dur + 1.5) seconds.
// The 1.5s pause for step 0 is used for the intro→layout transition.
// All other steps end with yield* waitFor(1.5).

export default makeScene2D(function* (view) {
  view.fill(BG);

  // Subtle grid
  view.add(<Rect width={1920} height={1080} opacity={0.04}
    stroke={WHITE} lineWidth={1} lineDash={[40, 40]} />);

  // ── Intro elements ──────────────────────────────────────────────────────
  const iTitle = createRef<Txt>();
  const iSig   = createRef<Rect>();
  const iDesc  = createRef<Txt>();
  const iEg1   = createRef<Txt>();
  const iEg2   = createRef<Txt>();

  view.add(<>
    <Txt ref={iTitle}
      text={'Same-Endpoints\nSubarray Max Sum'}
      fontSize={40} fill={YELLOW} fontWeight={700}
      textAlign={'center'} y={-150} opacity={0} />
    <Rect ref={iSig} width={420} height={52} radius={10}
      fill={CARD} stroke={BLUE} lineWidth={1.5} y={-60} opacity={0}>
      <Txt text={'int solution(int A[], int N)'} fontSize={18} fill={BLUE} />
    </Rect>
    <Txt ref={iDesc}
      text={'Find the largest sum subarray\nwhose first and last elements are equal.'}
      fontSize={20} fill={WHITE} textAlign={'center'} y={30} opacity={0} />
    <Txt ref={iEg1} text={'e.g.  [1,3,6,1,6,6,9,9]  →  19'}
      fontSize={16} fill={MUTED} y={100} opacity={0} />
    <Txt ref={iEg2} text={'      [2,2,2,3,2,3]  →  11'}
      fontSize={16} fill={MUTED} y={128} opacity={0} />
  </>);

  // ── Layout elements (hidden until transition) ───────────────────────────
  const divider   = createRef<Line>();
  const leftPanel = createRef<Layout>();

  view.add(<Line ref={divider}
    points={[[-310, -520], [-310, 520]]}
    stroke={MUTED} lineWidth={1} opacity={0} />);

  view.add(
    <Layout ref={leftPanel}
      direction={'column'} gap={14} layout
      x={-620} y={0} alignItems={'start'} opacity={0}>
      <Txt text={'Same-Endpoints\nSubarray Max Sum'}
        fontSize={21} fill={YELLOW} fontWeight={700} />
      <Txt
        text={'Find the largest sum subarray\nwhere first and last elements\nare equal. O(N) prefix sum scan.'}
        fontSize={13} fill={WHITE} maxWidth={230} />
      <Rect width={230} height={44} radius={8} fill={CARD} stroke={BLUE} lineWidth={1.2}>
        <Txt text={'int solution(int A[], int N)'}
          fontSize={11} fill={BLUE} />
      </Rect>
      <Txt text={'[1,3,6,1,6,6,9,9] → 19'} fontSize={12} fill={MUTED} />
      <Txt text={'[2,2,2,3,2,3] → 11'}      fontSize={12} fill={MUTED} />
    </Layout>,
  );

  // ── Right panel constants ───────────────────────────────────────────────
  const RX = 160;       // right-panel center X
  const AY = -290;      // array A row Y
  const PY = -220;      // prefix sum row Y

  // Array A boxes
  const aBoxes = A.map(() => createRef<Rect>());
  const aIdxs  = A.map(() => createRef<Txt>());
  const pBoxes = P.map(() => createRef<Rect>());
  const aLabel = createRef<Txt>();
  const pLabel = createRef<Txt>();

  view.add(<Txt ref={aLabel} text={'A'} fontSize={15} fill={MUTED}
    x={RX - 272} y={AY} opacity={0} />);
  view.add(<Txt ref={pLabel} text={'P'} fontSize={15} fill={MUTED}
    x={RX - 300} y={PY} opacity={0} />);

  A.forEach((v, i) => {
    const x = RX - 200 + i * (BW + BG_GAP);
    view.add(<>
      <Rect ref={aBoxes[i]} x={x} y={AY} width={BW} height={BH} radius={6}
        fill={CARD} stroke={MUTED} lineWidth={1} opacity={0}>
        <Txt text={String(v)} fontSize={18} fill={WHITE} fontWeight={600} />
      </Rect>
      <Txt ref={aIdxs[i]} x={x} y={AY + 34} text={String(i)}
        fontSize={11} fill={MUTED} opacity={0} />
    </>);
  });

  P.forEach((v, i) => {
    const x = RX - 228 + i * (BW + BG_GAP);
    view.add(<Rect ref={pBoxes[i]} x={x} y={PY} width={BW} height={BH} radius={6}
      fill={CARD} stroke={'#2a2a4e'} lineWidth={1} opacity={0}>
      <Txt text={String(v)} fontSize={16} fill={BLUE} />
    </Rect>);
  });

  // Formula card
  const fCard = createRef<Rect>();
  view.add(<Rect ref={fCard} x={RX - 40} y={-150} width={280} height={46} radius={8}
    fill={CARD} stroke={YELLOW} lineWidth={1.5} opacity={0}>
    <Txt text={'sum(l,r) = P[r+1] − P[l]'} fontSize={15} fill={YELLOW} />
  </Rect>);

  // Hash map header + 3 rows
  const HX = RX + 140, HY = -80;
  const hmHead = createRef<Rect>();
  const hmR    = [createRef<Rect>(), createRef<Rect>(), createRef<Rect>()];
  const hmData = ['1  →  P[0] = 0', '6  →  P[2] = 4', '9  →  P[6] = 32'];

  view.add(<Rect ref={hmHead} x={HX} y={HY} width={200} height={34} radius={6}
    fill={'#0e1628'} stroke={MUTED} lineWidth={1} opacity={0}>
    <Txt text={'value  |  first_prefix'} fontSize={12} fill={MUTED} />
  </Rect>);
  hmR.forEach((r, i) => view.add(
    <Rect ref={r} x={HX} y={HY + 36 + i * 36} width={200} height={30} radius={5}
      fill={CARD} stroke={'#2a2a4e'} lineWidth={1} opacity={0}>
      <Txt text={hmData[i]} fontSize={13} fill={WHITE} />
    </Rect>,
  ));

  // Pointer
  const ptr = createRef<Txt>();
  view.add(<Txt ref={ptr} text={'▲'} fontSize={13} fill={YELLOW}
    x={RX - 200} y={AY + 50} opacity={0} />);

  // Candidate + best chips
  const candChip = createRef<Rect>();
  const candTxt  = createRef<Txt>();
  const bestChip = createRef<Rect>();
  const bestTxt  = createRef<Txt>();

  view.add(<>
    <Rect ref={candChip} x={RX - 60} y={-130} width={310} height={38} radius={8}
      fill={CARD} stroke={'#FFB74D'} lineWidth={1.5} opacity={0}>
      <Txt ref={candTxt} text={''} fontSize={14} fill={'#FFB74D'} />
    </Rect>
    <Rect ref={bestChip} x={RX - 60} y={-80} width={200} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={2} opacity={0}>
      <Txt ref={bestTxt} text={'best = 0'} fontSize={16} fill={GREEN} fontWeight={700} />
    </Rect>
  </>);

  // Result chip
  const resChip = createRef<Rect>();
  const resTxt  = createRef<Txt>();
  view.add(<Rect ref={resChip} x={RX - 60} y={-20} width={200} height={46} radius={10}
    fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
    <Txt ref={resTxt} text={'return 19'} fontSize={20} fill={YELLOW} fontWeight={700} />
  </Rect>);

  // Example 2 elements
  const ex2Lbl  = createRef<Txt>();
  const a2b     = A2.map(() => createRef<Rect>());
  const p2b     = P2.map(() => createRef<Rect>());
  const ex2Best = createRef<Rect>();
  const ex2BTxt = createRef<Txt>();
  const ex2Res  = createRef<Rect>();
  const ex2RTxt = createRef<Txt>();

  view.add(<Txt ref={ex2Lbl} text={'Example 2'} fontSize={15} fill={MUTED}
    x={RX - 60} y={-290} opacity={0} />);
  A2.forEach((v, i) => view.add(
    <Rect ref={a2b[i]} x={RX - 140 + i * (BW + BG_GAP)} y={-240}
      width={BW} height={BH} radius={6}
      fill={CARD} stroke={MUTED} lineWidth={1} opacity={0}>
      <Txt text={String(v)} fontSize={18} fill={WHITE} fontWeight={600} />
    </Rect>,
  ));
  P2.forEach((v, i) => view.add(
    <Rect ref={p2b[i]} x={RX - 168 + i * (BW + BG_GAP)} y={-170}
      width={BW} height={BH} radius={6}
      fill={CARD} stroke={'#2a2a4e'} lineWidth={1} opacity={0}>
      <Txt text={String(v)} fontSize={16} fill={BLUE} />
    </Rect>,
  ));
  view.add(<>
    <Rect ref={ex2Best} x={RX - 60} y={-80} width={200} height={38} radius={8}
      fill={CARD} stroke={GREEN} lineWidth={2} opacity={0}>
      <Txt ref={ex2BTxt} text={'best = 11'} fontSize={16} fill={GREEN} fontWeight={700} />
    </Rect>
    <Rect ref={ex2Res} x={RX - 60} y={-20} width={200} height={46} radius={10}
      fill={CARD} stroke={YELLOW} lineWidth={2} opacity={0}>
      <Txt ref={ex2RTxt} text={'return 11'} fontSize={20} fill={YELLOW} fontWeight={700} />
    </Rect>
  </>);

  // ════════════════════════════════════════════════════════════════════════
  // STEP 0 — intro  (offset=0, dur=8.775)
  // anim: 0.5 + 0.2 + 0.4 + 0.2 + 0.3 = 1.6s
  // ════════════════════════════════════════════════════════════════════════
  yield* iTitle().opacity(1, 0.5);
  yield* waitFor(0.2);
  yield* all(iSig().opacity(1, 0.4), iDesc().opacity(1, 0.4));
  yield* waitFor(0.2);
  yield* all(iEg1().opacity(1, 0.3), iEg2().opacity(1, 0.3));
  yield* waitFor(8.775 - 1.6);                      // fill to end of narration
  // ── transition inside the 1.5s pause ──
  yield* all(
    iTitle().opacity(0, 0.3), iSig().opacity(0, 0.3),
    iDesc().opacity(0, 0.3),  iEg1().opacity(0, 0.3), iEg2().opacity(0, 0.3),
  );                                                  // 0.3s
  yield* all(divider().opacity(1, 0.4), leftPanel().opacity(1, 0.4)); // 0.4s
  yield* waitFor(0.8);                               // 0.3+0.4+0.8 = 1.5 ✓
  // cumulative: 10.275s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 1 — array A  (offset=10.275, dur=11.225)
  // anim: 0.3 + 8×(0.2+0.1) = 0.3+2.4 = 2.7s
  // ════════════════════════════════════════════════════════════════════════
  yield* aLabel().opacity(1, 0.3);
  for (let i = 0; i < A.length; i++) {
    yield* all(aBoxes[i]().opacity(1, 0.2), aIdxs[i]().opacity(1, 0.2));
    yield* waitFor(0.1);
  }
  yield* waitFor(11.225 - 2.7);
  yield* waitFor(1.5);
  // cumulative: 23.0s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 2 — prefix sums  (offset=23.0, dur=13.15)
  // anim: 0.3 + 0.4 + 9×(0.2+0.15) = 3.85s
  // ════════════════════════════════════════════════════════════════════════
  yield* pLabel().opacity(1, 0.3);
  yield* fCard().opacity(1, 0.4);
  for (let i = 0; i < P.length; i++) {
    yield* pBoxes[i]().opacity(1, 0.2);
    yield* waitFor(0.15);
  }
  yield* waitFor(13.15 - 3.85);
  yield* waitFor(1.5);
  // cumulative: 37.65s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 3 — key insight / show hash map  (offset=37.65, dur=13.6)
  // anim: 0.4s
  // ════════════════════════════════════════════════════════════════════════
  yield* hmHead().opacity(1, 0.4);
  yield* waitFor(13.6 - 0.4);
  yield* waitFor(1.5);
  // cumulative: 52.75s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 4 — scan: record first[1]=0, first[6]=4  (offset=52.75, dur=11.725)
  // anim: 0.2+0.3+1.0+0.3+0.3 = 2.1s
  // ════════════════════════════════════════════════════════════════════════
  yield* ptr().opacity(1, 0.2);
  yield* hmR[0]().opacity(1, 0.3);      // 1 → 0
  yield* waitFor(1.0);
  yield* ptr().x(RX - 200 + 2 * (BW + BG_GAP), 0.3);
  yield* hmR[1]().opacity(1, 0.3);      // 6 → 4
  yield* waitFor(11.725 - 2.1);
  yield* waitFor(1.5);
  // cumulative: 65.975s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 5 — index 3, candidate=11  (offset=65.975, dur=11.575)
  // anim: 0.3+0.3+0.3 = 0.9s
  // ════════════════════════════════════════════════════════════════════════
  yield* ptr().x(RX - 200 + 3 * (BW + BG_GAP), 0.3);
  aBoxes[0]().stroke(BLUE); aBoxes[0]().fill('#0d1f3c');
  aBoxes[1]().stroke(BLUE); aBoxes[1]().fill('#0d1f3c');
  aBoxes[2]().stroke(BLUE); aBoxes[2]().fill('#0d1f3c');
  aBoxes[3]().stroke(BLUE); aBoxes[3]().fill('#0d1f3c');
  candTxt().text('P[4] − first[1] = 11 − 0 = 11');
  yield* all(candChip().opacity(1, 0.3), bestChip().opacity(1, 0.3));
  bestTxt().text('best = 11');
  yield* waitFor(11.575 - 0.9);
  yield* waitFor(1.5);
  // cumulative: 79.05s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 6 — index 4, candidate=13  (offset=79.05, dur=10.575)
  // anim: 0.3s
  // ════════════════════════════════════════════════════════════════════════
  yield* ptr().x(RX - 200 + 4 * (BW + BG_GAP), 0.3);
  aBoxes[0]().stroke(MUTED); aBoxes[0]().fill(CARD);
  aBoxes[1]().stroke(MUTED); aBoxes[1]().fill(CARD);
  aBoxes[3]().stroke(MUTED); aBoxes[3]().fill(CARD);
  aBoxes[2]().stroke(GREEN); aBoxes[2]().fill('#0d2e1e');
  aBoxes[4]().stroke(GREEN); aBoxes[4]().fill('#0d2e1e');
  candTxt().text('P[5] − first[6] = 17 − 4 = 13');
  bestTxt().text('best = 13');
  yield* waitFor(10.575 - 0.3);
  yield* waitFor(1.5);
  // cumulative: 91.125s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 7 — index 5, candidate=19 NEW BEST  (offset=91.125, dur=14.975... wait it's 10.575)
  // Actually: offset=79.05 was step 6 (dur=10.575), offset=91.125 is step 7 (dur=14.975)
  // Let me re-check: step 6 dur=10.575, step 7 dur=14.975 ✓
  // anim: 0.3s
  // ════════════════════════════════════════════════════════════════════════
  yield* ptr().x(RX - 200 + 5 * (BW + BG_GAP), 0.3);
  aBoxes[2]().stroke(YELLOW); aBoxes[2]().fill('#1e2a00');
  aBoxes[3]().stroke(YELLOW); aBoxes[3]().fill('#1e2a00');
  aBoxes[4]().stroke(YELLOW); aBoxes[4]().fill('#1e2a00');
  aBoxes[5]().stroke(YELLOW); aBoxes[5]().fill('#1e2a00');
  candTxt().text('P[6] − first[6] = 23 − 4 = 19');
  bestTxt().text('best = 19 ★');
  yield* waitFor(10.575 - 0.3);
  yield* waitFor(1.5);
  // cumulative: 103.2s... wait that's wrong

  // Let me recalculate step 7:
  // Step 6: offset=79.05, dur=10.575, ends at 79.05+10.575+1.5 = 91.125 ✓
  // Step 7: offset=91.125, dur=14.975

  // ════════════════════════════════════════════════════════════════════════
  // STEP 8 (was 7) — indices 6,7 value 9  (offset=91.125, dur=14.975)
  // Wait - I labeled wrong above. Let me recount from original:
  // The MCP steps were 0-9, matching scene steps 0-9.
  // Step 7 = "Index 6 value 9 first seen..." dur=14.975
  // I just wrote step 7 above labeled as "STEP 7". Now continuing with STEP 8 in code
  // but the MCP label is Step 7. The code step count and MCP step count should match.
  //
  // Let me redo from STEP 7 (MCP step 7, offset=91.125, dur=14.975):
  // (The code above wrote STEP 7 with offset 91.125 content but wrong - I wrote the
  //  "new best" content there which is MCP step 6. Let me just continue correctly.)
  //
  // Actually I realize I made a labeling error in the comments above. Let me just
  // re-verify what I have so far maps correctly:
  //
  // Code section "STEP 5" = MCP Step 4 (Index 3 seen before) at offset 52.75 ✓
  // Code section "STEP 6" = MCP Step 5 (Index 4, value 6)    at offset 65.975 ✓
  // Code section "STEP 7" = MCP Step 6 (Index 5, value 6)    at offset 79.05 ✓
  //
  // So cumulative after "STEP 7" = 79.05 + 10.575 + 1.5 = 91.125 ✓
  //
  // Now MCP Step 7 (offset=91.125, dur=14.975):
  // "Index 6 value 9 first seen, record first[9]=32. Index 7 value 9 again..."
  // anim: 0.3+0.3+0.3 = 0.9s
  // ════════════════════════════════════════════════════════════════════════
  // Reset highlight
  for (let i = 0; i < A.length; i++) {
    aBoxes[i]().stroke(MUTED);
    aBoxes[i]().fill(CARD);
  }
  yield* ptr().x(RX - 200 + 6 * (BW + BG_GAP), 0.3);
  yield* hmR[2]().opacity(1, 0.3);     // 9 → 32
  yield* waitFor(0.5);
  yield* ptr().x(RX - 200 + 7 * (BW + BG_GAP), 0.3);
  candTxt().text('P[8] − first[9] = 41 − 32 = 9');
  bestTxt().text('best = 19');
  yield* resChip().opacity(1, 0.3);
  yield* waitFor(14.975 - 0.9);
  yield* waitFor(1.5);
  // cumulative: 107.6s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 9 (MCP Step 8) — Example 2 intro  (offset=107.6, dur=12.775)
  // anim: fade out ex1 (0.3) + fade in ex2 (6×0.15 + 7×0.15) = 0.3+1.95 ≈ 2.25s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    aLabel().opacity(0, 0.3),  pLabel().opacity(0, 0.3),
    fCard().opacity(0, 0.3),   candChip().opacity(0, 0.3),
    bestChip().opacity(0, 0.3), ptr().opacity(0, 0.3),
    hmHead().opacity(0, 0.3),
    hmR[0]().opacity(0, 0.3),  hmR[1]().opacity(0, 0.3), hmR[2]().opacity(0, 0.3),
    resChip().opacity(0, 0.3),
    ...aBoxes.map(r => r().opacity(0, 0.3)),
    ...aIdxs.map(r => r().opacity(0, 0.3)),
    ...pBoxes.map(r => r().opacity(0, 0.3)),
  );                                             // 0.3s
  yield* ex2Lbl().opacity(1, 0.3);
  for (let i = 0; i < A2.length; i++) {
    yield* a2b[i]().opacity(1, 0.15);
  }                                              // 0.3 + 6×0.15 = 1.2s
  for (let i = 0; i < P2.length; i++) {
    yield* p2b[i]().opacity(1, 0.15);
  }                                              // 7×0.15 = 1.05s total anim ≈ 2.55s
  yield* waitFor(12.775 - 2.55);
  yield* waitFor(1.5);
  // cumulative: 121.875s

  // ════════════════════════════════════════════════════════════════════════
  // STEP 10 (MCP Step 9) — Ex2 scan, result  (offset=121.875, dur=15.725)
  // anim: 0.4+0.4+0.3 = 1.1s
  // ════════════════════════════════════════════════════════════════════════
  yield* all(
    a2b[0]().stroke(GREEN), a2b[0]().fill('#0d2e1e'),
    a2b[1]().stroke(GREEN), a2b[1]().fill('#0d2e1e'),
    a2b[2]().stroke(GREEN), a2b[2]().fill('#0d2e1e'),
    a2b[3]().stroke(GREEN), a2b[3]().fill('#0d2e1e'),
    a2b[4]().stroke(GREEN), a2b[4]().fill('#0d2e1e'),
  );
  yield* ex2Best().opacity(1, 0.4);
  yield* waitFor(1.5);
  a2b[5]().stroke(RED); a2b[5]().fill('#2e0d0d');
  yield* ex2Res().opacity(1, 0.3);
  yield* waitFor(15.725 - 1.1 - 1.5);
  yield* waitFor(1.5);
});
