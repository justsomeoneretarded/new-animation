// Screen-space layers: phone point-of-view, HUD counter, dialogue, captions and text cards.
'use strict';
const FONT_HAND = '"FilmHand", "Patrick Hand", "Poppins", sans-serif';
const FONT_DIGIT = '"FilmDigit", "DejaVu Sans Mono", monospace';

function typed(text, u, cps = 26) { return text.slice(0, Math.max(0, Math.floor(u * cps))); }

function textShadowed(ctx, text, x, y, size, color, opts = {}) {
  ctx.font = `${opts.bold ? 'bold ' : ''}${size}px ${FONT_HAND}`;
  ctx.textAlign = opts.align || 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = opts.glow || 'rgba(0,0,0,.85)'; ctx.shadowBlur = opts.glowBlur ?? 10;
  ctx.fillStyle = color; ctx.fillText(text, x, y); ctx.shadowBlur = 0;
}

function wrapLines(ctx, text, maxW) {
  const words = text.split(/\s+/); const out = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }
  if (cur) out.push(cur); return out;
}

// ---------- HUD ----------
function drawHud(ctx, film, shot, u, K) {
  const hud = shot.hud; if (!hud || !film.hud) return;
  const p = clamp(u / Math.max(.6, Math.min(shot.dur * .8, 2.2)), 0, 1);
  let v = hud.value;
  if (Array.isArray(v)) v = Math.round(lerp(v[0], v[1], easeInOut(p)));
  const label = `${film.hud.label}: ${typeof v === 'number' ? v.toLocaleString('en-US') : v}`;
  const col = hud.alert ? '#ff4a4a' : 'rgba(240,238,230,.92)';
  ctx.save(); ctx.scale(K, K);
  textShadowed(ctx, label.toUpperCase(), 64, 132, 30, col, { align: 'left' });
  if (hud.chapter) textShadowed(ctx, hud.chapter.toUpperCase(), 64, film.hud.label ? 172 : 132, 24, 'rgba(220,218,210,.75)', { align: 'left' });
  ctx.restore();
}

// ---------- dialogue / captions ----------
function drawLines(ctx, shot, u, heads, K, film) {
  ctx.save(); ctx.scale(K, K);
  for (const ln of shot.lines || []) {
    const at = ln.at ?? 0, dur = ln.dur ?? (shot.dur - at);
    if (u < at || u > at + dur) continue;
    const lu = u - at, fadeOut = clamp((at + dur - u) / .25, 0, 1);
    ctx.globalAlpha = Math.min(1, lu / .12) * fadeOut;
    const who = ln.who || 'caption';
    const actor = (shot.actors || []).find(a => a.id === who);
    const isDemon = actor && (film.cast[who] || {}).kind === 'demon' || who === 'demon';
    const txt = typed(ln.text, lu, isDemon ? 20 : 28);
    if (who === 'caption' || who === 'narrator' || !heads[who]) {
      const y = who === 'caption' || who === 'narrator' ? 905 : 170;
      if (isDemon) { textShadowed(ctx, txt, 960 + noise1(u * 8, 1) * 2, 170, 46, '#ff3b3b', { glow: 'rgba(255,0,0,.6)', glowBlur: 18 }); }
      else textShadowed(ctx, txt, 960, y, 38, C.text);
    } else {
      const [hx, hy] = heads[who];
      ctx.font = `${isDemon ? 42 : 34}px ${FONT_HAND}`;
      const x = clamp(hx + (isDemon ? 0 : 0), 220, 1700), y = clamp(hy - (isDemon ? 60 : 50), 150, 900);
      if (isDemon) textShadowed(ctx, txt, x + noise1(u * 9, 2) * 2.5, y, 42, '#ff3b3b', { glow: 'rgba(255,0,0,.7)', glowBlur: 18 });
      else textShadowed(ctx, txt, x, y, 34, C.text);
    }
  }
  ctx.globalAlpha = 1; ctx.restore();
}

