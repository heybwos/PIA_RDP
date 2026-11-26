"use strict";
/* ============================================================
   App conectada al backend (docs/EVENTOS.md).
   El backend calcula y manda rápido; esta cola anima cada evento a su ritmo,
   con las duraciones y los textos de pie de run() de la maqueta.
   Prohibido calcular aquí algo del reconocimiento: todo valor viene del backend.
   ============================================================ */
if(/[?&]sinvidrio=1/.test(location.search)) RAIZ.classList.add('sin-vidrio');

/* ---------- decodificación de imágenes {ancho, alto, tipo, datos} ---------- */
function dec(im){const b=atob(im.datos),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);
  return im.tipo==='f32'?new Float32Array(u.buffer):u}
function pintar(cv,im,estirar=false){const d=dec(im);if(cv.width!==im.ancho||cv.height!==im.alto){cv.width=im.ancho;cv.height=im.alto}
  if(im.tipo==='u8'){const x=cv.getContext('2d'),o=x.createImageData(im.ancho,im.alto);
    for(let i=0;i<d.length;i++){o.data[i*4]=o.data[i*4+1]=o.data[i*4+2]=d[i];o.data[i*4+3]=255}x.putImageData(o,0,0)}
  else drawGray(cv,d,im.ancho,im.alto,estirar)}

/* ---------- conexión ---------- */
let ws=null, cola=[], procesando=false, reintento=null;
function enviar(o){if(ws&&ws.readyState===1)ws.send(JSON.stringify(o))}
function conectar(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  ws.onopen=()=>{clearTimeout(reintento)};
  ws.onmessage=e=>{const m=JSON.parse(e.data);
    if(m.tipo==='estado'){H.estado(m);return}       // el estado no espera turno
    /* la cámara en vivo tampoco: si la cola sigue animando la huella, se adelanta hasta alcanzarla */
    if(m.tipo==='rostro_vivo'){if(procesando||cola.length)alcanzar=true;vivo(m);return}
    cola.push(m); if(!procesando) procesar()};
  ws.onclose=()=>{const chip=$('#connChip');chip.className='chip no';cambiarIcono(icono(chip),'unplug');cambiarTexto($('#connTxt'),'Backend desconectado');
    caption('sin backend','No hay conexión con el backend. Arráncalo con: python -m pia (desde pc/). Reintentando…','no');
    S.running=false;updateButtons();reintento=setTimeout(conectar,2000)};
}
async function procesar(){
  procesando=true;
  while(cola.length){const m=cola.shift(), id=S.runId;
    try{ if(H[m.tipo]) await H[m.tipo](m,id) }
    catch(e){ if(e!==ABORT){console.error(e);caption('error','Falla al dibujar '+m.tipo+': '+e.message,'no')} }}
  procesando=false; alcanzar=false;
}
/* si la cola crece, las animaciones se acortan: la animación nunca frena al pipeline */
let alcanzar=false; // true: la cámara en vivo ya empezó; lo pendiente se dibuja sin animar
const _anim=anim, _wait=wait;
/* con la pestaña oculta el navegador no corre requestAnimationFrame: se salta al final para no trabar la cola */
anim=(ms,fn,id)=>(document.hidden||alcanzar)?(fn(1,1),Promise.resolve()):_anim(cola.length>40?ms/4:ms,fn,id);
wait=(ms,id)=>alcanzar?Promise.resolve():_wait(cola.length>40?ms/4:ms,id);
const _beat=beat; beat=(k,t,ms,id)=>alcanzar?(caption(k,t),Promise.resolve()):_beat(k,t,ms,id);

/* Cámara en vivo (modo ESP32 con DroidCam / IP Webcam): el backend manda ~8 cuadros por segundo
   reducidos, con los rectángulos de Viola-Jones, hasta que el rostro queda estable. */
