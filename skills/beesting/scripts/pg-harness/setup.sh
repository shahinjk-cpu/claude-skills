#!/bin/sh
# Ставит зависимости стенда в ЕГО каталоге. Копируйте pg-harness во временную папку
# и запускайте setup.sh там, чтобы node_modules не попали в скилл или в проект.
set -e
cd "$(dirname "$0")"
npm install --no-audit --no-fund --silent
# На macOS пакет бинарников иногда приезжает без симлинков библиотек — восстанавливаем.
for d in node_modules/@embedded-postgres/*/; do
  if [ -f "$d/scripts/hydrate-symlinks.js" ]; then
    (cd "$d" && node scripts/hydrate-symlinks.js >/dev/null 2>&1) || true
  fi
done
echo "pg-harness готов: node $(pwd)/harness.mjs --repo <путь к проекту>"
