"use strict";
/* Sección Datos (datos.html): muestra lo registrado. Solo dibuja; todo lo calcula el backend
   (pc/pia/seccion_datos.py). Se actualiza sola, así que los compañeros aparecen al registrarse. */
const RAIZ=document.documentElement;
const ic=n=>`<svg class="ic" data-n="${n}" viewBox="0 0 24 24" aria-hidden="true">${IC[n]||''}</svg>`;
document.querySelectorAll('[data-ic]').forEach(e=>{e.outerHTML=ic(e.dataset.ic)});
/* acento claro: mismo cálculo que dibujo.js (verde FIME con 38 % de blanco) */
(()=>{const v=(getComputedStyle(RAIZ).getPropertyValue('--verde-fime')||'#1F9F5C').trim().replace('#','');
  const c=[0,2,4].map(i=>parseInt(v.slice(i,i+2),16)).map(c=>Math.round(c+(255-c)*.38));
  RAIZ.style.setProperty('--acento-claro',`rgb(${c})`)})();

const API='/api/datos';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>v==null?'—':`${(v*100).toFixed(1)} %`;
const num=(v,d=3)=>v==null?'—':Number(v).toFixed(d);
const fecha=s=>{if(!s)return'—';const d=new Date(s);return isNaN(d)?s:d.toLocaleString('es-MX',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})};
const NIVEL={1:'Lector',2:'Editor'};
const FUENTE={as608:'AS608',fvc2002:'FVC2002',camara:'cámara',orl:'ORL'};
const DEDO={indice:'índice',menique:'meñique',corazon:'corazón',izq:'izquierdo',der:'derecho'};
const nombreDedo=s=>{const [p,...r]=s.split('_');return `${p[0].toUpperCase()+p.slice(1)} · ${r.map(x=>DEDO[x]||x).join(' ')||'dedo'}`};
const guardar=(k,v)=>{try{sessionStorage.setItem(k,v)}catch(e){}};
const leer=k=>{try{return sessionStorage.getItem(k)}catch(e){return null}};

let D=null, firma='', tab='usuarios', dominio='camara';
const minCache=new Map();   // muestra -> minucias (no cambian: la plantilla queda fija al registrar)

/* ---------------- privacidad: las imágenes empiezan difuminadas ---------------- */
function privado(on){
  RAIZ.classList.toggle('privado',on);
  $('#verImg').setAttribute('aria-pressed',String(!on));
  $('#verImgTxt').textContent=on?'Mostrar imágenes':'Ocultar imágenes';
  guardar('datos.privado',on?'1':'0');
}
$('#verImg').onclick=()=>privado(!RAIZ.classList.contains('privado'));
privado(leer('datos.privado')!=='0');

/* ---------------- pestañas ---------------- */
function irA(t){
  if(t!==tab) window.scrollTo(0,0);
  tab=t;
  document.querySelectorAll('#tabs button').forEach(b=>{const on=b.dataset.t===t;b.setAttribute('aria-pressed',on);b.setAttribute('aria-selected',on)});
  document.querySelectorAll('.d-tab').forEach(s=>{s.hidden=s.id!==`t-${t}`});
  if(location.hash!==`#${t}`) history.replaceState(null,'',`#${t}`);
  pintar();
}
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>irA(b.dataset.t));
document.querySelectorAll('#dominio button').forEach(b=>b.onclick=()=>{
  dominio=b.dataset.d;document.querySelectorAll('#dominio button').forEach(x=>x.setAttribute('aria-pressed',x===b));pintarModelo()});
$('#verMin').onchange=()=>RAIZ.classList.toggle('sin-minucias',!$('#verMin').checked);