function vivo(m){
  if(m.estado==='tomado'){$('#faceSt').innerHTML=est('ok','foto tomada');
    caption('fase 1','Foto tomada: tu cara estuvo dentro de la guía. Sigue el análisis.','ok');
    textoCam('Foto tomada',C_OK);return}
  if(V.etapa!==3&&V.seguir) mostrarEtapa(3);
  panel('#pRostro','active'); setPhase(1,'rostro');
  camBase=mkCanvas(m.imagen.ancho,m.imagen.alto); pintar(camBase,m.imagen);
  camDraw({rostro:m.rostro,ojos:m.ojos},{box:m.rostro?1:0,eyes:1,line:0});
  guiaCam(m);
  $('#camTag').textContent='cámara en vivo';
  const prep=m.estado==='preparate';
  const grande=prep?String(Math.ceil(m.falta_s)):m.dentro?'No te muevas':m.pista;
  textoCam(grande,prep?C_AC:m.dentro?C_OK:C_AV,prep?64:20);
  const t=prep?`Prepárate: pon tu cara dentro del óvalo y mira al lente (empieza en ${Math.ceil(m.falta_s)} s)`:m.pista;
  $('#faceSt').innerHTML=est(m.dentro&&!prep?'ok':'wait',prep?'prepárate':m.dentro?'dentro de la guía':'ajusta');
  caption('fase 1',`${t} · quedan ${Math.ceil(m.limite_s)} s`,m.dentro&&!prep?'ok':'wait');
}
/* óvalo guía, flecha hacia él y barra de "no te muevas", en las coordenadas del lienzo */
function guiaCam(m){
  const {s,ox,oy}=camFit(), w=camBase.width, h=camBase.height, g=m.guia;
  const cx=ox+g.cx*w*s, cy=oy+g.cy*h*s, rx=(g.ancho_min+g.ancho_max)/2*w*s*0.62, ry=rx*1.32;
  const color=m.dentro?C_OK:C_AV;
  camCtx.save(); camCtx.lineWidth=3; camCtx.setLineDash(m.dentro?[]:[10,8]); camCtx.strokeStyle=rgb(color,.95);
  camCtx.beginPath(); camCtx.ellipse(cx,cy,rx,ry,0,0,2*PI); camCtx.stroke(); camCtx.setLineDash([]);
  if(m.progreso>0){camCtx.lineWidth=7;camCtx.strokeStyle=rgb(C_OK);camCtx.beginPath();
    camCtx.ellipse(cx,cy,rx+8,ry+8,0,-PI/2,-PI/2+2*PI*m.progreso);camCtx.stroke()}
  if(m.flecha&&!m.dentro&&m.rostro){const [dx,dy]=m.flecha, L=Math.hypot(dx*w,dy*h)*s;
    if(L>12){const fx=cx-dx*w*s, fy=cy-dy*h*s, ang=Math.atan2(cy-fy,cx-fx);
      camCtx.strokeStyle=rgb(C_AV);camCtx.lineWidth=4;camCtx.beginPath();camCtx.moveTo(fx,fy);camCtx.lineTo(cx,cy);camCtx.stroke();
      camCtx.beginPath();camCtx.moveTo(cx,cy);camCtx.lineTo(cx-14*Math.cos(ang-0.5),cy-14*Math.sin(ang-0.5));
      camCtx.moveTo(cx,cy);camCtx.lineTo(cx-14*Math.cos(ang+0.5),cy-14*Math.sin(ang+0.5));camCtx.stroke()}}
  camCtx.restore();
}
function textoCam(t,color,tam=20){
  camCtx.save(); camCtx.font=`600 ${tam}px Inter, sans-serif`; camCtx.textAlign='center';
  const y=tam>40?336/2+tam/3:336-16, wTxt=camCtx.measureText(t).width+24; // abajo: arriba está la etiqueta
  if(tam<=40){camCtx.fillStyle='rgba(0,0,0,.62)';camCtx.fillRect(224-wTxt/2,y-tam-2,wTxt,tam+14)}
  camCtx.fillStyle=rgb(color); camCtx.fillText(t,224,y); camCtx.restore();
}

/* ---------- estado de la verificación en curso ---------- */
let F=null, T=null, M=null, idActual='', pcaDibujado=false;
const lctx=$('#fpL').getContext('2d');
const nombreDe=id=>S.usuarios[id]?.nombre;
const nivelTxt=n=>n===2?'Editor: compartimentos 1 y 2':'Lector: compartimento 1';
const stageAnim=async(key,ms,k,txt,id)=>{caption(k,txt);await anim(ms,e=>drawStage(lctx,F,key,e),id);thumbDone(key,F);
  $('#fpLblL').textContent='Captura · '+STAGES.find(s=>s[0]===key)[1].toLowerCase();await beat(k,txt,450,id)};
function bloquesDeMascara(){ // muestreo de la máscara recibida en el centro de cada bloque (solo para el trazo del borde)
  const B=F.bloque||16;F.bw=Math.floor(F.w/B);F.bh=Math.floor(F.h/B);F.bm=new Uint8Array(F.bw*F.bh);
  for(let by=0;by<F.bh;by++)for(let bx=0;bx<F.bw;bx++)F.bm[by*F.bw+bx]=F.mask[(by*B+(B>>1))*F.w+bx*B+(B>>1)]?1:0}
function pintarPCA(){const p=S.pca; if(!p) return;
  const eig=$('#eig'); eig.innerHTML='';
  [p.media,...p.eigenfaces.slice(0,7)].forEach((im,i)=>{const c=mkCanvas(im.ancho,im.alto);pintar(c,im,i>0);c.title=i?`Eigenface ${i}`:'Cara media';c.classList.add('in');eig.appendChild(c)});
  $('#eigCap').textContent=`k = ${p.k} · ${(p.varianza*100).toFixed(1)} % de varianza · modelo #${p.modelo_id}`;
  pcaDibujado=true}

