"use strict";
/* Dibujo, vistas y elementos de la interfaz: copiados de la maqueta (líneas 918-1301) y adaptados a datos del backend. */
/* ============================================================
   Color e iconos para el dibujo (canvas y SVG)
   El acento se lee del token --verde-fime: al confirmar el valor
   con la FIME solo hay que cambiarlo en :root.
   ============================================================ */
const RAIZ=document.documentElement;
const hexRGB=v=>{v=v.trim().replace('#','');return [0,2,4].map(i=>parseInt(v.slice(i,i+2),16))};
const C_FIME=hexRGB(getComputedStyle(RAIZ).getPropertyValue('--verde-fime')||'#1F9F5C');
const C_AC=C_FIME.map(c=>Math.round(c+(255-c)*.38));       // acento claro: texto y trazos finos sobre oscuro
const C_OK=[48,209,88], C_NO=[255,66,69], C_AV=[255,146,48]; // systemGreen, systemRed y systemOrange (oscuro)
const rgb=(c,a=1)=>`rgba(${c[0]},${c[1]},${c[2]},${a})`;
RAIZ.style.setProperty('--acento-claro',rgb(C_AC));
const GRIS2='rgba(235,235,245,.6)', LINEA='#48484A', MONO='"JetBrains Mono", monospace';
const ic=n=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${IC[n]||''}</svg>`;
document.querySelectorAll('[data-ic]').forEach(e=>{e.outerHTML=ic(e.dataset.ic)});
/* estado con icono y texto: no depende solo del color */
const est=(s,txt='')=>`<span class="est ${s}">${s==='ok'?ic('check'):s==='no'?ic('x'):'<span class="punto"></span>'}${txt}</span>`;

/* grano del fondo: se genera una sola vez y queda como imagen estática */
(function grano(){
  const c=document.createElement('canvas');c.width=c.height=160;const x=c.getContext('2d'),d=x.createImageData(160,160),r=mulberry32(77);
  for(let i=0;i<160*160;i++){const v=r()<.5?0:255;d.data[i*4]=d.data[i*4+1]=d.data[i*4+2]=v;d.data[i*4+3]=Math.floor(r()*255)}
  x.putImageData(d,0,0);RAIZ.style.setProperty('--grano',`url(${c.toDataURL('image/png')})`);
})();

/* ============================================================
   Huella: imágenes de cada etapa. Solo dibujo: los datos llegan del backend.
   F = {w, h (tamaño procesado), img (cruda), norm, mask, gab, bin, skel, bm, bw, bh, bphi, coh, minu, c}
   ============================================================ */
function mkCanvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c}
function grayCanvas(w,h,fn){const c=mkCanvas(w,h),x=c.getContext('2d'),d=x.createImageData(w,h);
  for(let i=0;i<w*h;i++){const [r,g,b]=fn(i);d.data[i*4]=r;d.data[i*4+1]=g;d.data[i*4+2]=b;d.data[i*4+3]=255}x.putImageData(d,0,0);return c}
/* La cruda puede ser algo mayor que la procesada (se recorta a múltiplo de 16): se lee con su propio ancho. */
function construir(F,key){
  const g=(fn)=>grayCanvas(F.w,F.h,fn), cr=i=>F.img[(Math.floor(i/F.w))*F.rawW+(i%F.w)];
  F.c=F.c||{};
  switch(key){
    case 'raw': F.c.raw=g(i=>{const v=cr(i);return[v,v,v]}); F.c.dim=g(i=>{const v=cr(i)*.32+8;return[v,v,v]}); break;
    case 'seg': F.c.seg=g(i=>{const v=clamp(128+F.norm[i]*55,0,255);return F.mask[i]?[v,v,v]:[v*.16+10,v*.16+10,v*.16+11]}); break;
    case 'gab': {let gs=0,gn=0;for(let i=0;i<F.gab.length;i++)if(F.mask[i]){gs+=F.gab[i]*F.gab[i];gn++}const gsd=Math.sqrt(gs/(gn||1))||1;
      F.c.gab=g(i=>{if(!F.mask[i])return[14,14,15];const v=clamp(128+62*F.gab[i]/gsd,0,255);return[v,v,v]}); break;}
    case 'bin': F.c.bin=g(i=>!F.mask[i]?[14,14,15]:F.bin[i]?[20,20,22]:[235,235,240]); break;
    case 'skel': F.c.skel=g(i=>F.skel[i]?[226,226,234]:F.bin[i]?[44,44,46]:[14,14,15]); break;
  }
}
const STAGES=[['raw','Captura'],['seg','Segmentación'],['ori','Orientación'],['gab','Gabor'],['bin','Binaria'],['skel','Esqueleto'],['min','Minucias']];
/* terminación: círculo en el acento; bifurcación: cuadro en systemOrange */
function drawMinutia(x,m,s,alpha=1){
  const X=m.x*s,Y=m.y*s,L=9*s,dx=Math.cos(m.t)*L,dy=Math.sin(m.t)*L;
  x.globalAlpha=alpha; x.lineWidth=Math.max(1,1.5*s);
  x.strokeStyle=m.type==='T'?rgb(C_AC):rgb(C_AV);
  x.beginPath(); if(m.type==='T') x.arc(X,Y,3.6*s,0,2*PI); else x.rect(X-3.4*s,Y-3.4*s,6.8*s,6.8*s); x.stroke();
  x.beginPath(); x.moveTo(X,Y); x.lineTo(X+dx,Y+dy); x.stroke(); x.globalAlpha=1;
}
function drawStage(ctx,F,stage,p=1,sc){
  const s=sc||ctx.canvas.width/F.w, W=F.w*s, H=F.h*s, B=(F.bloque||16)*s; ctx.clearRect(0,0,ctx.canvas.width,ctx.canvas.height);
  ctx.imageSmoothingEnabled=true;
  const img=c=>ctx.drawImage(c,0,0,W,H);
  switch(stage){
    case 'raw': img(F.c.raw); break;
    case 'seg': img(F.c.raw); ctx.globalAlpha=p; img(F.c.seg); ctx.globalAlpha=1;
      ctx.strokeStyle=rgb(C_AC,.7);ctx.lineWidth=Math.max(1,s*.8);
      for(let by=0;by<F.bh;by++)for(let bx=0;bx<F.bw;bx++){if(!F.bm[by*F.bw+bx])continue;
        if(bx===0||!F.bm[by*F.bw+bx-1]){ctx.beginPath();ctx.moveTo(bx*B,by*B);ctx.lineTo(bx*B,by*B+B);ctx.stroke()}
        if(bx===F.bw-1||!F.bm[by*F.bw+bx+1]){ctx.beginPath();ctx.moveTo(bx*B+B,by*B);ctx.lineTo(bx*B+B,by*B+B);ctx.stroke()}
        if(by===0||!F.bm[(by-1)*F.bw+bx]){ctx.beginPath();ctx.moveTo(bx*B,by*B);ctx.lineTo(bx*B+B,by*B);ctx.stroke()}
        if(by===F.bh-1||!F.bm[(by+1)*F.bw+bx]){ctx.beginPath();ctx.moveTo(bx*B,by*B+B);ctx.lineTo(bx*B+B,by*B+B);ctx.stroke()}}
      break;
    case 'ori': { img(F.c.dim); const tot=F.bw*F.bh, lim=Math.floor(p*tot); ctx.lineCap='round';
      for(let k=0;k<lim;k++){if(!F.bm[k])continue;const bx=k%F.bw,by=(k/F.bw)|0,t=F.bphi[k]+PI/2,L=6.2*s,cx=bx*B+B/2,cy=by*B+B/2;
        ctx.strokeStyle=rgb(C_AC,.35+.65*clamp(F.coh[k],0,1));ctx.lineWidth=Math.max(1,1.6*s);
        ctx.beginPath();ctx.moveTo(cx-Math.cos(t)*L,cy-Math.sin(t)*L);ctx.lineTo(cx+Math.cos(t)*L,cy+Math.sin(t)*L);ctx.stroke();}
      break; }
    case 'gab': img(F.c.dim); ctx.save(); ctx.beginPath(); ctx.rect(0,0,W*p,H); ctx.clip(); img(F.c.gab); ctx.restore();
      if(p<1){ctx.fillStyle=rgb(C_AC,.9);ctx.fillRect(W*p-1,0,2,H)} break;
    case 'bin': img(F.c.gab); ctx.globalAlpha=p; img(F.c.bin); ctx.globalAlpha=1; break;
    case 'skel': img(F.c.bin); ctx.globalAlpha=.85; ctx.fillStyle='#0E0E0F'; ctx.fillRect(0,0,W,H*p); ctx.globalAlpha=1;
      ctx.save(); ctx.beginPath(); ctx.rect(0,0,W,H*p); ctx.clip(); img(F.c.skel); ctx.restore(); break;
    case 'min': { img(F.c.skel); const n=Math.floor(p*F.minu.length); for(let i=0;i<n;i++) drawMinutia(ctx,F.minu[i],s); break; }
  }
}

/* ============================================================
   Estado. Usuarios, escenarios, umbrales y distribuciones llegan del backend
   (evento "estado" y eventos de cada verificación); aquí no se calcula nada.
   ============================================================ */
const FLOOR=.5;
const S={speed:1,step:false,mode:'sim',running:false,runId:0,instant:false,showDigits:true,runs:0,lastF:null,lastResult:null,
  usuarios:{},umbralH:null,umbralFusion:.6};
const ABORT=Symbol('abort');
let DIST=null; // distribución de la calibración de rostro: {genuinos, impostores, max, umbral}

/* ============================================================
   Tiempo y animación
   ============================================================ */
const guard=id=>{if(id!==S.runId)throw ABORT};
function wait(ms,id){ if(S.instant) return Promise.resolve(); return new Promise(r=>setTimeout(r,ms/S.speed)).then(()=>guard(id)); }
function anim(ms,fn,id){
  if(S.instant){fn(1,1);return Promise.resolve()}
  return new Promise((res,rej)=>{const t0=performance.now(),D=ms/S.speed;
    const f=now=>{if(id!==S.runId){rej(ABORT);return}const t=Math.min(1,(now-t0)/D);fn(ease(t),t);if(t<1)requestAnimationFrame(f);else res()};requestAnimationFrame(f)});
}
let nextResolver=null;
function caption(k,text,state='wait'){ $('#capK').textContent=k; $('#capText').textContent=text; $('#capDot').innerHTML=est(state); }
async function beat(k,text,ms,id){
  caption(k,text);
  if(S.instant) return;
  if(S.step){ $('#nextBtn').hidden=false; await new Promise(r=>nextResolver=r); $('#nextBtn').hidden=true; guard(id); }
  else await wait(ms,id);
}

/* ============================================================
   Vistas y navegador de etapas
   Las dos vistas usan los mismos paneles; solo cambia data-vista y
   data-etapa en la rejilla. V.etapa es la etapa visible y V.curso la
   que está ejecutando el flujo (0 si no hay verificación en curso).
   ============================================================ */
const ETAPAS=[null,{n:'PIN',panel:'#pFrontal'},{n:'Huella',panel:'#pHuella'},{n:'Rostro',panel:'#pRostro'},{n:'Actuación',panel:'#pDecision'}];
const EST_TXT={pend:'pendiente',curso:'en curso',ok:'aprobada',no:'rechazada',omit:'no se pidió'};
const V={vista:'etapa',etapa:4,curso:0,seguir:true,vt:null,sinVT:/[?&]sinvt=1/.test(location.search),est:[null,'pend','pend','pend','pend'],dato:[null,'','','','']};
const grid=$('#grid'), pasos=[...document.querySelectorAll('.paso')];
const pocoMov=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;

function posInd(){ // desliza el indicador hasta el paso visible, como el selector de un control segmentado
  const b=pasos[V.etapa-1], ind=$('#navInd'); if(!b) return;
  ind.style.width=b.offsetWidth+'px'; ind.style.transform=`translateX(${b.offsetLeft}px)`;
}
function pintarNav(){
  pasos.forEach((b,i)=>{const n=i+1,e=V.est[n];
    b.dataset.est=e; if(n===V.etapa) b.setAttribute('aria-current','step'); else b.removeAttribute('aria-current');
    b.querySelector('.fig').innerHTML=e==='ok'?ic('check'):e==='no'?ic('x'):e==='curso'?'<i></i>':e==='omit'?ic('minus'):String(n);
    b.querySelector('.dato').textContent=e==='curso'&&!V.dato[n]?'en curso':e==='omit'?'no se pidió':V.dato[n];
    b.setAttribute('aria-label',`Etapa ${n}, ${ETAPAS[n].n}: ${EST_TXT[e]}${V.dato[n]?', '+V.dato[n]:''}`);});
  posInd();
  const fuera=S.running&&V.curso>0&&!V.seguir;
  $('#volver').hidden=!fuera; if(fuera) $('#volverTxt').textContent='En curso: '+ETAPAS[V.curso].n;
}
function marcar(n,e,dato=''){V.est[n]=e;V.dato[n]=dato;pintarNav()}
function limpiarNav(){for(let n=1;n<=4;n++){V.est[n]='pend';V.dato[n]=''}V.curso=0;V.seguir=true;pintarNav()}
function redibujar(){drawOverlay();posInd()} // lo que depende del tamaño del panel

/* Ejecuta el cambio con una transición y resuelve cuando termina. */
async function transicion(aplicar,dir){
  RAIZ.dataset.dir=dir;
  if(V.vt){try{V.vt.skipTransition()}catch(e){}}
  if(document.startViewTransition&&!V.sinVT){
    RAIZ.classList.add('vt');
    const t=document.startViewTransition(()=>{aplicar()}); V.vt=t;
    t.ready.catch(()=>{}); // con la pestaña oculta la transición se omite (el cambio sí se aplica) y "ready" se rechaza
    try{await t.finished}catch(e){}
    if(V.vt===t){V.vt=null;RAIZ.classList.remove('vt')}
  }else{ // respaldo: opacidad y transform
    const r=pocoMov(), dx=dir==='adelante'?-1:dir==='atras'?1:0;
    const sale=r||!dx?[{opacity:1},{opacity:0}]:[{opacity:1,transform:'none'},{opacity:0,transform:`translateX(${dx*4}%) scale(.98)`}];
    const entra=r||!dx?[{opacity:0},{opacity:1}]:[{opacity:0,transform:`translateX(${-dx*4}%) scale(.98)`},{opacity:1,transform:'none'}];
    try{await grid.animate(sale,{duration:r?75:180,easing:'ease-in',fill:'forwards'}).finished}catch(e){}
    aplicar();
    const a=grid.animate(entra,{duration:r?75:320,easing:'cubic-bezier(.32,.72,0,1)'}); grid.getAnimations().forEach(x=>{if(x!==a)x.cancel()});
    try{await a.finished}catch(e){}
  }
}
/* En la vista completa, "mostrar" una etapa es desplazar la página hasta su panel. */
function desplazarA(sel){
  const p=$(sel), r=p.getBoundingClientRect(), cab=$('#cabecera'), arriba=(getComputedStyle(cab).position==='sticky'?cab.offsetHeight:0)+12, abajo=innerHeight-88;
  if(r.top>=arriba-1&&r.bottom<=abajo) return Promise.resolve();
  const y=Math.max(0,scrollY+r.top-arriba);
  if(Math.abs(y-scrollY)<2) return Promise.resolve();
  return new Promise(res=>{let listo=false;const fin=()=>{if(listo)return;listo=true;removeEventListener('scrollend',fin);res()};
    addEventListener('scrollend',fin); setTimeout(fin,900); scrollTo({top:y,behavior:pocoMov()?'auto':'smooth'});});
}
/* Muestra la etapa n. Devuelve una promesa que se cumple al terminar la transición. */
async function mostrarEtapa(n,desplazar=true){
  n=clamp(n,1,4);
  const dir=n>V.etapa?'adelante':'atras', cambia=n!==V.etapa;
  const aplicar=()=>{V.etapa=n;grid.dataset.etapa=n;pintarNav();redibujar()};
  if(V.vista!=='etapa'){ aplicar(); if(desplazar&&!S.instant) await desplazarA(ETAPAS[n].panel); return; }
  if(!cambia){pintarNav();return}
  if(S.instant){aplicar();return}
  await transicion(aplicar,dir);
  redibujar();
}
/* El flujo de la verificación entra a la etapa n: espera a que la vista llegue antes de animar. */
async function etapaFlujo(n,id){
  V.curso=n; V.est[n]='curso'; V.dato[n]=''; pintarNav();
  if(V.seguir) await mostrarEtapa(n);
  guard(id);
}
/* El usuario elige una etapa (clic o flechas). Si se aparta de la que está en curso, la vista deja de seguir el flujo. */
function navUsuario(n){
  n=clamp(n,1,4);
  if(S.running&&V.curso>0) V.seguir=(n===V.curso);
  return mostrarEtapa(n);
}
pasos.forEach(b=>b.addEventListener('click',()=>navUsuario(+b.dataset.e)));
$('#volver').addEventListener('click',()=>{V.seguir=true;mostrarEtapa(V.curso)});
document.addEventListener('keydown',e=>{
  if(e.altKey||e.ctrlKey||e.metaKey||e.shiftKey) return;
  if(e.key!=='ArrowLeft'&&e.key!=='ArrowRight') return;
  if(e.target.closest&&e.target.closest('select,input,textarea,[contenteditable]')) return;
  const n=V.etapa+(e.key==='ArrowRight'?1:-1); if(n<1||n>4) return;
  e.preventDefault(); navUsuario(n);
});
/* En la vista completa, si el usuario mueve la página durante la verificación, tampoco se le arrastra de vuelta. */
const soltar=()=>{if(S.running&&V.curso>0&&V.vista==='completa'&&V.seguir&&!S.instant){V.seguir=false;pintarNav()}};
addEventListener('wheel',soltar,{passive:true}); addEventListener('touchmove',soltar,{passive:true});

function setVista(v,guardar=true){
  v=v==='etapa'?'etapa':'completa';
  const aplicar=()=>{V.vista=v;grid.dataset.vista=v;
    document.querySelectorAll('#vista button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===v));
    pintarNav();redibujar()};
  if(guardar){try{localStorage.setItem('pia.vista',v)}catch(e){}}
  if(v===V.vista||S.instant||!guardar){aplicar();return Promise.resolve()}
  return transicion(aplicar,'fundido').then(redibujar);
}
document.querySelectorAll('#vista button').forEach(b=>b.addEventListener('click',()=>setVista(b.dataset.v)));
$('#verLog').addEventListener('click',()=>{const on=$('#pBitacora').classList.toggle('completa');
  $('#verLog').setAttribute('aria-expanded',on);$('#verLogTxt').textContent=on?'Ver solo el último':'Ver bitácora completa'});
/* la cabecera fija cambia de alto al envolver: se mide para los márgenes de scroll y el alto libre */
new ResizeObserver(()=>{RAIZ.style.setProperty('--cab-h',$('#cabecera').offsetHeight+'px');posInd()}).observe($('#cabecera'));

/* ============================================================
   Elementos de la interfaz
   ============================================================ */
const KEYS=['1','2','3','A','4','5','6','B','7','8','9','C','*','0','#','D'];
const keyEls={};
KEYS.forEach(k=>{const b=document.createElement('button');b.className='key'+(/[A-D*#]/.test(k)?' fn':'');b.textContent=k;b.type='button';b.setAttribute('aria-label','Tecla '+k);
  b.addEventListener('click',()=>manualKey(k));keyEls[k]=b;$('#keypad').appendChild(b)});
function flashKey(k){const b=keyEls[k];if(!b)return;b.classList.add('hit');setTimeout(()=>b.classList.remove('hit'),S.instant?0:170)}

const thumbs=[];
STAGES.forEach(([key,label],i)=>{const b=document.createElement('button');b.className='thumb';b.type='button';b.dataset.stage=key;
  const c=mkCanvas(128,144);b.appendChild(c);const sp=document.createElement('span');sp.textContent=label;b.appendChild(sp);
  b.addEventListener('click',()=>{if(!S.lastF||S.running||!b.classList.contains('done'))return;showStage(key)});
  thumbs.push({key,b,c});$('#strip').appendChild(b)});
function showStage(key){drawStage($('#fpL').getContext('2d'),S.lastF,key,1);thumbs.forEach(t=>t.b.classList.toggle('cur',t.key===key));
  $('#fpLblL').textContent='Captura · '+STAGES.find(s=>s[0]===key)[1].toLowerCase()}
function thumbDone(key,F){const t=thumbs.find(t=>t.key===key);drawStage(t.c.getContext('2d'),F,key,1);t.b.classList.add('done');thumbs.forEach(x=>x.b.classList.toggle('cur',x.key===key))}

/* fases 1 a 4 del PIA dentro de cada factor */
const FASES=['Captura','Preproceso','Características','Matching'];
['#fasesH','#fasesR'].forEach(s=>{$(s).innerHTML=FASES.map((f,i)=>`<li data-p="${i+1}"><span class="n">${i+1}</span>${f}</li>`).join('')});
function setPhase(p,factor){
  const sel=factor==='huella'?'#fasesH':factor==='rostro'?'#fasesR':null; if(!sel) return;
  document.querySelectorAll(sel+' li').forEach(li=>{const n=+li.dataset.p,done=n<p;li.classList.toggle('on',n===p);li.classList.toggle('done',done);
    li.querySelector('.n').innerHTML=done?ic('check'):String(n);if(n===p)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current')});
}

/* OLED: texto rasterizado a 1 bit y sin acentos, como la pantalla real */
const oledCtx=$('#oled').getContext('2d'), oledTmp=mkCanvas(128,64).getContext('2d',{willReadFrequently:true});
let oledState={l1:'',l2:'',prog:-1};
function oled(l1,l2='',prog=-1){
  oledState={l1,l2,prog};
  const t=oledTmp;t.fillStyle='#000';t.fillRect(0,0,128,64);t.fillStyle='#fff';t.textBaseline='alphabetic';
  t.font='500 9px '+MONO;t.fillText('PIA RDP',1,8);t.fillText(S.mode==='sim'?'SIM':'USB',109,8);t.fillRect(0,11,128,1);
  t.font='600 12px '+MONO;t.fillText(l1,1,30);t.fillText(l2,1,47);
  if(prog>=0){t.fillRect(0,54,128,1);t.fillRect(0,63,128,1);t.fillRect(0,54,1,10);t.fillRect(127,54,1,10);t.fillRect(2,56,Math.round(124*prog),6)}
  const d=t.getImageData(0,0,128,64),o=oledCtx.createImageData(128,64);
  for(let i=0;i<128*64;i++){const on=d.data[i*4]>118;o.data[i*4]=on?214:3;o.data[i*4+1]=on?236:6;o.data[i*4+2]=on?255:8;o.data[i*4+3]=255}
  oledCtx.putImageData(o,0,0);
}
function leds(g,r){$('#ledG').classList.toggle('on',g);$('#ledR').classList.toggle('on',r)}
function serial(dir,txt){const el=$('#serial'),d=document.createElement('div');
  const cls=dir==='in'?'in':dir==='out'?'out':'note';
  d.innerHTML=dir==='note'?`<span class="note">${txt}</span>`:`<span class="dir">${dir==='in'?'ESP32 a PC':'PC a ESP32'}</span><span class="${cls}">${txt}</span>`;
  el.appendChild(d);while(el.children.length>40)el.removeChild(el.firstChild);el.scrollTop=el.scrollHeight}
let slotsNow={id:'',pin:'',err:false};
function setSlots(id,pin,err){
  slotsNow={id,pin,err:!!err};
  [...$('#slotId').children].forEach((s,i)=>{s.textContent=id[i]??'';s.className='slot'+(id[i]?' fill':'')});
  [...$('#slotPin').children].forEach((s,i)=>{s.textContent=pin[i]?(S.showDigits?pin[i]:'•'):'';s.className='slot'+(pin[i]?(err?' err':' fill'):'')});
}
function panel(id,state){$(id).dataset.state=state}

/* compartimentos con servo */
function compSVG(n){return `
  <rect x="4" y="16" width="152" height="92" rx="8" fill="#1C1C1E" stroke="#48484A"/>
  <g class="lid" id="lid${n}" style="transform-origin:150px 16px"><rect x="4" y="10" width="152" height="8" rx="3" fill="#3A3A3C" stroke="#636366"/><rect x="86" y="18" width="10" height="34" fill="#636366"/><rect x="86" y="48" width="22" height="6" rx="1.5" fill="#636366"/></g>
  <circle cx="148" cy="14" r="3" fill="#8E8E93"/>
  <rect x="16" y="66" width="48" height="24" rx="3" fill="#2C2C2E" stroke="#48484A"/>
  <text x="40" y="82" text-anchor="middle" font-size="8" fill="${GRIS2}" font-family='${MONO}'>SG90</text>
  <circle cx="54" cy="62" r="5" fill="#8E8E93"/>
  <g class="arm" id="arm${n}" style="transform-origin:54px 62px"><rect x="52" y="58" width="56" height="8" rx="4" fill="#D1D1D6"/></g>
  <circle cx="54" cy="62" r="2" fill="#1C1C1E"/>
  <text x="128" y="100" text-anchor="end" font-size="8" fill="${GRIS2}" font-family='${MONO}'>GPIO${n===1?18:19}</text>`}
$('#c1').innerHTML=compSVG(1); $('#c2').innerHTML=compSVG(2);
function servo(n,open){ $('#arm'+n).style.transform=open?'rotate(90deg)':'rotate(0deg)'; $('#lid'+n).style.transform=open?'rotate(-14deg)':'rotate(0deg)';
  const s=$('#c'+n+'s'); s.innerHTML=ic(open?'lock-keyhole-open':'lock-keyhole')+(open?'Liberado':'Bloqueado'); s.className='pill'+(open?' ok':''); }

/* dibujo de rostro */
function drawGray(cv,data,w,h,norm){const x=cv.getContext('2d'),d=x.createImageData(w,h);let mn=0,mx=1;
  if(norm){mn=Infinity;mx=-Infinity;for(const v of data){if(v<mn)mn=v;if(v>mx)mx=v}}
  for(let i=0;i<w*h;i++){const v=clamp(Math.round((data[i]-mn)/((mx-mn)||1)*255),0,255);d.data[i*4]=v;d.data[i*4+1]=v;d.data[i*4+2]=v;d.data[i*4+3]=255}x.putImageData(d,0,0)}
const camCtx=$('#cam').getContext('2d'); let camBase=mkCanvas(1,1);
/* Cuadro real de la cámara o del dataset, ajustado al lienzo de 448 × 336 sin deformarlo.
   Los rectángulos son los que devolvió Viola-Jones en OpenCV (coordenadas del cuadro). */
function camFit(){const s=Math.min(448/camBase.width,336/camBase.height);return {s,ox:(448-camBase.width*s)/2,oy:(336-camBase.height*s)/2}}
function camDraw(Fc,p){ // Fc: {rostro:[x,y,w,h]|null, ojos:[[x,y,w,h]…]}; p: {box, eyes, line} de 0 a 1
  const {s,ox,oy}=camFit();
  camCtx.imageSmoothingEnabled=true; camCtx.clearRect(0,0,448,336); camCtx.drawImage(camBase,ox,oy,camBase.width*s,camBase.height*s);
  const X=v=>ox+v*s, Y=v=>oy+v*s;
  if(p.box>0&&Fc.rostro){const [x,y,w,h]=Fc.rostro, cx=x+w/2, cy=y+h/2, k=.4+.6*p.box;
    camCtx.strokeStyle=rgb(C_AC,p.box);camCtx.lineWidth=2;camCtx.strokeRect(X(cx-w*k/2),Y(cy-h*k/2),w*k*s,h*k*s);
    camCtx.fillStyle=rgb(C_AC,p.box);camCtx.font='500 13px '+MONO;camCtx.fillText('rostro',X(cx-w*k/2)+2,Math.max(14,Y(cy-h*k/2)-6));}
  const centros=(Fc.ojos||[]).map(([x,y,w,h])=>[x+w/2,y+h/2]);
  if(p.eyes>0){camCtx.strokeStyle=rgb(C_AV,p.eyes);camCtx.lineWidth=2;
    for(const [x,y,w,h] of Fc.ojos||[]) camCtx.strokeRect(X(x),Y(y),w*s,h*s)}
  if(p.line>0&&centros.length===2){const [a,b]=centros;camCtx.strokeStyle=rgb(C_AV,p.line);camCtx.setLineDash([6,5]);camCtx.beginPath();camCtx.moveTo(X(a[0]),Y(a[1]));camCtx.lineTo(X(b[0]),Y(b[1]));camCtx.stroke();camCtx.setLineDash([])}
}
function histSVG(hb,ha,p=1){const mb=Math.max(...hb),ma=Math.max(...ha),W=160,H=70,bw=W/32;let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Histograma antes y después">`;
  for(let i=0;i<32;i++){const h=hb[i]/mb*(H-6);s+=`<rect x="${i*bw+.5}" y="${H-h}" width="${bw-1}" height="${h}" fill="${LINEA}"/>`}
  let d='';for(let i=0;i<32;i++){const h=ha[i]/ma*(H-6)*p;d+=(i?'L':'M')+(i*bw+bw/2).toFixed(1)+' '+(H-h).toFixed(1)}
  s+=`<path d="${d}" fill="none" stroke="${rgb(C_AC)}" stroke-width="1.6"/></svg>`;return s}
