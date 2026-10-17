"""Parse 2026 국방전략기술 taxonomy (L1 30 / L2 100 / L3 ~300) + 기술개발소요 tables."""
import re, json, glob, os
import pdfplumber
from common import bbox_pages, DOCS, SRC, WORK, rows_of, join, text_of

FIELDS = ["인공지능", "유·무인 복합", "양자", "우주", "에너지", "첨단소재", "사이버·네트워크", "센서·전자기전", "추진", "WMD 대응"]
SEC_START = {24: "인공지능", 72: "유·무인 복합", 102: "양자", 117: "우주", 147: "에너지", 161: "첨단소재", 183: "사이버·네트워크",
             230: "센서·전자기전", 254: "추진", 275: "WMD 대응"}  # book pages


def page_text(p):
    return open(f"{SRC}/pages_26_{p:03d}.txt").read()


def clean(ln):
    ln = re.sub(r'\s{4,}[가-힣0-9]{1,2}\s*$', '', ln)  # side tab
    return ln.rstrip()


def taxonomy():
    L1, L2, L3 = [], [], []
    field = None
    mode = False
    cur1 = cur2 = cur3 = None
    for p in range(26, 305):
        t = page_text(p)
        for raw in t.split("\n"):
            ln = clean(raw)
            m = re.search(r'제\s*\d+\s*절\s*\|\s*(인공지능|유[･·]무인 복합|양자|우주|에너지|첨단소재|사이버[･·]네트워크|센서[･·]전자기전|추진|WMD 대응)', ln)
            if m:
                field = m.group(1).replace("･", "·")
            if re.search(r'국방전략기술 명세', ln):
                mode = True
                continue
            if re.search(r'국방전략기술 확보계획', ln):
                mode = False
                cur1 = cur2 = cur3 = None
                continue
            if not mode:
                continue
            s = ln.strip()
            if not s or re.match(r'^’26-’40|^\d{1,3}$', s):
                continue
            m = re.match(r'^\s{0,4}(\d{1,2})\.\s+(\S.*)$', ln)
            if m and int(m.group(1)) <= 30:
                cur1 = dict(id=f"S{int(m.group(1)):02d}", no=int(m.group(1)), name=m.group(2).strip(), field=field, desc="")
                L1.append(cur1); cur2 = cur3 = None
                continue
            m = re.match(r'^\s{0,10}(\d{1,3}-\d{1,2})\s+(\S.*)$', ln)
            if m and cur2:
                cur3 = dict(id="T" + m.group(1), no=m.group(1), name=m.group(2).strip(), l2=cur2["id"], desc="")
                L3.append(cur3)
                continue
            m = re.match(r'^\s{0,8}(\d{1,3})\s+([가-힣A-Za-z(].*)$', ln)
            if m and cur1 and int(m.group(1)) <= 100 and int(m.group(1)) > (L2[-1]["no"] if L2 else 0) and int(m.group(1)) <= (L2[-1]["no"] if L2 else 0) + 3:
                cur2 = dict(id=f"D{int(m.group(1)):03d}", no=int(m.group(1)), name=m.group(2).strip(), l1=cur1["id"], desc="")
                L2.append(cur2); cur3 = None
                continue
            tgt = cur3 or cur2 or cur1
            if tgt is not None:
                tgt["desc"] = (tgt["desc"] + " " + s).strip()
    # L3 name wrap fix: if desc begins with short fragment ending in 기술 and name has no 기술
    return L1, L2, L3


PERIOD = r'(단기|중기|장기|단/중기|중/장기|단/장기|단/중/장기|단기/중기|중기/장기)'
METHOD = r'(핵심기술|미래도전|민간기술|핵심/미래|핵심/민간|미래/민간|국제공동|민군|핵심/미래/민간|기타)'