const H={};
H.estado=m=>{
  S.usuarios=Object.fromEntries(m.usuarios.map(u=>[u.id,u]));
  const sel=$('#scn'), prev=sel.value;
  if(m.escenarios.length){sel.innerHTML=m.escenarios.map(e=>`<option value="${e.clave}">${e.nombre}</option>`).join('');
    sel.value=m.escenarios.some(e=>e.clave===prev)?prev:'l2'}
  else sel.innerHTML='<option value="">Sin escenarios: corre sembrar_simular.py</option>';
  const chip=$('#connChip');
  if(m.modo==='esp32'&&typeof m.conexion==='object'){const c=m.conexion;
    if(S.mode!=='esp32'){S.mode='esp32';$('#mSim').setAttribute('aria-pressed',false);$('#mEsp').setAttribute('aria-pressed',true);verOcultar($('#espPanel'),true,'baja');updateButtons()}
    chip.className='chip ok';cambiarIcono(icono(chip),'monitor');cambiarTexto($('#connTxt'),`ESP32 · ${c.puerto.replace('socket://','')} · v${c.version}`);
    if(busqueda) scanFin(true);
    $('#bancoTxt').textContent='AS608 · '+(S.camara||'cámara');
    $('#espMsg').innerHTML=`Conectado a <span class="mono">${c.puerto}</span> · firmware ${c.version} · sensor ${c.sensor?'OK':'<strong>ERR</strong>'} · OLED ${c.oled?'OK':'<strong>ERR</strong>'}. La verificación empieza al teclear el ID en la caja.`;
  }else if(S.mode==='esp32'){chip.className='chip no';cambiarIcono(icono(chip),'unplug');cambiarTexto($('#connTxt'),'ESP32 · sin conexión')}
  else{$('#bancoTxt').textContent=`${(m.bancos.huella||'').toUpperCase()} · ${(m.bancos.rostro||'').toUpperCase()}`;
    chip.className='chip ok';cambiarIcono(icono(chip),'monitor');cambiarTexto($('#connTxt'),'Dispositivo simulado')}
  S.running=S.mode==='sim'&&!!m.ocupado; updateButtons();
};
H.puertos=m=>{
  const sel=$('#port');
  /* un firmware de prueba (test_…) contesta HOLA pero no sabe verificar: se lista y no se conecta solo */
  const prueba=p=>p.responde&&/^test_/.test(p.version||'');
  const ok=m.puertos.filter(p=>p.responde&&!prueba(p));
  if(!m.puertos.length){sel.innerHTML='<option>Ningún puerto detectado</option>';sel.disabled=true;scanFin(false);
    $('#espMsg').innerHTML='<strong>No hay puertos serie.</strong> Revisa el cable USB (que sea de datos) y el driver CP210x o CH340.';return}
  sel.innerHTML=m.puertos.map(p=>`<option value="${p.puerto}"${p.responde&&!prueba(p)?'':' disabled'}>${p.puerto}${!p.responde?' · no contesta':prueba(p)?` · firmware de prueba (${p.version})`:` · v${p.version} · sensor ${p.sensor?'OK':'ERR'} · OLED ${p.oled?'OK':'ERR'}`}</option>`).join('');
  sel.disabled=!ok.length;
  if(!ok.length){scanFin(false);$('#espMsg').innerHTML=m.puertos.some(prueba)
      ?'<strong>La placa tiene un firmware de prueba.</strong> Carga el entorno principal (esp32dev) para verificar.'
      :'<strong>Ningún puerto contestó HOLA.</strong> Carga el firmware principal (esp32dev) y cierra el monitor serie de PlatformIO.';return}
  sel.value=ok[0].puerto; $('#espMsg').innerHTML=`Conectando a <span class="mono">${ok[0].puerto}</span>…`; scanEstado('conectando');
  enviar({tipo:'conectar',puerto:ok[0].puerto});
};
H.etapa=async(m,id)=>{
  const sel=ETAPAS[m.n].panel;
  if(S.mode==='esp32'&&m.n===1&&m.estado==='curso'){ // con el ESP32 cada verificación empieza sola, en la caja
    resetUI(); limpiarNav(); F=T=M=null; idActual=''; S.running=true; S.lastResult=null; S.esperandoOtra=false; S.cerrando=false; updateButtons();
    caption('ESP32','Teclea tu ID y PIN en el teclado de la caja.','wait')}
  if(m.estado==='curso'){await etapaFlujo(m.n,id);panel(sel,'active');
    if(m.n===4) caption('fase 5','Decisión: PIN, umbral de cada factor y fusión ponderada.');}
  else{marcar(m.n,m.estado,m.dato);if(m.estado!=='omit')panel(sel,'done');
    if(m.n===1&&m.estado==='ok') await beat('fase 1',`PIN correcto. Huella y rostro se comparan solo contra el usuario ${idActual} (verificación 1:1).`,900,id);
    if(m.n===1&&m.estado==='no'){setSlots(idActual,'••••',true);
      await beat('fase 1',m.dato==='PIN incorrecto'?'PIN incorrecto. Se niega el acceso sin pedir huella ni rostro.':'ID no registrado. Se niega el acceso.',900,id)}
    if(m.n===4){S.running=false;V.curso=0;V.seguir=true;pintarNav();updateButtons()}}
};
H.tecla=m=>{flashKey(m.c);serial('in','TECLA:'+(S.showDigits||'#*D'.includes(m.c)?m.c:'•'))};
H.casillas=m=>{idActual=m.id;setSlots(m.id,m.pin.replace(/\*/g,'•'));
  caption('fase 1',m.fase==='id'?'El usuario escribe su ID de 2 dígitos y presiona #.':'Ahora el PIN de 4 dígitos y #.')};
H.oled=m=>{oled(m.l1,m.l2);
  if(S.mode!=='esp32') return;
  if(m.l1==='Cerrando'&&S.esperandoOtra){S.esperandoOtra=false;cerrando(true)}
  else if(m.l1==='Listo'&&S.cerrando) cerrando(false)};
H.serie=m=>serial(m.dir,m.linea);
H.leds=m=>leds(m.verde,m.rojo);
H.servo=async(m,id)=>{servo(m.n,m.abierto,m.angulo);modServoPinta(m.n,m.angulo??(m.abierto?90:0),m.abierto);
  if(m.manual) servoLlego(m.n); else await wait(300,id)};
H.servos_error=m=>{const e=$('#msMsg');e.textContent=m.mensaje;e.className='cap ms-msg no';servosError()};

