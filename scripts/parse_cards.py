"""Parse project cards (과제카드) from '21~'26 plans using pdftotext bbox words + pdfplumber ruling lines."""
import sys, re, json, os
import pdfplumber
from common import *
from common import WORK

LABELS = {"개요": "ov", "개 요": "ov", "연구항목": "items", "사업기간": "period", "세부과제": "sub"}
PROGRAMS = ["기초연구", "응용연구", "시험개발", "응용연구/시험개발", "무기체계 패키지형 핵심기술", "국방협업", "국방선행",
            "선도형 핵심기술", "핵심SW", "선행핵심기술", "선도형핵심기술", "국제공동 연구개발", "국제공동기술개발", "국제공동연구개발",
            "미래도전국방기술", "미래도전", "민군기술협력사업", "민･군기술협력사업", "민·군기술협력사업", "특화연구실", "특화연구센터",
            "국방반도체", "핵심기술", "기초연구(특화연구실)", "선도형 핵심기술/핵심SW/선행핵심기술"]
PROG_RE = re.compile(r'(개별기초|특화실|특화센터|응용/시험|선행핵심|선도형|미래도전|국제공동|기초연구|응용연구/시험개발|응용연구|시험개발|무기체계 ?패키지형 ?핵심기술|국방협업|국방선행|선도형 ?핵심기술|핵심 ?SW|선행 ?핵심기술|국제공동 ?(?:연구개발|기술개발)|미래도전 ?국방기술|민[･·]?군 ?기술협력(?:사업)?|특화연구실|특화연구센터|국방반도체)')
DOM_RE = re.compile(r'지휘통제\s*[·ㆍ･]?\s*통신|감시\s*[·ㆍ･]?\s*정찰|기동|함정|항공|우주|화력|방호|사이버|기타|국방전력지원|전력지원|공통')
PERIOD_RE = re.compile(r'(\d{4})\s*-\s*(\d{4})\s*\((\d+)\s*개월\)')


def hedges(pg):
    ys = sorted(e["top"] for e in pg.edges if e["orientation"] == "h" and e["width"] > 60)
    out = []
    for y in ys:
        if not out or y - out[-1] > 2.0:
            out.append(y)
    return out


