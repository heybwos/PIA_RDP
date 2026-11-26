"use strict";
/* ============================================================
   Movimiento de la interfaz: lo que responde a los botones.
   - Solo opacidad, translate, scale y rotate (más un brillo o un anillo puntual).
   - Curvas: ENT para entradas y presión; CURVA es la de la app (--curva).
   - Sin movimiento con prefers-reduced-motion (queda un fundido corto), con S.instant
     (regresiones), con la pestaña oculta y durante el arranque (html.sin-anim).
   Lo usan dibujo.js y principal.js; ninguna función se llama al cargar.
   ============================================================ */
const ENT='cubic-bezier(.22,1,.36,1)', CURVA='cubic-bezier(.32,.72,0,1)';
const sinMov=()=>S.instant||document.hidden||RAIZ.classList.contains('sin-anim');

/* anima con WAAPI; con movimiento reducido solo hace el fundido (si la animación lo lleva) */
function animar(el,kf,ms,easing=ENT,extra={}){
  if(!el||!el.animate||sinMov()) return null;
  if(pocoMov()){
    if(!kf.some(k=>'opacity' in k)) return null;
    return el.animate(kf.map(k=>({opacity:k.opacity??1})),{duration:Math.min(ms,120),easing:'linear',...extra});
  }
  return el.animate(kf,{duration:ms,easing,...extra});
}
/* valor de reposo de cada propiedad, para cerrar los keyframes con las mismas propiedades */
const REPOSO={opacity:1,translate:'0 0',scale:'1',rotate:'0deg',filter:'blur(0)'};
const reposo=k=>Object.fromEntries(Object.keys(k).map(p=>[p,REPOSO[p]]));
/* fn se ejecuta una vez al terminar la animación o, si el navegador no avanza cuadros
   (ventana minimizada, panel oculto), a los ms + 150: el estado final nunca depende de la animación */
function alTerminar(a,ms,fn){
  let hecho=false; const t=setTimeout(()=>{if(!hecho){hecho=true;a.cancel();fn()}},ms+150);
  a.addEventListener('finish',()=>{if(!hecho){hecho=true;clearTimeout(t);fn()}});
  a.addEventListener('cancel',()=>clearTimeout(t));
}

/* ---------- aparecer y desaparecer (en lugar de cambiar hidden de golpe) ---------- */
const APARECE={
  sube:  {de:{opacity:0,translate:'0 6px'},  ms:200, sale:{opacity:0,translate:'0 -6px'}, msSale:150},
  baja:  {de:{opacity:0,translate:'0 -8px'}, ms:220, sale:{opacity:0,translate:'0 -8px'}, msSale:150},
  crece: {de:{opacity:0,scale:'.9'},         ms:220, sale:{opacity:0,scale:'.95'},        msSale:120},
  lado:  {de:{opacity:0,translate:'8px 0'},  ms:200, sale:{opacity:0,translate:'8px 0'},  msSale:120},
  panel: {de:{opacity:0,scale:'.9'},         ms:220, sale:{opacity:0,scale:'.92'},        msSale:150},
};
/* muestra u oculta el elemento con su animación; si se invierte a la mitad, retoma desde ahí */
function verOcultar(el,ver,tipo='sube'){
  if(!el) return;
  const destino=!ver; // valor final de hidden
  if(el._mov){ if(el._mov.destino===destino) return; const a=el._mov.anim; el._mov=null; a.cancel(); }
  else if(el.hidden===destino) return;
  const t=APARECE[tipo];
  if(ver){
    el.hidden=false;
    const a=animar(el,[t.de,reposo(t.de)],t.ms);
    if(a){el._mov={destino,anim:a}; alTerminar(a,t.ms,()=>{if(el._mov&&el._mov.anim===a)el._mov=null})}
    return;
  }
  const a=animar(el,[reposo(t.sale),t.sale],t.msSale,'ease-out');
  if(!a){el.hidden=true;return}
  el._mov={destino,anim:a};
  alTerminar(a,t.msSale,()=>{if(el._mov&&el._mov.anim===a){el._mov=null;el.hidden=true}});
}

/* ---------- texto e icono que cambian en su lugar ---------- */
function cambiarTexto(el,txt){
  if(!el||el.textContent===txt) return;
  el.textContent=txt;
  animar(el,[{opacity:0,filter:'blur(2px)',translate:'0 3px'},{opacity:1,filter:'blur(0)',translate:'0 0'}],180);
}
/* reemplaza un <svg class="ic"> por otro icono; "giro" entra rotando (play → reiniciar) */
function cambiarIcono(viejo,n,modo='pop'){
  if(!viejo) return null;
  if(viejo.getAttribute('data-n')===n) return viejo;
  const t=document.createElement('span'); t.innerHTML=ic(n); const nuevo=t.firstElementChild;
  viejo.replaceWith(nuevo);
  const de=modo==='giro'?{opacity:0,scale:'.6',rotate:'-90deg',filter:'blur(2px)'}:{opacity:0,scale:'.6',filter:'blur(2px)'};
  animar(nuevo,[de,reposo(de)],200);
  return nuevo;
}
const icono=el=>el&&el.querySelector('svg.ic');

