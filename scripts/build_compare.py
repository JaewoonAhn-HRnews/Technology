"""분야별·연도별 비교 데이터(data/compare.json) 생성."""
import json, re, os
from collections import Counter, defaultdict

W = os.environ.get("ATLAS_WORK", os.path.join(os.path.dirname(__file__), "..", "work"))
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
FIELDS = ["인공지능", "유·무인 복합", "양자", "우주", "에너지", "첨단소재", "사이버·네트워크", "센서·전자기전", "추진", "WMD 대응"]
cmp_ = json.load(open(f"{W}/compare.json"))
taxo = json.load(open(f"{W}/taxo.json"))
P = json.load(open(f"{OUT}/projects.json"))
needs = json.load(open(f"{OUT}/needs.json"))
L1 = {x["id"]: x for x in taxo["L1"]}
L2_26 = taxo["L2"]
L3 = taxo["L3"]
norm = lambda s: re.sub(r'[\s·ㆍ･‧/,()\-]', '', s or "")


def grams(s, n=2):
    s = norm(s)
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def sim(a, b):
    A, B = grams(a), grams(b)
    return len(A & B) / max(1, len(A | B))


# 사업유형 표 정규화(행 순서 기준)
ORDER = ["기초연구", "특화연구실", "특화연구센터", "응용연구", "응용/시험", "시험개발", "국방협업", "국방선행", "선도형 핵심기술", "핵심SW", "선행핵심기술", "국제공동", "미래도전"]
ORDER26 = ["기초연구", "특화연구실", "특화연구센터", "응용연구", "응용/시험", "시험개발", "국방반도체", "국방협업", "국방선행", "선도형 핵심기술", "핵심SW", "선행핵심기술", "국제공동", "미래도전"]
fieldProg = {}
for ed, rows in cmp_["fieldProg"].items():
    items = [(k, v) for k, v in rows.items() if k != "총계"]
    names = ORDER26 if ed == "2026" else ORDER
    fieldProg[ed] = {names[i]: v[:10] for i, (k, v) in enumerate(items[:len(names)])}
    fieldProg[ed]["총계"] = rows["총계"][:10]
fieldCount = {f: {} for f in FIELDS}
for ed in fieldProg:
    for i, f in enumerate(FIELDS):
        fieldCount[f][ed] = fieldProg[ed]["총계"][i]
# ’23-’37: 10대 분야별 국방기술 수(과제 아님), ’22-’36: 8대 분야 핵심기술 수
TECH23 = dict(zip(FIELDS, [44, 43, 15, 19, 16, 19, 56, 50, 16, 44]))
FIELDS22 = [["자율·인공지능 기반 감시정찰", 157, ["인공지능", "센서·전자기전"]], ["초연결 지능형 지휘통제", 167, ["인공지능", "사이버·네트워크"]],
            ["초고속·고위력 정밀타격", 70, ["추진", "WMD 대응"]], ["미래형 추진 및 스텔스 기반 플랫폼", 140, ["추진", "첨단소재"]],
            ["유·무인 복합 전투수행", 120, ["유·무인 복합"]], ["첨단기술 기반 개인전투체계", 16, ["유·무인 복합"]],
            ["사이버 능동대응 및 미래형 방호", 98, ["사이버·네트워크", "WMD 대응"]], ["미래형 첨단 신기술", 53, ["양자", "우주", "에너지"]]]

# 프로젝트 조회: (판, 카드번호) → 고유 과제
pid = {}
for p in P:
    for h in p["hist"]:
        if h.get("no") is not None:
            pid[(h["ed"], h["no"])] = p

# 로드맵 연결(’24·’25 공식): 과제 → L1, 세부기술 추정
L2_25 = cmp_["l2_25"]
l2_25_by_l1 = defaultdict(list)
for x in L2_25:
    l2_25_by_l1[x["l1"]].append(x)


def guess_l2(l1, ctx, name):
    cands = l2_25_by_l1.get(l1, [])
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]["no"]
    best, bs = None, 0
    for c in cands:
        s = sim(c["name"], ctx) * 1.5 + sim(c["name"], name) * 0.5
        if s > bs:
            best, bs = c, s
    return best["no"] if best and bs > 0.08 else None


