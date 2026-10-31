// The blob character: rig, poses, faces. Local coordinates: origin at the feet, y up is negative.
'use strict';

const RIG = { pelvisY: -100, shoulderX: 46, shoulderY: -110, headY: -168, headR: 64, hipX: 21,
  thigh: 51, shin: 50, upper: 52, fore: 50, legW: 31, armW: 25 };

const MOODS = {
  neutral:    { brow: [0, 0], browY: 0,  eyes: 'dot',   lid: 0,   mouth: 'flat' },
  flat:       { brow: [0, 0], browY: 5,  eyes: 'dot',   lid: .45, mouth: 'flat' },
  sad:        { brow: [.28, 0], browY: -2, eyes: 'dot', lid: .15, mouth: 'frown', lookY: 2 },
  worried:    { brow: [.38, 0], browY: -5, eyes: 'dot', lid: 0,   mouth: 'wavy' },
  happy:      { brow: [0, 0], browY: -7, eyes: 'happy', lid: 0,   mouth: 'smile' },
  determined: { brow: [-.3, 0], browY: 4, eyes: 'dot',  lid: .2,  mouth: 'tight' },
  shocked:    { brow: [.1, 0], browY: -12, eyes: 'wide', lid: 0,  mouth: 'o' },
  tired:      { brow: [.05, 0], browY: 6, eyes: 'dot',  lid: .6,  mouth: 'flat', bags: true },
  angry:      { brow: [-.45, 0], browY: 5, eyes: 'dot', lid: .1,  mouth: 'frown' },
  smirk:      { brow: [0, -.25], browY: 0, eyes: 'dot', lid: .4,  mouth: 'smirk' },
  asleep:     { brow: [0, 0], browY: 3,  eyes: 'closed', lid: 0, mouth: 'small' },
  nervous:    { brow: [.32, 0], browY: -4, eyes: 'small', lid: 0, mouth: 'wavy', sweat: true }
};

// ---------- poses ----------
function basePose() {
  return { pelvis: [0, RIG.pelvisY], lean: 0, rot: 0, lift: 0, headDy: 0, headTilt: 0, shoulderDy: 0,
    feet: [[-24, 0], [24, 0]], hands: [[-54, -108], [54, -108]], look: [0, 0], faceDx: 0, squash: 1,
    hold: null, phoneGlow: 0, legsHidden: false, kneelDepth: 0 };
}

function breathe(P, u, seed) { const b = Math.sin(u * 2.1 + seed) ; P.squash = 1 + b * .012; P.shoulderDy = b * 1.5; }

