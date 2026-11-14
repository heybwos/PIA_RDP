// Regresión de la app: levanta el backend, corre los cinco escenarios en el navegador y revisa
// el veredicto, cero errores de consola y cero peticiones fuera de localhost. Guarda capturas de
// las cuatro etapas a 1440 × 900 en datos/capturas_app/ (no van a git: llevan caras y huellas).
//
// Uso (desde la raíz del repositorio, con el backend ya sembrado: pc/scripts/sembrar_simular.py):
//   npm i playwright            (una vez; usa el Edge instalado, no descarga navegadores)
//   node app/pruebas/regresion.js
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const RAIZ = path.resolve(__dirname, '..', '..');
const PUERTO = 8123;
const ESPERADO = { l1: [true, 1], l2: [true, 2], ih: [false, 0], ir: [false, 0], pin: [false, 0] };
const PYTHON = process.platform === 'win32'
  ? path.join(RAIZ, '.venv', 'Scripts', 'python.exe')
  : path.join(RAIZ, '.venv', 'bin', 'python');

const esperar = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const servidor = spawn(PYTHON, ['-m', 'pia', '--puerto', String(PUERTO)], { cwd: path.join(RAIZ, 'pc'), stdio: 'ignore' });
  let navegador;
  let bien = true;
  try {
    for (let i = 0; i < 40; i++) { // espera a que el backend responda
      try { const r = await fetch(`http://127.0.0.1:${PUERTO}/api/bitacora?limite=1`); if (r.ok) break; } catch (e) {}
      await esperar(500);
    }
    navegador = await chromium.launch({ channel: process.env.PW_CANAL || 'msedge' });
    const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
    let errores = 0, externas = [];
    pagina.on('pageerror', e => { errores++; console.log('Error en la página:', e.message); });
    pagina.on('console', m => { if (m.type() === 'error') { errores++; console.log('Consola:', m.text()); } });
    pagina.on('request', r => { const u = new URL(r.url()); if (!['127.0.0.1', 'localhost'].includes(u.hostname) && u.protocol !== 'data:') externas.push(r.url()); });

    await pagina.goto(`http://127.0.0.1:${PUERTO}/`);
    await pagina.waitForFunction(() => window.__pia && document.querySelector('#scn option[value="l1"]'), null, { timeout: 30000 });

    for (const [clave, [concede, nivel]] of Object.entries(ESPERADO)) {
      const r = await pagina.evaluate(async clave => {
        const P = window.__pia;
        P.S.instant = true; P.S.lastResult = null;
        document.querySelector('#scn').value = clave;
        document.querySelector('#runBtn').click();
        const t0 = Date.now();
        while ((P.S.running || !P.S.lastResult) && Date.now() - t0 < 60000) await new Promise(r => setTimeout(r, 100));
        while (P.cola().length && Date.now() - t0 < 60000) await new Promise(r => setTimeout(r, 100));
        return P.S.lastResult;
      }, clave);
      const paso = !!r && r.ok === concede && r.nivel === nivel;
      bien = bien && paso;
      console.log(`${paso ? 'OK   ' : 'FALLA'} ${clave}: ${r ? (r.ok ? 'concedido nivel ' + r.nivel : 'negado (' + r.motivo + ')') : 'sin veredicto'}`);
    }

    // capturas de las cuatro etapas tras una verificación l2 completa
    const carpeta = path.join(RAIZ, 'datos', 'capturas_app');
    fs.mkdirSync(carpeta, { recursive: true });
    await pagina.evaluate(async () => {
      const P = window.__pia; P.S.instant = true; P.S.lastResult = null;
      document.querySelector('#scn').value = 'l2'; document.querySelector('#runBtn').click();
      const t0 = Date.now();
      while ((P.S.running || !P.S.lastResult || P.cola().length) && Date.now() - t0 < 60000) await new Promise(r => setTimeout(r, 100));
      P.S.instant = false;
    });
    for (const n of [1, 2, 3, 4]) {
      await pagina.evaluate(n => window.__pia.mostrarEtapa(n, false), n);
      await esperar(900);
      await pagina.screenshot({ path: path.join(carpeta, `etapa_${n}.png`) });
    }
    console.log(`Capturas en ${path.relative(RAIZ, carpeta)}`);
    console.log(`Errores en consola: ${errores}`);
    console.log(`Peticiones fuera de localhost: ${externas.length}${externas.length ? ' ' + externas.join(', ') : ''}`);
    bien = bien && errores === 0 && externas.length === 0;
  } finally {
    if (navegador) await navegador.close();
    servidor.kill();
  }
  console.log(bien ? 'REGRESIÓN OK' : 'REGRESIÓN CON FALLAS');
  process.exit(bien ? 0 : 1);
})();