/* ---------------- carga y actualización ---------------- */
async function cargar(forzar=false){
  try{
    const r=await fetch(API,{cache:'no-store'});
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    const txt=await r.text();
    $('#estado').textContent=`Actualizado a las ${new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})} · se actualiza solo cada 15 s`;
    if(txt===firma && !forzar) return;
    firma=txt; D=JSON.parse(txt); pintar(true);
  }catch(e){
    $('#estado').textContent=`No se pudo leer el backend (${e.message}). ¿Está corriendo python -m pia?`;
  }
}
$('#actualizar').onclick=()=>cargar(true);
setInterval(()=>{if(!document.hidden) cargar()},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden) cargar()});

const hechos=new Set();   // pestañas ya dibujadas con los datos actuales
function pintar(nuevos=false){
  if(!D) return;
  if(nuevos) hechos.clear();
  if(hechos.has(tab)) return;
  hechos.add(tab);
  ({usuarios:pintarUsuarios,modelo:pintarModelo,calibracion:pintarCalibracion,banco:pintarBanco})[tab]();
}

/* ---------------- huella con minucias ---------------- */
function huellaFig(h,cap){
  return `<figure class="d-fig"><button class="d-img bio d-huella" data-h="${h.id}" style="aspect-ratio:${h.ancho}/${h.alto}" aria-label="Ver huella ${h.id}">
    <img src="${API}/huella/${h.id}.png" alt="" loading="lazy" width="${h.ancho}" height="${h.alto}">
    <svg class="d-min" viewBox="0 0 ${h.ancho} ${h.alto}" aria-hidden="true"></svg></button>
    <figcaption class="cap mono">${cap}</figcaption></figure>`;
}
function svgMinucias(ms){
  return ms.map(m=>{
    const dx=Math.cos(m.t)*9, dy=Math.sin(m.t)*9;   // dirección en [0, π), en coordenadas de imagen (como dibujo.js)
    const marca=m.tipo==='B'?`<rect x="${m.x-3.5}" y="${m.y-3.5}" width="7" height="7" class="b"/>`:`<circle cx="${m.x}" cy="${m.y}" r="4" class="t"/>`;
    return `${marca}<line x1="${m.x}" y1="${m.y}" x2="${(m.x+dx).toFixed(1)}" y2="${(m.y+dy).toFixed(1)}" class="${m.tipo==='B'?'b':'t'}"/>`;
  }).join('');
}
async function minucias(id){
  if(!minCache.has(id)) minCache.set(id,fetch(`${API}/huella/${id}/minucias`).then(r=>r.json()));
  return minCache.get(id);
}
function llenarMinucias(raiz){
  raiz.querySelectorAll('.d-huella').forEach(async b=>{b.querySelector('svg').innerHTML=svgMinucias(await minucias(+b.dataset.h))});
}