/* ----- huella ----- */
H.huella_inicio=async(m,id)=>{
  if(F){ // reintento: se limpia el panel de la captura anterior
    thumbs.forEach(t=>{t.b.classList.remove('done','cur');t.c.getContext('2d').clearRect(0,0,128,144)});
    overlayState=null; drawOverlay(); lctx.clearRect(0,0,512,576);
    $('#mMin').textContent='—'; $('#mScore').textContent='—'; $('#mScoreBar').style.width='0%'; $('#mPairs').textContent='Pares en correspondencia: —'}
  F={rawW:m.ancho,rawH:m.alto,w:m.ancho,h:m.alto,img:new Uint8Array(m.ancho*m.alto),filas:0,fuente:m.fuente,bytes:m.ancho*m.alto/2};
  F.cruda=mkCanvas(m.ancho,m.alto); S.lastF=F;
  setPhase(1,'huella'); $('#fpSt').innerHTML=est('wait','recibiendo');
  $('#fpMeta').textContent=`${m.fuente.toUpperCase()} · ${m.ancho} × ${m.alto} · 4 bits/px${m.simulada?' · simulada':''}`;
  caption('fase 1',`La imagen llega por partes: ${m.ancho} × ${m.alto} píxeles a 4 bits, ${F.bytes.toLocaleString('en-US')} bytes al ritmo del sensor (57600 baudios).${m.simulada?' Viene del banco '+m.fuente.toUpperCase()+', no del sensor.':''}`);
};
H.huella_filas=m=>{
  const d=dec(m.filas), y0=m.y0, n=m.filas.alto, x=F.cruda.getContext('2d'), o=x.createImageData(F.rawW,n);
  F.img.set(d,y0*F.rawW);
  for(let i=0;i<d.length;i++){o.data[i*4]=o.data[i*4+1]=o.data[i*4+2]=d[i];o.data[i*4+3]=255}
  x.putImageData(o,0,y0); F.filas=y0+n;
  const s=512/F.rawW; lctx.clearRect(0,0,512,576); lctx.drawImage(F.cruda,0,0,F.rawW,F.filas,0,0,512,F.filas*s);
  if(F.filas<F.rawH){lctx.fillStyle=rgb(C_FIME);lctx.fillRect(0,F.filas*s-1,512,3)}
  const t=F.filas/F.rawH, b=Math.round(t*F.bytes);
  $('#mBytes').innerHTML=`${b.toLocaleString('en-US')} <small>/ ${F.bytes.toLocaleString('en-US')} B</small>`; $('#mBytesBar').style.width=(t*100)+'%';
};
H.huella_fin=async(m,id)=>{
  serial('note',m.crc_ok?'CRC32 verificado':'CRC32 incorrecto');
  $('#fpSt').innerHTML=est(m.crc_ok?'ok':'no',m.crc_ok?'imagen completa':'imagen dañada');
  await beat('fase 1',`Huella recibida completa (${m.bytes.toLocaleString('en-US')} bytes) y con CRC correcto.`,500,id);
};
H.huella_etapa=async(m,id)=>{
  switch(m.nombre){
    case 'normalizada': F.norm=dec(m.imagen);F.w=m.imagen.ancho;F.h=m.imagen.alto;construir(F,'raw');thumbDone('raw',F);setPhase(2,'huella');break;
    case 'segmentacion': {const u=dec(m.imagen);F.mask=new Uint8Array(u.length);for(let i=0;i<u.length;i++)F.mask[i]=u[i]>0?1:0;
      bloquesDeMascara();construir(F,'seg');
      await stageAnim('seg',700,'fase 2','Normalización y segmentación: los bloques de 16 px con poca varianza son fondo.',id);break}
    case 'orientacion': {F.bloque=m.bloque;F.bphi=dec(m.angulos);F.coh=dec(m.coherencia);F.bw=m.angulos.ancho;F.bh=m.angulos.alto;
      const b=dec(m.mascara);F.bm=new Uint8Array(b.length);for(let i=0;i<b.length;i++)F.bm[i]=b[i]>0?1:0;
      await stageAnim('ori',1100,'fase 2','Campo de orientación: gradientes de Sobel por bloque, suavizado sobre el doble del ángulo.',id);break}
    case 'gabor': F.gab=dec(m.imagen);construir(F,'gab');
      await stageAnim('gab',1200,'fase 2','Realce con filtros de Gabor orientados según el campo (24 orientaciones, desviación estándar de 4 px).',id);break;
    case 'binaria': {const u=dec(m.imagen);F.bin=new Uint8Array(u.length);for(let i=0;i<u.length;i++)F.bin[i]=u[i]>0?1:0;construir(F,'bin');
      await stageAnim('bin',600,'fase 2','Binarización: cresta donde la respuesta del filtro es negativa.',id);break}
    case 'esqueleto': {const u=dec(m.imagen);F.skel=new Uint8Array(u.length);for(let i=0;i<u.length;i++)F.skel[i]=u[i]>0?1:0;construir(F,'skel');
      await stageAnim('skel',1000,'fase 2','Adelgazamiento morfológico (skeletonize de scikit-image): crestas de 1 píxel de ancho.',id);break}
  }
};
H.huella_minucias=async(m,id)=>{
  F.minu=m.minucias.map(q=>({x:q.x,y:q.y,t:q.t,type:q.tipo}));
  setPhase(3,'huella');
  const nT=F.minu.filter(q=>q.type==='T').length,nB=F.minu.length-nT;
  await stageAnim('min',1300,'fase 3',`Minucias por número de cruce: ${nT} terminaciones y ${nB} bifurcaciones, cada una con posición y orientación.`,id);
  $('#mMin').innerHTML=`${F.minu.length} <small>${nT} T · ${nB} B</small>`;
};
H.huella_matching=async(m,id)=>{
  const sk=m.plantilla.esqueleto, u=dec(sk), b=dec(m.plantilla.binaria);
  T={w:sk.ancho,h:sk.alto,skel:Uint8Array.from(u,v=>v>0),bin:Uint8Array.from(b,v=>v>0),minu:m.plantilla.minucias.map(q=>({x:q.x,y:q.y,t:q.t,type:q.tipo}))};
  construir(T,'skel'); drawStage($('#fpR').getContext('2d'),T,'min',1); $('#fpLblR').textContent=`Plantilla registrada · ID ${idActual}`;
  /* el backend compara (plantilla, captura): se invierte para dibujar captura a la izquierda */
  M={score:m.puntaje,pairs:m.pares.map(([a,b])=>[b,a]),edgesA:m.aristas_b,edgesB:m.aristas_a};
  S.umbralH=m.umbral; $('#mThr').style.left=(m.umbral*100)+'%';
  setPhase(4,'huella'); $('#fpLblL').textContent='Captura · minucias';
  caption('fase 4','Matching por grafos: cada minucia se describe por sus 4 vecinas más cercanas (distancias y ángulos relativos).');
  overlayState={F,T,M,p:0};
  await anim(2200,e=>{overlayState.p=e;drawOverlay();const sc=M.score*clamp((e-.25)/.75,0,1);
    $('#mScore').innerHTML=`${fmt(sc)} <small>umbral ${fmt(m.umbral)}</small>`;$('#mScoreBar').style.width=clamp(sc*100,0,100)+'%';
    $('#mPairs').textContent=`Pares en correspondencia: ${Math.floor(clamp((e-.25)/.75,0,1)*M.pairs.length)} de ${F.minu.length} / ${T.minu.length}`},id);
  const hOk=M.score>=m.umbral;
  $('#mScoreBar').style.background=hOk?'var(--acento-claro)':'var(--no)';
  $('#fpSt').innerHTML=est(hOk?'ok':'no',hOk?'coincide':'no coincide'); setPhase(5,'huella');
  await beat('fase 4',`Puntaje de huella ${fmt3(M.score,m.umbral)} contra umbral ${fmt(m.umbral)}${m.eer!=null?` (EER ${(m.eer*100).toFixed(1)} %)`:''}: ${hOk?'coincide':'no coincide'}.${m.de>1?` Intento ${m.intento} de ${m.de}.`:''}`,1000,id);
  listo('huella'); // la caja sigue (otro intento o la cámara) cuando la app ya mostró esta huella
};
H.huella_reintento=async(m,id)=>{
  $('#fpSt').innerHTML=est('wait',`intento ${m.intento} de ${m.de}`);
  caption('fase 1',`Huella débil (${fmt3(m.puntaje,m.umbral)}): levanta el dedo y vuelve a ponerlo, plano y cubriendo el sensor. Intento ${m.intento} de ${m.de}.`,'wait');
  await wait(1200,id);
};
/* avisa al backend que la app terminó de mostrar un punto (solo con el ESP32: sincroniza la caja) */
function listo(punto){ if(S.mode==='esp32') enviar({tipo:'listo',punto}) }
/* 3 decimales cerca del umbral: que no se vea "0.60" y luego salga negado */
function fmt3(v,u){ return Math.abs(v-u)<0.01?v.toFixed(3):fmt(v) }

