# Guía para publicar DepaSeguro AQP en GitHub

El informe dice que el código está en GitHub y que las incidencias están registradas como Issues. Esta guía deja eso verdadero antes de la entrega del 01-12-2026.

## 1. Crear el repositorio

1. La responsable de versiones crea un repositorio vacío llamado `DepaSeguroAQP` en su cuenta.
2. Copia la URL exacta y compárala con la de la carátula del informe. Si cambia, edita `REPOSITORIO` en `scripts/generar_informe.py` y vuelve a generar el informe.
3. Agrega a la otra integrante como colaboradora en Settings, Collaborators.

## 2. Subir la versión base

Cada integrante configura su identidad una sola vez:

```
git config --global user.name "Nombre Apellido"
git config --global user.email "correo-de-su-cuenta@github"
```

La responsable de versiones ejecuta:

```
bash scripts/crear_repositorio.sh https://github.com/USUARIO/DepaSeguroAQP.git
```

## 3. Trabajar con ramas y Pull Requests

Cada cambio, por pequeño que sea, sigue este ciclo desde la cuenta de quien lo hizo:

```
git switch develop
git pull
git switch -c feature/nombre-del-cambio
python -m pytest
git add .
git commit -m "feat(modulo): descripción corta"
git push -u origin feature/nombre-del-cambio
```

Luego se abre un Pull Request hacia `develop`, la otra integrante lo revisa y lo aprueba. Al final se fusiona `develop` en `main` y se crea la etiqueta `v1.0`.

## 4. Registrar los Issues

Crea un Issue por cada fila de `docs/ISSUES.md`, ISSUE-01 a ISSUE-06, con la causa, la solución y la prevención. Ciérralos mencionando el commit o el Pull Request que los corrige.

## 5. Reemplazar las capturas del informe

Las figuras de la sección 3.4 salen de `docs/evidencias/git_grafo.png`, `git_ramas.png` y `git_commit.png`. Reemplázalas con capturas del repositorio real: el grafo de `git log --oneline --graph --all`, la lista de ramas, un commit con el nombre de una integrante y la pestaña de Issues. Después vuelve a generar el informe.
