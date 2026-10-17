#!/usr/bin/env bash
# 전체 파이프라인: PDF → 구조화 JSON → data/*.json
set -e
cd "$(dirname "$0")"
mkdir -p ../work
bash split_pages.sh
for y in 2021 2022 2023 2024 2025 2026; do python3 parse_cards.py $y; done
python3 parse_old.py
python3 parse_taxo.py
python3 extract_misc.py
python3 build_data.py
python3 parse_compare.py
python3 build_compare.py