/* ---------------- pestaña Usuarios ---------------- */
function pintarUsuarios(){
  const us=D.usuarios, reales=us.filter(u=>!u.de_prueba).length;
  $('#usResumen').innerHTML=us.length?`<b>${us.length}</b> usuarios: <b>${reales}</b> registrados con la caja (AS608 y cámara) y <b>${us.length-reales}</b> de prueba para Simular (FVC2002 y ORL).`:'';
  if(!us.length){$('#usLista').innerHTML=vacio('Aún no hay usuarios. Se agregan con pc\\scripts\\registrar.py y aparecen aquí solos.');return}
  const orden=[...us].sort((a,b)=>a.de_prueba-b.de_prueba||a.id.localeCompare(b.id));
  $('#usLista').innerHTML=orden.map(u=>{
    const fh=[...new Set(u.huellas.map(h=>FUENTE[h.fuente]||h.fuente))].join(', ');
    const fr=[...new Set(u.rostros.map(r=>FUENTE[r.fuente]||r.fuente))].join(', ');
    const mins=u.huellas.map(h=>h.n_minucias);
    return `<article class="panel d-usuario${u.de_prueba?' prueba':''}">
      <div class="panel-head"><span class="d-id mono">${esc(u.id)}</span><h2>${esc(u.nombre)}</h2>
        <span class="chip">Nivel ${u.nivel} · ${NIVEL[u.nivel]||''}</span>
        ${u.de_prueba?'<span class="chip aviso">'+ic('flask-conical')+'Prueba · dataset</span>':''}
        <span class="meta mono">alta ${fecha(u.creado_en)}</span></div>
      <div class="sect"><span class="label">Huellas · ${esc(fh)||'—'} · ${u.huellas.length} plantillas${mins.length?` · ${Math.min(...mins)}–${Math.max(...mins)} minucias`:''}</span>
        <div class="d-tira d-tira-h">${u.huellas.map(h=>huellaFig(h,`${h.n_minucias} min · q ${num(h.calidad,2)}`)).join('')||'<span class="cap">Sin huellas</span>'}</div></div>
      <div class="sect"><span class="label">Rostro · ${esc(fr)||'—'} · ${u.rostros.length} caras alineadas (64 × 64, CLAHE y máscara)</span>
        <div class="d-tira d-tira-r">${u.rostros.map(r=>`<button class="d-img bio d-cara" data-r="${r.id}" data-n="${esc(u.nombre)}" aria-label="Ver cara ${r.id}"><img src="${API}/rostro/${r.id}.png?alineado=1" alt="" loading="lazy" width="64" height="64"></button>`).join('')||'<span class="cap">Sin caras</span>'}</div></div>
      ${u.tanda2.length?`<div class="sect"><span class="label">Segunda tanda · ${u.tanda2.length} cuadros (genuinos para calibrar el rostro)</span>
        <div class="d-tira d-tira-t">${u.tanda2.map(a=>`<button class="d-img bio d-t2" data-src="${API}/tanda2/${encodeURIComponent(u.id)}/${encodeURIComponent(a)}" data-n="${esc(u.nombre)}" aria-label="Ver cuadro ${esc(a)}"><img src="${API}/tanda2/${encodeURIComponent(u.id)}/${encodeURIComponent(a)}" alt="" loading="lazy"></button>`).join('')}</div></div>`:''}
    </article>`}).join('');
  llenarMinucias($('#usLista'));
}

