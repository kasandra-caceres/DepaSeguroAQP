#!/usr/bin/env bash
# Prepara el repositorio con ramas main y develop y lo sube a GitHub.
# Usa la identidad Git de quien lo ejecuta: cada integrante debe tener configurados
# git config --global user.name y user.email con los datos de su cuenta de GitHub.
#
# Uso:  bash scripts/crear_repositorio.sh https://github.com/USUARIO/DepaSeguroAQP.git
set -e
REMOTO="$1"
if [ -z "$REMOTO" ]; then
  echo "Indica la URL del repositorio vacío creado en GitHub." >&2
  exit 1
fi
if [ -z "$(git config user.email)" ]; then
  echo "Configura primero tu nombre y correo de GitHub con git config --global." >&2
  exit 1
fi
if [ ! -d .git ]; then
  git init -b main
fi
git config core.longpaths true
git add .
git commit -m "chore: versión base del proyecto DepaSeguro AQP"
git branch -M main
git switch -c develop
git remote add origin "$REMOTO" 2>/dev/null || git remote set-url origin "$REMOTO"
git push -u origin main develop
echo "Listo. Trabaja cada cambio en una rama feature/* y súbelo con un Pull Request hacia develop."
