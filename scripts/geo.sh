#!/usr/bin/env bash
# Gera web/data/municipios.topojson (geometria simplificada, id = código IBGE).
set -euo pipefail
cd "$(dirname "$0")/.."
npx -y mapshaper@0.6.102 data/raw/mun.geojson \
  -filter-fields id \
  -simplify 4% keep-shapes \
  -o format=topojson quantization=1e5 id-field=id web/data/municipios.topojson
