// Marble Nations renderer.
// env: TEAMS="INDIA:in,USA:us"  THEME=snow  EP="EP. 12"  SEED=1234  MUSIC=drop_the_tapes_a.mp3  OUT=out
// Downloads flags, finds a seed that gives a clean 26-42s race, renders 1080x1920 frames,
// builds sound effects, mixes music that ducks under the effects, writes OUT/race.mp4 + OUT/meta.json
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const APP = path.join(__dirname, 'app');
const OUT = process.env.OUT || path.join(__dirname, 'out');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(path.join(APP, 'flags'), { recursive: true });

const teams = (process.env.TEAMS || 'INDIA:in,USA:us').split(',').map(s => {
  const [name, code] = s.split(':').map(x => x.trim());
  return { name: name.toUpperCase().slice(0, 14), code: (code || '').toLowerCase() };
});
const theme = process.env.THEME || 'sky';
const ep = process.env.EP || 'COUNTRY MARBLE RACE';
let seed = parseInt(process.env.SEED || String(Date.now() % 100000), 10);

async function getFlag(code) {
  const file = path.join(APP, 'flags', code + '.png');
  if (fs.existsSync(file)) return;
  const res = await fetch(`https://flagcdn.com/w640/${code}.png`);
  if (!res.ok) throw new Error('flag not found: ' + code);
  fs.writeFileSync(file, Buffer.from(await res.arrayBuffer()));
}

function serve() {
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png' };
  return new Promise(r => {
    const srv = http.createServer((req, res) => {
      const f = path.join(APP, decodeURIComponent(req.url.split('?')[0]));
      if (!f.startsWith(APP) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).pipe(res);
    }).listen(8765, () => r(srv));
  });
}

// ---------- sound effects (synthesized, no samples needed) ----------
function buildSfx(ev, durSec, file) {
  const SR = 44100, N = Math.ceil(SR * (durSec + 1));
  const a = new Float32Array(N);
  let rs = 12345; const rand = () => { rs = (rs * 16807) % 2147483647; return rs / 2147483647 * 2 - 1; };
  const add = (i0, fn, len) => { for (let k = 0; k < len && i0 + k < N; k++) a[i0 + k] += fn(k / SR); };
  for (let k = 0; k < 4; k++) { const f = k < 3 ? 880 : 1760; add(Math.floor(k * SR), t => Math.sin(2 * Math.PI * f * t) * Math.exp(-t * 8) * .35, Math.floor(.25 * SR)); }
  const last = {};
  for (const e of ev.events) {
    if (e.t > durSec || e.t - (last[e.kind] ?? -1) < .05) continue;
    last[e.kind] = e.t; const i0 = Math.floor(e.t * SR);
    if (e.kind === 'win') {
      [523, 659, 784, 1047, 1319].forEach((f, k) => add(i0 + Math.floor(k * .11 * SR), t => (Math.sin(2 * Math.PI * f * t) + .3 * Math.sin(4 * Math.PI * f * t)) * Math.exp(-t * 3) * .22, Math.floor(.6 * SR)));
    } else if (e.kind === 'whoosh') {
      let lp = 0; add(i0, t => { lp = lp * .88 + rand() * .12; return lp * Math.sin(Math.PI * t / .45) * 2.2; }, Math.floor(.45 * SR));
    } else {
      const f = { hit: 160, bump: 620, clack: 1400 }[e.kind] || 300;
      add(i0, t => (Math.sin(2 * Math.PI * f * t) + .6 * Math.sin(2 * Math.PI * f * 2.7 * t) + .4 * rand()) * Math.exp(-t * 45) * .3 * (.35 + e.amp), Math.floor(.12 * SR));
    }
  }
  const buf = Buffer.alloc(44 + N * 2);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 2, 4); buf.write('WAVEfmt ', 8); buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22); buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 2, 28);
  buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34); buf.write('data', 36); buf.writeUInt32LE(N * 2, 40);
  for (let i = 0; i < N; i++) buf.writeInt16LE(Math.round(Math.tanh(a[i] * 1.2) * 32000), 44 + i * 2);
  fs.writeFileSync(file, buf);
}

(async () => {
  for (const t of teams) await getFlag(t.code);
  const srv = await serve();
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  const teamParam = encodeURIComponent(teams.map(t => `${t.name}:flags/${t.code}.png`).join(','));
  const url = s => `http://127.0.0.1:8765/index.html?seed=${s}&theme=${theme}&teams=${teamParam}&ep=${encodeURIComponent(ep)}`;

  // 1) find a seed with a clean race (winner, 26-42 seconds)
  let chosen = null;
  for (let tries = 0; tries < 15 && !chosen; tries++, seed += 7) {
    await page.goto(url(seed) + '&dry=1'); await page.evaluate(() => window.ready);
    const r = await page.evaluate(() => { let i; do { i = window.stepFrame(); } while (!i.done); return { t: i.simT, w: i.winner }; });
    console.log('dry seed', seed, JSON.stringify(r));
    if (r.w && r.t >= 26 && r.t <= 42) chosen = seed;
  }
  if (!chosen) chosen = seed;

  // 2) render frames
  await page.goto(url(chosen)); await page.evaluate(() => window.ready);
  const silent = path.join(OUT, 'silent.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', '30', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', silent]);
  let n = 0, info; const t0 = Date.now();
  while (true) {
    info = await page.evaluate(() => window.stepFrame());
    const buf = await page.screenshot({ type: 'jpeg', quality: 90 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (++n % 150 === 0) console.log(`frame ${n} sim ${info.simT.toFixed(1)}s elapsed ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    if (info.done) break;
  }
  const events = await page.evaluate(() => window.getEvents());
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  await browser.close(); srv.close();

  const dur = n / 30;
  const winEv = events.find(e => e.kind === 'win');
  buildSfx({ events }, dur, path.join(OUT, 'sfx.wav'));

  // 3) music ducks under the effects; fades in/out
  const musicDir = path.join(__dirname, 'music');
  const tracks = fs.readdirSync(musicDir).filter(f => f.endsWith('.mp3'));
  const music = path.join(musicDir, process.env.MUSIC && tracks.includes(process.env.MUSIC) ? process.env.MUSIC : tracks[chosen % tracks.length]);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', silent, '-i', path.join(OUT, 'sfx.wav'), '-i', music, '-filter_complex',
    `[1:a]asplit=2[sc][fx];[2:a]volume=0.5,afade=t=in:d=0.8,afade=t=out:st=${Math.max(0, dur - 1.5).toFixed(2)}:d=1.5[m];` +
    `[m][sc]sidechaincompress=threshold=0.02:ratio=6:attack=5:release=250[md];[md][fx]amix=inputs=2:normalize=0:duration=first[a]`,
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', dur.toFixed(2), '-movflags', '+faststart', path.join(OUT, 'race.mp4')]);
  const meta = { seed: chosen, theme, teams, winner: info.winner, winT: winEv ? +winEv.t.toFixed(2) : null, duration: +dur.toFixed(2), music: path.basename(music) };
  fs.writeFileSync(path.join(OUT, 'meta.json'), JSON.stringify(meta, null, 1));
  console.log('DONE', JSON.stringify(meta));
})().catch(e => { console.error(e); process.exit(1); });
