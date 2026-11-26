#!/bin/sh
# SRI-хэш (sha384) для файлов с CDN. Использование: sh sri.sh URL [URL ...]
# Вставлять в тег: integrity="sha384-..." crossorigin="anonymous"
set -e
[ $# -gt 0 ] || { echo "Использование: sh sri.sh https://cdn.jsdelivr.net/npm/pkg@1.2.3/dist/pkg.js"; exit 1; }
for url in "$@"; do
  case "$url" in
    *@latest*|*@[0-9]/*|*@[0-9][0-9]/*) echo "⚠ $url — версия не точная, хэш сломается при обновлении пакета" ;;
  esac
  hash=$(curl -fsSL "$url" | openssl dgst -sha384 -binary | openssl base64 -A)
  echo "$url"
  echo "  integrity=\"sha384-$hash\" crossorigin=\"anonymous\""
done
