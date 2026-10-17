import re, subprocess, os, json, html

SRC = os.environ.get("ATLAS_SRC", os.path.join(os.path.dirname(__file__), "..", "pdfs"))
WORK = os.environ.get("ATLAS_WORK", os.path.join(os.path.dirname(__file__), "..", "work"))
DOCS = {
    "2017": "17-31_핵심기술기획서.pdf",
    "2018": "18-32_핵심기술기획서.pdf",
    "2019": "19-33_핵심기술기획서.pdf",
    "2021": "21-35_국방기술기획서.pdf",
    "2022": "22-36_국방기술기획서.pdf",
    "2023": "23-37_국방기술기획서.pdf",
    "2024": "24-38_국방기술기획서.pdf",
    "2025": "25-39_국방기술기획서.pdf",
    "2026": "26-40_국방기술기획서.pdf",
}

WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE_RE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')


def bbox_pages(pdf):
    """Return list of pages: dict(w,h,words=[(x0,y0,x1,y1,text)])"""
    cache = os.path.join(WORK, "cache", os.path.basename(pdf) + ".bbox.html")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    if not os.path.exists(cache):
        subprocess.run(["pdftotext", "-bbox-layout", os.path.join(SRC, pdf), cache],
                       stderr=subprocess.DEVNULL)
    data = open(cache, encoding="utf8").read()
    pages = []
    parts = re.split(r'(?=<page width=)', data)
    for part in parts[1:]:
        m = PAGE_RE.match(part)
        w, h = float(m.group(1)), float(m.group(2))
        words = [(float(a), float(b), float(c), float(d), html.unescape(t))
                 for a, b, c, d, t in WORD_RE.findall(part)]
        pages.append(dict(w=w, h=h, words=words))
    return pages


def rows_of(words, tol=3.0):
    """group words into rows by y center"""
    ws = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows = []
    for w in ws:
        c = (w[1] + w[3]) / 2
        if rows and abs(rows[-1]["c"] - c) <= tol:
            rows[-1]["w"].append(w)
        else:
            rows.append({"c": c, "w": [w]})
    for r in rows:
        r["w"].sort(key=lambda w: w[0])
    return rows


def join(words):
    out = ""
    prev = None
    for w in sorted(words, key=lambda w: w[0]):
        if prev is not None and w[0] - prev[2] < 1.2:
            out += w[4]
        else:
            out += (" " if out else "") + w[4]
        prev = w
    return out


def text_of(words):
    rows = rows_of(words)
    lines = [join(r["w"]) for r in rows]
    # merge Korean line wraps: if line ends with hangul and next starts with hangul, no space? keep space conservatively
    s = ""
    for ln in lines:
        if not s:
            s = ln
        elif re.search(r'[가-힣]$', s) and re.match(r'^[가-힣]', ln) and len(ln) > 0:
            # word wrapped mid-word typically when line is full; join without space if previous line long
            last = s.split()[-1]
            first = ln.split()[0]
            glue = (len(last) <= 2 and last not in ("및", "등", "위한", "통한", "대한")) or len(re.sub(r'[^가-힣]', '', first)) <= 1
            s += ln if glue else " " + ln
        else:
            s += " " + ln
    return re.sub(r"\s+", " ", s).strip()
