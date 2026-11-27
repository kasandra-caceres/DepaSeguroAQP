// Interacciones de interfaz. Toda la lógica de negocio se ejecuta en Python.
(function () {
  const boton = document.querySelector('[data-menu]');
  const menu = document.getElementById('menu');
  if (boton && menu) {
    boton.addEventListener('click', () => {
      const abierto = menu.classList.toggle('abierto');
      boton.setAttribute('aria-expanded', String(abierto));
    });
  }

  const pagina = encodeURIComponent(location.href);
  const texto = encodeURIComponent('Revisa este aviso en DepaSeguro AQP antes de pagar: ');
  const destinos = {
    whatsapp: `https://wa.me/?text=${texto}${pagina}`,
    facebook: `https://www.facebook.com/sharer/sharer.php?u=${pagina}`,
    x: `https://x.com/intent/post?text=${texto}&url=${pagina}`,
  };
  document.querySelectorAll('[data-compartir]').forEach((enlace) => {
    enlace.href = destinos[enlace.dataset.compartir];
  });

  document.querySelectorAll('[data-confirmar]').forEach((formulario) => {
    formulario.addEventListener('submit', (evento) => {
      if (!window.confirm(formulario.dataset.confirmar)) evento.preventDefault();
    });
  });

  const rol = document.querySelector('[data-rol]');
  if (rol) {
    const campos = document.querySelector('[data-campos-arrendador]');
    const actualizar = () => { campos.hidden = rol.value !== 'arrendador'; };
    rol.addEventListener('change', actualizar);
    actualizar();
  }
})();

const COLOR_NIVEL = { 'Confiable': '#2c7a4b', 'Precaución': '#a87406', 'Riesgo alto': '#c2571a', 'Crítico': '#a32020' };

function crearMapa(id, zoom) {
  const mapa = L.map(id).setView([-16.4040, -71.5370], zoom || 13);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; colaboradores de OpenStreetMap',
  }).addTo(mapa);
  return mapa;
}

async function iniciarMapaGeneral(id) {
  const mapa = crearMapa(id, 13);
  const respuesta = await fetch('/api/mapa');
  const datos = await respuesta.json();
  datos.campus.forEach((c) => {
    L.circleMarker([c.lat, c.lon], { radius: 7, color: '#22303c', fillColor: '#22303c', fillOpacity: .9 })
      .bindPopup(`<b>${c.universidad}</b><br>Local ${c.local}<br>${c.licencia || ''}`).addTo(mapa);
  });
  datos.avisos.forEach((a) => {
    const color = COLOR_NIVEL[a.nivel] || '#66717a';
    L.circleMarker([a.lat, a.lon], { radius: 9, color: '#fff', weight: 2, fillColor: color, fillOpacity: 1 })
      .bindPopup(`<b>${a.titulo}</b><br>${a.distrito} · S/ ${Math.round(a.precio)}<br>${a.nivel} (${a.trust} puntos)<br><a href="${a.url}">Ver ficha</a>`)
      .addTo(mapa);
  });
}

function iniciarSelectorMapa(id, campoLat, campoLon) {
  const mapa = crearMapa(id, 13);
  const lat = document.getElementById(campoLat);
  const lon = document.getElementById(campoLon);
  let marcador = null;
  const colocar = (punto) => {
    if (marcador) marcador.setLatLng(punto); else marcador = L.marker(punto).addTo(mapa);
  };
  if (lat.value && lon.value) {
    const punto = [Number(lat.value), Number(lon.value)];
    colocar(punto);
    mapa.setView(punto, 15);
  }
  mapa.on('click', (evento) => {
    colocar(evento.latlng);
    lat.value = evento.latlng.lat.toFixed(6);
    lon.value = evento.latlng.lng.toFixed(6);
  });
}

function iniciarMapaPunto(id, lat, lon) {
  const mapa = crearMapa(id, 15);
  mapa.setView([lat, lon], 15);
  L.marker([lat, lon]).addTo(mapa);
}

async function graficarSerie(id, url) {
  const contenedor = document.getElementById(id);
  const respuesta = await fetch(url);
  const datos = await respuesta.json();
  const etiquetasFuturas = datos.proyeccion.map((_, i) => `+${i + 1} mes`);
  const relleno = new Array(datos.valores.length - 1).fill(null);
  const ultimo = datos.valores[datos.valores.length - 1];
  if (contenedor._grafico) contenedor._grafico.destroy();
  contenedor._grafico = new Chart(contenedor, {
    type: 'line',
    data: {
      labels: [...datos.etiquetas, ...etiquetasFuturas],
      datasets: [
        { label: 'Estafas denunciadas', data: datos.valores, borderColor: '#22303c', backgroundColor: '#22303c', tension: .25, pointRadius: 2 },
        { label: 'Proyección', data: [...relleno, ultimo, ...datos.proyeccion], borderColor: '#b4532a', backgroundColor: '#b4532a', borderDash: [6, 4], pointRadius: 3 },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } }, scales: { y: { beginAtZero: true } } },
  });
}

async function graficarPanel(idNiveles, idMotivos) {
  const respuesta = await fetch('/api/admin/indicadores');
  const datos = await respuesta.json();
  const niveles = Object.keys(COLOR_NIVEL);
  new Chart(document.getElementById(idNiveles), {
    type: 'bar',
    data: { labels: niveles, datasets: [{ label: 'Avisos', data: niveles.map((n) => datos.niveles[n] || 0), backgroundColor: niveles.map((n) => COLOR_NIVEL[n]) }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
  new Chart(document.getElementById(idMotivos), {
    type: 'bar',
    data: { labels: datos.motivos.map((m) => m.motivo.replaceAll('_', ' ')), datasets: [{ label: 'Reportes', data: datos.motivos.map((m) => m.total), backgroundColor: '#b4532a' }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}