road = {"2024": cmp_["road24"], "2025": cmp_["road25"]}
link = {"2024": {}, "2025": {}}  # project id -> l1
l2link = {"2024": Counter(), "2025": Counter()}
l1cnt = {"2024": Counter(), "2025": Counter()}
for ed, rows in road.items():
    for r in rows:
        if not r["l1"].startswith("S"):
            continue
        l1cnt[ed][r["l1"]] += 1
        g = guess_l2(r["l1"], r["ctx"], r["name"])
        if g:
            l2link[ed][g] += 1
        p = pid.get((ed, r["no"]))
        if p:
            link[ed][p["id"]] = r["l1"]
# ’26: 기획서 국방전략기술 표기(분야) + 추정 L1
link26 = {}
for p in P:
    if p.get("current") and p.get("stratField") in FIELDS:
        link26[p["id"]] = p.get("l1") or ""
l1cnt["2026"] = Counter(v for v in link26.values() if v)

# 기술개발소요(’26)
nd_l1 = Counter(n["l1"] for n in needs)
nd_open = Counter(n["l1"] for n in needs if n["status"] == "○")
nd_l2 = Counter(n["l2"] for n in needs if n.get("l2"))
nd_l2open = Counter(n["l2"] for n in needs if n.get("l2") and n["status"] == "○")
nd_per = defaultdict(Counter)
nd_meth = defaultdict(Counter)
for n in needs:
    pp = n["period"]
    nd_per[n["l1"]]["단기" if pp.startswith("단") else ("중기" if pp.startswith("중") else "장기")] += 1
    nd_meth[n["l1"]][n["method"]] += 1
l3_by_l2 = Counter(x["l2"] for x in L3)

# 세부기술 시계열: ’26 L2 ↔ ’25 L2 매칭
l1rows = []
for l1 in taxo["L1"]:
    rows26 = [x for x in L2_26 if x["l1"] == l1["id"]]
    rows25 = list(l2_25_by_l1.get(l1["id"], []))
    used = set()
    l2rows = []
    for x in rows26:
        best, bs = None, 0
        for y in rows25:
            if y["no"] in used:
                continue
            s = sim(x["name"], y["name"])
            if s > bs:
                best, bs = y, s
        if best and bs >= 0.34:
            used.add(best["no"])
            st = "동일" if norm(best["name"]) == norm(x["name"]) else "명칭 변경"
        else:
            best, st = None, "’26 신설"
        l2rows.append(dict(id=x["id"], name=x["name"], name25=best["name"] if best else "", no25=best["no"] if best else None, status=st,
                           c24=l2link["2024"].get(best["no"], 0) if best else 0, c25=l2link["2025"].get(best["no"], 0) if best else 0,
                           l3=l3_by_l2.get(x["id"], 0), needs=nd_l2.get(x["id"], 0), open=nd_l2open.get(x["id"], 0)))
    # 이름이 크게 달라진 경우: 같은 국방전략기술 안에서 남은 항목끼리 순서대로 짝지어 ‘명칭 변경’ 처리
    left25 = [y for y in rows25 if y["no"] not in used]
    for r in l2rows:
        if r["status"] == "’26 신설" and left25:
            y = left25.pop(0)
            used.add(y["no"])
            r.update(name25=y["name"], no25=y["no"], status="명칭 변경", c24=l2link["2024"].get(y["no"], 0), c25=l2link["2025"].get(y["no"], 0))
    for y in rows25:
        if y["no"] not in used:
            l2rows.append(dict(id="", name="", name25=y["name"], no25=y["no"], status="’26 삭제·통합", c24=l2link["2024"].get(y["no"], 0), c25=l2link["2025"].get(y["no"], 0), l3=0, needs=0, open=0))
    l1rows.append(dict(id=l1["id"], name=l1["name"], field=l1["field"], c24=l1cnt["2024"].get(l1["id"], 0), c25=l1cnt["2025"].get(l1["id"], 0),
                       c26=l1cnt["2026"].get(l1["id"], 0), needs=nd_l1.get(l1["id"], 0), open=nd_open.get(l1["id"], 0),
                       period=nd_per[l1["id"]], method=nd_meth[l1["id"]], l2=l2rows))

