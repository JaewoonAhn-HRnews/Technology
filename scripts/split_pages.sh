#!/usr/bin/env bash
# pdfs/ 폴더의 기획서를 쪽 단위 텍스트(pages_YY_NNN.txt)로 분리
set -e
cd "$(dirname "$0")/../pdfs"
for y in 17 18 19 21 22 23 24 25 26; do
  f=$(ls ${y}-*_*기획서.pdf | head -1)
  n=$(pdfinfo "$f" | awk '/^Pages:/{print $2}')
  for p in $(seq 1 $n); do pdftotext -layout -f $p -l $p "$f" "pages_${y}_$(printf %03d $p).txt" 2>/dev/null; done
done
