"""보조 자료 추출: ’26판 목록의 국방전략기술 표기, 민간보유기술, 소재·부품 과제, 전력지원체계 과제."""
import re, json, os, glob, subprocess
from common import SRC, WORK

def pages_text(pdf, f=None, l=None):
    args = ["pdftotext", "-layout"] + (["-f", str(f), "-l", str(l)] if f else []) + [os.path.join(SRC, pdf), "-"]
    return subprocess.run(args, capture_output=True).stdout.decode("utf8", "ignore")

def strat_2026(pdf):
    m = {}
    for p in range(300, 336):
        for ln in pages_text(pdf, p, p).split("\n"):
            r = re.match(r'^\s*(\d{1,3})\s+(.*?)\s+(\d[\d,]*\.\d{1,2})\s+(인공지능|유·무인 복합|양자|우주|에너지|첨단소재|사이버·네트워크|센서·전자기전|추진|WMD 대응|-)\s*$', ln)
            if r: m[int(r.group(1))] = r.group(4)
    json.dump(m, open(f"{WORK}/strat_2026.json", "w"), ensure_ascii=False)

def parts(pdf):
    rows = {}
    for ln in pages_text(pdf).split("\n"):
        m = re.match(r'^\s*(\d{2}-[A-Z]-\d{2}-\d{3})\s+(\S+)\s{2,}(.+?)\s{2,}(.+?)\s{2,}(\S+)\s+(\d{4})\s+(\d+)\s+([\d.,]+)\s*$', ln)
        if m:
            rows[m.group(1)] = dict(id=m.group(1), domain=m.group(2), system=m.group(3).strip(), name=m.group(4).strip(), type=m.group(5),
                                    start=int(m.group(6)), months=int(m.group(7)), budget=float(m.group(8).replace(",", "")))
    json.dump(list(rows.values()), open(f"{WORK}/parts.json", "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    import sys
    strat_2026(os.environ.get("PDF_2026", "26-40_국방기술기획서.pdf"))
    parts(os.environ.get("PDF_PARTS", "26-30_소재부품기획서.pdf"))
    print("민간보유기술(civil.json)·전력지원(support.json) 추출은 README의 안내를 따르세요.")
