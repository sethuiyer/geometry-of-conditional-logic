import { useState } from "react";

// ── EXACT NUMBERS FROM THE WALKTHROUGH ────────────────────────────────
// Cores: [C0=prime5, C1=prime7, C2=prime11], P=385
// Initial: P1→C0 (res=1), P2→C1 (res=2), P3→C2 (res=3) → z=366
// Locks: C0, C1 (warm cache) → M=5×7=35
// P3 blocks, P4 needs C2, new residue=4
// k=6, Δz=35×6=210, z'=576 mod 385=191
// Verify: 191 mod 5=1✓ 191 mod 7=2✓ 191 mod 11=4✓

const STEPS = [
  {
    id: "init",
    label: "INITIAL STATE",
    subtitle: "3 cores, 3 processes running. Encode as CRT coordinate.",
    z: 366,
    cores: [
      { id: 0, prime: 5,  process: "P1", residue: 1, state: "running", locked: false },
      { id: 1, prime: 7,  process: "P2", residue: 2, state: "running", locked: false },
      { id: 2, prime: 11, process: "P3", residue: 3, state: "running", locked: false },
    ],
    highlight: null,
  },
  {
    id: "lock",
    label: "LOCK WARM CACHES",
    subtitle: "P1 and P2 are hot in L1/L2. Commit their cores. M = 5×7 = 35.",
    z: 366,
    cores: [
      { id: 0, prime: 5,  process: "P1", residue: 1, state: "hot",     locked: true  },
      { id: 1, prime: 7,  process: "P2", residue: 2, state: "hot",     locked: true  },
      { id: 2, prime: 11, process: "P3", residue: 3, state: "running", locked: false },
    ],
    highlight: "M = 5 × 7 = 35 — cache-affinity shield",
    Mval: 35,
  },
  {
    id: "block",
    label: "P3 BLOCKS ON I/O",
    subtitle: "Core2 is now free. P4 arrives and needs to run. New residue = 4.",
    z: 366,
    cores: [
      { id: 0, prime: 5,  process: "P1", residue: 1, state: "hot",     locked: true  },
      { id: 1, prime: 7,  process: "P2", residue: 2, state: "hot",     locked: true  },
      { id: 2, prime: 11, process: "P3", residue: 3, state: "blocked", locked: false },
    ],
    highlight: "Geometric ELSE branch: compute exact displacement, preserve locked cores",
    Mval: 35,
  },
  {
    id: "repair",
    label: "CRT REPAIR JUMP",
    subtitle: "z′ = z + k·M. Solve for k. No global reschedule needed.",
    z: 366,
    zPrime: 191,
    delta: 210,
    k: 6,
    Mval: 35,
    cores: [
      { id: 0, prime: 5,  process: "P1", residue: 1, state: "hot",     locked: true  },
      { id: 1, prime: 7,  process: "P2", residue: 2, state: "hot",     locked: true  },
      { id: 2, prime: 11, process: "P4", residue: 4, state: "repair",  locked: false },
    ],
    highlight: "366 + 35k ≡ 4 (mod 11)  →  3 + 2k ≡ 4 (mod 11)  →  k = 6",
    steps: [
      "366 mod 11 = 3   (current residue)",
      "35  mod 11 = 2   (M mod p₂)",
      "3 + 2k ≡ 4 (mod 11)  →  2k ≡ 1 (mod 11)",
      "inv(2, 11) = 6   →   k = 6",
      "z′ = 366 + 35×6 = 576",
      "576 mod 385 = 191",
    ],
  },
  {
    id: "verify",
    label: "VERIFY — ALL COMMITMENTS PRESERVED",
    subtitle: "One coordinate changed. Two warm caches untouched. Repair radius = 1.",
    z: 191,
    zPrime: 191,
    delta: 210,
    k: 6,
    Mval: 35,
    cores: [
      { id: 0, prime: 5,  process: "P1", residue: 1, state: "hot",     locked: true  },
      { id: 1, prime: 7,  process: "P2", residue: 2, state: "hot",     locked: true  },
      { id: 2, prime: 11, process: "P4", residue: 4, state: "solved",  locked: false },
    ],
    verify: [
      { core: "C0", prime: 5,  val: 1, check: "191 mod 5 = 1",  ok: true,  note: "P1 cache preserved ✓" },
      { core: "C1", prime: 7,  val: 2, check: "191 mod 7 = 2",  ok: true,  note: "P2 cache preserved ✓" },
      { core: "C2", prime: 11, val: 4, check: "191 mod 11 = 4", ok: true,  note: "P4 scheduled ✓" },
    ],
    repairRadius: 1,
  },
];

