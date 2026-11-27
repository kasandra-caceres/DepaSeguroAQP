# Guía de trabajo con GitHub

Cómo se trabaja con el repositorio del proyecto en GitHub.

## 1. Repositorio

El repositorio es https://github.com/kasandra-caceres/DepaSeguroAQP y lo administra Kasandra Cáceres Quispe, líder y responsable del repositorio. Alisson Dolorier Arias, responsable de integración, pruebas y demostración, se agrega como colaboradora en Settings, Collaborators, y trabaja desde su propia cuenta.

Ramas: `main` guarda versiones estables etiquetadas, como `v1.0.0`; `develop` integra; cada cambio va en `feature/*` o `fix/*` y entra a `develop` por Pull Request con fusión `--no-ff`.

## 2. Configurar Git en tu equipo

Cada integrante configura su identidad una sola vez, con el correo de su cuenta de GitHub:

```
git config --global user.name "Nombre Apellido"
git config --global user.email "correo-de-su-cuenta@github"
git clone https://github.com/kasandra-caceres/DepaSeguroAQP.git
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

Luego se abre un Pull Request hacia `develop`, la otra integrante lo revisa y lo aprueba. Al final se fusiona `develop` en `main` y se crea una etiqueta de versión, por ejemplo `v1.1.0`.

## 4. Registrar los Issues

Cada incidencia nueva se registra como Issue con su causa, solución y prevención, y se agrega a `docs/ISSUES.md`. El Pull Request que la corrige la cierra con `Closes #n` en su descripción. ISSUE-01 a ISSUE-08 ya están registrados y cerrados.

## 5. Reemplazar las capturas del informe

Las figuras de la sección 3.4 salen de `docs/evidencias/git_grafo.png`, `git_ramas.png` y `git_commit.png`. Reemplázalas con capturas del repositorio real: el grafo de `git log --oneline --graph --all`, la lista de ramas, un commit con el nombre de una integrante y la pestaña de Issues. Después vuelve a generar el informe.