function weightsSVG(w,ref,p=1){const n=Math.min(16,w.length),W=320,H=110,mid=H/2,bw=W/n,m=Math.max(...w.slice(0,n).map(Math.abs),...ref.slice(0,n).map(Math.abs))||1;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Vector de pesos"><line x1="0" x2="${W}" y1="${mid}" y2="${mid}" stroke="${LINEA}"/>`;
  for(let i=0;i<n;i++){const q=clamp(p*n-i,0,1);const h=w[i]/m*(mid-6)*q,hr=ref[i]/m*(mid-6);
    s+=`<rect x="${i*bw+3}" y="${Math.min(mid,mid-hr)}" width="${bw-6}" height="${Math.abs(hr)}" fill="none" stroke="${GRIS2}" stroke-dasharray="2 2"/>`;
    s+=`<rect x="${i*bw+5}" y="${Math.min(mid,mid-h)}" width="${bw-10}" height="${Math.abs(h)}" fill="${rgb(C_AC)}" rx="1.5"/>`;}
  return s+'</svg>'}
/* genuinos en el acento, impostores en systemRed; cada serie lleva su etiqueta de texto */
/* DIST: histogramas de la calibración activa, calculados en Python (calibracion.distribucion) */
function distSVG(d,p=1){if(!DIST||!DIST.genuinos) return '';
  const {genuinos:hg,impostores:hi,max:dmax,umbral:thr}=DIST,W=320,H=120,base=88,nb=hg.length,X=v=>8+clamp(v/dmax,0,1)*(W-16);
  const mg=Math.max(...hg)||1,mi=Math.max(...hi)||1,bw=(W-16)/nb;
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distancia frente a distribuciones">`;
  for(let i=0;i<nb;i++){const a=hi[i]/mi*58,b=hg[i]/mg*58;
    s+=`<rect x="${8+i*bw+.5}" y="${base-a}" width="${bw-1}" height="${a}" fill="${rgb(C_NO,.4)}"/>`;
    s+=`<rect x="${8+i*bw+.5}" y="${base-b}" width="${bw-1}" height="${b}" fill="${rgb(C_AC,.6)}"/>`;}
  s+=`<line x1="8" x2="${W-8}" y1="${base}" y2="${base}" stroke="${LINEA}"/>`;
  s+=`<line x1="${X(thr)}" x2="${X(thr)}" y1="18" y2="${base+4}" stroke="#fff" stroke-dasharray="3 3"/><text x="${X(thr)+4}" y="26" font-size="9" fill="${GRIS2}" font-family='${MONO}'>umbral ${thr.toFixed(2)}</text>`;
  if(d!=null){const x=X(d*p),okD=d<thr;s+=(okD?`<path d="M${x} ${base+4} l-6 10 h12 z" fill="${rgb(C_OK)}"/>`:`<rect x="${x-5}" y="${base+5}" width="10" height="9" rx="2" fill="${rgb(C_NO)}"/>`)
    +`<text x="${clamp(x,34,W-34)+(x>W/2?-12:12)}" y="${H-1}" text-anchor="${x>W/2?'end':'start'}" font-size="10" fill="#fff" font-family='${MONO}'>d = ${(d*p).toFixed(2)}</text>`}
  s+=`<text x="8" y="12" font-size="9" fill="${rgb(C_AC)}" font-family='${MONO}'>genuinos</text><text x="64" y="12" font-size="9" fill="${rgb(C_NO)}" font-family='${MONO}'>impostores</text>`;
  return s+'</svg>'}