// ── STYLE CONSTANTS ───────────────────────────────────────────────────
const mono  = "'Space Mono','Courier New',monospace";
const sans  = "'Exo 2',sans-serif";
const C_LOCK   = "#f6ad55";
const C_FREE   = "#63b3ed";
const C_JUMP   = "#a78bfa";
const C_SOLVED = "#68d391";
const C_ERR    = "#fc8181";
const C_LABEL  = "rgba(255,255,255,0.22)";
const C_DIM    = "rgba(255,255,255,0.07)";

function stateColor(state) {
  if (state === "hot")     return C_LOCK;
  if (state === "blocked") return C_ERR;
  if (state === "repair")  return C_JUMP;
  if (state === "solved")  return C_SOLVED;
  return C_FREE;
}

function stateLabel(state) {
  if (state === "hot")     return "🔥 HOT CACHE";
  if (state === "blocked") return "⏸ BLOCKED";
  if (state === "repair")  return "⚡ REPAIR";
  if (state === "solved")  return "✓ RUNNING";
  return "◉ RUNNING";
}

// ── CORE CARD ─────────────────────────────────────────────────────────
function CoreCard({ core, animating }) {
  const col = stateColor(core.state);
  const isLocked = core.locked;
  return (
    <div className={animating && core.state === "repair" ? "core-repair" : animating && isLocked ? "core-lock-pulse" : ""}
      style={{
        flex: 1, minWidth: 0,
        border: `2px solid ${col}44`,
        borderRadius: 10,
        background: isLocked
          ? "rgba(246,173,85,0.06)"
          : core.state === "blocked" ? "rgba(252,129,129,0.06)"
          : core.state === "repair"  ? "rgba(167,139,250,0.06)"
          : core.state === "solved"  ? "rgba(104,211,145,0.06)"
          : "rgba(99,179,237,0.04)",
        padding: "14px 10px",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
        boxShadow: isLocked ? `0 0 12px ${C_LOCK}22` : core.state === "repair" ? `0 0 16px ${C_JUMP}33` : "none",
        transition: "all 0.4s ease",
      }}>
      {/* Core label */}
      <div style={{ fontFamily: mono, fontSize: 9, color: C_LABEL, letterSpacing: 2 }}>
        CORE {core.id}
      </div>
      {/* Prime */}
      <div style={{ fontFamily: mono, fontSize: 10, color: col }}>
        p = {core.prime}
      </div>
      {/* Lock icon */}
      {isLocked && (
        <div style={{ fontSize: 16, lineHeight: 1 }}>⚑</div>
      )}
      {/* Process */}
      <div style={{
        fontFamily: mono, fontSize: 18, fontWeight: 700,
        color: core.state === "blocked" ? C_ERR : col,
        textDecoration: core.state === "blocked" ? "line-through" : "none",
        opacity: core.state === "blocked" ? 0.6 : 1,
      }}>
        {core.process}
      </div>
      {/* State label */}
      <div style={{ fontFamily: mono, fontSize: 8, color: col, textAlign: "center", letterSpacing: 1 }}>
        {stateLabel(core.state)}
      </div>
      {/* Residue */}
      <div style={{
        fontFamily: mono, fontSize: 10, color: col,
        background: `${col}15`, border: `1px solid ${col}33`,
        borderRadius: 5, padding: "3px 8px",
      }}>
        mod {core.prime} = {core.residue}
      </div>
    </div>
  );
}