def parse_doc(year):
    pdf = DOCS[year]
    pages = bbox_pages(pdf)
    plumb = pdfplumber.open(os.path.join(SRC, pdf))
    cards = []
    cur_prog = None
    for pi, pg in enumerate(pages):
        words = [w for w in pg["words"] if not ((len(w[4]) == 1 and w[0] > 0.84 * pg["w"]) or "\uf000" in w[4] or w[4] in ("\uf000",))]
        txt = " ".join(w[4] for w in words)
        W, H = pg["w"], pg["h"]
        # program headings anywhere on page (record y)
        heads = []
        for r in rows_of(words):
            t = join(r["w"])
            if len(t) < 45 and re.match(r'^(부록\s*\d?\s*[|｜]\s*|제\s*\d+\s*절\s*[|｜]?\s*|\d\s+|[가-하]\.\s*)?' , t):
                m = PROG_RE.search(t)
                big = max(w[3] - w[1] for w in r["w"])
                if m and (re.match(r'^(부록|제\s*\d+\s*절|\d\s)', t) or t.strip() == m.group(0)) and "사업기간" not in t:
                    heads.append((r["c"], m.group(0)))
        if "사업기간" not in txt:
            if heads:
                cur_prog = heads[-1][1]
            continue
        edges = hedges(plumb.pages[pi])
        if len(edges) < 3:
            continue
        # bands
        bands = []
        for a, b in zip(edges, edges[1:]):
            bw = [w for w in words if a - 0.5 <= (w[1] + w[3]) / 2 < b + 0.5]
            bands.append(dict(top=a, bot=b, w=bw))
        # words above first edge -> headings already handled
        labelx = 0.24 * W
        current = None
        for bd in bands:
            bw = bd["w"]
            if not bw:
                continue
            # headings inside page before this band
            for hy, ht in heads:
                if hy < bd["top"] and (current is None or hy > current.get("_y", -1)):
                    cur_prog = ht
            lab_words = [w for w in bw if w[0] < labelx and (w[4] in ("개", "요", "개요", "연구항목", "사업기간", "세부과제", "과제명") or re.fullmatch(r'\d{1,3}\.?', w[4]))]
            lab = re.sub(r'\s+', '', join(lab_words)) if lab_words else ""
            body = [w for w in bw if w not in lab_words]
            num_w = [w for w in lab_words if re.fullmatch(r'\d{1,3}\.?', w[4])]
            is_title = False
            if num_w and not any(k in lab for k in ("개요", "연구항목", "사업기간", "세부과제")):
                is_title = True
            elif not lab and body and re.match(r'^\d{1,3}\.\s', join(body)):
                is_title = True
            if is_title:
                hs = sorted(set(round(w[3] - w[1], 1) for w in body))
                tsize = max(hs) if hs else 0
                title_w, right_w, small_left = [], [], []
                for w in body:
                    hgt = round(w[3] - w[1], 1)
                    if hgt >= tsize - 0.4:
                        title_w.append(w)
                    elif w[0] > 0.6 * W:
                        right_w.append(w)
                    else:
                        small_left.append(w)
                # if all same size, domain words at far right
                if not right_w:
                    rr = [w for w in title_w if w[0] > 0.78 * W]
                    if rr:
                        right_w = rr
                        title_w = [w for w in title_w if w not in rr]
                num = None
                if num_w:
                    num = int(num_w[0][4].rstrip("."))
                title = text_of(title_w)
                m = re.match(r'^(\d{1,3})\.?\s+(.*)$', title)
                if m and num is None:
                    num, title = int(m.group(1)), m.group(2)
                rtext = " ".join(join(r["w"]) for r in rows_of(right_w))
                dom = ""
                md = DOM_RE.search(rtext)
                if md:
                    dom = md.group(0)
                    rtext = rtext[:md.start()] + " " + rtext[md.end():]
                tf = ""
                mt = list(re.finditer(r'\(([^()]{1,12})\)', rtext))
                if mt:
                    tf = mt[-1].group(1).strip()
                    rtext = rtext[:mt[-1].start()] + rtext[mt[-1].end():]
                extra = (text_of(small_left) + " " + rtext.strip()).strip()
                old = ""
                mo = re.search(r'\(구\s*\.?\s*(.*?)\)?$', extra)
                if mo:
                    old = mo.group(1).strip(" )")
                    extra = extra[:mo.start()].strip()
                mo = re.search(r'\(구\s*\.?\s*([^)]*)\)', title)
                if mo:
                    old = old or mo.group(1).strip()
                    title = (title[:mo.start()] + title[mo.end():]).strip()
                prog_suffix = ""
                mo = re.search(r'\((기초연구|응용연구|시험개발|응용/시험|응용연구/시험개발)\)\s*$', title)
                if mo:
                    prog_suffix = mo.group(1)
                    title = title[:mo.start()].strip()
                if not dom and PROG_RE.fullmatch(title.replace(" ", "")) or (not dom and PROG_RE.fullmatch(title)):
                    cur_prog = title
                    current = None
                    continue
                if not dom and PROG_RE.search(title) and len(title) < 30 and num is not None and num < 10:
                    cur_prog = title
                    current = None
                    continue
                current = dict(edition=year, no=num, name=title, oldName=old, domain=dom, techField=tf,
                               program=prog_suffix or (cur_prog or ""), page=pi + 1, ov="", items="", sub=[], _y=bd["top"])
                cards.append(current)
                continue
            if current is None:
                continue
            key = None
            for k, v in LABELS.items():
                if k.replace(" ", "") in lab:
                    key = v
            if key is None and current.get("_sub"):
                key = "sub"
            if key in ("ov", "items"):
                current[key] = (current[key] + " " + text_of(body)).strip()
            elif key == "period":
                t = join(sorted(body, key=lambda w: (round((w[1] + w[3]) / 2 / 4), w[0])))
                t2 = re.sub(r'\s+', ' ', t)
                current["periodRaw"] = t2
                m = PERIOD_RE.search(t2)
                if m:
                    current["start"], current["end"], current["months"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
                else:
                    ys = re.findall(r'(20\d\d)', t2)
                    if len(ys) >= 2:
                        current["start"], current["end"] = int(ys[0]), int(ys[1])
                m = re.search(r'예산\s*\(억원\)\s*([\d,]+\.?\d*)', t2)
                if m:
                    current["budget"] = float(m.group(1).replace(",", ""))
                else:
                    nums = re.findall(r'(?<![\d(/-])(\d{1,3}(?:,\d{3})*\.\d{1,2})(?![\d)])', t2)
                    if nums:
                        current["budget"] = float(nums[0].replace(",", ""))
                m = re.search(r'주관형태\s*([가-힣·]+)', t2)
                if m:
                    current["org"] = m.group(1)
                m = re.search(r'사업구분\s*([가-힣A-Za-z/·\s]+?)$', t2)
                if m:
                    current["program"] = m.group(1).strip()
                current["_done"] = True
                current["_sub"] = False
            elif key == "sub":
                current["_sub"] = True
                t = text_of(body)
                if "과제명" in t and "기간" in t:
                    continue
                t = re.sub(r'\s*\d{4}\s*-\s*\d{4}\s*(국과연|산학연|업체|미정|정출연)?\s*$', '', t).strip()
                if t:
                    current["sub"].append(t)
        if heads:
            cur_prog = heads[-1][1]
    for c in cards:
        for k in [k for k in c if k.startswith("_")]:
            del c[k]
    return cards


if __name__ == "__main__":
    y = sys.argv[1]
    cards = parse_doc(y)
    json.dump(cards, open(f"{WORK}/cards_{y}.json", "w"), ensure_ascii=False, indent=1)
    print(y, len(cards), sum(1 for c in cards if c.get("budget")), sum(1 for c in cards if c.get("start")))