def needs(L1, L2, L3):
    pages = bbox_pages(DOCS["2026"])
    plumb = pdfplumber.open(os.path.join(SRC, DOCS["2026"]))
    out = []
    l1_by_no = {x["no"]: x for x in L1}
    norm = lambda s: re.sub(r'[\s·‧･/,()\-]', '', s or "")
    l3_by = {}
    for x in L3:
        l3_by.setdefault(norm(x["name"]), x)
    l2_by = {norm(x["name"]): x for x in L2}
    cur_l1 = None
    for pi in range(40, 310):
        t = page_text(pi + 1)
        m = re.search(r'^\s*(\d{2})\.\s+(\S.*)$', t, re.M)
        if m and int(m.group(1)) in l1_by_no:
            cur_l1 = l1_by_no[int(m.group(1))]
        if "기술개발소요명" not in t:
            continue
        pg = pages[pi]
        W = pg["w"]
        ws = [w for w in pg["words"] if not (len(w[4]) == 1 and w[0] > 0.86 * W)]
        hdr = [w for w in ws if w[4].startswith("기술개발소요명")]
        hdr2 = [w for w in ws if w[4] == "명세" or w[4].startswith("기술개발소요") and w is not hdr[0]]
        if not hdr:
            continue
        hy = hdr[0][3]
        anchors = [w for w in ws if re.fullmatch(PERIOD, w[4]) and w[1] > hy + 5]
        if not anchors:
            continue
        ax = min(a[0] for a in anchors)
        name_x0 = hdr[0][0] - 25
        spec_x0 = None
        specw = [w for w in ws if w[4] == "명세" and abs(w[1] - hdr[0][1]) < 6]
        if specw:
            spec_x0 = specw[0][0] - 60
        else:
            spec_x0 = hdr[0][2] + 30
        tables = plumb.pages[pi].find_tables()
        items = []
        for tb in tables:
            rows = tb.rows
            if not rows:
                continue
            hdr_cells = rows[0].cells
            if len(hdr_cells) < 5 or not hdr_cells[2] or not hdr_cells[3]:
                continue
            ncol = hdr_cells[2]; scol = hdr_cells[3]
            prev_l2 = ""
            for r in rows[1:]:
                cells = r.cells
                ry0, ry1 = r.bbox[1], r.bbox[3]
                ra = sorted([a for a in anchors if ry0 - 1 <= (a[1] + a[3]) / 2 <= ry1 + 1], key=lambda a: a[1])
                if not ra:
                    continue
                def cell_text(cb):
                    if not cb: return ""
                    return text_of([w for w in ws if cb[0] - 1 <= w[0] and w[2] <= cb[2] + 1 and cb[1] - 1 <= (w[1] + w[3]) / 2 <= cb[3] + 1])
                l3t = cell_text(cells[1]) if len(cells) > 1 else ""
                l2t = cell_text(cells[0]) if cells[0] else prev_l2
                prev_l2 = l2t or prev_l2
                cs = [(a[1] + a[3]) / 2 for a in ra]
                bounds = [ry0] + [(cs[i] + cs[i + 1]) / 2 for i in range(len(cs) - 1)] + [ry1]
                for i, a in enumerate(ra):
                    y0, y1 = bounds[i], bounds[i + 1]
                    def grab(col):
                        return text_of([w for w in ws if col[0] - 1 <= w[0] and w[2] <= col[2] + 1 and y0 <= (w[1] + w[3]) / 2 < y1])
                    c = cs[i]
                    meth = [w for w in ws if abs((w[1] + w[3]) / 2 - c) < 3 and w[0] > a[2] and re.match(METHOD, w[4])]
                    stat = [w for w in ws if abs((w[1] + w[3]) / 2 - c) < 4 and w[0] > a[2] and w[4] in ("●", "○", "◐", "◑")]
                    items.append(dict(name=grab(ncol), spec=grab(scol), period=a[4], method=meth[0][4] if meth else "",
                                      status=stat[0][4] if stat else "", l3t=l3t, l2t=prev_l2))
        for it in items:
            g = ("", it["l3t"])
            l3 = l3_by.get(norm(g[1]))
            if not l3 and g[1]:
                for kk, v in l3_by.items():
                    if kk and (kk in norm(g[1]) or norm(g[1]) in kk) and l2_belongs(v, cur_l1, L2):
                        l3 = v; break
            l2 = l2_by.get(norm(it["l2t"]))
            out.append(dict(l1=cur_l1["id"] if cur_l1 else "", l3=l3["id"] if l3 else "", l3name=it["l3t"],
                            l2=(l3["l2"] if l3 else (l2["id"] if l2 else "")), l2name=it["l2t"], name=it["name"], spec=it["spec"],
                            period=it["period"], method=it["method"], status=it["status"], page=pi + 1))
    return out


def l2_belongs(l3, l1, L2):
    if not l1:
        return True
    d = {x["id"]: x for x in L2}
    return d.get(l3["l2"], {}).get("l1") == l1["id"]


if __name__ == "__main__":
    L1, L2, L3 = taxonomy()
    print(len(L1), len(L2), len(L3))
    N = needs(L1, L2, L3)
    print("needs", len(N))
    json.dump(dict(L1=L1, L2=L2, L3=L3, needs=N), open(WORK + "/taxo.json", "w"), ensure_ascii=False, indent=1)