// ---------- phone point of view ----------
function phoneScreen(ctx, ph, u, t) {
  const W = 500, H = 940;
  ctx.fillStyle = '#0f1116'; ctx.fillRect(0, 0, W, H);
  ctx.font = `20px ${FONT_HAND}`; ctx.fillStyle = '#c9ccd4'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(ph.time || '23:41', 34, 34); ctx.textAlign = 'right'; ctx.fillText('▮▮▮  82%', W - 30, 34);
  const app = ph.app || 'chat';
  if (app === 'chat') {
    // header
    ctx.fillStyle = '#171a21'; ctx.fillRect(0, 60, W, 92);
    ctx.fillStyle = ph.color || '#e07a2e'; ctx.beginPath(); ctx.arc(66, 106, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = `bold 24px ${FONT_HAND}`; ctx.textAlign = 'center'; ctx.fillText((ph.contact || 'Sam')[0].toUpperCase(), 66, 107);
    ctx.textAlign = 'left'; ctx.font = `28px ${FONT_HAND}`; ctx.fillText(ph.contact || 'Sam', 108, 96);
    ctx.font = `18px ${FONT_HAND}`; ctx.fillStyle = '#7d8492'; ctx.fillText(ph.status || 'online', 108, 124);
    let y = 190;
    const msgs = (ph.messages || []).filter(m => u >= (m.at ?? 0)).slice();
    // a sent typed message appears as a bubble
    const ty = ph.typing;
    let input = '';
    if (ty) {
      const at = ty.at ?? .3, cps = ty.cps || 11, n = ty.text.length, full = at + n / cps;
      if (u >= at) {
        if (ty.action === 'delete') {
          const del = full + (ty.pause ?? .7);
          if (u < del) input = ty.text.slice(0, Math.floor((u - at) * cps));
          else input = ty.text.slice(0, Math.max(0, n - Math.floor((u - del) * cps * 2.4)));
        } else if (ty.action === 'send') {
          if (u < full + .35) input = ty.text.slice(0, Math.floor((u - at) * cps));
          else msgs.push({ from: 'me', text: ty.text, at: full + .35 });
        } else input = ty.text.slice(0, Math.floor((u - at) * cps));
      }
    }
    for (const m of msgs) {
      ctx.font = `25px ${FONT_HAND}`;
      const lines = wrapLines(ctx, m.text, 300); const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 36, bh = lines.length * 32 + 22;
      const pop = backOut(clamp((u - (m.at ?? 0)) / .25, 0, 1));
      const me = m.from === 'me', x = me ? W - 26 - bw : 26;
      ctx.save(); ctx.translate(x + (me ? bw : 0), y); ctx.scale(pop, pop); ctx.translate(-(me ? bw : 0), 0);
      rr(ctx, 0, 0, bw, bh, 18, me ? '#3478f6' : '#262a33');
      ctx.fillStyle = '#f3f4f6'; ctx.textAlign = 'left';
      lines.forEach((l, i) => ctx.fillText(l, 18, 27 + i * 32));
      ctx.restore();
      y += bh + 14;
    }
    if (ph.seen && u > ph.seen) { ctx.font = `16px ${FONT_HAND}`; ctx.fillStyle = '#7d8492'; ctx.textAlign = 'right'; ctx.fillText('seen', W - 30, y + 4); }
    // input bar
    rr(ctx, 20, H - 96, W - 110, 58, 29, '#1d2028', '#2c303a', 2);
    ctx.font = `25px ${FONT_HAND}`; ctx.textAlign = 'left';
    ctx.fillStyle = input ? '#f3f4f6' : '#5b6170'; ctx.fillText(input || 'Message', 44, H - 67);
    if (Math.floor(t * 2) % 2 === 0 && ty && u >= (ty.at ?? .3)) { const w = ctx.measureText(input).width; ctx.fillStyle = '#3478f6'; ctx.fillRect(46 + w, H - 82, 3, 30); }
    ctx.fillStyle = '#3478f6'; ctx.beginPath(); ctx.arc(W - 50, H - 67, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.moveTo(W - 60, H - 78); ctx.lineTo(W - 38, H - 67); ctx.lineTo(W - 60, H - 56); ctx.fill();
  } else if (app === 'call') {
    const c = ph.call || {}; const dec = c.decline_at, ans = c.answer_at;
    ctx.fillStyle = '#12151c'; ctx.fillRect(0, 60, W, H);
    ctx.fillStyle = '#3a3f4c'; ctx.beginPath(); ctx.arc(W / 2, 270, 70, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#7c8394'; ctx.beginPath(); ctx.arc(W / 2, 250, 28, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.ellipse(W / 2, 318, 46, 26, 0, Math.PI, 0); ctx.fill();
    ctx.textAlign = 'center'; ctx.fillStyle = '#f3f4f6'; ctx.font = `38px ${FONT_HAND}`; ctx.fillText(ph.contact || 'unknown number', W / 2, 400);
    const ended = dec !== undefined && u > dec, live = ans !== undefined && u > ans;
    ctx.font = `22px ${FONT_HAND}`; ctx.fillStyle = '#8b92a1';
    ctx.fillText(ended ? 'call declined' : live ? `00:${String(Math.floor(u - ans)).padStart(2, '0')}` : 'incoming call...', W / 2, 444);
    if (!ended && !live) {
      const pulse = 1 + .06 * Math.sin(u * 8);
      for (const [x, col] of [[W / 2 - 110, '#ff3b30'], [W / 2 + 110, '#34c759']]) { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, H - 170, 42 * pulse, 0, Math.PI * 2); ctx.fill(); }
    } else if (live) { ctx.fillStyle = '#ff3b30'; ctx.beginPath(); ctx.arc(W / 2, H - 170, 42, 0, Math.PI * 2); ctx.fill(); }
  } else if (app === 'lock') {
    const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#1a2033'); g.addColorStop(1, '#0c0e14'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.fillStyle = '#eef1f6'; ctx.font = `110px ${FONT_HAND}`; ctx.fillText(ph.time || '02:14', W / 2, 220);
    ctx.font = `24px ${FONT_HAND}`; ctx.fillStyle = '#aab1c0'; ctx.fillText(ph.date || 'Tuesday', W / 2, 300);
    let y = 360;
    for (const n of (ph.notifications || [])) {
      if (u < (n.at ?? 0)) continue;
      const k = backOut(clamp((u - (n.at ?? 0)) / .3, 0, 1));
      ctx.save(); ctx.translate(0, (1 - k) * -40); ctx.globalAlpha = clamp(k, 0, 1);
      rr(ctx, 24, y, W - 48, 92, 20, 'rgba(60,66,82,.85)');
      ctx.textAlign = 'left'; ctx.fillStyle = '#f3f4f6'; ctx.font = `bold 20px ${FONT_HAND}`; ctx.fillText((n.app || 'Messages').toUpperCase(), 48, y + 28);
      ctx.font = `24px ${FONT_HAND}`; ctx.fillText(n.text, 48, y + 62);
      ctx.restore(); y += 108;
    }
  } else if (app === 'feed') {
    ctx.fillStyle = '#0d0f14'; ctx.fillRect(0, 60, W, H);
    ctx.font = `bold 26px ${FONT_HAND}`; ctx.fillStyle = '#f3f4f6'; ctx.textAlign = 'left'; ctx.fillText('feed', 30, 96);
    const scroll = u * (ph.speed || 260);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 120, W, H - 120); ctx.clip();
    for (let i = 0; i < 12; i++) {
      const y = 140 + i * 430 - (scroll % (430 * 6)) ;
      if (y < -440 || y > H) continue;
      const hue = [ '#e07a2e', '#3f9a5a', '#3b6fc4', '#c8383b', '#9a5ac8', '#d9a92e'][i % 6];
      ctx.fillStyle = hue; ctx.beginPath(); ctx.arc(52, y + 22, 18, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#d7dae0'; ctx.font = `20px ${FONT_HAND}`; ctx.fillText(['max', 'jo', 'leo', 'ana', 'kit', 'sam'][i % 6], 82, y + 24);
      const g = ctx.createLinearGradient(0, y + 52, 0, y + 352); g.addColorStop(0, shade(hue, -.45)); g.addColorStop(1, shade(hue, -.75));
      ctx.fillStyle = g; ctx.fillRect(20, y + 52, W - 40, 300);
      // tiny happy people in the post
      for (let k = 0; k < 3 + (i % 2); k++) {
        const px = 90 + k * 95, py = y + 330;
        ctx.save(); ctx.translate(px, py); ctx.scale(.42, .42);
        drawCharacter(ctx, { wx: 0, wy: 0, scale: 1, mood: 'happy', hat: ['beanie_orange', 'none', 'cap_red', 'beanie_blue'][(i + k) % 4] }, (() => { const P = basePose(); P.hands = [[-66, -300 - 20 * Math.sin(t * 4 + k)], [66, -300]]; P.lift = Math.abs(Math.sin(t * 4 + k)) * 12; return P; })(), { zoom: .45, t, noShadow: true });
        ctx.restore();
      }
      ctx.fillStyle = '#ff4d6d'; ctx.font = `22px ${FONT_HAND}`; ctx.fillText(`♥ ${(1200 + i * 731) % 9000 + 300}`, 30, y + 382);
    }
    ctx.restore();
  } else if (app === 'alarm') {
    ctx.fillStyle = '#0d0f14'; ctx.fillRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.fillStyle = '#f3f4f6'; ctx.font = `120px ${FONT_HAND}`; ctx.fillText(ph.time || '05:30', W / 2, 330);
    ctx.font = `28px ${FONT_HAND}`; ctx.fillStyle = '#aab1c0'; ctx.fillText(ph.label || 'alarm', W / 2, 410);
    rr(ctx, 60, H - 260, W - 120, 80, 40, '#2a2e38'); ctx.fillStyle = '#f3f4f6'; ctx.fillText('snooze', W / 2, H - 220);
    rr(ctx, 60, H - 160, W - 120, 80, 40, '#ff9f0a'); ctx.fillStyle = '#111'; ctx.fillText('stop', W / 2, H - 120);
  }
}

function drawPhonePOV(ctx, shot, u, t, K) {
  const ph = shot.phone || {};
  const ring = (ph.app === 'call' && !(ph.call && (u > (ph.call.decline_at ?? 1e9) || u > (ph.call.answer_at ?? 1e9)))) || ph.app === 'alarm';
  const jx = ring ? Math.sin(u * 60) * 3 * (Math.sin(u * 5) > 0 ? 1 : 0) : 0;
  const rise = easeOut(clamp(u / .35, 0, 1));
  ctx.save(); ctx.scale(K, K);
  ctx.translate(960 + jx + noise1(t * .4, 9) * 6, 600 + (1 - rise) * 80 + noise1(t * .35, 4) * 5);
  ctx.rotate(noise1(t * .3, 2) * .01 - .015);
  // glow from the screen onto the room
  pool(ctx, 0, 0, 720, 'rgba(120,160,255,A)', .1);
  // left hand behind
  ctx.fillStyle = C.cream; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(-300, 360, 90, 200, -.25, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  // phone body
  rr(ctx, -272, -500, 544, 1040, 64, '#1b1d22', '#565a63', 4);
  ctx.save(); roundRect(ctx, -250, -478, 500, 996, 48); ctx.clip(); ctx.translate(-250, -478);
  phoneScreen(ctx, ph, u, t);
  ctx.restore();
  rr(ctx, -70, -466, 140, 26, 13, '#08090b');
  // right thumb (taps while typing)
  const typing = ph.typing && u > (ph.typing.at ?? .3);
  const tap = typing ? Math.abs(Math.sin(u * 22)) * 14 : 0;
  ctx.fillStyle = C.cream; ctx.strokeStyle = C.ink; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(250, 420 - tap, 80, 190, .45, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(170, 300 - tap, 34, 86, .7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  ctx.restore();
}

// ---------- cards ----------
function drawCard(ctx, shot, u, t, K) {
  const cd = shot.card; const lines = cd.lines || [];
  const k = easeOut(clamp(u / .4, 0, 1));
  ctx.save(); ctx.scale(K, K);
  const style = cd.style || 'title';
  if (style === 'red') {
    textShadowed(ctx, lines[0] || '', 960, 430, 120 + (1 - k) * 30, '#ff3434', { glow: 'rgba(255,0,0,.55)', glowBlur: 30 });
    if (lines[1]) { ctx.globalAlpha = clamp((u - .6) / .4, 0, 1); textShadowed(ctx, lines[1], 960, 540, 40, C.text); }
  } else if (style === 'quote') {
    lines.forEach((l, i) => { ctx.globalAlpha = clamp((u - i * .9) / .5, 0, 1); textShadowed(ctx, l, 960, 470 + i * 70, 50, i === lines.length - 1 && lines.length > 1 ? '#ffd27a' : C.text); });
  } else if (style === 'cta') {
    textShadowed(ctx, lines[0] || 'If this hit, like and subscribe.', 960, 400, 46, C.text);
    const press = clamp((u - 1.2) / .2, 0, 1), press2 = clamp((u - 2.2) / .2, 0, 1);
    rr(ctx, 760, 470, 190, 64, 32, press ? '#3478f6' : '#2a2e38'); textShadowed(ctx, 'LIKE', 855, 503, 28, '#fff', { glowBlur: 0 });
    rr(ctx, 980, 470, 230, 64, 32, press2 ? '#3a3d45' : '#ff2d2d'); textShadowed(ctx, press2 ? 'SUBSCRIBED' : 'SUBSCRIBE', 1095, 503, 28, '#fff', { glowBlur: 0 });
    const cx = u < 1.2 ? lerp(1300, 860, easeInOut(u / 1.2)) : u < 2.2 ? lerp(860, 1100, easeInOut(u - 1.2)) : 1100;
    const cy = u < 1.2 ? lerp(700, 515, easeInOut(u / 1.2)) : 515;
    ctx.fillStyle = '#fff'; ctx.strokeStyle = '#000'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx, cy + 34); ctx.lineTo(cx + 9, cy + 26); ctx.lineTo(cx + 16, cy + 40); ctx.lineTo(cx + 22, cy + 37); ctx.lineTo(cx + 15, cy + 24); ctx.lineTo(cx + 26, cy + 24); ctx.closePath(); ctx.fill(); ctx.stroke();
  } else {
    lines.forEach((l, i) => { ctx.globalAlpha = clamp((u - i * .6) / .5, 0, 1); textShadowed(ctx, l, 960, 460 + i * 74 - (lines.length - 1) * 30, i === 0 ? 64 : 40, C.text); });
  }
  ctx.globalAlpha = 1; ctx.restore();
}
