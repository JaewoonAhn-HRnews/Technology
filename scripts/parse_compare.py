"""판별 비교용 추출: (1) 10대 분야×사업유형 과제 수(’24·’25·’26), (2) ’24·’25 국방전략기술 로드맵의 과제-전략기술 연결, (3) ’25 세부기술(L2) 명칭, (4) ’24 세부기술 라벨."""
import re, json, glob, os
from common import SRC, WORK

FIELDS = ["인공지능", "유·무인 복합", "양자", "우주", "에너지", "첨단소재", "사이버·네트워크", "센서·전자기전", "추진", "WMD 대응"]
L1N = json.load(open(f"{WORK}/taxo.json"))["L1"]
norm = lambda s: re.sub(r'[\s·ㆍ･‧/,()\-]', '', s or "")
L1_BY = {norm(x["name"]): x for x in L1N}


def page(y, p):
    f = f"{SRC}/pages_{y}_{p:03d}.txt"
    return open(f).read() if os.path.exists(f) else ""


def npages(y):
    return len(glob.glob(f"{SRC}/pages_{y}_*.txt"))


def field_prog():
    out = {}
    for y in ("24", "25", "26"):
        for p in range(1, npages(y) + 1):
            t = page(y, p)
            if "국방전략기술 분야별 현황" not in t or "총계" not in t:
                continue
            rows = {}
            lines = t.split("\n")
            pend = ""
            for ln in lines:
                nums = re.findall(r'(?<![\d.])(\d+|-)(?![\d.])', ln)
                lab = re.sub(r'[\d\-]+', ' ', ln).strip()
                lab = re.sub(r'\s+', '', lab)
                if len(nums) >= 11 and re.search(r'\d', ln):
                    vals = [0 if v == "-" else int(v) for v in nums[-11:]]
                    name = (pend + lab).replace("무기체계패키지형", "").replace("제3장국방기술과제추진계획", "")
                    rows[name or f"row{len(rows)}"] = vals
                    pend = ""
                elif lab and len(lab) <= 12 and not re.search(r'분야|구분|단위|구성됨|과제로', lab):
                    pend = (pend + lab)[-14:]
            if any(k.endswith("총계") for k in rows):
                rows = {("총계" if k.endswith("총계") else k): v for k, v in rows.items()}
                out["20" + y] = rows
                break
    return out


PROG_RX = r'(기초연구|응용연구|시험개발|특화실|특화센터|특화연구실|특화연구센터|패키지형|국방협업|국방선행|미래도전|국제공동|응용/시험|선도형|핵심SW|선행핵심|개별기초|국방반도체|응용|시험|기초)'


def roadmap(y, p0, p1):
    """로드맵 표: L1 제목 'N. 이름', 행 '[세부기술 조각]  NNN 과제명  단계  'YY-'YY'"""
    res = []
    cur = None
    for p in range(p0, p1 + 1):
        lines = page(y, p).split("\n")
        for i, ln in enumerate(lines):
            m = re.match(r'^\s{0,6}(\d{1,2})\.\s+(\S.*?)\s*$', ln)
            if m and int(m.group(1)) <= 30:
                nm = re.sub(r'\s{3,}.*$', '', m.group(2))
                l1 = L1_BY.get(norm(nm))
                if not l1:
                    # 유사 명칭
                    for k, v in L1_BY.items():
                        if k[:5] and (k[:5] in norm(nm) or norm(nm)[:5] in k):
                            l1 = v; break
                cur = l1["id"] if l1 else f"?{m.group(1)}"
                continue
            m = re.search(r"^(.*?)\s(\d{3})\s+(\S.*?)\s{2,}" + PROG_RX + r"\s+'(\d\d)\s*-\s*'(\d\d)", ln)
            if m and cur:
                left = m.group(1).strip()
                ctx = [left]
                for j in range(max(0, i - 2), min(len(lines), i + 3)):
                    if j == i: continue
                    lj = lines[j]
                    mm = re.match(r'^(\s{0,3}\S.{0,14}?)(\s{3,}|$)', lj)
                    if mm and not re.search(r"\d{3}\s|'\d\d", lj[:20]):
                        ctx.append(mm.group(1).strip())
                res.append(dict(ed="20" + y, l1=cur, no=int(m.group(2)), name=m.group(3).strip(), prog=m.group(4),
                                start=2000 + int(m.group(5)), end=2000 + int(m.group(6)), ctx=" ".join(c for c in ctx if c)))
    return res


def l2_2025():
    out = []
    cur = None
    for p in range(24, 100):
        t = page("25", p)
        for ln in t.split("\n"):
            m = re.match(r'^\s{0,4}(\d{1,2})\.\s+(\S.*?)\s*$', ln)
            if m and int(m.group(1)) <= 30:
                l1 = L1_BY.get(norm(m.group(2)))
                if not l1:
                    for k, v in L1_BY.items():
                        if k[:5] and (k[:5] in norm(m.group(2)) or norm(m.group(2))[:5] in k):
                            l1 = v; break
                cur = l1["id"] if l1 else None
                continue
            if "'" in ln or "’" in ln:
                continue
            for piece in re.split(r'/\s*◯', ln):
                mm = re.match(r'^\s*◯?\s*([1-9]\d{0,2})\s+([가-힣A-Za-z].*?)\s*$', piece)
                if not mm:
                    continue
                n = int(mm.group(1))
                nm = re.sub(r'\s{3,}.*$', '', mm.group(2).strip())
                last = out[-1]["no"] if out else 0
                if cur and 1 <= n <= 100 and len(nm) >= 2 and last < n <= last + 3:
                    out.append(dict(no=n, name=nm, l1=cur))
    return out


if __name__ == "__main__":
    fp = field_prog()
    print({k: v.get("총계") for k, v in fp.items()})
    r24 = roadmap("24", 24, 76)
    r25 = roadmap("25", 25, 98)
    print("roadmap", len(r24), len(r25))
    l25 = l2_2025()
    print("L2 2025", len(l25))
    json.dump(dict(fieldProg=fp, road24=r24, road25=r25, l2_25=l25), open(f"{WORK}/compare.json", "w"), ensure_ascii=False, indent=1)