/* ----- rostro ----- */
let DET=null;
H.rostro_cuadro=async(m,id)=>{
  pcaDibujado=false; camBase=mkCanvas(m.imagen.ancho,m.imagen.alto); pintar(camBase,m.imagen);
  $('#camTag').textContent=`${m.fuente==='camara'?'cámara':m.fuente.toUpperCase()} · ${m.imagen.ancho} × ${m.imagen.alto} gris`;
  setPhase(1,'rostro'); $('#faceSt').innerHTML=est('wait','capturando');
  await anim(600,e=>{camCtx.globalAlpha=e;camDraw({},{box:0,eyes:0,line:0});camCtx.globalAlpha=1},id);
  await beat('fase 1',m.fuente==='camara'?'La PC toma un cuadro de DroidCam y lo pasa a escala de grises.':`Cuadro del dataset ${m.fuente.toUpperCase()}, en escala de grises.`,700,id);
};
H.rostro_deteccion=async(m,id)=>{
  DET=m; setPhase(2,'rostro');
  if(!m.rostro){camDraw(m,{box:0,eyes:0,line:0});$('#faceSt').innerHTML=est('no','sin rostro');
    await beat('fase 2','Viola-Jones no encontró un rostro en el cuadro.',900,id);return}
  caption('fase 2','Viola-Jones (cascadas de Haar de OpenCV) busca el rostro y, dentro de él, los ojos. Los rectángulos son los que devolvió OpenCV.');
  await anim(800,e=>camDraw(m,{box:e,eyes:0,line:0}),id);
  await anim(500,e=>camDraw(m,{box:1,eyes:e,line:0}),id);
  await beat('fase 2',`Rostro encontrado y ${m.ojos.length} ${m.ojos.length===1?'ojo':'ojos'}${m.con_relleno?' (con borde agregado: la imagen del dataset viene recortada al ras)':''}.`,500,id);
  if(m.ojos.length===2) await anim(500,e=>camDraw(m,{box:1,eyes:1,line:e}),id);
};
H.rostro_alineado=async(m,id)=>{
  const fa=$('#fAlign'); pintar(fa,m.imagen);
  const a=m.angulo||0; fa.style.transition='none'; fa.style.transform=`rotate(${a}deg) scale(.86)`; void fa.offsetWidth;
  fa.style.transition=''; requestAnimationFrame(()=>{fa.style.transform='none'});
  if(m.metodo==='ojos'){$('#fAlignCap').textContent=`${a>=0?'+':''}${a.toFixed(1)}° a 0°`;
    await beat('fase 2',`Alineación: se gira ${Math.abs(a).toFixed(1)}° para dejar los ojos horizontales, se escala a distancia fija entre ojos y se recorta a 64 × 64.`,1100,id)}
  else{$('#fAlignCap').textContent=m.metodo==='respaldo'?'respaldo':'sin rostro';
    await beat('fase 2',m.metodo==='respaldo'?'No se encontraron los dos ojos: respaldo documentado, recorte centrado del rectángulo del rostro a 64 × 64.':'Sin rostro: se usa la imagen completa (solo para datasets recortados).',1100,id)}
};
H.rostro_normalizado=async(m,id)=>{
  pintar($('#fNorm'),m.imagen);
  await anim(700,e=>{$('#fHist').innerHTML=histSVG(m.hist_antes,m.hist_despues,e)},id);
  await beat('fase 2','Normalización fotométrica: CLAHE y máscara elíptica. Gris: histograma antes; línea: después.',800,id);
};
H.rostro_pca=async(m,id)=>{
  S.pca=m; setPhase(3,'rostro');
  caption('fase 3',`PCA: la cara se proyecta en ${m.k} eigenfaces, que explican el ${(m.varianza*100).toFixed(1)} % de la varianza.`);
  pintarPCA(); const cs=[...$('#eig').children]; cs.forEach(c=>c.classList.remove('in'));
  for(const c of cs){await wait(110,id);c.classList.add('in')}
};
H.rostro_pesos=async(m,id)=>{
  if(!pcaDibujado){setPhase(3,'rostro');pintarPCA()}
  const ws=m.pesos.map((v,i)=>v/m.sigma[i]), rs=m.referencia.map((v,i)=>v/m.sigma[i]);
  caption('fase 3','Vector de pesos (barras) frente al promedio de las muestras registradas del usuario (contorno), en desviaciones estándar.');
  await anim(900,e=>{$('#wChart').innerHTML=weightsSVG(ws,rs,e)},id);
};
H.rostro_reconstruccion=async(m,id)=>{
  caption('fase 3','Reconstrucción con 1, 5, 10, 20 y k componentes: el vector de pesos basta para recuperar la cara.');
  const k=m.pasos[m.pasos.length-1].componentes;
  for(const p of m.pasos){pintar($('#fRec'),p.imagen);$('#recCap').textContent=`n = ${p.componentes} / ${k} · error ${p.error.toFixed(3)}`;await wait(350,id)}
  await beat('fase 3','Vector de pesos listo.',600,id);
};
H.rostro_distancia=async(m,id)=>{
  DIST=m.distribucion?{...m.distribucion,umbral:m.umbral}:null; setPhase(4,'rostro');
  caption('fase 4',`Distancia euclidiana contra las ${m.n_muestras} muestras registradas del usuario ${idActual}.`);
  await anim(1200,e=>{$('#dChart').innerHTML=distSVG(m.distancia,e)},id);
  const rOk=m.distancia<m.umbral;
  $('#dCap').innerHTML=`Mínima <b class="mono">${m.distancia.toFixed(2)}</b> · umbral <b class="mono">${m.umbral.toFixed(2)}</b>${m.eer!=null?` (EER ${(m.eer*100).toFixed(1)} %)`:''}`;
  $('#faceSt').innerHTML=est(rOk?'ok':'no',rOk?'coincide':'no coincide'); setPhase(5,'rostro');
  await beat('fase 4',`Distancia ${m.distancia.toFixed(2)} contra umbral ${m.umbral.toFixed(2)}: ${rOk?'coincide':'no coincide'}.`,1000,id);
};

