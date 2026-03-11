<script>
  import { onMount, onDestroy } from 'svelte';

  // ── State ──────────────────────────────────────────────
  let status = 'standby';   // standby | listening | thinking | speaking
  let transcript = [];       // { speaker, text }[]
  let ws = null;
  let canvasEl;
  let animFrame;
  let pulsePhase = 0;
  let rings = [0, 0, 0];    // ripple offsets for speaking state

  // ── WebSocket ──────────────────────────────────────────
  function connect() {
    ws = new WebSocket('ws://localhost:8765');

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.event === 'status')     status = msg.state;
      if (msg.event === 'transcript') {
        transcript = [...transcript, { speaker: msg.speaker, text: msg.text }];
        // auto-scroll
        setTimeout(() => {
          const feed = document.getElementById('feed');
          if (feed) feed.scrollTop = feed.scrollHeight;
        }, 50);
      }
    };

    ws.onclose = () => {
      status = 'standby';
      setTimeout(connect, 2000); // auto-reconnect
    };
  }

  // ── Canvas Arc Reactor ─────────────────────────────────
  function draw() {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    const W = canvasEl.width;
    const H = canvasEl.height;
    const cx = W / 2;
    const cy = H / 2;

    ctx.clearRect(0, 0, W, H);

    pulsePhase += 0.03;

    // ── Outer static rings ──
    const ringRadii = [130, 105, 82];
    const ringAlphas = [0.12, 0.2, 0.3];
    ringRadii.forEach((r, i) => {
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 212, 255, ${ringAlphas[i]})`;
      ctx.lineWidth = 1;
      ctx.stroke();

      // Tick marks on each ring
      for (let t = 0; t < (i === 0 ? 36 : i === 1 ? 24 : 12); t++) {
        const angle = (t / (i === 0 ? 36 : i === 1 ? 24 : 12)) * Math.PI * 2;
        const tickLen = i === 2 ? 8 : 4;
        const x1 = cx + Math.cos(angle) * r;
        const y1 = cy + Math.sin(angle) * r;
        const x2 = cx + Math.cos(angle) * (r + tickLen);
        const y2 = cy + Math.sin(angle) * (r + tickLen);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = `rgba(0, 212, 255, ${ringAlphas[i] * 2})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    });

    // ── Rotating arc (always on) ──
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(pulsePhase * 0.5);
    ctx.beginPath();
    ctx.arc(0, 0, 118, 0, Math.PI * 1.5);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.6)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();

    // ── Counter-rotating arc ──
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-pulsePhase * 0.3);
    ctx.beginPath();
    ctx.arc(0, 0, 95, Math.PI * 0.3, Math.PI * 1.8);
    ctx.strokeStyle = 'rgba(0, 180, 255, 0.4)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();

    // ── State-specific effects ──
    if (status === 'listening') {
      // Breathing glow
      const breathe = (Math.sin(pulsePhase * 2) + 1) / 2;
      const grad = ctx.createRadialGradient(cx, cy, 10, cx, cy, 75);
      grad.addColorStop(0, `rgba(0, 255, 180, ${0.3 + breathe * 0.3})`);
      grad.addColorStop(1, 'rgba(0, 255, 180, 0)');
      ctx.beginPath();
      ctx.arc(cx, cy, 75, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      // Pulsing outer ring
      ctx.beginPath();
      ctx.arc(cx, cy, 130 + Math.sin(pulsePhase * 3) * 4, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 255, 150, ${0.4 + breathe * 0.3})`;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    if (status === 'thinking') {
      // Spinning dashed ring
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(pulsePhase * 2);
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      ctx.arc(0, 0, 60, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255, 200, 0, 0.7)';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();

      // Orbiting dot
      ctx.beginPath();
      const ox = cx + Math.cos(pulsePhase * 3) * 60;
      const oy = cy + Math.sin(pulsePhase * 3) * 60;
      ctx.arc(ox, oy, 4, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255, 200, 0, 0.9)';
      ctx.fill();
    }

    if (status === 'speaking') {
      // Expanding ripples
      rings = rings.map((r, i) => (r + 1.2) % 80);
      rings.forEach((r, i) => {
        const alpha = (1 - r / 80) * 0.5;
        ctx.beginPath();
        ctx.arc(cx, cy, 65 + r, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });
    }

    // ── Core glow ──
    const coreColor = {
      standby:  [0, 180, 255],
      listening:[0, 255, 150],
      thinking: [255, 200, 0],
      speaking: [0, 212, 255],
    }[status] || [0, 180, 255];

    const intensity = status === 'standby' ? 0.5 + Math.sin(pulsePhase) * 0.1 : 0.85;
    const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 55);
    coreGrad.addColorStop(0, `rgba(${coreColor.join(',')}, ${intensity})`);
    coreGrad.addColorStop(0.5, `rgba(${coreColor.join(',')}, ${intensity * 0.4})`);
    coreGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.beginPath();
    ctx.arc(cx, cy, 55, 0, Math.PI * 2);
    ctx.fillStyle = coreGrad;
    ctx.fill();

    // Solid inner circle
    ctx.beginPath();
    ctx.arc(cx, cy, 28, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${coreColor.join(',')}, ${intensity * 0.9})`;
    ctx.fill();

    // Inner ring
    ctx.beginPath();
    ctx.arc(cx, cy, 40, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(${coreColor.join(',')}, 0.8)`;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Hex detail in center
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(pulsePhase * 0.2);
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      const hx = Math.cos(a) * 14;
      const hy = Math.sin(a) * 14;
      i === 0 ? ctx.moveTo(hx, hy) : ctx.lineTo(hx, hy);
    }
    ctx.closePath();
    ctx.strokeStyle = `rgba(255,255,255,0.6)`;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();

    animFrame = requestAnimationFrame(draw);
  }

  // ── Lifecycle ──────────────────────────────────────────
  onMount(() => {
    connect();
    canvasEl.width = 320;
    canvasEl.height = 320;
    draw();
  });

  onDestroy(() => {
    ws?.close();
    cancelAnimationFrame(animFrame);
  });

  // ── Helpers ────────────────────────────────────────────
  const statusLabel = {
    standby:  'STANDBY',
    listening:'LISTENING',
    thinking: 'PROCESSING',
    speaking: 'SPEAKING',
  };

  const statusColor = {
    standby:  '#00b4ff',
    listening:'#00ff96',
    thinking: '#ffc800',
    speaking: '#00d4ff',
  };
</script>

<!-- ─────────────────────── MARKUP ─────────────────────── -->
<main>
  <header>
    <div class="logo">J.A.R.V.I.S</div>
    <div class="subtitle">Just A Rather Very Intelligent System</div>
  </header>

  <!-- Arc Reactor -->
  <div class="reactor-wrap">
    <canvas bind:this={canvasEl} />
    <div class="status-badge" style="color: {statusColor[status]}">
      <span class="dot" style="background:{statusColor[status]}"></span>
      {statusLabel[status]}
    </div>
  </div>

  <!-- Hint -->
  <p class="hint">Hold <kbd>SPACE</kbd> to speak · <kbd>ESC</kbd> to quit</p>

  <!-- Transcript feed -->
  <div class="feed" id="feed">
    {#if transcript.length === 0}
      <p class="empty">Awaiting input, sir.</p>
    {/if}
    {#each transcript as line}
      <div class="line {line.speaker}">
        <span class="speaker-label">{line.speaker === 'user' ? 'YOU' : 'JARVIS'}</span>
        <span class="text">{line.text}</span>
      </div>
    {/each}
  </div>
</main>

<!-- ─────────────────────── STYLES ─────────────────────── -->
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }

  :global(body) {
    background: #04080f;
    color: #c8e6f5;
    font-family: 'Share Tech Mono', monospace;
    height: 100vh;
    overflow: hidden;
    /* Subtle grid overlay */
    background-image:
      linear-gradient(rgba(0, 180, 255, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0, 180, 255, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  main {
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100vh;
    padding: 24px 16px 16px;
    gap: 0;
  }

  header {
    text-align: center;
    margin-bottom: 8px;
  }

  .logo {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    font-size: 2rem;
    letter-spacing: 0.25em;
    color: #00d4ff;
    text-shadow: 0 0 20px rgba(0, 212, 255, 0.7), 0 0 40px rgba(0, 212, 255, 0.3);
  }

  .subtitle {
    font-size: 0.62rem;
    letter-spacing: 0.2em;
    color: rgba(0, 212, 255, 0.4);
    margin-top: 2px;
  }

  /* Reactor */
  .reactor-wrap {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  canvas {
    display: block;
    filter: drop-shadow(0 0 24px rgba(0, 212, 255, 0.35));
  }

  .status-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    margin-top: -8px;
    transition: color 0.4s;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
    animation: blink 1.2s ease-in-out infinite;
    transition: background 0.4s;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
  }

  /* Hint */
  .hint {
    font-size: 0.65rem;
    color: rgba(200, 230, 245, 0.3);
    letter-spacing: 0.08em;
    margin: 10px 0 12px;
  }

  kbd {
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 3px;
    padding: 1px 5px;
    font-family: inherit;
    font-size: inherit;
    color: rgba(0, 212, 255, 0.7);
  }

  /* Transcript feed */
  .feed {
    width: 100%;
    max-width: 560px;
    flex: 1;
    overflow-y: auto;
    border-top: 1px solid rgba(0, 212, 255, 0.1);
    padding-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 212, 255, 0.2) transparent;
  }

  .empty {
    font-size: 0.75rem;
    color: rgba(200, 230, 245, 0.2);
    text-align: center;
    margin-top: 12px;
    letter-spacing: 0.1em;
    font-style: italic;
  }

  .line {
    display: flex;
    gap: 12px;
    align-items: baseline;
    animation: fadeIn 0.3s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .speaker-label {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    min-width: 44px;
    padding-top: 2px;
    flex-shrink: 0;
  }

  .line.user .speaker-label  { color: rgba(200, 230, 245, 0.5); }
  .line.jarvis .speaker-label { color: #00d4ff; }

  .text {
    font-size: 0.82rem;
    line-height: 1.55;
    color: #c8e6f5;
  }

  .line.jarvis .text {
    color: #e0f7ff;
    text-shadow: 0 0 8px rgba(0, 212, 255, 0.25);
  }
</style>
