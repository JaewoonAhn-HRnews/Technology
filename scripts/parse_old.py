"""Parse '17~'31 and '18~'32 핵심기술과제 lists (부록2) and '19~'33 과제 목록."""
import re, json, glob

from common import SRC, WORK
TF = r'(센서|정보통신|제어/전자|제어전자|탄약/에너지|추진|화생방|소재|플랫폼/구조|플랫폼구조)'
TYPES = r'(순수기초|기초|응용|시험|특화연구실|특화연구센터|특화|핵심|미래도전|민군|응용/시험|국제공동)'


def pages(y):
    fs = sorted(glob.glob(f"{SRC}/pages_{y[2:]}_*.txt"))
    return [(int(f[-7:-4]), open(f).read()) for f in fs]


def parse_1718(y):
    out = []
    for pn, t in pages(y):
        if "8대 기술분야" not in t or "사업기간" not in t:
            continue
        lines = t.split("\n")
        blocks = []
        cur = None
        for ln in lines:
            if re.search(r'과\s*제\s*명|사업기간|8대 기술분야|^\s*번호|부록\s*2\.', ln):
                continue
            m = re.search(r'^(.*?)\s{1,}(\d{4})\s*-\s*(\d{4})\s+(\S+)\s*$', ln)
            if m and len(m.group(1).strip()) > 2:
                cur = {"lines": [], "head": m}
                blocks.append(cur)
                continue
            if cur is not None:
                cur["lines"].append(ln)
        for b in blocks:
            m = b["head"]
            name = m.group(1).strip()
            num = None
            mn = re.match(r'^(\d{1,3})\s+(.*)$', name)
            if mn:
                num, name = int(mn.group(1)), mn.group(2)
            rec = dict(edition=y, no=num, name=name, start=int(m.group(2)), end=int(m.group(3)), org=m.group(4),
                       oldName="", program="", techField="", ov="", page=pn)
            desc = []
            for ln in b["lines"]:
                s = ln
                mt = re.search(r'\s{2,}' + TYPES + r'\s+' + TF + r'\s*$', s)
                if mt:
                    rec["program"], rec["techField"] = mt.group(1), mt.group(2)
                    s = s[:mt.start()]
                else:
                    mt = re.search(r'\s{2,}' + TF + r'\s*$', s)
                    if mt and not rec["techField"]:
                        rec["techField"] = mt.group(1)
                        s = s[:mt.start()]
                    mt2 = re.search(r'\s{2,}' + TYPES + r'\s*$', s)
                    if mt2 and not rec["program"]:
                        rec["program"] = mt2.group(1)
                        s = s[:mt2.start()]
                mn = re.match(r'^\s*(\d{1,3})\s*(\s{2,}.*)?$', s)
                if mn and rec["no"] is None:
                    rec["no"] = int(mn.group(1))
                    s = mn.group(2) or ""
                s = s.strip()
                if not s:
                    continue
                mo = re.match(r'^\(구\s*\.?\s*(.*)\)$', s)
                if mo and not desc:
                    rec["oldName"] = mo.group(1).strip()
                    continue
                desc.append(s)
            rec["ov"] = re.sub(r'\s+', ' ', " ".join(desc)).strip()
            out.append(rec)
    return out


def parse_19():
    """19~33: lists grouped by 8대 기술분야 section (제2절 센서 ...), columns 분류/과제명/기간/주관"""
    out = []
    tf = None
    horizon = None
    sec_map = {"센서": "센서", "정보통신": "정보통신", "제어/전자": "제어/전자", "탄약/에너지": "탄약/에너지", "추진": "추진",
               "화생방": "화생방", "소재": "소재", "플랫폼/구조": "플랫폼/구조"}
    for pn, t in pages("2019"):
        if pn < 88 or pn > 160:
            continue
        for ln in t.split("\n"):
            m = re.search(r'제\s*\d절\s*(센서|정보통신|제어/전자|탄약/에너지|추진|화생방|소재|플랫폼/구조)\s*기술', ln)
            if m:
                tf = m.group(1)
            m = re.search(r'([가나])\s*(중기|장기)\s*대상기간', ln)
            if m:
                horizon = m.group(2)
        if "과 제 명" not in t and "과제명" not in t:
            continue
        lines = t.split("\n")
        cat = None
        pend = ""
        for ln in lines:
            m = re.search(r'^(.*?)\s{2,}(단기|중기|장기)\s+(\S+)\s*$', ln)
            if m:
                left = m.group(1)
                # category label may be at col 0
                mc = re.match(r'^(\S{1,6})\s{3,}(.*)$', left)
                name = left.strip()
                if mc and not re.search(r'[a-zA-Z]', mc.group(1)) and len(mc.group(1)) <= 4 and mc.group(1) in ("순수", "기초", "응용", "시험", "특화", "핵심", "연구실"):
                    name = mc.group(2).strip()
                name = (pend + " " + name).strip() if pend and not name else name
                if not name and pend:
                    name = pend
                pend = ""
                out.append(dict(edition="2019", no=None, name=re.sub(r'\s+', ' ', name), term=m.group(2), org=m.group(3),
                                techField=tf, horizon=horizon, oldName="", program="", page=pn))
                continue
            s = ln.strip()
            if not s or re.search(r'분류\s+과 제 명|과제명|^\d+$|^\*|WMD', s):
                continue
            mo = re.match(r'^.*?\(구\s*\.?\s*(.*)\)\s*$', s)
            if mo and out and out[-1]["page"] == pn:
                out[-1]["oldName"] = mo.group(1).strip()
                continue
            # category labels in left column
            mcat = re.match(r'^(순수|기초|응용|시험|특화|연구실|핵심|기술|센터|\(\d+개\)|/|순수기초|응용연구|시험개발)', s)
            if mcat and len(s) <= 8:
                continue
            # name split across lines when name precedes term line
            if len(s) > 4 and not re.search(r'(단기|중기|장기)', s):
                parts = re.split(r'\s{3,}', ln.strip())
                pend = parts[-1] if len(parts) > 1 and len(parts[0]) <= 6 else ln.strip()
    return out


