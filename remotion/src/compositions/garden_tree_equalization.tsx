import React from 'react';
import {
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  AbsoluteFill,
  Audio,
  Sequence,
} from 'remotion';

// ── Colors ────────────────────────────────────────────────────────────────
const YELLOW   = '#CCFF00';
const BG       = '#1a1a2e';
const CARD     = '#16213e';
const BLUE     = '#4FC3F7';
const GREEN    = '#69F0AE';
const ORANGE   = '#FFB74D';
const MUTED    = '#666688';
const WHITE    = '#FFFFFF';
const DARK_BG  = '#0e1628';

// ── Step timing (seconds) ─────────────────────────────────────────────────
// Scene offsets (include 1.5s silent pauses between steps)
const S = [0, 15.275, 29.125, 46.4, 64.4, 82.25, 99.2, 114.675];
// WAV start times (TTS-only WAV, no pauses)
const W = [0, 13.775, 26.125, 41.9, 58.4, 74.75, 90.2, 104.175];
const D = [13.775, 12.35, 15.775, 16.5, 16.35, 15.45, 13.975, 14.6];

// ── Layout constants (1280×720 pixels) ───────────────────────────────────
const RCENTER  = 800;  // center x of right panel
const RCHIP_L  = RCENTER - 160; // left edge for 320px chips

// Array box layout helpers
const BW = 62, BH = 50, BGAP = 8;
const arrLeft = (n: number) => RCENTER - (n * (BW + BGAP) - BGAP) / 2;