/* ----- decisión ----- */
H.fusion=async(m,id)=>{
  const ok=m.fusion>=m.umbral_fusion&&m.huella>=m.umbral_factor&&m.rostro>=m.umbral_factor;
  caption('fase 5',`Fusión: los puntajes se normalizan y se combinan con pesos ${m.pesos.huella} y ${m.pesos.rostro}. Cada factor debe pasar su propio umbral (${fmt(m.umbral_factor)} normalizado) y la suma, ${fmt(m.umbral_fusion)}.`);
  await anim(900,e=>{
    $('#zH').textContent=fmt3(m.huella*e,m.umbral_factor);$('#zHb').style.width=(m.huella*e*100)+'%';$('#zHb').className=m.huella<m.umbral_factor?'low':'';
    $('#zR').textContent=fmt3(m.rostro*e,m.umbral_factor);$('#zRb').style.width=(m.rostro*e*100)+'%';$('#zRb').className=m.rostro<m.umbral_factor?'low':'';},id);
  await anim(700,e=>{$('#zS').textContent=fmt3(m.fusion*e,m.umbral_fusion);$('#zSb').style.width=(m.fusion*e*100)+'%';$('#zSb').className=ok?'':'low'},id);
};
H.veredicto=async(m,id)=>{
  const u=S.usuarios[idActual];
  if(m.concedido){verdict({ok:true,t:`Acceso concedido · nivel ${m.nivel}`,s:`${u?u.nombre:'ID '+idActual} · ${nivelTxt(m.nivel)}`});
    caption('fase 5',`Acceso concedido. Se libera ${m.nivel===2?'el compartimento 1 y, 300 ms después, el 2':'el compartimento 1'}.`,'ok')}
  else{verdict({ok:false,t:'Acceso negado',s:/PIN|registrado/.test(m.motivo)?m.motivo+(u?' para el ID '+idActual:'')+'.':'Motivo: '+m.motivo+'.'});
    caption('fase 5','Acceso negado: '+m.motivo+'. Los compartimentos siguen bloqueados.','no')}
  S.lastResult={ok:m.concedido,nivel:m.nivel,motivo:m.motivo};
  await wait(600,id);
  listo('veredicto'); // ahora la caja muestra el resultado en la OLED y mueve los servos
};
H.bitacora_fila=m=>logRow(filaLog(m));
/* ESP32: el resultado se queda en pantalla (y los servos abiertos) hasta "Intentar de nuevo" o # en la caja */
H.esperando_otra=m=>{S.esperandoOtra=true; updateButtons();
  caption('fase 5',(m.concedido?'Saca lo que necesites y cierra las puertas de los compartimentos. ':'')+
    'Pulsa "Intentar de nuevo" (o # en la caja): se cierran los servos y empieza otra verificación.',m.concedido?'ok':'no')};
function filaLog(f){const hora=(f.fecha||'').slice(11,19);
  return {hora,id:f.usuario_id??'—',user:f.nombre||'—',pin:!!f.pin_ok,h:f.puntaje_huella!=null?fmt(f.puntaje_huella):null,
    r:f.distancia_rostro!=null?f.distancia_rostro.toFixed(2):null,s:f.fusion!=null?fmt(f.fusion):null,ok:f.decision>0,
    res:f.decision>0?'Nivel '+f.decision:f.pin_ok?'Negado':'Negado · PIN'}}
H.error=m=>{caption('error',m.mensaje+(m.que_revisar?'. '+m.que_revisar:''),'no'); if(busqueda) scanFin(false);
  if(/cancelada/.test(m.mensaje)){S.running=false;updateButtons()}};

