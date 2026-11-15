// Run after npm run build. All listeners bind loopback; no real DB/backend used.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { cp, readdir, readFile } from 'node:fs/promises';
import { once } from 'node:events';
import { setTimeout as delay } from 'node:timers/promises';

async function listen(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return server.address().port;
}
let unavailable = false;
const requests = [];
const backend = createServer((request, response) => {
  requests.push(request.url);
  response.writeHead(unavailable ? 503 : 200, { 'Content-Type': 'application/json' });
  response.end(unavailable ? JSON.stringify({ private: 'do-not-leak-traceback' }) : JSON.stringify({ status: 'healthy' }));
});
const backendPort = await listen(backend);
const reservation = createServer();
const port = await listen(reservation);
await new Promise(resolve => reservation.close(resolve));
await cp('.next/static', '.next/standalone/.next/static', { recursive: true });
await cp('public', '.next/standalone/public', { recursive: true });
let logs = '';
const app = spawn(process.execPath, ['.next/standalone/server.js'], {
  env: {
    PATH: process.env.PATH, NODE_ENV: 'production', NEXT_TELEMETRY_DISABLED: '1',
    HOSTNAME: '127.0.0.1', PORT: String(port),
    INTERNAL_API_URL: `http://127.0.0.1:${backendPort}`,
  },
  stdio: ['ignore', 'pipe', 'pipe'],
});
app.stdout.on('data', chunk => { logs += chunk; });
app.stderr.on('data', chunk => { logs += chunk; });
const base = `http://127.0.0.1:${port}`;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { ready = (await fetch(`${base}/health`)).ok; } catch { /* wait for startup */ }
    if (ready || app.exitCode !== null) break;
    await delay(100);
  }
  assert.ok(ready, logs);
  assert.deepEqual(await (await fetch(`${base}/health`)).json(), { status: 'healthy' });
  const home = await fetch(base);
  assert.equal(home.status, 200);
  const html = await home.text();
  assert.match(html, /Бизнес Афиша/);
  assert.match(html, /Соединение с сервисом установлено/);
  const script = html.match(/src="([^\"]+\.js[^\"]*)"/);
  assert.ok(script, 'HTML references a browser chunk');
  assert.equal((await fetch(new URL(script[1].replaceAll('&amp;', '&'), base))).status, 200);
  assert.equal((await fetch(`${base}/unknown-page`)).status, 404);
  unavailable = true;
  const failed = await fetch(base);
  assert.equal(failed.status, 200);
  const fallback = await failed.text();
  assert.match(fallback, /Сервис временно недоступен/);
  assert.doesNotMatch(fallback, /do-not-leak-traceback|INTERNAL_API_URL|127\.0\.0\.1|backend:8039/);
  assert.ok(requests.length >= 2);
  assert.ok(requests.every(path => path === '/health'), JSON.stringify(requests));
  for (const file of await readdir('.next/static', { recursive: true })) {
    if (!file.endsWith('.js')) continue;
    const source = await readFile(`.next/static/${file}`, 'utf8');
    assert.doesNotMatch(source, /INTERNAL_API_URL|backend:8039|afisha-internal-canary/);
  }
  console.log('PASS standalone: home, health, static JS, 404, API fallback, no secrets/DB, public-only requests and bundle isolation');
} finally {
  if (app.exitCode === null && app.signalCode === null) {
    const exited = once(app, 'exit');
    app.kill('SIGTERM');
    const watchdog = setTimeout(() => app.kill('SIGKILL'), 5000);
    await exited;
    clearTimeout(watchdog);
  }
  await new Promise(resolve => backend.close(resolve));
}