export const SceneComponent: React.FC<{ audioSrc: string }> = ({ audioSrc }) => {
  const frame   = useCurrentFrame();
  const { fps } = useVideoConfig();
  const clamp   = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

  // Fade in/out helpers
  const fi = (s: number, d = 0.3) =>
    interpolate(frame, [s * fps, (s + d) * fps], [0, 1], clamp);
  const fo = (s: number, d = 0.3) =>
    interpolate(frame, [s * fps, (s + d) * fps], [1, 0], clamp);
  // Element visible from startS to hideS (or forever if hideS omitted)
  const op = (startS: number, hideS?: number, d = 0.3): number =>
    hideS !== undefined
      ? interpolate(frame, [startS * fps, (startS + d) * fps, hideS * fps, (hideS + d) * fps],
          [0, 1, 1, 0], clamp)
      : interpolate(frame, [startS * fps, (startS + d) * fps], [0, 1], clamp);

  // ── Reusable style helpers ────────────────────────────────────────────
  const chip = (border: string, h = 42): React.CSSProperties => ({
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    backgroundColor: CARD, border: `1.5px solid ${border}`,
    borderRadius: 8, height: h, padding: '0 16px',
  });

  const arrayBox = (border = MUTED, bg = CARD): React.CSSProperties => ({
    width: BW, height: BH, backgroundColor: bg,
    border: `1.5px solid ${border}`, borderRadius: 6,
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  });

  // ── Helpers: should a step's content be visible? ──────────────────────
  const inStep = (stepIdx: number) => frame >= S[stepIdx] * fps;
  const TRANS  = S[0] + D[0]; // 13.775s — end of step 0 narration → transition

  return (
    <AbsoluteFill style={{
      backgroundColor: BG,
      fontFamily: 'system-ui, -apple-system, Arial, sans-serif',
      overflow: 'hidden',
    }}>

      {/* ── Audio: one Sequence per step for precise sync ──────────────── */}
      {S.map((sceneOffset, i) => (
        <Sequence key={i} from={Math.round(sceneOffset * fps)}>
          <Audio
            src={audioSrc}
            startFrom={Math.round(W[i] * fps)}
            endAt={Math.round((W[i] + D[i]) * fps)}
          />
        </Sequence>
      ))}

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* PHASE 1 — INTRO (full screen, centered)                         */}
      {/* ════════════════════════════════════════════════════════════════ */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 22,
        opacity: op(0, TRANS),
      }}>
        <div style={{
          opacity: fi(0, 0.5), color: YELLOW, fontSize: 40, fontWeight: 700,
          textAlign: 'center', lineHeight: 1.25,
        }}>
          Garden Tree<br />Equalization
        </div>
        <div style={{ opacity: fi(0.7, 0.4), ...chip(BLUE, 50), paddingLeft: 24, paddingRight: 24 }}>
          <span style={{ color: BLUE, fontSize: 18 }}>int solution(int A[], int N)</span>
        </div>
        <div style={{
          opacity: fi(0.7, 0.4), color: WHITE, fontSize: 18,
          textAlign: 'center', lineHeight: 1.55,
        }}>
          Minimize plant/move actions to<br />equalize all section tree counts.
        </div>
        <div style={{ opacity: fi(1.1, 0.3), color: MUTED, fontSize: 15, lineHeight: 1.9, textAlign: 'center' }}>
          <div>e.g. [1,2,2,4] → 4</div>
          <div>[4,2,4,6] → 2</div>
          <div>[1,1,2,1] → 3</div>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* PHASE 2 — LAYOUT CHROME                                         */}
      {/* ════════════════════════════════════════════════════════════════ */}

      {/* Vertical divider */}
      <div style={{
        position: 'absolute', left: 320, top: 0, width: 1, height: 720,
        backgroundColor: MUTED, opacity: op(TRANS + 0.3),
      }} />

      {/* Left panel */}
      <div style={{
        position: 'absolute', left: 15, top: 0, width: 285, height: 720,
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        gap: 14, padding: '0 10px',
        opacity: op(TRANS + 0.3),
      }}>
        <div style={{ color: YELLOW, fontSize: 20, fontWeight: 700, lineHeight: 1.3 }}>
          Garden Tree<br />Equalization
        </div>
        <div style={{ color: WHITE, fontSize: 12, lineHeight: 1.65 }}>
          Minimize plant or move actions<br />to equalize all N section<br />tree counts. No removal allowed.
        </div>
        <div style={{ ...chip(BLUE, 40), justifyContent: 'flex-start', padding: '0 10px' }}>
          <span style={{ color: BLUE, fontSize: 11 }}>int solution(int A[], int N)</span>
        </div>
        <div style={{ color: MUTED, fontSize: 11, lineHeight: 1.9 }}>
          <div>[1,2,2,4] → 4</div>
          <div>[4,2,4,6] → 2</div>
          <div>[1,1,2,1] → 3</div>
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════ */}
      {/* RIGHT PANEL                                                      */}
      {/* ════════════════════════════════════════════════════════════════ */}

      {/* ── Array A1 = [1,2,2,4]  visible steps 1–4 ────────────────── */}
      <div style={{
        position: 'absolute', top: 42, left: arrLeft(4) - 50,
        display: 'flex', alignItems: 'center', gap: 8,
        opacity: op(S[1], S[5]),
      }}>
        <span style={{ color: MUTED, fontSize: 14, width: 42, textAlign: 'right' }}>A =</span>
        {[1, 2, 2, 4].map((v, i) => {
          const highlight = i === 3 && inStep(4);
          return (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
              <div style={arrayBox(highlight ? ORANGE : MUTED, highlight ? '#2e1a00' : CARD)}>
                <span style={{ color: WHITE, fontSize: 22, fontWeight: 600 }}>{v}</span>
              </div>
              <span style={{ color: MUTED, fontSize: 11 }}>{i}</span>
            </div>
          );
        })}
      </div>

      {/* ── STEP 1: action icons ─────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 120, left: 380,
        display: 'flex', gap: 16, opacity: op(S[1] + 0.3, S[2]),
      }}>
        <div style={{ ...chip(GREEN, 38), padding: '0 16px' }}>
          <span style={{ color: GREEN, fontSize: 14 }}>+ plant new tree</span>
        </div>
        <div style={{ ...chip(BLUE, 38), padding: '0 16px' }}>
          <span style={{ color: BLUE, fontSize: 13 }}>↔ move between sections</span>
        </div>
      </div>

      {/* ── STEP 2: sum/T + constraint ───────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 120, left: RCHIP_L,
        width: 320, display: 'flex', flexDirection: 'column', gap: 12,
        opacity: op(S[2], S[3]),
      }}>
        <div style={chip(MUTED)}>
          <span style={{ color: WHITE, fontSize: 15 }}>sum(A) = 9,  N = 4</span>
        </div>
        <div style={chip(YELLOW)}>
          <span style={{ color: YELLOW, fontSize: 15 }}>T = ⌈9 / 4⌉ = 3</span>
        </div>
        <div style={{
          opacity: fi(S[2] + 0.8),
          color: BLUE, fontSize: 13, textAlign: 'center', marginTop: 4,
        }}>
          T ≥ ⌈sum / N⌉  (cannot remove trees)
        </div>
      </div>

      {/* ── STEP 3: formula ──────────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 100, left: RCHIP_L - 20,
        width: 360, display: 'flex', flexDirection: 'column', gap: 14,
        opacity: op(S[3], S[4]),
      }}>
        <div style={chip(ORANGE)}>
          <span style={{ color: ORANGE, fontSize: 14 }}>planted = N×T − sum(A)</span>
        </div>
        <div style={{ opacity: fi(S[3] + 0.4), color: MUTED, fontSize: 12, textAlign: 'center' }}>
          larger T → more planted → minimize T
        </div>
        <div style={{ opacity: fi(S[3] + 0.8), ...chip(ORANGE) }}>
          <span style={{ color: ORANGE, fontSize: 13 }}>excess = Σ max(0, A[K] − T)</span>
        </div>
        <div style={{ opacity: fi(S[3] + 1.2), ...chip(YELLOW, 50), borderWidth: 2 }}>
          <span style={{ color: YELLOW, fontSize: 18, fontWeight: 700 }}>total = excess + planted</span>
        </div>
      </div>

      {/* ── STEP 4: example 1 detail ─────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 120, left: RCHIP_L,
        width: 320, display: 'flex', flexDirection: 'column', gap: 12,
        opacity: op(S[4], S[5]),
      }}>
        <div style={{ color: WHITE, fontSize: 15, textAlign: 'center', marginBottom: 4 }}>
          Example 1: A = [1, 2, 2, 4]
        </div>
        <div style={chip(YELLOW, 38)}>
          <span style={{ color: YELLOW, fontSize: 14 }}>T = ⌈9/4⌉ = 3</span>
        </div>
        <div style={{ opacity: fi(S[4] + 0.4), ...chip(ORANGE, 38) }}>
          <span style={{ color: ORANGE, fontSize: 13 }}>excess = max(0, 4−3) = 1</span>
        </div>
        <div style={{ opacity: fi(S[4] + 0.8), ...chip(GREEN, 38) }}>
          <span style={{ color: GREEN, fontSize: 13 }}>planted = 4×3 − 9 = 3</span>
        </div>
        <div style={{ opacity: fi(S[4] + 1.2), ...chip(YELLOW, 50), borderWidth: 2, marginTop: 4 }}>
          <span style={{ color: YELLOW, fontSize: 22, fontWeight: 700 }}>return 4</span>
        </div>
      </div>

      {/* ── STEP 5: array A2 + example 2 detail ─────────────────────── */}
      <div style={{
        position: 'absolute', top: 42, left: arrLeft(4) - 50,
        display: 'flex', alignItems: 'center', gap: 8,
        opacity: op(S[5], S[6]),
      }}>
        <span style={{ color: MUTED, fontSize: 14, width: 42, textAlign: 'right' }}>A =</span>
        {[4, 2, 4, 6].map((v, i) => (
          <div key={i} style={arrayBox(i === 3 ? ORANGE : MUTED, i === 3 ? '#2e1a00' : CARD)}>
            <span style={{ color: WHITE, fontSize: 22, fontWeight: 600 }}>{v}</span>
          </div>
        ))}
      </div>
      <div style={{
        position: 'absolute', top: 120, left: RCHIP_L,
        width: 320, display: 'flex', flexDirection: 'column', gap: 12,
        opacity: op(S[5], S[6]),
      }}>
        <div style={{ color: WHITE, fontSize: 15, textAlign: 'center', marginBottom: 4 }}>
          Example 2: A = [4, 2, 4, 6]
        </div>
        <div style={chip(YELLOW, 38)}>
          <span style={{ color: YELLOW, fontSize: 14 }}>T = 16/4 = 4</span>
        </div>
        <div style={{ opacity: fi(S[5] + 0.4), ...chip(ORANGE, 38) }}>
          <span style={{ color: ORANGE, fontSize: 13 }}>excess = max(0, 6−4) = 2</span>
        </div>
        <div style={{ opacity: fi(S[5] + 0.8), ...chip(GREEN, 38) }}>
          <span style={{ color: GREEN, fontSize: 13 }}>planted = 4×4 − 16 = 0</span>
        </div>
        <div style={{ opacity: fi(S[5] + 1.2), ...chip(YELLOW, 50), borderWidth: 2, marginTop: 4 }}>
          <span style={{ color: YELLOW, fontSize: 22, fontWeight: 700 }}>return 2</span>
        </div>
      </div>

      {/* ── STEP 6: array A3 + example 3 detail ─────────────────────── */}
      <div style={{
        position: 'absolute', top: 42, left: arrLeft(4) - 50,
        display: 'flex', alignItems: 'center', gap: 8,
        opacity: op(S[6], S[7]),
      }}>
        <span style={{ color: MUTED, fontSize: 14, width: 42, textAlign: 'right' }}>A =</span>
        {[1, 1, 2, 1].map((v, i) => (
          <div key={i} style={arrayBox()}>
            <span style={{ color: WHITE, fontSize: 22, fontWeight: 600 }}>{v}</span>
          </div>
        ))}
      </div>
      <div style={{
        position: 'absolute', top: 120, left: RCHIP_L,
        width: 320, display: 'flex', flexDirection: 'column', gap: 12,
        opacity: op(S[6], S[7]),
      }}>
        <div style={{ color: WHITE, fontSize: 15, textAlign: 'center', marginBottom: 4 }}>
          Example 3: A = [1, 1, 2, 1]
        </div>
        <div style={chip(YELLOW, 38)}>
          <span style={{ color: YELLOW, fontSize: 14 }}>T = ⌈5/4⌉ = 2</span>
        </div>
        <div style={{ opacity: fi(S[6] + 0.4), ...chip(ORANGE, 38) }}>
          <span style={{ color: ORANGE, fontSize: 13 }}>excess = 0  (none exceed T=2)</span>
        </div>
        <div style={{ opacity: fi(S[6] + 0.8), ...chip(GREEN, 38) }}>
          <span style={{ color: GREEN, fontSize: 13 }}>planted = 4×2 − 5 = 3</span>
        </div>
        <div style={{ opacity: fi(S[6] + 1.2), ...chip(YELLOW, 50), borderWidth: 2, marginTop: 4 }}>
          <span style={{ color: YELLOW, fontSize: 22, fontWeight: 700 }}>return 3</span>
        </div>
      </div>

      {/* ── STEP 7: algorithm code ────────────────────────────────────── */}
      <div style={{
        position: 'absolute', top: 80, left: RCENTER - 220, width: 440,
        display: 'flex', flexDirection: 'column', gap: 14,
        opacity: op(S[7]),
      }}>
        <div style={{ color: GREEN, fontSize: 14, textAlign: 'center', letterSpacing: 1 }}>
          O(N) time  ·  O(1) space
        </div>
        <div style={{
          backgroundColor: DARK_BG, border: `1.5px solid ${BLUE}`,
          borderRadius: 10, padding: '18px 22px',
          display: 'flex', flexDirection: 'column', gap: 7,
        }}>
          {([
            ['long sum = 0;', MUTED],
            ['for (k=0..N-1) sum += A[k];', MUTED],
            ['long T = (sum + N - 1) / N;', YELLOW],
            [' ', MUTED],
            ['long excess = 0;', MUTED],
            ['for (k=0..N-1)', MUTED],
            ['  if (A[k] > T) excess += A[k]-T;', ORANGE],
            [' ', MUTED],
            ['return excess + N*T - sum;', YELLOW],
          ] as [string, string][]).map(([line, color], i) => (
            <div key={i} style={{
              color, fontSize: 13,
              fontFamily: 'Courier New, Courier, monospace',
              fontWeight: line.startsWith('return') ? 700 : 400,
            }}>
              {line}
            </div>
          ))}
        </div>
      </div>

    </AbsoluteFill>
  );
};
