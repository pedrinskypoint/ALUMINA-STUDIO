#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -n "$(git status --porcelain)" ]; then
  echo 'Hay cambios locales. Sincronizalos antes de actualizar para no pisar tu trabajo.'
  read -r -p 'Presioná Enter para cerrar.'
  exit 1
fi
git pull --ff-only
echo 'Código actualizado. Detené ALUMINA con Ctrl+C y volvé a abrir Iniciar ALUMINA.command.'
echo 'Si cambiaron requirements.txt, instalá esas dependencias en el entorno virtual antes de reiniciar.'
read -r -p 'Presioná Enter para cerrar.'