/* ============================================================
   Controles
   ============================================================ */
function manualKey(k){flashKey(k);
  caption('teclado','En Simular la verificación sale de un escenario. El teclado físico se conecta en el modo ESP32 (N6).','wait')}
function updateButtons(){
  const sim=S.mode==='sim', sinWs=!ws||ws.readyState!==1;
  /* con el ESP32 la verificación empieza en la caja; el botón solo sirve para "Intentar de nuevo" */
  const run=$('#runBtn'), cerr=!sim&&S.cerrando;
  run.disabled=sinWs||(sim?false:!S.esperandoOtra);
  cambiarTexto($('#runTxt'),!sim?(cerr?'Cerrando…':'Intentar de nuevo'):S.running?'Reiniciar verificación':'Iniciar verificación');
  cambiarIcono(icono(run),cerr?'loader-circle':(!sim||S.running)?'rotate-ccw':'play','giro');
  /* las opciones de simulación (escenario, rostro, velocidad) solo se ven en Simular; en ESP32 el botón
     principal se oculta: aparece como "Intentar de nuevo" con una decisión en pantalla y "Cerrando…" después */
  document.querySelectorAll('.solo-sim').forEach(e=>verOcultar(e,sim,'sube'));
  const llega=!sim&&S.esperandoOtra&&run.hidden;
  verOcultar(run,sim||S.esperandoOtra||cerr,'crece'); if(llega) brillo(run);
  Object.values(keyEls).forEach(b=>b.disabled=!sim||S.running);
}
const LISTO='Elige un escenario y pulsa Iniciar verificación.';
function detener(){S.runId++;cola=[];verOcultar($('#nextBtn'),false,'crece');nextResolver=null}
/* ESP32: tras "Intentar de nuevo" (o # en la caja) el botón dice "Cerrando…" hasta que la OLED vuelve a "Listo" */
let cerrandoTope=null;
function cerrando(on){clearTimeout(cerrandoTope); S.cerrando=on; if(on) cerrandoTope=setTimeout(()=>cerrando(false),8000); updateButtons()}
function iniciar(){
  if(S.running) enviar({tipo:'cancelar'});
  detener(); resetUI(); limpiarNav(); $('#serial').innerHTML=''; F=T=M=null; DET=null; idActual='';
  S.running=true; S.runs++; updateButtons();
  enviar({tipo:'iniciar',escenario:$('#scn').value,fuente_rostro:S.fuenteRostro,velocidad:S.step?1:1/S.speed});
}
$('#runBtn').addEventListener('click',()=>{
  if(S.mode==='esp32'){ if(!S.esperandoOtra) return;
    S.esperandoOtra=false; cerrando(true); enviar({tipo:'otra'});
    caption('ESP32','Cerrando los compartimentos uno a la vez; después empieza una verificación nueva.','wait'); return }
  S.instant=false;iniciar()});
$('#resetBtn').addEventListener('click',()=>{ const quieta=V.vista==='completa'||V.etapa===1; // si la etapa cambia, su transición ya es la señal
  if(S.running) enviar({tipo:'cancelar'}); detener(); S.running=false; resetUI(); limpiarNav(); $('#serial').innerHTML='';
  if(S.mode==='sim'){oled('Listo','Teclea tu ID'); caption('listo',LISTO,'ok');}
  updateButtons(); mostrarEtapa(1);
  animar(icono($('#resetBtn')),[{rotate:'0deg'},{rotate:'-360deg'}],400,CURVA);
  if(quieta) animar(grid,[{opacity:.35},{opacity:1}],200,'ease-out'); });
$('#nextBtn').addEventListener('click',()=>{ animar(icono($('#nextBtn')),[{translate:'0 0'},{translate:'4px 0'},{translate:'0 0'}],150,'ease-out');
  if(nextResolver){const r=nextResolver;nextResolver=null;r()} });
document.querySelectorAll('#speed button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#speed button').forEach(x=>x.setAttribute('aria-pressed',x===b));
  const v=b.dataset.v; S.step=v==='paso'; S.speed=S.step?1:+v;
  if(!S.step && nextResolver){const r=nextResolver;nextResolver=null;verOcultar($('#nextBtn'),false,'crece');r()}
}));
S.fuenteRostro='dataset';
document.querySelectorAll('#fuenteRostro button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('#fuenteRostro button').forEach(x=>x.setAttribute('aria-pressed',x===b));
  S.fuenteRostro=b.dataset.v;
  caption('rostro',S.fuenteRostro==='camara'?'El rostro se tomará de DroidCam ([camara] en config.toml). Necesita usuarios registrados con cámara y su calibración.':'El rostro se tomará del dataset ORL del escenario.','ok');
}));
$('#showDigits').addEventListener('change',e=>{S.showDigits=e.target.checked; setSlots(slotsNow.id,slotsNow.pin,slotsNow.err)});
function setMode(m){
  S.mode=m; if(!modServos.hidden) modServoModo(); $('#mSim').setAttribute('aria-pressed',m==='sim'); $('#mEsp').setAttribute('aria-pressed',m==='esp32');
  verOcultar($('#espPanel'),m==='esp32','baja'); S.cerrando=false; clearTimeout(cerrandoTope);
  const chip=$('#connChip');
  if(m==='esp32'){ if(S.running){enviar({tipo:'cancelar'});detener();S.running=false} V.curso=0;V.seguir=true;pintarNav();
    chip.className='chip no'; cambiarIcono(icono(chip),'unplug'); cambiarTexto($('#connTxt'),'ESP32 · sin conexión');
    oled('Sin conexion','con la PC'); caption('ESP32','Modo ESP32: conecta la placa por USB y pulsa Buscar ESP32.','no');
  } else {
    chip.className='chip ok'; cambiarIcono(icono(chip),'monitor'); cambiarTexto($('#connTxt'),'Dispositivo simulado');
    oled('Listo','Teclea tu ID'); caption('listo',LISTO,'ok');
  }
  if(m==='sim') enviar({tipo:'modo',modo:'simular'}); // en ESP32, el backend cambia de modo al conectar
  updateButtons();
}
$('#mSim').addEventListener('click',()=>setMode('sim'));
$('#mEsp').addEventListener('click',()=>setMode('esp32'));
/* Buscar ESP32: buscando → conectando → "Conectado" (verde, 1.2 s) o sacudida en rojo; luego vuelve a su estado */
let busqueda=null, scanTope=null, scanVuelta=null;
function scanEstado(e){const b=$('#scanBtn'); busqueda=e; clearTimeout(scanTope); clearTimeout(scanVuelta);
  b.classList.remove('exito','fallo'); b.disabled=true;
  cambiarIcono(icono(b),'loader-circle'); cambiarTexto($('#scanTxt'),e==='buscando'?'Buscando…':'Conectando…');
  scanTope=setTimeout(()=>scanFin(false),e==='buscando'?20000:10000)}
