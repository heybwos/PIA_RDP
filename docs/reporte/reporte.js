// Genera docs/reporte/Reporte_PIA_RDP.docx (reporte técnico del PIA).
//   node docs/reporte/reporte.js        (necesita el paquete npm "docx")
// Los números vienen de datos/pia.db y docs/ESTADO_DEL_PROYECTO.md (26 nov 2026).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, BorderStyle, HeadingLevel, PageBreak, TableOfContents, Footer, PageNumber, LevelFormat,
  VerticalAlign, PageBorderDisplay, PageBorderOffsetFrom, TableLayoutType,
} = require("docx");

const AQUI = __dirname;
const FIG = (f) => path.join(AQUI, "figuras", f);
const FUENTE = "Arial";
const AZUL = "2E74B5", FRANJA_AZUL = "DAE3F3", FRANJA_VERDE = "E2EFDA";
// Contenido en carta con márgenes de 1 in: 9360 DXA de ancho útil (las tablas suman eso)

// ------------------------------------------------------------ ayudantes de texto
const t = (texto, o = {}) => new TextRun({ text: texto, font: FUENTE, ...o });
const p = (runs, o = {}) => new Paragraph({
  children: (Array.isArray(runs) ? runs : [runs]).map((r) => (typeof r === "string" ? t(r) : r)),
  spacing: { before: 100, after: 120, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o,
});
const h1 = (texto) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(texto)] });
const h2 = (texto) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(texto)] });
const lista = (items, ref = "vinetas") => items.map((it) => new Paragraph({
  numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 290 },
  children: (Array.isArray(it) ? it : [it]).map((r) => (typeof r === "string" ? t(r) : r)),
}));
const ecuacion = (texto) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
  children: [new TextRun({ text: texto, font: "Cambria Math", italics: true, size: 22 })],
});
let nFig = 0, nTab = 0;
const pieFigura = (texto) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
  children: [t(`Figura ${++nFig}. `, { bold: true, size: 20 }), t(texto, { size: 20 })],
});
const tituloTabla = (texto) => new Paragraph({
  keepNext: true, spacing: { before: 120, after: 60 },
  children: [t(`Tabla ${++nTab}. `, { bold: true, size: 20 }), t(texto, { size: 20 })],
});

// ------------------------------------------------------------ tablas
const borde = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
function tabla(anchos, filas, { encabezado = true, tam = 19 } = {}) {
  const total = anchos.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: anchos, layout: TableLayoutType.FIXED,
    rows: filas.map((fila, i) => new TableRow({
      tableHeader: encabezado && i === 0, cantSplit: true,
      children: fila.map((celda, j) => new TableCell({
        width: { size: anchos[j], type: WidthType.DXA }, borders: bordes,
        margins: { top: 50, bottom: 50, left: 90, right: 90 }, verticalAlign: VerticalAlign.CENTER,
        shading: encabezado && i === 0 ? { fill: FRANJA_AZUL, type: ShadingType.CLEAR, color: "auto" } : undefined,
        children: String(celda).split("\n").map((linea) => new Paragraph({
          spacing: { after: 0, line: 260 }, keepNext: i < filas.length - 1, // la tabla no se parte entre páginas
          children: [t(linea, { size: tam, bold: encabezado && i === 0 })],
        })),
      })),
    })),
  });
}

// ------------------------------------------------------------ imágenes
function tamPng(f) {
  const b = fs.readFileSync(f);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), datos: b };
}
function imagen(f, anchoPx) {
  const { w, h, datos } = tamPng(f);
  return new ImageRun({ type: "png", data: datos, transformation: { width: anchoPx, height: Math.round((anchoPx * h) / w) } });
}
const figura = (archivo, anchoPx, pie) => [
  new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 0 }, children: [imagen(FIG(archivo), anchoPx)] }),
  pieFigura(pie),
];