/* superposición del matching */
const fpO=$('#fpO'); let overlayState=null;
function drawOverlay(){
  const r=$('#fpPair').getBoundingClientRect(), dpr=window.devicePixelRatio||1;
  if(!r.width||!r.height) return; // panel oculto: se vuelve a dibujar al mostrarlo
  fpO.width=Math.round(r.width*dpr); fpO.height=Math.round(r.height*dpr); const x=fpO.getContext('2d'); x.setTransform(dpr,0,0,dpr,0,0); x.clearRect(0,0,r.width,r.height);
  if(!overlayState) return;
  const {F,T,M,p}=overlayState, lr=$('#fpL').getBoundingClientRect(), rr=$('#fpR').getBoundingClientRect();
  /* la imagen se dibuja con la escala del ancho (drawStage), así que x e y usan el mismo factor */
  const L=(m)=>[lr.left-r.left+m.x*lr.width/F.w, lr.top-r.top+m.y*lr.width/F.w], R=(m)=>[rr.left-r.left+m.x*rr.width/T.w, rr.top-r.top+m.y*rr.width/T.w];
  x.lineWidth=1; x.strokeStyle=`rgba(174,174,178,${.5*Math.min(1,p*3)})`;
  for(const [a,b] of M.edgesA){const P=L(F.minu[a]),Q=L(F.minu[b]);x.beginPath();x.moveTo(...P);x.lineTo(...Q);x.stroke()}
  for(const [a,b] of M.edgesB){const P=R(T.minu[a]),Q=R(T.minu[b]);x.beginPath();x.moveTo(...P);x.lineTo(...Q);x.stroke()}
  const n=Math.floor(clamp((p-.25)/.75,0,1)*M.pairs.length);
  for(let i=0;i<n;i++){const [a,b]=M.pairs[i],P=L(F.minu[a]),Q=R(T.minu[b]);
    x.strokeStyle=rgb(C_AC,.8);x.lineWidth=1.2;x.beginPath();x.moveTo(...P);x.lineTo(...Q);x.stroke();
    x.fillStyle=rgb(C_AC);x.beginPath();x.arc(...P,2.6,0,2*PI);x.arc(...Q,2.6,0,2*PI);x.fill();}
}
new ResizeObserver(()=>drawOverlay()).observe($('#fpPair'));