const POSES = {
  stand(P, a, u, d, w) {
    breathe(P, u, a.seed);
    const s = noise1(u * .6, a.seed) * 3;
    P.hands = [[-53 + s, -106], [53 + s, -106]];
  },
  walk(P, a, u, d, w, run) {
    const stride = run ? 260 : 150, lift = run ? 34 : 17;
    const phase = w.walked / stride;
    const dir = w.dir;
    for (let i = 0; i < 2; i++) {
      const ph = 2 * Math.PI * (phase + i * .5);
      const fx = dir * Math.sin(ph) * (run ? 40 : 27);
      const fy = -Math.max(0, dir * Math.cos(ph) * dir) * lift;
      P.feet[i] = [(i ? 18 : -18) + fx, fy];
      const sw = -dir * Math.sin(ph) * (run ? 26 : 16);
      P.hands[i] = run ? [(i ? 34 : -34) + sw, -150 + Math.abs(sw) * .3] : [(i ? 52 : -52) + sw, -108];
    }
    if (!w.moving) { POSES.stand(P, a, u, d, w); return; }
    P.pelvis[1] = RIG.pelvisY - 3 + Math.abs(Math.cos(2 * Math.PI * phase)) * (run ? 9 : 4);
    P.lean = dir * (run ? .14 : .04);
    P.faceDx = dir * .8;
  },
  run(P, a, u, d, w) { POSES.walk(P, a, u, d, w, true); },
  sit(P, a, u, d, w) {
    breathe(P, u, a.seed);
    const h = w.seat || 58;
    P.pelvis = [0, -h - 10];
    const fy = Math.min(0, -h + 66);
    P.feet = [[-30, fy], [30, fy]];
    P.hands = [[-36, -h - 6], [36, -h - 6]];
    P.thighShort = true;
  },
  slump(P, a, u, d, w) {
    POSES.sit(P, a, u, d, w);
    P.headDy = 16; P.shoulderDy = 6; P.lean = 0;
    P.hands = [[-16, -(w.seat || 58) + 18], [16, -(w.seat || 58) + 18]];
    P.look = [0, 4];
  },
  lie(P, a, u, d, w) {
    breathe(P, u, a.seed);
    P.rot = -Math.PI / 2 * (a.facing === 1 ? -1 : 1);
    P.lieH = (w.seat || 0) + 62;
    P.hands = [[-40, -120], [40, -120]];
  },
  phone(P, a, u, d, w) {
    if (a.seated) POSES.sit(P, a, u, d, w); else POSES.stand(P, a, u, d, w);
    const by = P.pelvis[1] + RIG.pelvisY * 0 - 70;
    P.hands = [[-12, by - 4], [16, by - 8]];
    P.hold = P.hold || 'phone'; P.look = [0, 4]; P.phoneGlow = 1; P.headDy = 3;
  },
  type(P, a, u, d, w) {
    POSES.sit(P, a, u, d, w);
    const tap = i => Math.sin(u * 17 + i * 2.1) * 3 + noise1(u * 4, i + a.seed) * 4;
    if (w.desk) {
      const y = -w.desk - 4;
      P.hands = [[-34 + tap(0), y + Math.abs(tap(1)) * .6], [40 + tap(2) * 1.6, y + Math.abs(tap(3)) * .6]];
    } else {
      // drawing in a sketchbook on the lap
      const y = -(w.seat || 58) - 26;
      P.hands = [[-28, y], [22 + tap(2) * 1.5, y - 4 + tap(3) * .5]];
      P.lapBook = true;
    }
    P.look = [0, 4]; P.headDy = 4;
  },
  reach(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = easeOut(u / Math.min(1.2, d * .5));
    const strain = Math.sin(u * 9) * 3 * k;
    P.hands[1] = [lerp(53, 44, k) + strain, lerp(-106, -395, k)];
    P.lift = 10 * k; P.look = [.3, -5 * k]; P.feet = [[-22, 0], [22, 0]];
  },
  wave(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = easeOut(u / .35);
    P.hands[1] = [lerp(53, 92, k) + Math.sin(u * 11) * 16 * k, lerp(-106, -262, k)];
  },
  fall(P, a, u, d, w) {
    const k = easeIn(clamp(u / .45, 0, 1));
    const settle = Math.sin(clamp((u - .45) / .3, 0, 1) * Math.PI) * 6;
    POSES.kneel(P, a, u, d, w, k);
    P.pelvis[1] += settle;
    P.hands = [[lerp(-53, -64, k), lerp(-106, -2, k)], [lerp(53, 64, k), lerp(-106, -2, k)]];
    P.headDy = lerp(0, 30, k);
  },
  kneel(P, a, u, d, w, kk) {
    const k = kk === undefined ? 1 : kk;
    breathe(P, u, a.seed);
    P.pelvis = [0, lerp(RIG.pelvisY, -52, k)];
    P.kneelDepth = k;
    P.feet = [[-26, 0], [26, 0]];
    P.hands = [[-34, lerp(-106, -40, k)], [34, lerp(-106, -40, k)]];
    P.headDy = 12 * k; P.look = [0, 4 * k];
  },
  getup(P, a, u, d, w) {
    const k = easeInOut(clamp(u / Math.min(1.6, d * .7), 0, 1));
    POSES.kneel(P, a, u, d, w, 1 - k);
    P.hands = [[lerp(-34, -53, k), lerp(-40, -106, k)], [lerp(34, 53, k), lerp(-40, -106, k)]];
    P.headDy = 12 * (1 - k);
  },
  lift(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const rep = (Math.sin(u * 2.4 - Math.PI / 2) + 1) / 2;
    const y = lerp(-218, -392, easeInOut(rep));
    const shake = Math.sin(u * 30) * 2 * rep;
    P.hands = [[-78, y + shake], [78, y - shake]];
    P.feet = [[-34, 0], [34, 0]];
    P.pelvis[1] = RIG.pelvisY + (1 - rep) * 6;
    P.hold = 'barbell';
  },
  crossarms(P, a, u, d, w) { POSES.stand(P, a, u, d, w); P.hands = [[22, -150], [-22, -146]]; P.crossed = true; },
  headhands(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const sh = Math.sin(u * 7) * 2;
    P.hands = [[-62 + sh, -276], [62 + sh, -276]]; P.headDy = 6; P.elbowOut = true;
  },
  shrug(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const k = (Math.sin(u * 3) + 1) / 2;
    P.shoulderDy = -8 * k; P.hands = [[-82, -150 - 8 * k], [82, -150 - 8 * k]];
  },
  point(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = a.facing || 1, k = easeOut(u / .3);
    P.hands[dir > 0 ? 1 : 0] = [lerp(53 * dir, 112 * dir, k), lerp(-106, -212, k)];
    P.faceDx = dir * .7;
  },
  celebrate(P, a, u, d, w) {
    const j = Math.abs(Math.sin(u * Math.PI * 1.6));
    P.lift = j * 46; P.hands = [[-66, -360], [66, -360]]; P.feet = [[-22, -j * 6], [22, -j * 6]];
  },
  lean(P, a, u, d, w) {
    POSES.stand(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1;
    const k = easeOut(u / .8);
    P.lean = dir * .2 * k; P.faceDx = dir * .8; P.headDy = 6 * k;
    P.hands[dir > 0 ? 1 : 0] = [dir * lerp(53, 90, k), lerp(-106, -150, k)];
  },
  grab(P, a, u, d, w) {
    POSES.lean(P, a, u, d, w);
    const dir = w.targetDx >= 0 ? 1 : -1, k = easeOut(u / .6);
    if (w.targetShoulder) {
      const [tx, ty] = w.targetShoulder;
      P.hands[dir > 0 ? 1 : 0] = [lerp(dir * 53, tx, k), lerp(-106, ty, k)];
    }
  }
};

function evalPose(a, u, d, w) {
  const P = basePose();
  P.look = [a.facing || 0, 0];
  P.faceDx = (a.facing || 0) * .55;
  (POSES[a.pose] || POSES.stand)(P, a, u, d, w);
  if (a.hold && a.hold !== 'none') P.hold = a.hold;
  if (a.pose !== 'walk' && a.pose !== 'run' && a.pose !== 'lean' && a.pose !== 'grab' && a.pose !== 'point' && a.facing !== undefined) P.faceDx = (a.facing || 0) * .55;
  return P;
}

// ---------- drawing ----------
function limb(ctx, pts, w, fill, out, lw) {
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(pts[0], pts[1]);
  for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
  if (out) { ctx.strokeStyle = out; ctx.lineWidth = w + lw * 2; ctx.stroke(); }
  ctx.strokeStyle = fill; ctx.lineWidth = w; ctx.stroke();
}

function torsoPath(ctx, s) {
  // Head and torso as one soft "bean" (relative to pelvis).
  ctx.beginPath();
  ctx.moveTo(-36, -128);
  ctx.bezierCurveTo(-52, -110, -62, -66, -60, -24);
  ctx.bezierCurveTo(-58, 6, -34, 12, 0, 12);
  ctx.bezierCurveTo(34, 12, 58, 6, 60, -24);
  ctx.bezierCurveTo(62, -66, 52, -110, 36, -128);
  ctx.closePath();
}

function drawHat(ctx, hat, hx, hy, r, fdx) {
  if (!hat || hat === 'none') return;
  const [kind, color] = hat.split('_');
  const col = { orange: '#e07a2e', green: '#3f9a5a', blue: '#3b6fc4', red: '#c8383b', grey: '#7c7f86' }[color] || '#888';
  ctx.save(); ctx.translate(hx, hy);
  if (kind === 'beanie') {
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.ellipse(0, -r * .38, r * .98, r * .78, 0, Math.PI, 0); ctx.closePath(); ctx.fill();
    ctx.fillStyle = shade(col, -.18);
    roundRect(ctx, -r * 1.02, -r * .5, r * 2.04, r * .32, 8); ctx.fill();
    ctx.strokeStyle = shade(col, -.3); ctx.lineWidth = 2;
    for (let i = -3; i <= 3; i++) { ctx.beginPath(); ctx.moveTo(i * r * .27, -r * .48); ctx.lineTo(i * r * .27, -r * .2); ctx.stroke(); }
  } else if (kind === 'cap') {
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.ellipse(0, -r * .42, r * .96, r * .62, 0, Math.PI, 0); ctx.closePath(); ctx.fill();
    ctx.fillStyle = shade(col, -.2);
    ctx.beginPath(); ctx.ellipse(r * .55 * (fdx >= 0 ? 1 : -1), -r * .42, r * .7, r * .14, 0, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16); let r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  const f = v => clamp(Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k), 0, 255);
  return `rgb(${f(r)},${f(g)},${f(b)})`;
}
function skinOf(o) { return o.skin || C.cream; }
function rr0(ctx) { ctx.fillStyle = '#efe9db'; ctx.strokeStyle = '#2a2a30'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(-58, -6); ctx.lineTo(58, -6); ctx.lineTo(50, 18); ctx.lineTo(-50, 18); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.fillStyle = '#7a4b3a'; ctx.fillRect(-52, 16, 104, 6); }
function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

function drawFace(ctx, m, P, hx, hy, opts) {
  const fdx = P.faceDx * 15, lx = clamp(P.look[0], -1, 1) * 4 + fdx * .1, ly = P.look[1];
  const ink = opts.demon ? C.red : C.ink;
  const eyeY = hy + 6, browY = hy - 18 + m.browY, mouthY = hy + 32;
  const blink = opts.blink && m.eyes !== 'closed' && m.eyes !== 'happy';
  for (const side of [-1, 1]) {
    const ex = hx + side * 21 + fdx;
    // Eyes
    ctx.fillStyle = ink; ctx.strokeStyle = ink; ctx.lineCap = 'round';
    if (opts.demon) {
      ctx.lineWidth = 6; ctx.beginPath();
      ctx.moveTo(ex - side * 13, eyeY - 4); ctx.lineTo(ex + side * 11, eyeY + 3); ctx.stroke();
      continue;
    }
    if (blink || m.eyes === 'closed') {
      ctx.lineWidth = 3.4; ctx.beginPath(); ctx.moveTo(ex - 8, eyeY + 1); ctx.quadraticCurveTo(ex, eyeY + 6, ex + 8, eyeY + 1); ctx.stroke();
    } else if (m.eyes === 'happy') {
      ctx.lineWidth = 3.6; ctx.beginPath(); ctx.moveTo(ex - 8, eyeY + 4); ctx.quadraticCurveTo(ex, eyeY - 7, ex + 8, eyeY + 4); ctx.stroke();
    } else {
      const rx = m.eyes === 'wide' ? 9 : m.eyes === 'small' ? 4.5 : 6.5, ry = m.eyes === 'wide' ? 11 : m.eyes === 'small' ? 5.5 : 8.5;
      ctx.beginPath(); ctx.ellipse(ex + lx, eyeY + ly, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(200,215,255,.8)';
      ctx.beginPath(); ctx.arc(ex + lx - rx * .3, eyeY + ly - ry * .35, Math.max(1.4, rx * .28), 0, Math.PI * 2); ctx.fill();
      if (m.lid > 0) {
        ctx.fillStyle = opts.skin;
        ctx.fillRect(ex - 13, eyeY - 14, 26, 14 * m.lid + (ry * 2) * m.lid * .55 - 1 + (m.lid > .3 ? 3 : 0));
        ctx.strokeStyle = ink; ctx.lineWidth = 3;
        const lidY = eyeY - ry + ry * 2 * m.lid;
        ctx.beginPath(); ctx.moveTo(ex - 9, lidY); ctx.lineTo(ex + 9, lidY); ctx.stroke();
      }
      if (m.bags) { ctx.strokeStyle = 'rgba(80,70,60,.45)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(ex - 7, eyeY + 13); ctx.quadraticCurveTo(ex, eyeY + 17, ex + 7, eyeY + 13); ctx.stroke(); }
    }
    // Brows: thick rounded bars. brow[0] tilts the inner end up (+) or down (-); brow[1] raises one side.
    const inner = m.brow[0] * 16, raise = side > 0 ? m.brow[1] * 30 : 0;
    ctx.strokeStyle = ink; ctx.lineWidth = 7; ctx.lineCap = 'round';
    const bx0 = ex - side * 2 - side * 13 * -1, bx1 = ex + side * 13;
    ctx.beginPath(); ctx.moveTo(ex - side * 13, browY - inner + raise); ctx.lineTo(bx1, browY + raise * .4); ctx.stroke();
  }
  if (opts.demon) return;
  // Mouth
  ctx.strokeStyle = ink; ctx.fillStyle = ink; ctx.lineWidth = 3.4; ctx.lineCap = 'round';
  const mx = hx + fdx * 1.1;
  let mouth = m.mouth;
  if (opts.talking) mouth = (Math.floor(opts.t * 9) % 3 === 0) ? 'flat' : (Math.floor(opts.t * 9) % 3 === 1 ? 'o' : 'small');
  ctx.beginPath();
  switch (mouth) {
    case 'smile': ctx.moveTo(mx - 12, mouthY - 3); ctx.quadraticCurveTo(mx, mouthY + 9, mx + 12, mouthY - 3); ctx.stroke(); break;
    case 'frown': ctx.moveTo(mx - 10, mouthY + 4); ctx.quadraticCurveTo(mx, mouthY - 5, mx + 10, mouthY + 4); ctx.stroke(); break;
    case 'o': ctx.ellipse(mx, mouthY + 1, 6, 8, 0, 0, Math.PI * 2); ctx.fill(); break;
    case 'small': ctx.ellipse(mx, mouthY, 3.5, 3, 0, 0, Math.PI * 2); ctx.fill(); break;
    case 'wavy': ctx.moveTo(mx - 11, mouthY); ctx.bezierCurveTo(mx - 5, mouthY - 5, mx + 2, mouthY + 5, mx + 11, mouthY - 1); ctx.stroke(); break;
    case 'tight': ctx.moveTo(mx - 9, mouthY + 1); ctx.lineTo(mx + 9, mouthY + 1); ctx.lineWidth = 4.2; ctx.stroke(); break;
    case 'smirk': ctx.moveTo(mx - 9, mouthY + 2); ctx.quadraticCurveTo(mx + 3, mouthY + 4, mx + 12, mouthY - 4); ctx.stroke(); break;
    default: ctx.moveTo(mx - 9, mouthY); ctx.lineTo(mx + 9, mouthY); ctx.stroke();
  }
  if (m.sweat) { ctx.fillStyle = '#9fd0ff'; ctx.beginPath(); ctx.moveTo(hx + 52, hy - 30); ctx.quadraticCurveTo(hx + 60, hy - 14, hx + 52, hy - 10); ctx.quadraticCurveTo(hx + 44, hy - 14, hx + 52, hy - 30); ctx.fill(); }
}

function drawHold(ctx, item, P, hands, opts) {
  const [L, R] = hands;
  ctx.save();
  if (item === 'phone') {
    const x = (L[0] + R[0]) / 2, y = (L[1] + R[1]) / 2 - 10;
    ctx.translate(x, y); ctx.rotate(-.06);
    ctx.fillStyle = '#16181d'; roundRect(ctx, -15, -27, 30, 50, 6); ctx.fill();
    ctx.fillStyle = opts.demon ? '#300' : '#9cc4ff'; ctx.globalAlpha = .9; roundRect(ctx, -12, -24, 24, 42, 4); ctx.fill();
  } else if (item === 'cup') {
    ctx.translate(R[0] + 6, R[1] - 10);
    ctx.fillStyle = '#f2efe6'; roundRect(ctx, -11, -24, 22, 28, 4); ctx.fill();
    ctx.fillStyle = '#8b5a3c'; ctx.fillRect(-11, -14, 22, 7);
  } else if (item === 'pencil') {
    ctx.translate(R[0], R[1]); ctx.rotate(.6);
    ctx.fillStyle = '#f1c232'; ctx.fillRect(-3, -30, 6, 34); ctx.fillStyle = '#333'; ctx.fillRect(-3, 4, 6, 5);
  } else if (item === 'book') {
    ctx.translate((L[0] + R[0]) / 2, (L[1] + R[1]) / 2 - 6);
    ctx.fillStyle = '#7a4b3a'; roundRect(ctx, -30, -22, 60, 40, 3); ctx.fill(); ctx.fillStyle = '#efe6d2'; ctx.fillRect(-27, -19, 54, 4);
  } else if (item === 'bag') {
    ctx.translate(R[0] + 4, R[1] + 30);
    ctx.fillStyle = '#3a4a5e'; roundRect(ctx, -22, -26, 44, 50, 8); ctx.fill();
  } else if (item === 'barbell') {
    ctx.strokeStyle = '#9aa0a8'; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(L[0] - 70, L[1]); ctx.lineTo(R[0] + 70, R[1]); ctx.stroke();
    ctx.fillStyle = '#2b2d33'; ctx.strokeStyle = '#555a63'; ctx.lineWidth = 2;
    for (const [hx, hy, sd] of [[L[0], L[1], -1], [R[0], R[1], 1]]) for (let k = 0; k < 2; k++) {
      roundRect(ctx, hx + sd * (40 + k * 18) - 8, hy - 44 + k * 6, 16, 88 - k * 12, 4); ctx.fill(); ctx.stroke();
    }
  }
  ctx.restore();
}

// Draw a character. a = actor spec (with world x/y), P = pose, opts: {demon, skin, hat, t, blink, talking, zoom}
function drawCharacter(ctx, a, P, opts) {
  const s = a.scale || 1, lw = 2.6 / (opts.zoom || 1) / s;
  const skin = opts.skin || C.cream, out = opts.demon ? '#050505' : C.ink;
  const shadeCol = opts.demon ? '#050505' : shade(skin, -.12);
  ctx.save();
  ctx.translate(a.wx, a.wy - P.lift * s);
  ctx.scale(s, s);
  if (P.rot) { ctx.translate(0, -P.lieH); ctx.rotate(P.rot); ctx.translate(-0, 0); }
  // contact shadow
  if (!P.rot && !opts.demon && !opts.noShadow) {
    ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.beginPath(); ctx.ellipse(0, 2 + P.lift, 62, 9, 0, 0, Math.PI * 2); ctx.fill();
  }
  const [px, py] = P.pelvis;
  const cosL = Math.cos(P.lean), sinL = Math.sin(P.lean);
  const rotP = (x, y) => [px + x * cosL - y * sinL, py + x * sinL + y * cosL];
  // Legs
  if (!P.legsHidden) {
    for (let i = 0; i < 2; i++) {
      const side = i ? 1 : -1;
      const [hx, hy] = rotP(side * RIG.hipX, -4);
      const [fx, fy] = P.feet[i];
      if (P.kneelDepth > .05) {
        // Kneeling: knee goes to the floor, shin tucked behind (hidden).
        const kx = lerp(fx, side * 30, P.kneelDepth), ky = lerp(-RIG.shin, -8, P.kneelDepth);
        const k = ik(hx, hy, kx, ky, RIG.thigh, RIG.shin, side * (P.kneelDepth > .5 ? 1 : -1));
        limb(ctx, [hx, hy, k[0], k[1], k[2], k[3]], RIG.legW, shadeCol, out, lw);
      } else if (P.thighShort) {
        limb(ctx, [fx * 1.1, hy + 16, fx, fy - 3], RIG.legW, shadeCol, out, lw);
        // foreshortened thigh: a knee pointing at the camera
        ctx.fillStyle = shade(skinOf(opts), -.06); ctx.strokeStyle = out; ctx.lineWidth = lw * 2;
        ctx.beginPath(); ctx.ellipse(fx * 1.1, hy + 10, 24, 21, 0, 0, Math.PI * 2); ctx.stroke(); ctx.fill();
      } else {
        const k = ik(hx, hy, fx, fy - 4, RIG.thigh, RIG.shin, P.lean ? (P.lean > 0 ? -1 : 1) : -side);
        limb(ctx, [hx, hy, k[0], k[1], k[2], k[3]], RIG.legW, shadeCol, out, lw);
      }
    }
  }
  // Body (torso + head) rotates with lean around the pelvis.
  ctx.save();
  ctx.translate(px, py); ctx.rotate(P.lean);
  ctx.scale(1, P.squash); ctx.translate(0, (1 - P.squash) * 20);
  const hx = 0, hy = RIG.headY + P.headDy + P.shoulderDy * .5;
  const drawBody = (fill) => {
    ctx.fillStyle = fill; torsoPath(ctx); ctx.fill();
    ctx.beginPath(); ctx.arc(hx, hy, RIG.headR, 0, Math.PI * 2); ctx.fill();
  };
  ctx.strokeStyle = out; ctx.lineWidth = lw * 2;
  torsoPath(ctx); ctx.stroke(); ctx.beginPath(); ctx.arc(hx, hy, RIG.headR, 0, Math.PI * 2); ctx.stroke();
  drawBody(skin);
  if (!opts.demon) {
    // soft side shading
    ctx.save(); torsoPath(ctx); ctx.clip();
    const g = ctx.createLinearGradient(-60, 0, 60, 0); g.addColorStop(0, 'rgba(0,0,0,0.10)'); g.addColorStop(.4, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.06)');
    ctx.fillStyle = g; ctx.fillRect(-70, -140, 140, 160); ctx.restore();
  }
  drawFace(ctx, MOODS[a.mood] || MOODS.neutral, P, hx, hy, { ...opts, skin });
  drawHat(ctx, a.hat, hx, hy, RIG.headR, P.faceDx);
  if (P.phoneGlow && !opts.demon) {
    const g = ctx.createRadialGradient(hx, hy + 20, 5, hx, hy + 20, 90);
    g.addColorStop(0, 'rgba(150,190,255,0.22)'); g.addColorStop(1, 'rgba(150,190,255,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(hx, hy + 20, 90, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
  if (P.lapBook) { ctx.save(); ctx.translate(0, P.pelvis[1] - 18); rr0(ctx); ctx.restore(); }
  // Arms (drawn over the body, with outline so they read against it).
  const hands = [];
  for (let i = 0; i < 2; i++) {
    const side = i ? 1 : -1;
    const [sx, sy] = rotP(side * RIG.shoulderX, RIG.shoulderY + P.shoulderDy + (1 - P.squash) * 20);
    let [tx, ty] = P.hands[i];
    // choose the elbow solution that sits away from the body (reads naturally from the front)
    const k1 = ik(sx, sy, tx, ty, RIG.upper, RIG.fore, 1), k2 = ik(sx, sy, tx, ty, RIG.upper, RIG.fore, -1);
    const k = P.crossed ? (Math.abs(k1[0]) < Math.abs(k2[0]) ? k1 : k2) : (side * k1[0] > side * k2[0] ? k1 : k2);
    hands.push([k[2], k[3]]);
    const col = (P.crossed && i === 0) ? shadeCol : skin;
    limb(ctx, [sx, sy, k[0], k[1], k[2], k[3]], RIG.armW, col, out, lw);
  }
  if (P.hold) drawHold(ctx, P.hold, P, hands, opts);
  ctx.restore();
  return { hands, head: [a.wx + (px + hx) * s, a.wy + (py + hy) * s] };
}
