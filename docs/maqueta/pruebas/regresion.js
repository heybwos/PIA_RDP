// Prueba de regresión de la maqueta: corre los cinco escenarios y revisa el veredicto.
// Uso (desde la raíz del repositorio):  npm i playwright  &&  npx playwright install chromium
//                                       node docs/maqueta/pruebas/regresion.js
const path = require('path');
const { chromium } = require('playwright');

const ESPERADO = { l1: true, l2: true, ih: false, ir: false, pin: false };

(async () => {
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage();
  let errores = 0;
  pagina.on('pageerror', e => { errores++; console.log('Error en la página:', e.message); });
  const archivo = path.resolve(__dirname, '..', 'acceso_biometrico.html');
  await pagina.goto('file://' + archivo.replace(/\\/g, '/'));
  await pagina.waitForFunction(() => window.__pia, null, { timeout: 60000 });
  const resultado = await pagina.evaluate(async () => {
    const P = window.__pia, salida = {};
    for (const s of ['l1', 'l2', 'ih', 'ir', 'pin']) {
      P.S.instant = true;
      await P.run(P.SCN[s], { seed: 11 });
      salida[s] = P.S.lastResult ? P.S.lastResult.ok : null;
    }
    return salida;
  });
  let bien = errores === 0;
  for (const [s, ok] of Object.entries(ESPERADO)) {
    const paso = resultado[s] === ok;
    bien = bien && paso;
    console.log(`${paso ? 'OK   ' : 'FALLA'} ${s}: ${resultado[s] ? 'concedido' : 'negado'} (esperado: ${ok ? 'concedido' : 'negado'})`);
  }
  console.log(`Errores en consola: ${errores}`);
  await navegador.close();
  process.exit(bien ? 0 : 1);
})();