/* ============================================================
   Reinicio
   ============================================================ */
function resetUI(keepKeys){
  if(!keepKeys) setSlots('','');
  leds(false,false); servo(1,false); servo(2,false); setPhase(0,'huella'); setPhase(0,'rostro');
  ['#pFrontal','#pHuella','#pRostro','#pDecision'].forEach(p=>panel(p,'idle'));
  ['#fpL','#fpR'].forEach(c=>{const x=$(c).getContext('2d');x.clearRect(0,0,512,576)});
  thumbs.forEach(t=>{t.b.classList.remove('done','cur');t.c.getContext('2d').clearRect(0,0,128,144)});
  overlayState=null; drawOverlay();
  $('#mBytes').innerHTML='0 <small>B</small>'; $('#mBytesBar').style.width='0%'; $('#mMin').textContent='—'; $('#mScore').textContent='—'; $('#mScoreBar').style.width='0%'; $('#mScoreBar').style.background=''; $('#mPairs').textContent='Pares en correspondencia: —';
  if(S.umbralH!=null) $('#mThr').style.left=(S.umbralH*100)+'%'; $('#fpSt').textContent=''; $('#faceSt').textContent=''; $('#fpLblL').textContent='Captura'; $('#fpLblR').textContent='Plantilla registrada';
  camCtx.clearRect(0,0,448,336); ['#fAlign','#fNorm','#fRec'].forEach(c=>$(c).getContext('2d').clearRect(0,0,64,64)); $('#fAlign').style.transform='none';
  $('#fAlignCap').textContent='—'; $('#fHist').innerHTML=''; $('#eig').innerHTML=''; $('#eigCap').textContent='—'; $('#wChart').innerHTML=''; $('#recCap').textContent='—';
  $('#dChart').innerHTML=distSVG(null); $('#dCap').textContent='—';
  ['zH','zR','zS'].forEach(k=>{$('#'+k).textContent='—';$('#'+k+'b').style.width='0%';$('#'+k+'b').className=''});
  verdict(null);
}
function verdict(v){const el=$('#verdict');el.className='verdict'+(v?(v.ok?' ok':' no'):'');
  $('#vT').textContent=v?v.t:'En espera'; $('#vS').textContent=v?v.s:'Inicia una verificación.';
  $('#vIc').innerHTML=ic(!v?'lock-keyhole':v.ok?'check':'x');}

/* ============================================================
   Verificación completa
   ============================================================ */
async function typeKeys(seq,onKey,id){for(const k of seq){await wait(k==='#'?380:300+((k.charCodeAt(0)*37)%140),id);flashKey(k);onKey(k);
  serial('in','TECLA:'+(S.showDigits||'#*D'.includes(k)?k:'•'))}}

function logRow(r){const tr=document.createElement('tr');if(!S.instant)tr.className='new';
  tr.innerHTML=`<td class="m">${r.hora}</td><td class="m">${r.id}</td><td>${r.user}</td><td>${r.pin?'Correcto':'Incorrecto'}</td><td class="m">${r.h??'—'}</td><td class="m">${r.r??'—'}</td><td class="m">${r.s??'—'}</td><td><span class="res ${r.ok?'ok':'no'}">${ic(r.ok?'check':'x')}${r.res}</span></td>`;
  $('#logBody').prepend(tr)}
