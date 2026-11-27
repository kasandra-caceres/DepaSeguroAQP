# DepaSeguro AQP

Plataforma web para verificar avisos de vivienda universitaria en Arequipa, calcular un Trust Score y prevenir estafas de alquiler.

Proyecto final del curso **Lenguajes de Programación**, Universidad Tecnológica del Perú, Grupo 08.

Repositorio: https://github.com/kasandra-caceres/DepaSeguroAQP

```
git clone https://github.com/kasandra-caceres/DepaSeguroAQP.git
```

## Qué hace

- Publica y evalúa cuartos, minidepartamentos y pensiones.
- Normaliza precios a soles por mes y por m².
- Detecta precios anormales, fotos repetidas, teléfonos reincidentes y lenguaje de estafa.
- Deduce patrones de fraude con un motor lógico tipo Prolog escrito en Python.
- Busca por cercanía a campus con coordenadas oficiales de SUNEDU.
- Verifica avisos vistos en redes sociales.
- Registra reseñas verificadas, reportes y descargos del arrendador.
- Revisa cláusulas abusivas y genera un contrato modelo.
- Genera alertas, redes de cuentas relacionadas y reportes en PDF, Excel y CSV.
- Prepara un expediente de apoyo para denunciar.

## Lectura automática de fuentes

| Fuente | Tipo | Uso |
| --- | --- | --- |
| BCRP | Estado | Tipo de cambio e IPC |
| MININTER | Estado | Denuncias policiales por distrito |
| Ministerio Público | Estado | Delitos informáticos en Arequipa |
| SUNEDU | Estado | Ubicación y licencia de campus |
| OpenStreetMap | ONG | Verificación de direcciones |
| Wikidata | ONG | Población por distrito |
| Transparency International, vía Our World in Data | ONG | Índice de Percepción de la Corrupción |

El planificador revisa cada hora y actualiza cada 24 horas. Si una fuente falla, el sistema conserva los últimos datos válidos.

## Instalación rápida

Requiere Python 3.12 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py --ingesta
python scripts/poblar_demo.py
python run.py
```

Abre <http://127.0.0.1:5000>. El manual completo está en `entregables/`.

Cuentas de demostración, con la clave definida en `scripts/poblar_demo.py`:

| Rol | Correo |
| --- | --- |
| Administración | `admin@depaseguro.test` |
| Estudiante | `estudiante@depaseguro.test` |
| Arrendador | `carlos@depaseguro.test` |

Todos los avisos y usuarios de demostración son ficticios y aparecen marcados.

## Documentos

`scripts/` contiene los generadores de diagramas, evidencias, informe, manual y presentación. Necesitan `requirements-docs.txt` y Microsoft Office.

## Pruebas

```bash
python -m pytest --cov=depaseguro
```

## Arquitectura

MVC con Flask, DAO, DTO, Factory, Strategy, Facade, Observer y Template Method. El backend y los cálculos usan Python; SQLite guarda los datos.

```text
depaseguro/
  models/      clases de dominio y DTO
  dao/         acceso a datos
  functional/  utilidades funcionales
  logic/       motor lógico y reglas
  services/    negocio y reportes
  ingestion/   fuentes y planificador
  web/         controladores Flask
  templates/   vistas
  static/      CSS, JavaScript y recursos
```

## Alcance y límites

El Trust Score es una estimación automática. No acusa a ninguna persona ni reemplaza una visita, un contrato o una consulta registral. Los precios de referencia dependen de los avisos registrados, porque no se encontró una fuente oficial de alquiler por distrito.