# 과제 흐름(분야 단위): 판 사이 계속/신규/빠짐
ed_field = {"2024": {}, "2025": {}, "2026": {}}
for ed in ("2024", "2025"):
    for pid_, l1 in link[ed].items():
        ed_field[ed][pid_] = L1[l1]["field"]
for p in P:
    if p.get("current") and p.get("stratField") in FIELDS:
        ed_field["2026"][p["id"]] = p["stratField"]
flows = {}
for f in FIELDS:
    fl = {}
    for a, b in (("2024", "2025"), ("2025", "2026")):
        A = {k for k, v in ed_field[a].items() if v == f}
        B = {k for k, v in ed_field[b].items() if v == f}
        allB = set(ed_field[b].keys())
        allA = set(ed_field[a].keys())
        moved_in = [k for k in B - A if k in allA]  # 다른 분야에서 이동
        moved_out = [k for k in A - B if k in allB]
        fl[f"{a}→{b}"] = dict(cont=sorted(A & B), new=sorted(k for k in B - A if k not in allA), out=sorted(k for k in A - B if k not in allB),
                             movedIn=sorted(moved_in), movedOut=sorted(moved_out))
    flows[f] = fl

# 자동 점검: 분야 간 유사 세부기술(중복 후보)
dups = []
for i, x in enumerate(L2_26):
    for y in L2_26[i + 1:]:
        fx, fy = L1[x["l1"]]["field"], L1[y["l1"]]["field"]
        if x["l1"] == y["l1"]:
            continue
        s = max(sim(x["name"], y["name"]), sim(x["name"] + " " + x["desc"][:80], y["name"] + " " + y["desc"][:80]) * 0.9)
        if s >= 0.32:
            dups.append(dict(a=x["id"], an=x["name"], af=fx, b=y["id"], bn=y["name"], bf=fy, s=round(s, 2)))
dups.sort(key=lambda d: -d["s"])

FRAME = [
    dict(ed="2022", label="’22-’36", basis="2019-2033 국방과학기술진흥정책서", cls="8대 분야", lower="핵심기술 821개(분야별 목록)", n=883,
         change="AI는 감시정찰·지휘통제 분야에 분산, 양자·우주는 ‘미래형 첨단 신기술’에 포함"),
    dict(ed="2023", label="’23-’37", basis="2023-2037 국방과학기술혁신 기본계획(’23.4)", cls="10대 분야 · 30개 국방전략기술 신설", lower="국방기술 322개(상향식 나열)", n=863,
         change="인공지능·유무인·양자·우주·사이버 분야 독립. 세부기술 계층 없음"),
    dict(ed="2024", label="’24-’38", basis="기본계획 + 2024 시행계획", cls="10대 · 30개", lower="세부기술(과제 분류 라벨) · 과제 400개", n=778,
         change="로드맵 표에 세부기술이 행 라벨로 등장"),
    dict(ed="2025", label="’25-’39", basis="기본계획 + 2025 시행계획", cls="10대 · 30개 · 세부기술 100개", lower="세부기술 명세·단/중/장기 개발목표 · 과제 378개", n=644,
         change="유무인 지상/해양/공중 분리, 세부기술 100개 공식화"),
    dict(ed="2026", label="’26-’40", basis="기본계획 + 2026 시행계획", cls="10대 · 30 · 세부 99 · 구성 302", lower=f"기술개발소요 {len(needs):,}건 로드맵(확보시기·추진방안·확보여부) · 과제 307개(분야 표기)", n=461,
         change="구성기술 계층 신설, 과제 목록 대신 소요 중심 로드맵"),
]

out = dict(fieldProg=fieldProg, fieldCount=fieldCount, tech23=TECH23, fields22=FIELDS22, l1=l1rows, flows=flows, dups=dups[:60], frame=FRAME,
           roadCount={ed: len(r) for ed, r in road.items()})
json.dump(out, open(f"{OUT}/compare.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("ok", {f: fieldCount[f] for f in FIELDS[:3]}, len(dups))
print(Counter(r["status"] for l in l1rows for r in l["l2"]))
for f in FIELDS[:2]:
    print(f, {k: {kk: len(vv) for kk, vv in v.items()} for k, v in flows[f].items()})