// ------------------------------------------------------------ portada
const ANCHO_PORTADA = 12240 - 2 * 1134; // carta, márgenes de 2 cm
const sinBordes = { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } };
const alto91 = (f) => { const { w, h } = tamPng(FIG(f)); return { width: Math.round((91 * w) / h), height: 91 }; };
const logos = new Table({
  width: { size: ANCHO_PORTADA, type: WidthType.DXA }, columnWidths: [ANCHO_PORTADA / 2, ANCHO_PORTADA / 2],
  rows: [new TableRow({ children: [
    new TableCell({ width: { size: ANCHO_PORTADA / 2, type: WidthType.DXA }, borders: sinBordes, children: [new Paragraph({ alignment: AlignmentType.LEFT,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG("logo_uanl.png")), transformation: alto91("logo_uanl.png") })] })] }),
    new TableCell({ width: { size: ANCHO_PORTADA / 2, type: WidthType.DXA }, borders: sinBordes, children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new ImageRun({ type: "png", data: fs.readFileSync(FIG("logo_fime.png")), transformation: alto91("logo_fime.png") })] })] }),
  ] })],
});
const franja = (texto, fill, antes, extra = []) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: antes, after: 0, line: 300 },
  shading: { fill, type: ShadingType.CLEAR, color: "auto" },
  border: { top: { style: BorderStyle.SINGLE, size: 1, color: fill, space: 6 }, bottom: { style: BorderStyle.SINGLE, size: 1, color: fill, space: 6 } },
  children: [new TextRun({ text: texto, font: "Bahnschrift SemiCondensed", size: 36 }), ...extra],
});
const celdaPortada = (texto, ancho, { enc = false, centro = true } = {}) => new TableCell({
  width: { size: ancho, type: WidthType.DXA }, borders: bordes, verticalAlign: VerticalAlign.CENTER,
  margins: { top: 40, bottom: 40, left: 80, right: 80 },
  children: [new Paragraph({ alignment: centro ? AlignmentType.CENTER : AlignmentType.LEFT,
    children: [new TextRun({ text: texto, font: "Century Gothic", size: 19, bold: enc, color: enc ? AZUL : "000000" })] })],
});
const colsAlumno = [3972, 1250, 1100, 1050, 1350, 1250]; // suma = 9972
const integrantes = [
  ["NESTOR ALEJANDRO JIMENEZ BARRAGAN", "2132189", "9", "IMC", "LMV", "003"],
  ["ORLANDO ALDAIR BELTRAN LUNA", "1878812", "", "IMC", "LMV", "003"],
  ["LUIS CARLOS MANRIQUE OSORIO", "1994165", "", "IMC", "LMV", "003"],
  ["IVAN ALEJANDRO ALVARADO SEGOVIA", "1992270", "", "IMC", "LMV", "003"],
  ["SANDRA NICOLE ORTIZ DE LA RIVA", "2037056", "", "IMC", "LMV", "003"],
  ["SANTIAGO CISNEROS", "2023472", "", "IMC", "LMV", "003"],
];
const tablaAlumnos = new Table({
  width: { size: ANCHO_PORTADA, type: WidthType.DXA }, columnWidths: colsAlumno, layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: ["NOMBRE", "MATRÍCULA", "SEMESTRE", "CARRERA", "FRECUENCIA", "GRUPO"].map((x, j) => celdaPortada(x, colsAlumno[j], { enc: true })) }),
    ...integrantes.map((fila) => new TableRow({ height: { value: 330, rule: "atLeast" },
      children: fila.map((x, j) => celdaPortada(x, colsAlumno[j], { centro: j > 0 })) })),
  ],
});
const tablaDocente = new Table({
  width: { size: ANCHO_PORTADA, type: WidthType.DXA }, columnWidths: [2400, ANCHO_PORTADA - 2400], layout: TableLayoutType.FIXED,
  rows: [new TableRow({ children: [celdaPortada("PROFESOR", 2400, { enc: true }), celdaPortada("ANTONIO JUAREZ ALONSO", ANCHO_PORTADA - 2400)] })],
});
const portada = [
  logos,
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 0, line: 380 },
    children: [new TextRun({ text: "UNIVERSIDAD AUTONOMA DE NUEVO LEON", font: "Century Gothic", size: 30, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0, line: 380 },
    children: [new TextRun({ text: "FACULTAD DE INGENIERIA MECANICA Y ELECTRICA", font: "Century Gothic", size: 30, bold: true })] }),
  franja("CLASE ORDINARIA", FRANJA_AZUL, 700),
  franja("RECONOCIMIENTO DE PATRONES", FRANJA_VERDE, 500),
  franja("PRODUCTO INTEGRADOR DE APRENDIZAJE", FRANJA_AZUL, 600,
    [new TextRun({ text: "Control de acceso biométrico con PIN, huella y rostro", font: "Bahnschrift SemiCondensed", size: 30, break: 1 })]),
  new Paragraph({ spacing: { before: 500, after: 0 }, children: [] }),
  tablaAlumnos,
  new Paragraph({ spacing: { before: 400, after: 0 }, children: [] }),
  tablaDocente,
  new Paragraph({ spacing: { before: 700, after: 0 },
    children: [new TextRun({ text: "Viernes 27 de noviembre del 2026", font: "Century Gothic", size: 20 })] }),
];

