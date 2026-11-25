#!/usr/bin/env bash
# Gera o PDF da proposta comercial SISCF a partir do HTML.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$DIR/Proposta_Comercial_SISCF.pdf}"
HTML="$DIR/proposta-siscf.html"

if ! command -v google-chrome >/dev/null 2>&1; then
  echo "google-chrome não encontrado. Abra proposta-siscf.html no navegador e use 'Salvar PDF / Imprimir'."
  exit 1
fi

timeout 60 google-chrome \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --emulate-media-type=print \
  --virtual-time-budget=15000 \
  --print-to-pdf="$OUT" \
  "file://$HTML" \
  >/dev/null 2>&1 || true

if [[ -f "$OUT" ]]; then
  echo "PDF gerado: $OUT"
else
  echo "Falha ao gerar PDF. Abra $HTML no Chrome e clique em 'Salvar PDF / Imprimir'."
  exit 1
fi