function scanFin(ok){const b=$('#scanBtn'); busqueda=null; clearTimeout(scanTope); clearTimeout(scanVuelta); b.disabled=false;
  b.classList.toggle('exito',ok); b.classList.toggle('fallo',!ok);
  cambiarIcono(icono(b),ok?'check':'search'); cambiarTexto($('#scanTxt'),ok?'Conectado':'Buscar ESP32');
  if(!ok) sacudir(b);
  scanVuelta=setTimeout(()=>{b.classList.remove('exito','fallo'); cambiarIcono(icono(b),'search'); cambiarTexto($('#scanTxt'),'Buscar ESP32')},1200)}
$('#scanBtn').addEventListener('click',()=>{
  scanEstado('buscando');
  $('#espMsg').innerHTML='Revisando los puertos COM y esperando <span class="mono">HOLA</span>…';
  /* ?puerto=socket://127.0.0.1:5333 busca solo ese puerto (el ESP32 falso) y no toca los COM reales */
  const p=new URLSearchParams(location.search).get('puerto');
  enviar({tipo:'buscar_puertos',puerto:p||undefined,solo:!!p});
});
$('#port').addEventListener('change',e=>{ if(e.target.value){scanEstado('conectando');enviar({tipo:'conectar',puerto:e.target.value})} });

/* ============================================================
   Módulo Servos: control manual, fuera del flujo de verificación.
   El backend mueve el servo (ESP32: SERVO:n:ángulo) y difunde el evento "servo".
   ============================================================ */
const modServos=$('#modServos');
function modServoPinta(n,a,abierto){const r=$('#msR'+n);if(!r)return;$('#msA'+n).textContent=a+'°';
  if(document.activeElement!==r) r.value=a;
  if(abierto!=null){const l=$('#msL'+n); l.classList.toggle('ok',!!abierto); l.title=`Compartimento ${n}: ${abierto?'liberado':'bloqueado'}`;
    cambiarIcono(icono(l),abierto?'lock-keyhole-open':'lock-keyhole');
    if(!modServos.hidden) destello(r.closest('.ms-servo'))}}
function modServoModo(){$('#msModo').textContent=S.mode==='esp32'?'ESP32 · servos reales':'Simular · solo dibujo'}
$('#servosBtn').addEventListener('click',()=>panelServos($('#servosBtn').getAttribute('aria-expanded')!=='true'));
$('#msCerrar').addEventListener('click',()=>panelServos(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('#servosBtn').getAttribute('aria-expanded')==='true')panelServos(false)});
modServos.addEventListener('click',e=>{const b=e.target.closest('button[data-accion]');if(!b||b._ocupado)return;
  $('#msMsg').textContent='';$('#msMsg').className='cap ms-msg'; servoOcupado(b);
  enviar({tipo:'servo',n:b.dataset.n==='ambos'?'ambos':+b.dataset.n,accion:b.dataset.accion})});
[1,2].forEach(n=>{const r=$('#msR'+n);let t=0,pend=null;
  const mandar=()=>{t=performance.now();enviar({tipo:'servo',n,angulo:+r.value})};
  r.addEventListener('input',()=>{$('#msA'+n).textContent=r.value+'°';clearTimeout(pend);
    if(performance.now()-t>90)mandar();else pend=setTimeout(mandar,90)});
  r.addEventListener('change',()=>{clearTimeout(pend);mandar()})});

/* ============================================================
   Arranque: sin verificación inventada; se muestra la bitácora real
   ============================================================ */
(async function boot(){
  const q=new URLSearchParams(location.search).get('vista');
  let v='etapa';
  if(q==='completa'||q==='etapa') v=q; else {try{v=localStorage.getItem('pia.vista')||'etapa'}catch(e){}}
  RAIZ.classList.add('sin-anim'); pildoras(); setVista(v,false); verdict(null); resetUI(); pintarNav(); mostrarEtapa(1,false);
  try{await Promise.all(['500 9px','600 12px','500 13px'].map(f=>document.fonts.load(f+' '+MONO)))}catch(e){}
  await (document.fonts?document.fonts.ready:Promise.resolve());
  oled('Listo','Teclea tu ID'); caption('listo',LISTO,'ok');
  try{const filas=await (await fetch('/api/bitacora?limite=20')).json(); filas.reverse().forEach(f=>{S.instant=true;logRow(filaLog(f))}); S.instant=false}catch(e){}
  conectar();
  requestAnimationFrame(()=>{redibujar();requestAnimationFrame(()=>RAIZ.classList.remove('sin-anim'))});
  window.__pia={S,V,H,enviar,setVista,mostrarEtapa,navUsuario,cola:()=>cola};
})();
