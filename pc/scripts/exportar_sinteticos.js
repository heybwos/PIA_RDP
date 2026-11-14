// Exporta el banco sintético de huellas desde la maqueta (sin navegador).
//
//   node pc/scripts/exportar_sinteticos.js [identidades=8] [impresiones=4]
//
// Toma del <script> de docs/maqueta/acceso_biometrico.html el bloque que va de
// "Utilidades" a "Huella: fases 2 a 4" (fingerParams y renderFinger) y lo ejecuta en
// un contexto aislado de Node. La maqueta no se modifica.
//
// Cada huella se guarda como el AS608 la entrega: 256 x 288, 4 bits por píxel,
// nibble alto primero, 36,864 bytes. Nombre: id<II>_imp<K>.bin.
// La impresión 0 es la plantilla (sin rotar ni mover); las demás llevan la misma
// variación que usa la maqueta para la muestra: rotación ±0.12 rad y ±7 px.

"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const raiz = path.resolve(__dirname, "..", "..");
const html = fs.readFileSync(path.join(raiz, "docs", "maqueta", "acceso_biometrico.html"), "utf8");
const ini = html.indexOf("Utilidades");
const fin = html.indexOf("Huella: fases 2 a 4");
if (ini < 0 || fin < 0) throw new Error("No encontré el generador en la maqueta");
const codigo = html.slice(html.lastIndexOf("/*", ini), html.lastIndexOf("/*", fin))
  .replace(/^const \$ = .*$/m, "");  // $ usa document; no hace falta

const ctx = { Math, Uint8Array, Uint32Array, Float32Array };
vm.createContext(ctx);
vm.runInContext(codigo + "\n;globalThis.__x={fingerParams,renderFinger,mulberry32,FW,FH};", ctx);
const { fingerParams, renderFinger, mulberry32, FW, FH } = ctx.__x;

const nId = parseInt(process.argv[2] || "8", 10);
const nImp = parseInt(process.argv[3] || "4", 10);
const salida = path.join(raiz, "pc", "tests", "fixtures", "huellas_sinteticas");
fs.mkdirSync(salida, { recursive: true });

for (let id = 1; id <= nId; id++) {
  const P = fingerParams(id);
  const r = mulberry32(5000 + id * 101);
  for (let k = 0; k < nImp; k++) {
    const imp = k === 0
      ? { rot: 0, dx: 0, dy: 0, seed: id * 13 + 1 }
      : { rot: (r() - 0.5) * 0.24, dx: (r() - 0.5) * 14, dy: (r() - 0.5) * 14, seed: id * 1000 + k * 37 };
    const { q4 } = renderFinger(P, imp);
    const buf = Buffer.alloc((FW * FH) / 2);
    for (let i = 0; i < buf.length; i++) buf[i] = (q4[2 * i] << 4) | q4[2 * i + 1];
    const nombre = `id${String(id).padStart(2, "0")}_imp${k}.bin`;
    fs.writeFileSync(path.join(salida, nombre), buf);
  }
}
console.log(`${nId * nImp} huellas en ${path.relative(raiz, salida)}`);