/* ---------------- pestaña Modelo de rostro ---------------- */
function pintarModelo(){
  if(!D) return;
  hechos.add('modelo');
  const hay=new Set(D.modelos.map(m=>m.dominio));
  document.querySelectorAll('#dominio button').forEach(b=>{b.disabled=!hay.has(b.dataset.d)});
  if(!hay.has(dominio) && hay.size) dominio=[...hay][0];
  document.querySelectorAll('#dominio button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.d===dominio));
  const m=D.modelos.find(x=>x.dominio===dominio);
  if(!m){$('#modResumen').textContent='';$('#modCuerpo').innerHTML=vacio('Todavía no hay un modelo de Eigenfaces: se entrena al registrar el primer usuario.');return}
  const v=`m=${m.id}`;   // cada reentrenamiento crea un modelo con otro id: así no se queda una imagen vieja
  const us=D.usuarios.filter(u=>u.rostros.some(r=>r.dominio===dominio));
  const ks=[...new Set([5,15,40].filter(k=>k<m.k).concat(m.k))];
  $('#modResumen').innerHTML=`Entrenado ${fecha(m.creado_en)} con <b>${m.n_entrenamiento}</b> caras: las de los usuarios y caras de fondo de ORL. Se reentrena con cada alta.`;
  $('#modCuerpo').innerHTML=`
  <div class="d-mod">
    <section class="panel d-mod-a">
      <div class="panel-head"><h2>Subespacio de caras</h2><span class="meta mono">PCA con NumPy · truco de la matriz pequeña</span></div>
      <div class="d-metricas">
        <div class="metric"><span class="label">Componentes (k)</span><div class="v">${m.k}</div></div>
        <div class="metric"><span class="label">Varianza explicada</span><div class="v">${pct(m.varianza)}</div></div>
        <div class="metric"><span class="label">Caras de entrenamiento</span><div class="v">${m.n_entrenamiento}</div></div>
        <div class="metric"><span class="label">Tamaño de cara</span><div class="v">${m.lado} × ${m.lado}</div></div>
      </div>
      <div class="d-media"><figure><img class="d-pix" src="${API}/modelo/${dominio}/media.png?${v}" alt="Cara media" width="${m.lado}" height="${m.lado}"><figcaption class="cap">Cara media</figcaption></figure>
        <div class="sect"><span class="label">Primeras ${m.eigenfaces} eigenfaces (de ${m.k})</span>
          <div class="d-eig">${Array.from({length:m.eigenfaces},(_,i)=>`<figure><img class="d-pix" src="${API}/modelo/${dominio}/eigenface/${i}.png?${v}" alt="Eigenface ${i+1}" loading="lazy" width="${m.lado}" height="${m.lado}"><figcaption class="cap mono">${i+1}</figcaption></figure>`).join('')}</div></div></div>
    </section>
    <section class="panel d-mod-b">
      <div class="panel-head"><h2>Varianza acumulada</h2><span class="meta mono">k = menor número que llega a 95 %</span></div>
      ${curvaVarianza(m.acumulada)}
    </section>
  </div>
  <section class="panel d-recon">
    <div class="panel-head"><h2>Reconstrucción con k componentes</h2><span class="meta mono">cara media + suma de pesos por eigenface</span></div>
    <p class="cap">Cada cara registrada se proyecta al subespacio y se vuelve a armar con las primeras k eigenfaces: con pocas solo queda la forma general; con todas, la persona. Los pesos de esa proyección son los que se comparan con distancia euclidiana.</p>
    ${us.length?`<div class="tbl-wrap"><table class="d-tabla-recon"><thead><tr><th>Usuario</th><th>Alineada</th>${ks.map(k=>`<th class="mono">k = ${k}</th>`).join('')}</tr></thead><tbody>
      ${us.map(u=>{const r=u.rostros.find(x=>x.dominio===dominio);return `<tr><td><span class="d-id mono">${esc(u.id)}</span> ${esc(u.nombre)}</td>
        <td><span class="d-img bio"><img class="d-pix" src="${API}/rostro/${r.id}.png?alineado=1" alt="" loading="lazy" width="64" height="64"></span></td>
        ${ks.map(k=>`<td><span class="d-img bio"><img class="d-pix" src="${API}/rostro/${r.id}/reconstruccion.png?k=${k}&${v}" alt="" loading="lazy" width="64" height="64"></span></td>`).join('')}</tr>`}).join('')}
    </tbody></table></div>`:vacio('Ningún usuario tiene caras en este modelo.')}
  </section>`;
}
function curvaVarianza(ac){
  const W=560,H=220,L=40,R=12,T=12,B=34,n=ac.length;
  const X=i=>L+(n>1?i/(n-1):0)*(W-L-R), Y=v=>T+(1-v)*(H-T-B);
  const pts=ac.map((v,i)=>`${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(' ');
  const ticks=[0,.25,.5,.75,1].map(v=>`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" class="rej"/><text x="${L-6}" y="${Y(v)+4}" text-anchor="end">${v*100}%</text>`).join('');
  const xs=[1,Math.round(n/2),n].map(k=>`<text x="${X(k-1)}" y="${H-B+16}" text-anchor="middle">${k}</text>`).join('');
  return `<svg class="d-graf" viewBox="0 0 ${W} ${H}" role="img" aria-label="Varianza acumulada: ${pct(ac[n-1])} con ${n} componentes">
    ${ticks}${xs}<line x1="${L}" x2="${W-R}" y1="${Y(.95)}" y2="${Y(.95)}" class="meta95"/>
    <text x="${W-R}" y="${Y(.95)-6}" text-anchor="end" class="meta95t">95 %</text>
    <polygon points="${X(0)},${Y(0)} ${pts} ${X(n-1)},${Y(0)}" class="area"/><polyline points="${pts}" class="linea"/>
    <text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">componentes</text></svg>`;
}

/* ---------------- pestaña Calibración ---------------- */
const CAL={'huella as608':'Huella · AS608 (caja)','huella fvc2002':'Huella · FVC2002 (Simular)','rostro camara':'Rostro · cámara (caja)','rostro dataset':'Rostro · ORL (Simular)'};
function pintarCalibracion(){
  const cs=[...D.calibraciones].sort((a,b)=>(a.dominio==='as608'||a.dominio==='camara'?0:1)-(b.dominio==='as608'||b.dominio==='camara'?0:1)||a.factor.localeCompare(b.factor));
  if(!cs.length){$('#calLista').innerHTML=vacio('Sin calibraciones activas: se crean con pc\\scripts\\calibrar.py.');return}
  $('#calLista').innerHTML=cs.map(c=>{
    const far0=c.criterio==='far0';
    return `<article class="panel">
      <div class="panel-head"><h2>${CAL[`${c.factor} ${c.dominio}`]||`${c.factor} · ${c.dominio}`}</h2>
        <span class="chip ${far0?'ok':''}">${far0?'Criterio FAR 0: ningún impostor pasa':'Criterio EER'}</span><span class="meta mono">${fecha(c.creada_en)}</span></div>
      <div class="d-metricas">
        <div class="metric"><span class="label">Umbral</span><div class="v">${num(c.umbral)}</div><span class="cap">${c.mayor_es_mejor?'acepta si puntaje ≥ umbral':'acepta si distancia &lt; umbral'}</span></div>
        <div class="metric"><span class="label">EER</span><div class="v">${pct(c.eer)}</div>${far0&&c.umbral_eer!=null?`<span class="cap">umbral EER ${num(c.umbral_eer)}</span>`:''}</div>
        <div class="metric"><span class="label">FAR</span><div class="v">${pct(c.far)}</div><span class="cap">impostores aceptados</span></div>
        <div class="metric"><span class="label">FRR</span><div class="v">${pct(c.frr)}</div><span class="cap">genuinos rechazados</span></div>
      </div>
      ${c.distribucion?histograma(c):'<p class="cap">Esta calibración no guardó la distribución.</p>'}
      <p class="cap">${c.n_genuinos} comparaciones genuinas y ${c.n_impostores} de impostor.</p>
    </article>`}).join('');
}
function histograma(c){
  const d=c.distribucion,n=d.genuinos.length,W=560,H=200,L=10,R=10,T=18,B=34,ancho=(W-L-R)/n;
  const mg=Math.max(1,...d.genuinos),mi=Math.max(1,...d.impostores);
  const barras=(arr,mx,cl)=>arr.map((v,i)=>{const h=v/mx*(H-T-B);return v?`<rect x="${(L+i*ancho+.5).toFixed(1)}" y="${(H-B-h).toFixed(1)}" width="${(ancho-1).toFixed(1)}" height="${h.toFixed(1)}" class="${cl}"><title>${v}</title></rect>`:''}).join('');
  const xu=L+clamp(c.umbral/d.max,0,1)*(W-L-R);
  const acepta=c.mayor_es_mejor?`<rect x="${xu}" y="${T}" width="${W-R-xu}" height="${H-T-B}" class="acepta"/>`:`<rect x="${L}" y="${T}" width="${xu-L}" height="${H-T-B}" class="acepta"/>`;
  const eje=c.mayor_es_mejor?'puntaje de matching por grafos (mayor = mismo dedo)':'distancia euclidiana entre pesos (menor = misma persona)';
  return `<svg class="d-graf d-hist" viewBox="0 0 ${W} ${H}" role="img" aria-label="Histograma de genuinos e impostores con el umbral en ${num(c.umbral)}">
    ${acepta}<line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}" class="rej"/>
    ${barras(d.impostores,mi,'imp')}${barras(d.genuinos,mg,'gen')}
    <line x1="${xu}" x2="${xu}" y1="${T-6}" y2="${H-B}" class="umbral"/><text x="${xu+4}" y="${T}" class="umbralt">umbral ${num(c.umbral)}</text>
    <text x="${L}" y="${H-B+16}">0</text><text x="${W-R}" y="${H-B+16}" text-anchor="end">${num(d.max,2)}</text>
    <text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">${eje}</text></svg>
    <div class="legend"><span><i class="lg-gen"></i>Genuinos</span><span><i class="lg-imp"></i>Impostores</span><span><i class="lg-acepta"></i>Zona que se acepta</span></div>`;
}

/* ---------------- pestaña Banco ---------------- */
function pintarBanco(){
  if(!D.banco.length){$('#bancoLista').innerHTML=vacio('El banco está vacío: se llena con pc\\scripts\\capturar_banco.py.');return}
  $('#bancoLista').innerHTML=D.banco.map(b=>`<article class="panel">
    <div class="panel-head"><h2>${esc(nombreDedo(b.identidad))}</h2><span class="meta mono">${b.archivos.length} capturas</span></div>
    <div class="d-tira d-tira-b">${b.archivos.map((a,i)=>{const src=`${API}/banco/${encodeURIComponent(b.identidad)}/${encodeURIComponent(a)}`;
      return `<figure class="d-fig"><button class="d-img bio d-bn" data-src="${src}" data-n="${esc(nombreDedo(b.identidad))}" aria-label="Ver captura ${esc(a)}"><img src="${src}" alt="" loading="lazy"></button>
      <figcaption class="cap mono">${i<5?'registro':'prueba'}</figcaption></figure>`}).join('')}</div>
  </article>`).join('');
}

const vacio=t=>`<div class="panel d-vacio"><p class="cap">${t}</p></div>`;

/* ---------------- visor: abrir una imagen en grande ---------------- */
const visor=$('#visor');
function abrir(tit,meta,html){
  $('#visorTit').textContent=tit;$('#visorMeta').textContent=meta;$('#visorCuerpo').innerHTML=html;
  visor.showModal();
}
$('#visorX').onclick=()=>visor.close();
visor.addEventListener('click',e=>{if(e.target===visor) visor.close()});
document.addEventListener('click',async e=>{
  const b=e.target.closest('button.d-img');if(!b) return;
  if(b.dataset.h){
    const h=D.usuarios.flatMap(u=>u.huellas.map(x=>({...x,u}))).find(x=>x.id===+b.dataset.h);
    abrir(`Huella de ${h.u.nombre}`,`${FUENTE[h.fuente]||h.fuente} · ${h.ancho} × ${h.alto} · ${h.n_minucias} minucias · calidad ${num(h.calidad,2)}`,
      `<div class="d-grande" style="aspect-ratio:${h.ancho}/${h.alto}"><img src="${API}/huella/${h.id}.png" alt=""><svg class="d-min" viewBox="0 0 ${h.ancho} ${h.alto}">${svgMinucias(await minucias(h.id))}</svg></div>`);
  }else if(b.dataset.r){
    const id=b.dataset.r;
    abrir(`Cara de ${b.dataset.n}`,'cuadro de la cámara y cara alineada que se guardó',
      `<div class="d-grande-par"><img src="${API}/rostro/${id}.png" alt="Cuadro original"><img class="d-pix" src="${API}/rostro/${id}.png?alineado=1" alt="Cara alineada"></div>`);
  }else{
    abrir(b.dataset.n||'Imagen','',`<div class="d-grande-par"><img src="${b.dataset.src}" alt=""></div>`);
  }
});

const desdeHash=()=>irA(['usuarios','modelo','calibracion','banco'].includes(location.hash.slice(1))?location.hash.slice(1):'usuarios');
window.addEventListener('hashchange',desdeHash);
desdeHash();
cargar();