if __name__ == "__main__":
    for y in ("2017", "2018"):
        r = parse_1718(y)
        json.dump(r, open(f"{WORK}/cards_{y}.json", "w"), ensure_ascii=False, indent=1)
        print(y, len(r), sum(1 for x in r if x["no"]), sum(1 for x in r if x["techField"]))
    r = parse_19()
    json.dump(r, open(WORK + "/cards_2019.json", "w"), ensure_ascii=False, indent=1)
    print("2019", len(r))


def parse_19b():
    from common import bbox_pages, DOCS, join
    pages = bbox_pages(DOCS["2019"])
    groups = [(99, 105), (110, 116), (120, 123), (126, 132), (135, 138), (141, 143), (146, 149), (153, 155)]
    tfs = ["센서", "정보통신", "제어/전자", "탄약/에너지", "추진", "화생방", "소재", "플랫폼/구조"]
    out = []
    for (a, b), tf in zip(groups, tfs):
        horizon = "중기"
        for pn in range(a - 1, b + 2):
            pg = pages[pn - 1]
            ws = pg["words"]
            txt = " ".join(w[4] for w in ws)
            if "기간" not in txt or "주관" not in txt:
                continue
            # horizon switches inside page: find "장기 대상기간" y
            hz_y = [w[1] for w in ws if "대상기간" in w[4]]
            hz_txt = [(w[1], "장기" if any(v[4].startswith("장기") and abs(v[1] - w[1]) < 3 for v in ws) else "중기") for w in ws if "대상기간" in w[4]]
            heads = [w for w in ws if w[4] in ("기간",)]
            if not heads:
                continue
            term_x = heads[0][0]
            name_hdr = [w for w in ws if w[4] in ("과", "과제명")]
            anchors = [w for w in ws if w[4] in ("단기", "중기", "장기") and abs(w[0] - term_x) < 25]
            name_x0 = 0.17 * pg["w"]
            names = [w for w in ws if w[0] >= name_x0 - 2 and w[2] < term_x - 5 and w not in anchors
                     and w[1] > heads[0][3] - 30 and w[4] not in ("과", "제", "명")]
            orgs = [w for w in ws if w[0] > term_x + 15 and w[4] in ("산학연", "국과연", "미정", "국/산", "업체", "산학연/국과연")]
            rows = {id(a): {"a": a, "w": []} for a in anchors}
            for w in names:
                c = (w[1] + w[3]) / 2
                # only words below the header of the same table
                best = min(anchors, key=lambda a: abs((a[1] + a[3]) / 2 - c), default=None)
                if best is None or abs((best[1] + best[3]) / 2 - c) > 14:
                    continue
                rows[id(best)]["w"].append(w)
            for r in sorted(rows.values(), key=lambda r: r["a"][1]):
                a = r["a"]
                hzn = horizon
                for y, h in sorted(hz_txt):
                    if y < a[1]:
                        hzn = h
                if not r["w"]:
                    continue
                from common import rows_of
                lines = [join(x["w"]) for x in rows_of(r["w"])]
                name = " ".join(l for l in lines if not l.strip().startswith("(구"))
                old = " ".join(l for l in lines if l.strip().startswith("(구"))
                old = re.sub(r'^\(구\s*\.?\s*|\)$', '', old).strip()
                org = min(orgs, key=lambda o: abs(o[1] - a[1]), default=None)
                out.append(dict(edition="2019", no=None, name=re.sub(r'\s+', ' ', name).strip(), oldName=old,
                                term=a[4], org=org[4] if org and abs(org[1] - a[1]) < 6 else "", techField=tf,
                                horizon=hzn, program="", page=pn))
            if hz_txt:
                horizon = sorted(hz_txt)[-1][1]
    return out


if __name__ == "__main__":
    r = parse_19b()
    json.dump(r, open(WORK + "/cards_2019.json", "w"), ensure_ascii=False, indent=1)
    print("2019b", len(r))