// ------------------------------------------------------------ contenido
const contenido = [
  new Paragraph({ spacing: { after: 200 }, children: [t("Índice", { bold: true, size: 32 })] }),
  new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),

  h1("1. Introducción"),
  p("Un control de acceso con un solo factor, como un PIN o una tarjeta, deja de servir cuando ese factor se comparte o se pierde. Los sistemas biométricos ligan el acceso a rasgos de la propia persona, y al combinar dos o más rasgos se reducen los errores que cada uno tiene por separado (Ross y Jain, 2003). En este proyecto se aplicaron los métodos de Reconocimiento de Patrones a un caso físico: una caja con dos compartimentos que se abren solo cuando el PIN, la huella dactilar y el rostro coinciden con los de un usuario registrado, y el nivel de acceso de ese usuario determina cuántos compartimentos se abren."),
  p("La huella se procesa con campo de orientación, filtros de Gabor y extracción de minucias, y se compara mediante un matching por grafos (Maltoni et al., 2009; Hong et al., 1998). El rostro se detecta con Viola-Jones, se alinea, se normaliza con CLAHE y se reconoce con Eigenfaces y distancia euclidiana (Viola y Jones, 2001; Zuiderveld, 1994; Turk y Pentland, 1991). El reconocimiento corre en Python en una PC. Un ESP32 controla el teclado, el sensor de huella, la pantalla y los servos, y una aplicación web muestra cada fase con los datos reales del proceso."),

  h1("2. Objetivo"),
  p("Diseñar y construir un sistema de control de acceso por niveles que verifique la identidad con tres factores (PIN, huella y rostro), usando solo los métodos clásicos de reconocimiento de patrones indicados en el PIA, y medir su desempeño con las tasas de falsa aceptación (FAR), falso rechazo (FRR) y error igual (EER)."),

  h1("3. Descripción del sistema"),
  h2("3.1 Componentes"),
  p("La Tabla 1 resume el hardware y el software. El reconocimiento no usa redes neuronales ni el matching interno del sensor: toda decisión la calcula el programa en Python."),
  tituloTabla("Componentes del sistema."),
  tabla([2100, 2700, 4560], [
    ["Componente", "Modelo", "Función"],
    ["Microcontrolador", "ESP32 DevKit V1 (CH340)", "Lee el teclado y el sensor, maneja la pantalla y los servos; habla con la PC por USB a 921 600 baudios."],
    ["Sensor de huella", "AS608", "Entrega la imagen cruda de 256 × 288 píxeles a 4 bits por píxel."],
    ["Teclado", "Matricial 4 × 4 de membrana", "Captura el ID (2 dígitos) y el PIN (4 dígitos)."],
    ["Pantalla", "OLED SSD1306, 128 × 64", "Instrucciones y resultado para el usuario."],
    ["Actuadores", "2 servos SG90 (GPIO18 y GPIO19)", "Cerrojos de los compartimentos 1 y 2."],
    ["Cámara", "Celular Android con IP Webcam", "Video MJPEG de 640 × 480 por WiFi hacia la PC."],
    ["Procesamiento", "PC con Python (NumPy, OpenCV, scikit-image, FastAPI)", "Reconocimiento, decisión, base de datos SQLite y aplicación web."],
  ]),

  h2("3.2 Flujo de una verificación"),
  p("Cada verificación sigue los pasos de la lista y queda registrada en una bitácora con todos sus puntajes:"),
  ...lista([
    "El usuario teclea su ID y su PIN. La PC compara el PIN con su hash (PBKDF2-SHA256 con sal y 200 000 iteraciones); el PIN nunca se guarda en claro (Moriarty et al., 2017).",
    "Pone el dedo en el AS608. El ESP32 descarga la imagen cruda y la envía a la PC con un CRC-32. Si la huella sale débil se piden hasta 3 capturas sin volver a teclear el PIN.",
    "Mira a la cámara. La PC toma el cuadro cuando el rostro lleva 1.5 s dentro del óvalo guía.",
    "La PC decide (sección 6) y el ESP32 muestra el resultado y mueve los servos: el nivel 1 (Lector) abre el compartimento 1 y el nivel 2 (Editor) abre los dos, uno a la vez con 300 ms entre ellos.",
  ], "numeros"),

  h1("4. Reconocimiento de huella"),
  p("La Tabla 2 muestra las fases. Al registrarse, cada usuario deja 5 capturas; al verificar, la huella se compara con las 5 plantillas y se conserva el mejor puntaje."),
  tituloTabla("Fases del reconocimiento de huella."),
  tabla([2000, 3000, 4360], [
    ["Fase", "Método", "Detalle"],
    ["Captura", "AS608 (comando UpImage)", "256 × 288 píxeles, 4 bits; 36 864 bytes por imagen."],
    ["Preprocesamiento", "Normalización, CLAHE y segmentación", "Bloques de 16 píxeles; se descartan los de varianza baja (fondo)."],
    ["Orientación", "Campo de orientación por gradientes", "Suavizado sobre el doble del ángulo (Hong et al., 1998)."],
    ["Realce", "Banco de 24 filtros de Gabor", "Cada bloque se filtra con la orientación local de sus crestas."],
    ["Extracción", "Binarización, esqueleto y número de cruce", "Terminaciones (CN = 1) y bifurcaciones (CN = 3) con su dirección; mínimo 10 minucias por plantilla."],
    ["Matching", "Grafos de minucias", "Estructura local con los 4 vecinos más cercanos; alineación global por rotación y traslación, tolerancia de 10 píxeles. Puntaje = m² / (nA · nB)."],
  ]),

  h1("5. Reconocimiento de rostro"),
  p("Las fases están en la Tabla 3. El modelo de Eigenfaces se reentrena con cada alta: hoy usa 210 caras (las 90 de los seis usuarios y 120 de fondo del banco ORL) y k = 96 componentes, que explican el 95 % de la varianza."),
  tituloTabla("Fases del reconocimiento de rostro."),
  tabla([2000, 3000, 4360], [
    ["Fase", "Método", "Detalle"],
    ["Captura", "IP Webcam, 640 × 480", "Vista en vivo con óvalo guía; registro de 15 cuadros por usuario."],
    ["Detección", "Viola-Jones (cascadas de Haar de OpenCV)", "Rostro y ojos (Viola y Jones, 2001)."],
    ["Alineación", "Rotación y escala con los ojos", "Cara de 64 × 64 píxeles con los ojos en posiciones fijas."],
    ["Normalización", "CLAHE y máscara elíptica", "Quita fondo, cabello y cuello (Zuiderveld, 1994)."],
    ["Extracción", "Eigenfaces con NumPy", "PCA con el truco de la matriz pequeña; k componentes hasta 95 % de varianza (Turk y Pentland, 1991)."],
    ["Matching", "Distancia euclidiana", "Mínima entre los pesos de la captura y los de las caras registradas del usuario."],
  ]),

  h1("6. Decisión"),
  p("Cada factor se normaliza con su umbral calibrado (u_h para la huella y u_r para el rostro), de modo que vale 0.50 justo en el umbral:"),
  ecuacion("s_h = min(1, puntaje / (2 · u_h))          s_r = max(0, 1 − d / (2 · u_r))"),
  p("El acceso se concede solo si el PIN es correcto, s_h ≥ 0.50, s_r ≥ 0.50 y la suma ponderada 0.5 · s_h + 0.5 · s_r ≥ 0.60 (Ross y Jain, 2003). Exigir que cada factor pase su propio umbral evita que una huella muy buena compense un rostro ajeno, o al revés."),

  h1("7. Calibración y resultados"),
  h2("7.1 Calibración"),
  p("Los umbrales se eligieron con puntajes de comparaciones genuinas (la misma persona) e impostoras (personas distintas). La huella se calibró con un banco de 6 dedos de una persona, 8 capturas cada uno; cada dedo cuenta como una identidad. El rostro se calibró el 26 de noviembre en el salón de la demostración: 10 cuadros de una segunda tanda de cada usuario (14, 15, 21, 33, 88 y 99) contra sus registros, y como impostores los otros usuarios y 160 caras del banco ORL. La Tabla 4 resume los resultados."),
  tituloTabla("Calibración activa."),
  tabla([1500, 1500, 1100, 1100, 1100, 1100, 1960], [
    ["Factor", "Criterio", "Umbral", "FAR", "FRR", "EER", "Comparaciones"],
    ["Huella (AS608)", "FAR = 0", "0.180", "0 %", "33 %", "16.7 %", "18 genuinas, 90 impostoras"],
    ["Rostro (cámara)", "EER", "10.24", "7.7 %", "8.3 %", "8.0 %", "60 genuinas, 1260 impostoras"],
  ]),
  p("Para el rostro se probó primero el criterio FAR = 0: con tres usuarios el umbral quedaba en 9.25 y rechazaba al 45 % de los usuarios legítimos, porque las distancias de genuinos e impostores se enciman. Por eso se usó el EER, que fue de 6.7 %, 10 %, 8 % y 8.0 % con tres, cuatro, cinco y seis usuarios. El 7.7 % de impostores que el rostro acepta todavía tiene que pasar la huella y la fusión. Las Figuras 1 y 2 muestran las distribuciones y las curvas FAR y FRR."),
  ...figura("calibracion_huella.png", 520, "Calibración de la huella: distribuciones de puntajes y curvas FAR (rojo) y FRR (verde)."),
  ...figura("calibracion_rostro.png", 520, "Calibración del rostro: distribuciones de distancias y curvas FAR y FRR."),
  p("Para el modo de simulación (sin hardware) se usan los bancos públicos FVC2002 DB1_B para huella y ORL para rostro (Maio et al., 2002; Samaria y Harter, 1994), con un EER de 0.2 % y 8.2 % respectivamente."),

  h2("7.2 Verificaciones con la caja"),
  p("La Tabla 5 reúne las verificaciones del 26 de noviembre en el salón. La primera falló porque las caras se habían registrado con la luz de otro lugar; después de registrarlas en el salón, los usuarios legítimos entraron con su nivel. En la última, una compañera tecleó el ID y el PIN de otro usuario: su rostro pasó por poco el umbral (0.541), pero su huella no (0.356) y el acceso se negó."),
  tituloTabla("Verificaciones del 26 de noviembre."),
  tabla([2600, 1300, 1700, 1100, 2660], [
    ["Intento", "Huella s_h", "Rostro d (s_r)", "Fusión", "Resultado"],
    ["ID 21, caras registradas en casa", "0.929", "8.60 (0.495)", "0.712", "Negado: rostro"],
    ["ID 21, caras registradas en el salón", "1.000", "7.82 (0.594)", "0.797", "Concedido, nivel 2"],
    ["ID 14, usuaria legítima", "1.000", "2.75 (0.865)", "0.932", "Concedido, nivel 1"],
    ["ID 21 tecleado por la usuaria 14 (impostora)", "0.356", "9.35 (0.541)", "0.448", "Negado: huella"],
  ]),

  h2("7.3 Prueba de aceptación"),
  p("La prueba planeada era de 10 intentos genuinos y 10 de impostor por persona; en el impostor, otra persona teclea el ID y el PIN del usuario y pone su propio dedo y su rostro. El 26 de noviembre, después del registro en el salón, se alcanzaron a hacer los intentos de la Tabla 6. Los 5 genuinos entraron con su nivel y los 3 de impostor se negaron: en dos de ellos el rostro del impostor sí pasó su umbral y fue la huella la que lo detuvo."),
  tituloTabla("Intentos con la caja después del registro en el salón (26 de noviembre)."),
  tabla([2000, 2400, 2400, 2560], [
    ["Usuario", "Genuinos aceptados", "Impostores rechazados", "Observaciones"],
    ["14 (Sandra)", "1 / 1", "—", ""],
    ["15 (Luis)", "1 / 1", "—", ""],
    ["21 (Nestor)", "2 / 2", "2 / 2", "Un impostor pasó el rostro (0.541); lo detuvo la huella."],
    ["33 (Orlando)", "—", "—", "Sin intentos registrados."],
    ["88 (Ivan)", "1 / 1", "1 / 1", "El impostor pasó el rostro (0.520); lo detuvo la huella."],
    ["99 (Santiago)", "—", "—", "3 intentos con PIN incorrecto, negados antes de la biometría."],
    ["Sistema", "5 / 5 (FRR = 0 %)", "3 / 3 (FAR = 0 %)", "Muestra pequeña: 8 intentos."],
  ]),
  p("Con 8 intentos, un FAR y un FRR de 0 % solo indican que no hubo errores en esta muestra; no son una estimación precisa de las tasas del sistema. Las tasas de cada factor de la Tabla 4 se calcularon con muchas más comparaciones."),

  h1("8. Limitaciones"),
  ...lista([
    "El AS608 entrega imágenes de 4 bits y de área pequeña; el banco para calibrar la huella es de una sola persona, así que su umbral es provisional.",
    "Con seis usuarios reales, la FAR del rostro se estima con pocas comparaciones entre personas del equipo.",
    "Eigenfaces es sensible a la iluminación: hay que registrar y verificar con la misma luz y la cámara en la misma posición.",
    "La red WiFi de la facultad aísla a los equipos entre sí; la cámara se conecta por el hotspot del celular.",
  ]),

  h1("9. Conclusiones"),
  p("El sistema cumplió con lo que pedía el PIA. La caja abre el compartimento que corresponde al nivel del usuario solo cuando el PIN, la huella y el rostro coinciden, y la aplicación muestra cada fase del reconocimiento con datos reales."),
  p("En la prueba con impostor del 26 de noviembre, el rostro de una compañera pasó por poco el umbral de otro usuario, pero su huella no, y el sistema negó el acceso. Con los datos disponibles, el rostro alcanzó un EER de 8.0 % y la huella uno de 16.7 %, así que ninguno de los dos factores sería confiable por sí solo; fue la combinación la que evitó el acceso indebido."),
  p("Lo que más pesó en los resultados fueron las limitaciones de la sección 8, en particular el banco de huellas de una sola persona y la iluminación: las caras registradas en casa fallaron en el salón hasta que se volvieron a registrar ahí. Con más usuarios y un banco de huellas de varias personas se podrían estimar los umbrales con más confianza."),

  new Paragraph({ children: [new PageBreak()] }),
  h1("Referencias"),
  ...[
    "Hong, L., Wan, Y., y Jain, A. (1998). Fingerprint image enhancement: Algorithm and performance evaluation. IEEE Transactions on Pattern Analysis and Machine Intelligence, 20(8), 777–789. https://doi.org/10.1109/34.709565",
    "Maio, D., Maltoni, D., Cappelli, R., Wayman, J. L., y Jain, A. K. (2002). FVC2002: Second fingerprint verification competition. En Proceedings of the 16th International Conference on Pattern Recognition (Vol. 3, pp. 811–814). IEEE. https://doi.org/10.1109/ICPR.2002.1048144",
    "Maltoni, D., Maio, D., Jain, A. K., y Prabhakar, S. (2009). Handbook of fingerprint recognition (2.ª ed.). Springer. https://doi.org/10.1007/978-1-84882-254-2",
    "Moriarty, K., Kaliski, B., y Rusch, A. (2017). PKCS #5: Password-based cryptography specification version 2.1 (RFC 8018). Internet Engineering Task Force. https://doi.org/10.17487/RFC8018",
    "Ross, A., y Jain, A. (2003). Information fusion in biometrics. Pattern Recognition Letters, 24(13), 2115–2125. https://doi.org/10.1016/S0167-8655(03)00079-5",
    "Samaria, F. S., y Harter, A. C. (1994). Parameterisation of a stochastic model for human face identification. En Proceedings of 1994 IEEE Workshop on Applications of Computer Vision (pp. 138–142). IEEE. https://doi.org/10.1109/ACV.1994.341300",
    "Turk, M., y Pentland, A. (1991). Eigenfaces for recognition. Journal of Cognitive Neuroscience, 3(1), 71–86. https://doi.org/10.1162/jocn.1991.3.1.71",
    "Viola, P., y Jones, M. (2001). Rapid object detection using a boosted cascade of simple features. En Proceedings of the 2001 IEEE Computer Society Conference on Computer Vision and Pattern Recognition (Vol. 1, pp. I-511–I-518). IEEE. https://doi.org/10.1109/CVPR.2001.990517",
    "Zuiderveld, K. (1994). Contrast limited adaptive histogram equalization. En P. S. Heckbert (Ed.), Graphics gems IV (pp. 474–485). Academic Press.",
  ].map((r) => new Paragraph({ spacing: { after: 120, line: 280 }, indent: { left: 720, hanging: 720 }, children: [t(r, { size: 21 })] })),
];