// ── TOPOLOGY SVG ──────────────────────────────────────────────────────
function TopologySVG({ cores, animating }) {
  const xs = [80, 220, 360];
  const cy = 40, r = 18;
  return (
    <svg width="440" height="80" style={{ overflow: "visible", display: "block", margin: "8px auto 0" }}>
      {[0,1].map(i => {
        const aL = cores[i].locked, bL = cores[i+1].locked;
        return <line key={i} x1={xs[i]} y1={cy} x2={xs[i+1]} y2={cy}
          stroke={aL && bL ? C_LOCK : "rgba(255,255,255,0.1)"}
          strokeWidth={1.5} strokeDasharray={!(aL&&bL)?"5 4":"none"} />;
      })}
      {cores.map((core, i) => {
        const col = stateColor(core.state);
        const isJumping = animating && core.state === "repair";
        return (
          <g key={i}>
            {isJumping && <circle cx={xs[i]} cy={cy} r={r+8} fill="none" stroke={C_JUMP} strokeWidth={1}
              opacity={0.4} style={{ animation: "ringOut2 0.8s ease-out infinite" }} />}
            <circle cx={xs[i]} cy={cy} r={r} fill="#06060e" stroke={col} strokeWidth={core.locked||isJumping?2:1}
              style={{ filter: `drop-shadow(0 0 6px ${col}55)` }} />
            <text x={xs[i]} y={cy+1} textAnchor="middle" dominantBaseline="middle"
              fontFamily={mono} fontSize={10} fill={col} fontWeight={700}>
              C{core.id}
            </text>
            <text x={xs[i]} y={cy+r+13} textAnchor="middle" fontFamily={mono} fontSize={8} fill={C_LABEL}>
              {core.locked ? "LOCKED" : core.state === "repair" ? "JUMP" : core.state === "solved" ? "REPAIRED" : core.state.toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── MAIN ──────────────────────────────────────────────────────────────
export default function CPUSchedulerCRT() {
  const [stepIdx, setStepIdx] = useState(0);
  const [animating, setAnimating] = useState(false);

  const step = STEPS[stepIdx];
  const isLast = stepIdx === STEPS.length - 1;

  const advance = () => {
    if (isLast) { setStepIdx(0); return; }
    setAnimating(true);
    setTimeout(() => setAnimating(false), 800);
    setStepIdx(i => i + 1);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#06060e", color: "#e2e8f0",
      fontFamily: sans, padding: "16px 10px" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Exo+2:wght@300;400;600;700&display=swap');
        .bg-grid {
          background-image: linear-gradient(rgba(99,179,237,.03) 1px,transparent 1px),
            linear-gradient(90deg,rgba(99,179,237,.03) 1px,transparent 1px);
          background-size: 28px 28px;
        }
        .btn{cursor:pointer;transition:all .16s;outline:none;}
        .btn:hover{transform:translateY(-1px);filter:brightness(1.2);}
        .btn:active{transform:translateY(0);}
        @keyframes ringOut2{from{opacity:.5;r:26}to{opacity:0;r:46}}
        @keyframes lockPulse2{0%,100%{box-shadow:0 0 12px ${C_LOCK}33}50%{box-shadow:0 0 22px ${C_LOCK}77}}
        @keyframes repairPulse{0%,100%{box-shadow:0 0 12px ${C_JUMP}33}50%{box-shadow:0 0 26px ${C_JUMP}88}}
        .core-lock-pulse{animation:lockPulse2 0.8s ease-in-out;}
        .core-repair{animation:repairPulse 0.8s ease-in-out;}
        .fade-in{animation:fadeIn .3s ease-out;}
        @keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        .step-dot{transition:all .2s;}
      `}</style>

      <div className="bg-grid" style={{ maxWidth: 680, margin: "0 auto", borderRadius: 14,
        border: "1px solid rgba(99,179,237,.12)", overflow: "hidden" }}>

        {/* HEADER */}
        <div style={{ padding: "15px 22px", borderBottom: "1px solid rgba(99,179,237,.09)",
          background: "rgba(99,179,237,.025)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontFamily: mono, fontSize: 10, color: C_FREE, letterSpacing: 3, marginBottom: 3 }}>
              GEOMETRIC IF-ELSE · CPU SCHEDULING REPAIR
            </div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>CRT Local Repair Walkthrough</div>
            <div style={{ fontFamily: mono, fontSize: 9, color: C_LABEL, marginTop: 3 }}>
              3 cores · primes [5, 7, 11] · P = 385
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {STEPS.map((s, i) => (
              <div key={i} className="step-dot" onClick={() => setStepIdx(i)} style={{
                width: i === stepIdx ? 28 : 8, height: 8, borderRadius: 4, cursor: "pointer",
                background: i < stepIdx ? C_SOLVED : i === stepIdx ? C_FREE : "rgba(255,255,255,0.1)",
                transition: "all 0.2s",
              }} />
            ))}
          </div>
        </div>

        {/* STEP LABEL */}
        <div className="fade-in" key={stepIdx} style={{ padding: "14px 22px 0" }}>
          <div style={{ fontFamily: mono, fontSize: 10, color: C_FREE, letterSpacing: 2, marginBottom: 4 }}>
            STEP {stepIdx + 1}/{STEPS.length} — {step.label}
          </div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", marginBottom: 14 }}>
            {step.subtitle}
          </div>
        </div>

        {/* CORE CARDS */}
        <div className="fade-in" key={`cores-${stepIdx}`} style={{ padding: "0 22px", display: "flex", gap: 12 }}>
          {step.cores.map(core => (
            <CoreCard key={core.id} core={core} animating={animating} />
          ))}
        </div>

        {/* TOPOLOGY */}
        <TopologySVG cores={step.cores} animating={animating} />

        {/* Z COORDINATE DISPLAY */}
        <div style={{ padding: "14px 22px" }}>
          <div style={{
            padding: "12px 16px",
            background: "rgba(104,211,145,0.04)", border: "1px solid rgba(104,211,145,0.15)",
            borderRadius: 10, display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap",
          }}>
            <div>
              <div style={{ fontFamily: mono, fontSize: 9, color: C_LABEL, letterSpacing: 2, marginBottom: 4 }}>
                CRT COORDINATE
              </div>
              {step.zPrime && step.zPrime !== step.z ? (
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontFamily: mono, fontSize: 22, color: "rgba(255,255,255,0.35)", textDecoration: "line-through" }}>
                    z = {step.z}
                  </span>
                  <span style={{ color: C_JUMP, fontSize: 16 }}>→</span>
                  <span style={{ fontFamily: mono, fontSize: 22, fontWeight: 700, color: C_SOLVED }}>
                    z′ = {step.zPrime}
                  </span>
                </div>
              ) : (
                <div style={{ fontFamily: mono, fontSize: 26, fontWeight: 700, color: C_SOLVED }}>
                  z = {step.z}
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              {step.cores.map(core => (
                <div key={core.id} style={{ textAlign: "center" }}>
                  <div style={{ fontFamily: mono, fontSize: 8, color: C_LABEL }}>C{core.id}</div>
                  <div style={{ fontFamily: mono, fontSize: 11, color: stateColor(core.state) }}>
                    mod {core.prime}={core.residue}
                  </div>
                </div>
              ))}
            </div>
            {step.Mval && (
              <div style={{
                marginLeft: "auto", fontFamily: mono, fontSize: 10,
                color: C_JUMP,
                background: "rgba(167,139,250,0.08)",
                border: "1px solid rgba(167,139,250,0.2)",
                borderRadius: 6, padding: "6px 12px",
              }}>
                M = {step.id === "init" ? "—" : step.cores.filter(c=>c.locked).map(c=>`p${c.id}=${c.prime}`).join("×") + ` = ${step.Mval}`}
              </div>
            )}
          </div>
        </div>

        {/* REPAIR COMPUTATION (step 3) */}
        {step.steps && (
          <div className="fade-in" style={{ padding: "0 22px 14px" }}>
            <div style={{ padding: "14px 16px",
              background: "rgba(167,139,250,0.04)", border: "1px solid rgba(167,139,250,0.18)", borderRadius: 10 }}>
              <div style={{ fontFamily: mono, fontSize: 9, color: "#c084fc", letterSpacing: 2, marginBottom: 12 }}>
                LOCAL CRT REPAIR STEP — z′ = z + k·M
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 24px" }}>
                {step.steps.map((s, i) => (
                  <div key={i} style={{
                    fontFamily: mono, fontSize: 10, color: i === step.steps.length - 1 ? C_SOLVED : "rgba(255,255,255,0.55)",
                    padding: "4px 0", borderBottom: "1px solid rgba(255,255,255,0.04)",
                  }}>
                    <span style={{ color: C_JUMP, marginRight: 8 }}>{i+1}.</span>{s}
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 14, padding: "10px 14px",
                background: "rgba(104,211,145,0.06)", border: "1px solid rgba(104,211,145,0.2)", borderRadius: 8,
                fontFamily: mono, fontSize: 11, color: C_SOLVED, textAlign: "center" }}>
                z′ = {step.z} + {step.k} × {step.Mval} = {step.z + step.k * step.Mval} → mod 385 = {step.zPrime}
                <span style={{ color: C_JUMP, marginLeft: 16 }}>Δz = +{step.delta}</span>
              </div>
            </div>
          </div>
        )}

        {/* VERIFY (step 4) */}
        {step.verify && (
          <div className="fade-in" style={{ padding: "0 22px 14px" }}>
            <div style={{ padding: "14px 16px",
              background: "rgba(104,211,145,0.04)", border: "1px solid rgba(104,211,145,0.18)", borderRadius: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontFamily: mono, fontSize: 9, color: C_SOLVED, letterSpacing: 2 }}>
                  INVARIANT VERIFICATION
                </div>
                <div style={{
                  fontFamily: mono, fontSize: 9, color: C_LABEL,
                  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 5, padding: "4px 10px", display: "flex", gap: 12,
                }}>
                  <span>REPAIR RADIUS <span style={{ color: C_FREE }}>= {step.repairRadius}</span></span>
                  <span>PRESERVED <span style={{ color: C_LOCK }}>2/3 cores</span></span>
                  <span>MIGRATIONS <span style={{ color: C_SOLVED }}>= 1</span></span>
                </div>
              </div>
              {step.verify.map((v, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "7px 10px", marginBottom: 5,
                  background: i < 2 ? "rgba(246,173,85,0.05)" : "rgba(99,179,237,0.05)",
                  border: `1px solid ${i < 2 ? "rgba(246,173,85,0.14)" : "rgba(99,179,237,0.14)"}`,
                  borderRadius: 7,
                }}>
                  <span style={{ fontFamily: mono, fontSize: 10, color: i < 2 ? C_LOCK : C_FREE, width: 28 }}>{v.core}</span>
                  <span style={{ fontFamily: mono, fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{v.check}</span>
                  <span style={{ fontFamily: mono, fontSize: 10, color: C_SOLVED, marginLeft: "auto" }}>{v.note}</span>
                </div>
              ))}
              <div style={{ marginTop: 10, fontFamily: mono, fontSize: 9, color: C_LABEL, textAlign: "center" }}>
                ONE coordinate changed · ZERO cache migrations disturbed · ZERO global rescheduling needed
              </div>
            </div>
          </div>
        )}

        {/* HIGHLIGHT */}
        {step.highlight && (
          <div style={{ padding: "0 22px 14px" }}>
            <div style={{ fontFamily: mono, fontSize: 10, color: C_JUMP,
              background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)",
              borderRadius: 8, padding: "10px 14px", textAlign: "center" }}>
              {step.highlight}
            </div>
          </div>
        )}

        {/* NAV */}
        <div style={{ padding: "0 22px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button className="btn" onClick={() => setStepIdx(i => Math.max(0, i-1))}
            style={{ padding: "8px 18px", background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: 7,
              color: "rgba(255,255,255,0.4)", fontFamily: mono, fontSize: 10, letterSpacing: 1,
              opacity: stepIdx === 0 ? 0.3 : 1, cursor: stepIdx === 0 ? "default" : "pointer" }}>
            ← BACK
          </button>

          <div style={{ fontFamily: mono, fontSize: 9, color: C_LABEL }}>
            {stepIdx + 1} / {STEPS.length}
          </div>

          <button className="btn" onClick={advance} style={{
            padding: "10px 24px",
            background: isLast ? "rgba(104,211,145,0.1)" : "rgba(99,179,237,0.1)",
            border: `1px solid ${isLast ? "rgba(104,211,145,0.3)" : "rgba(99,179,237,0.3)"}`,
            borderRadius: 7, color: isLast ? C_SOLVED : C_FREE,
            fontFamily: mono, fontSize: 11, letterSpacing: 1,
          }}>
            {isLast ? "RESTART ↺" : "NEXT STEP →"}
          </button>
        </div>

        {/* COMPARISON */}
        {stepIdx >= 2 && (
          <div style={{ margin: "0 22px 16px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ padding: "12px", background: "rgba(252,129,129,0.04)",
              border: "1px solid rgba(252,129,129,0.15)", borderRadius: 8 }}>
              <div style={{ fontFamily: mono, fontSize: 9, color: C_ERR, letterSpacing: 2, marginBottom: 8 }}>
                TRADITIONAL SCHEDULER
              </div>
              {["process blocked", "reconsider all queues", "maybe migrate many tasks", "recompute globally", "cache destroyed"].map((l,i) => (
                <div key={i} style={{ fontFamily: mono, fontSize: 9, color: "rgba(252,129,129,0.6)",
                  padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>→ {l}</div>
              ))}
            </div>
            <div style={{ padding: "12px", background: "rgba(104,211,145,0.04)",
              border: "1px solid rgba(104,211,145,0.15)", borderRadius: 8 }}>
              <div style={{ fontFamily: mono, fontSize: 9, color: C_SOLVED, letterSpacing: 2, marginBottom: 8 }}>
                CRT REPAIR SCHEDULER
              </div>
              {["process blocked", "compute exact displacement k", "jump z → z + kM", "1 core affected", "warm caches intact"].map((l,i) => (
                <div key={i} style={{ fontFamily: mono, fontSize: 9, color: "rgba(104,211,145,0.7)",
                  padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>→ {l}</div>
              ))}
            </div>
          </div>
        )}

        {/* FOOTER */}
        <div style={{ padding: "9px 22px", borderTop: "1px solid rgba(99,179,237,.06)",
          fontFamily: mono, fontSize: 8, display: "flex", flexDirection: "column", gap: 3 }}>
          <div style={{ display: "flex", gap: 6 }}>
            <span style={{ color: C_JUMP, letterSpacing: 1 }}>ARITHMETIC:</span>
            <span style={{ color: C_LABEL }}>exact residue-preserving jump · z′ = z + k·M · O(1) per repair</span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <span style={{ color: C_FREE, letterSpacing: 1 }}>SEARCH:</span>
            <span style={{ color: C_LABEL }}>process selection · priority · fairness — classical scheduler logic</span>
          </div>
        </div>

      </div>
    </div>
  );
}
