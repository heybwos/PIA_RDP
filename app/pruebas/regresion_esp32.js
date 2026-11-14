// Regresión del modo ESP32 contra el ESP32 falso: siembra una carpeta aparte, levanta el falso y
// el backend, y en la app pulsa ESP32 y "Buscar ESP32". El falso teclea 21#2468# y manda la huella;
// se espera "concedido nivel 2", cero errores de consola y cero peticiones fuera de localhost.
// No toca los puertos COM reales (busca solo el socket del falso).
//
//   node app/pruebas/regresion_esp32.js
const path = require('path');
const fs = require('fs');
const { spawn, spawnSync } = require('child_process');
const { chromium } = require('playwright');

const RAIZ = path.resolve(__dirname, '..', '..');
const PY = process.platform === 'win32' ? path.join(RAIZ, '.venv', 'Scripts', 'python.exe') : path.join(RAIZ, '.venv', 'bin', 'python');
const DATOS = path.join(RAIZ, 'datos', 'prueba_esp32');
const PUERTO_APP = 8124, PUERTO_FALSO = 5334;
const esperar = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  if (!fs.existsSync(path.join(DATOS, 'pia.db'))) {
    const s = spawnSync(PY, [path.join(RAIZ, 'pc', 'herramientas', 'sembrar_prueba_esp32.py'), DATOS], { stdio: 'inherit' });
    if (s.status !== 0) process.exit(1);
  }
  const falso = spawn(PY, [path.join(RAIZ, 'pc', 'herramientas', 'esp32_falso.py'), '--puerto', String(PUERTO_FALSO), '--guion', '21#2468#'], { stdio: 'ignore' });
  const servidor = spawn(PY, ['-m', 'pia', '--puerto', String(PUERTO_APP), '--datos', DATOS,
    '--camara-archivo', path.join(RAIZ, 'datos', 'datasets', 'orl', 's5', '8.pgm')], { cwd: path.join(RAIZ, 'pc'), stdio: 'ignore' });
  let navegador, bien = false;
  try {
    for (let i = 0; i < 40; i++) {
      try { if ((await fetch(`http://127.0.0.1:${PUERTO_APP}/api/bitacora?limite=1`)).ok) break; } catch (e) {}
      await esperar(500);
    }
    navegador = await chromium.launch({ channel: process.env.PW_CANAL || 'msedge' });
    const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
    let errores = 0; const externas = [];
    pagina.on('pageerror', e => { errores++; console.log('Error en la página:', e.message); });
    pagina.on('console', m => { if (m.type() === 'error') { errores++; console.log('Consola:', m.text()); } });
    pagina.on('request', r => { const u = new URL(r.url()); if (!['127.0.0.1', 'localhost'].includes(u.hostname) && u.protocol !== 'data:') externas.push(r.url()); });
    await pagina.goto(`http://127.0.0.1:${PUERTO_APP}/?puerto=socket://127.0.0.1:${PUERTO_FALSO}`);
    await pagina.waitForFunction(() => window.__pia, null, { timeout: 30000 });
    const r = await pagina.evaluate(async () => {
      const P = window.__pia; P.S.speed = 4;
      document.querySelector('#mEsp').click(); document.querySelector('#scanBtn').click();
      const t0 = Date.now();
      while (!P.S.lastResult && Date.now() - t0 < 90000) await new Promise(r => setTimeout(r, 200));
      return { res: P.S.lastResult, conn: document.querySelector('#connTxt').textContent,
               teclas: [...document.querySelectorAll('#slotId .slot')].map(s => s.textContent).join('') };
    });
    await pagina.screenshot({ path: path.join(RAIZ, 'datos', 'capturas_app', 'esp32_falso.png') });
    const ok = r.res && r.res.ok && r.res.nivel === 2;
    console.log(`${ok ? 'OK   ' : 'FALLA'} ESP32 falso (${r.conn}, ID ${r.teclas}): ${r.res ? (r.res.ok ? 'concedido nivel ' + r.res.nivel : 'negado (' + r.res.motivo + ')') : 'sin veredicto'}`);
    console.log(`Errores en consola: ${errores}`);
    console.log(`Peticiones fuera de localhost: ${externas.length}`);
    bien = ok && errores === 0 && externas.length === 0;
  } finally {
    if (navegador) await navegador.close();
    servidor.kill(); falso.kill();
  }
  console.log(bien ? 'REGRESIÓN ESP32 OK' : 'REGRESIÓN ESP32 CON FALLAS');
  process.exit(bien ? 0 : 1);
})();