// ------------------------------------------------------------ documento
const carta = { size: { width: 12240, height: 15840 } };
const doc = new Document({
  creator: "Nestor Alejandro Jiménez Barragán",
  title: "PIA de Reconocimiento de Patrones: control de acceso biométrico",
  styles: {
    default: { document: { run: { font: FUENTE, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FUENTE, size: 28, bold: true, color: "1F3864" },
        paragraph: { spacing: { before: 300, after: 120 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FUENTE, size: 24, bold: true, color: "2E74B5" },
        paragraph: { spacing: { before: 200, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "numeros", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
  ] },
  sections: [
    {
      properties: { page: { ...carta, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 },
        borders: {
          pageBorders: { display: PageBorderDisplay.ALL_PAGES, offsetFrom: PageBorderOffsetFrom.PAGE },
          pageBorderTop: { style: BorderStyle.THICK_THIN_SMALL_GAP, size: 18, color: "000000", space: 36 },
          pageBorderBottom: { style: BorderStyle.THIN_THICK_SMALL_GAP, size: 18, color: "000000", space: 36 },
          pageBorderLeft: { style: BorderStyle.THICK_THIN_SMALL_GAP, size: 18, color: "000000", space: 36 },
          pageBorderRight: { style: BorderStyle.THIN_THICK_SMALL_GAP, size: 18, color: "000000", space: 36 },
        } } },
      children: portada,
    },
    {
      properties: { page: { ...carta, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], font: FUENTE, size: 18 })] })] }) },
      children: contenido,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const salida = path.join(AQUI, "Reporte_PIA_RDP.docx");
  fs.writeFileSync(salida, buf);
  console.log("Escrito:", salida);
});