/* ---------- avisos puntuales ---------- */
function sacudir(el){
  animar(el,[{translate:'0 0'},{translate:'-4px 0'},{translate:'4px 0'},{translate:'-3px 0'},{translate:'3px 0'},{translate:'0 0'}],300,'ease-out');
}
function brillo(el){ // un solo pulso verde alrededor del botón: "aquí sigue"
  animar(el,[{boxShadow:'0 0 0 0 rgba(31,159,92,.6)'},{boxShadow:'0 0 0 12px rgba(31,159,92,0)'}],900,'ease-out',{delay:180});
}
function destello(el){ // anillo que se desvanece: "esto se acaba de mover"
  animar(el,[{boxShadow:'inset 0 0 0 1.5px rgba(116,196,154,.95)'},{boxShadow:'inset 0 0 0 1.5px rgba(116,196,154,0)'}],700,'ease-out');
}
function pop(el,ms=200){ animar(el,[{opacity:0,scale:'.6'},{opacity:1,scale:'1'}],ms) }

/* ---------- píldora deslizante de los controles segmentados ---------- */
function pildoras(){
  document.querySelectorAll('.seg').forEach(seg=>{
    const ind=document.createElement('span'); ind.className='seg-ind'; ind.setAttribute('aria-hidden','true');
    seg.prepend(ind); seg.classList.add('con-ind');
    let ancho=0; // 0: la píldora aún no tiene lugar (grupo oculto o recién creado): se coloca sin animar
    const colocar=()=>{
      const b=seg.querySelector('button[aria-pressed="true"]');
      if(!b||!b.offsetWidth){ancho=0;return}
      const directo=!ancho||sinMov();
      if(directo) ind.style.transition='none';
      ind.style.width=b.offsetWidth+'px'; ind.style.transform=`translateX(${b.offsetLeft}px)`; ind.style.opacity='1';
      if(directo){void ind.offsetWidth; ind.style.transition=''}
      ancho=b.offsetWidth;
    };
    new MutationObserver(colocar).observe(seg,{subtree:true,attributes:true,attributeFilter:['aria-pressed']});
    new ResizeObserver(colocar).observe(seg);
    colocar();
  });
}

/* ---------- despliegue de un contenedor (bitácora completa) ---------- */
/* poner(abierto) aplica el estado; la altura se anima de la actual a la nueva */
function desplegar(el,poner,abrir){
  if(el._despl){const d=el._despl; el._despl=null; d.anim.cancel(); d.fin()}
  const h0=el.offsetHeight;
  poner(abrir); const h1=el.offsetHeight;
  if(h0===h1||sinMov()||pocoMov()) return;
  if(!abrir) poner(true); // al cerrar, las filas siguen visibles mientras el contenedor se encoge
  const ov=el.style.overflow; el.style.overflow='hidden';
  const fin=()=>{el.style.overflow=ov; if(!abrir) poner(false)};
  const anim=el.animate([{height:h0+'px'},{height:h1+'px'}],{duration:250,easing:CURVA});
  el._despl={anim,fin};
  alTerminar(anim,250,()=>{if(el._despl&&el._despl.anim===anim){el._despl=null;fin()}});
}

/* ---------- panel de servos: sale del botón Servos y regresa a él ---------- */
function panelServos(abrir){
  const p=$('#modServos'), b=$('#servosBtn');
  b.setAttribute('aria-expanded',abrir);
  if(abrir){modServoModo(); $('#msMsg').textContent=''; $('#msMsg').className='cap ms-msg'}
  const oculto=p.hidden; if(oculto) p.hidden=false; // para medir
  const r=p.getBoundingClientRect(), rb=b.getBoundingClientRect();
  p.style.transformOrigin=`${rb.left+rb.width/2-r.left}px ${rb.top+rb.height/2-r.top}px`;
  if(oculto) p.hidden=true;
  verOcultar(p,abrir,'panel');
}

/* ---------- botones de servo: "Moviendo…" hasta que llega el evento de cada servo ---------- */
const MIN_OCUPADO=450; // ms: que el cambio alcance a verse aunque el backend conteste al instante
function servoOcupado(b){
  const n=b.dataset.n, t=b.querySelector('.t');
  b._ocupado={faltan:new Set(n==='ambos'?[1,2]:[+n]),t0:performance.now(),ic:icono(b).getAttribute('data-n'),txt:t.textContent,
    tope:setTimeout(()=>servoLibre(b),3000)};
  b.setAttribute('aria-busy','true');
  cambiarIcono(icono(b),'loader-circle'); cambiarTexto(t,'Moviendo…');
}
function servoLibre(b,error){
  const o=b._ocupado; if(!o) return;
  clearTimeout(o.tope); b._ocupado=null; b.removeAttribute('aria-busy');
  cambiarIcono(icono(b),o.ic); cambiarTexto(b.querySelector('.t'),o.txt);
  if(error) sacudir(b);
}
/* llega el evento "servo" (manual) del servo n */
function servoLlego(n){
  document.querySelectorAll('#modServos button[aria-busy]').forEach(b=>{const o=b._ocupado; if(!o) return;
    o.faltan.delete(n);
    if(!o.faltan.size) setTimeout(()=>servoLibre(b),Math.max(0,MIN_OCUPADO-(performance.now()-o.t0)));
  });
}
function servosError(){document.querySelectorAll('#modServos button[aria-busy]').forEach(b=>servoLibre(b,true))}
