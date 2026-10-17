"""통합 데이터셋 빌드: 과제 계보(entity resolution), 국방전략기술 분류, 개념 온톨로지, 유사도, 예산, 예측."""
import json, re, math, os
from collections import Counter, defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from concepts import CONCEPTS

W = os.environ.get("ATLAS_WORK", os.path.join(os.path.dirname(__file__), "..", "work"))
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT, exist_ok=True)
EDITIONS = ["2017", "2018", "2019", "2021", "2022", "2023", "2024", "2025", "2026"]
ED_LABEL = {"2017": "’17~’31 핵심기술기획서", "2018": "’18~’32 핵심기술기획서", "2019": "’19~’33 핵심기술기획서",
            "2021": "’21~’35 국방기술기획서", "2022": "’22~’36 국방기술기획서", "2023": "’23~’37 국방기술기획서",
            "2024": "’24~’38 국방기술기획서", "2025": "’25~’39 국방기술기획서", "2026": "’26~’40 국방기술기획서"}
FIELDS = ["인공지능", "유·무인 복합", "양자", "우주", "에너지", "첨단소재", "사이버·네트워크", "센서·전자기전", "추진", "WMD 대응"]

DOM_N = {"감시정찰": "감시·정찰", "지휘통제통신": "지휘통제·통신", "감시·정찰": "감시·정찰", "지휘통제·통신": "지휘통제·통신"}
TF_N = {"제어전자": "제어/전자", "플랫폼구조": "플랫폼/구조", "제어/전기": "제어/전자", "센서 및 제어": "센서 및 제어",
        "센서 및 제어전자": "센서 및 제어"}
# 8대 -> 6대 통합 기술분야
TF_UNI = {"센서": "센서·제어", "제어/전자": "센서·제어", "센서 및 제어": "센서·제어", "정보통신": "정보통신", "탄약/에너지": "탄약/에너지",
          "화생방": "화생방", "소재": "소재", "추진": "기계(추진·플랫폼)", "플랫폼/구조": "기계(추진·플랫폼)", "기계": "기계(추진·플랫폼)"}


def prog_norm(p, name=""):
    p = (p or "").replace(" ", "")
    if re.search(r'특화연구센터|특화센터', p) or "특화연구센터" in name: return "기초·특화연구센터"
    if re.search(r'특화연구실|특화실', p) or "특화연구실" in name: return "기초·특화연구실"
    if re.search(r'개별기초|기초연구|순수기초|^기초$', p): return "기초연구"
    if re.search(r'국방협업', p): return "패키지형·국방협업"
    if re.search(r'국방선행', p): return "패키지형·국방선행"
    if re.search(r'패키지', p): return "패키지형(무기체계)"
    if re.search(r'선도형|핵심SW|선행핵심', p): return "선도형·핵심SW"
    if re.search(r'국제공동', p): return "국제공동개발"
    if re.search(r'미래도전', p): return "미래도전국방기술"
    if re.search(r'민.?군|민군', p): return "민군기술협력"
    if re.search(r'반도체', p): return "국방반도체"
    if re.search(r'응용/시험|응용연구/시험개발', p): return "응용연구/시험개발"
    if re.search(r'응용', p): return "응용연구"
    if re.search(r'시험', p): return "시험개발"
    return p or "기타/미분류"


def key(s):
    s = re.sub(r'\(구\s*\.?[^)]*\)', '', s or "")
    s = re.sub(r'\((응용연구|시험개발|응용|시험|기초|응용/시험|선행핵심|국방선행|국방협업)\)', '', s)
    s = re.sub(r'\(\s*\)', '', s)
    s = s.lower()
    return re.sub(r'[\s·ㆍ･‧∙•・\-_/,.()\[\]~"\'“”‘’]', '', s)


def clean_name(s):
    s = re.sub(r'\s+', ' ', s or "").strip()
    s = re.sub(r'\s*\(구\s*\.?\s*[^)]*\)?\s*$', '', s)
    return s.strip()


def grams(s, n=3):
    s = key(s)
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def jacc(a, b):
    return len(a & b) / max(1, len(a | b))


# ---------------- load records
recs = []
for ed in EDITIONS:
    for c in json.load(open(f"{W}/cards_{ed}.json")):
        if not c.get("name") or len(c["name"]) < 4:
            continue
        if ed in ("2021", "2022", "2023", "2024", "2025", "2026") and not c.get("budget") and not c.get("ov"):
            continue
        name = clean_name(c["name"])
        old = c.get("oldName", "") or ""
        m = re.search(r'\(구\s*\.?\s*([^)]*)\)?', c["name"])
        if m and not old:
            old = m.group(1).strip()
        r = dict(ed=ed, no=c.get("no"), name=name, old=clean_name(old),
                 domain=DOM_N.get(c.get("domain", ""), c.get("domain", "")),
                 tf=TF_N.get(c.get("techField", ""), c.get("techField", "")),
                 prog=prog_norm(c.get("program", ""), name), progRaw=c.get("program", ""),
                 org=(c.get("org") or "").replace("국/산", "국과연/산학연"),
                 start=c.get("start"), end=c.get("end"), months=c.get("months"), budget=c.get("budget"),
                 ov=re.sub(r'\s+', ' ', c.get("ov", "") or "").strip(), items=c.get("items", "") or "",
                 sub=c.get("sub", []) or [], page=c.get("page"), term=c.get("term"), horizon=c.get("horizon"))
        if r["tf"] and r["tf"] not in TF_UNI:
            r["tf"] = ""
        recs.append(r)
print("records", len(recs), Counter(r["ed"] for r in recs))

# strategic labels 2026 (from list)
strat26 = {int(k): v for k, v in json.load(open(f"{W}/strat_2026.json")).items()}
for r in recs:
    if r["ed"] == "2026" and r["no"] in strat26:
        r["stratLabel"] = strat26[r["no"]]

# ---------------- entity resolution (union-find)
par = list(range(len(recs)))


def find(i):
    while par[i] != i:
        par[i] = par[par[i]]
        i = par[i]
    return i


def union(a, b):
    a, b = find(a), find(b)
    if a != b:
        par[max(a, b)] = min(a, b)


by_key = defaultdict(list)
for i, r in enumerate(recs):
    by_key[key(r["name"])].append(i)
for k, ids in by_key.items():
    for j in ids[1:]:
        union(ids[0], j)
for i, r in enumerate(recs):
    if r["old"]:
        for j in by_key.get(key(r["old"]), []):
            union(i, j)
# fuzzy between editions
gr = [grams(r["name"]) for r in recs]
ed_idx = defaultdict(list)
for i, r in enumerate(recs):
    ed_idx[r["ed"]].append(i)
for a_ed, b_ed in zip(EDITIONS, EDITIONS[1:]):
    for i in ed_idx[b_ed]:
        best, bj = 0, None
        for j in ed_idx[a_ed]:
            s = jacc(gr[i], gr[j])
            if s > best:
                best, bj = s, j
        if bj is not None and best >= 0.72:
            ri, rj = recs[i], recs[bj]
            if ri["start"] and rj["start"] and abs(ri["start"] - rj["start"]) > 3:
                continue
            union(i, bj)
groups = defaultdict(list)
for i in range(len(recs)):
    groups[find(i)].append(i)
print("unique projects", len(groups))

# ---------------- build project entities
projects = []
for gi, (root, ids) in enumerate(sorted(groups.items(), key=lambda kv: min(recs[i]["ed"] for i in kv[1]))):
    rs = sorted([recs[i] for i in ids], key=lambda r: r["ed"])
    last = rs[-1]
    pick = lambda f: next((r[f] for r in reversed(rs) if r.get(f)), None)
    names = []
    for r in rs:
        for n in (r["old"], r["name"]):
            if n and n not in names:
                names.append(n)
    p = dict(id=f"P{gi + 1:04d}", name=last["name"], aliases=[n for n in names if n != last["name"]],
             eds=sorted(set(r["ed"] for r in rs)), domain=pick("domain") or "", tf=pick("tf") or "",
             prog=next((r["prog"] for r in reversed(rs) if r["prog"] and r["prog"] != "기타/미분류"), last["prog"]),
             org=pick("org") or "", start=pick("start"), end=pick("end"), months=pick("months"), budget=pick("budget"),
             ov=max((r["ov"] for r in rs), key=len), items=pick("items") or "", sub=pick("sub") or [],
             strat=next((r.get("stratLabel") for r in reversed(rs) if r.get("stratLabel")), None),
             hist=[dict(ed=r["ed"], no=r["no"], name=r["name"], start=r["start"], end=r["end"], budget=r["budget"],
                        prog=r["prog"], page=r["page"], domain=r["domain"]) for r in rs])
    p["tfu"] = TF_UNI.get(p["tf"], "")
    p["current"] = "2026" in p["eds"]
    projects.append(p)

# ---------------- concepts
CRE = [(cid, nm, cat, re.compile(rx, re.I)) for cid, nm, cat, rx in CONCEPTS]


def concepts_of(text):
    return [cid for cid, nm, cat, rx in CRE if rx.search(text)]


for p in projects:
    txt = " ".join([p["name"]] + p["aliases"] + [p["ov"], p["items"]])
    p["cc"] = concepts_of(txt)

# ---------------- strategic classification
taxo = json.load(open(f"{W}/taxo.json"))
L1 = {x["id"]: x for x in taxo["L1"]}
needs, _seen = [], set()
for n in taxo["needs"]:
    k_ = (n["l1"], re.sub(r"\s", "", n["name"]), n["period"], re.sub(r"\s", "", n["spec"])[:30])
    if n["name"] and k_ not in _seen:
        _seen.add(k_); needs.append(n)
for n in needs:
    n["field"] = L1.get(n["l1"], {}).get("field", "")
civil = json.load(open(f"{W}/civil.json"))

ptext = lambda p: " ".join([p["name"], p["name"], " ".join(p["aliases"]), p["ov"], p["items"]])
X_txt, y = [], []
for p in projects:
    if p["strat"]:
        X_txt.append(ptext(p)); y.append(p["strat"] if p["strat"] != "-" else "해당없음")
lab_n = len(X_txt)
for n in needs:
    if n["field"]:
        X_txt.append(n["name"] + " " + n["spec"]); y.append(n["field"])
for c in civil:
    if c["strategic"] in FIELDS:
        X_txt.append(c["title"] + " " + c["ov"] + " " + " ".join(c["keywords"])); y.append(c["strategic"])
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True, max_features=120000)
allX = vec.fit_transform([ptext(p) for p in projects] + X_txt)
Xp = allX[:len(projects)]
Xl = allX[len(projects):]
clf = LogisticRegression(max_iter=3000, C=6, class_weight="balanced")
# quick CV on the project-labeled part only (fit on rest)
from sklearn.model_selection import StratifiedKFold
yy = np.array(y)
proj_idx = np.arange(lab_n)
skf = StratifiedKFold(5, shuffle=True, random_state=1)
accs = []
for tr, te in skf.split(proj_idx, yy[:lab_n]):
    trn = np.concatenate([tr, np.arange(lab_n, len(y))])
    clf.fit(Xl[trn], yy[trn])
    pr = clf.predict(Xl[te])
    accs.append((pr == yy[te]).mean())
print("CV acc (2026 labeled projects)", np.mean(accs))
clf.fit(Xl, yy)
proba = clf.predict_proba(Xp)
classes = list(clf.classes_)
for p, pr in zip(projects, proba):
    order = np.argsort(-pr)
    p["stratPred"] = [[classes[k], round(float(pr[k]), 3)] for k in order[:3]]
    if p["strat"]:
        p["stratField"] = p["strat"] if p["strat"] != "-" else "해당없음"
        p["stratSrc"] = "기획서"
    else:
        p["stratField"] = classes[order[0]]
        p["stratSrc"] = "추정"

# ---------------- L1 linkage via needs similarity
Xn = vec.transform([n["name"] + " " + n["spec"] for n in needs])
from sklearn.preprocessing import normalize
Xpn = normalize(Xp); Xnn = normalize(Xn)
S = (Xpn @ Xnn.T).tocsr() if hasattr(Xpn @ Xnn.T, "tocsr") else Xpn @ Xnn.T
S = S.toarray() if hasattr(S, "toarray") else S
for i, p in enumerate(projects):
    row = S[i]
    top = np.argsort(-row)[:8]
    vote = Counter()
    for k in top[:5]:
        vote[needs[k]["l1"]] += row[k]
    l1 = vote.most_common(1)[0][0] if vote else ""
    if p["stratField"] not in FIELDS:
        p["l1"] = ""
    else:
        cand = [(needs[k]["l1"], row[k]) for k in top if L1.get(needs[k]["l1"], {}).get("field") == p["stratField"]]
        p["l1"] = cand[0][0] if cand else ""
    p["needsRel"] = [[int(k), round(float(row[k]), 3)] for k in top[:3] if row[k] > 0.18]

# ---------------- project-project similarity (top neighbors)
PP = (Xpn @ Xpn.T)
PP = PP.toarray() if hasattr(PP, "toarray") else PP
np.fill_diagonal(PP, 0)
for i, p in enumerate(projects):
    top = np.argsort(-PP[i])[:6]
    p["sim"] = [[projects[k]["id"], round(float(PP[i, k]), 3)] for k in top if PP[i, k] >= 0.30]

# ---------------- civil linkage
Xc = vec.transform([c["title"] + " " + c["ov"] + " " + " ".join(c["keywords"]) for c in civil])
Xcn = normalize(Xc)
CP = (Xcn @ Xpn.T)
CP = CP.toarray() if hasattr(CP, "toarray") else CP
for i, c in enumerate(civil):
    top = np.argsort(-CP[i])[:5]
    c["rel"] = [[projects[k]["id"], round(float(CP[i, k]), 3)] for k in top if CP[i, k] > 0.2]
    c["cc"] = concepts_of(c["title"] + " " + c["ov"] + " " + " ".join(c["keywords"]))
    c["id"] = f"C{c['no']:03d}"
parts = json.load(open(f"{W}/parts.json"))
for x in parts:
    x["cc"] = concepts_of(x["name"] + " " + x["system"])
support = json.load(open(f"{W}/support.json"))
for i, x in enumerate(support):
    x["id"] = f"F{i + 1:03d}"
    x["cc"] = concepts_of(x["name"] + " " + x["ov"])
for i, n in enumerate(needs):
    n["id"] = i
    n["cc"] = concepts_of(n["name"] + " " + n["spec"])

# ---------------- edition stats (record level, per edition)
ed_stats = []
for ed in EDITIONS:
    rs = [r for r in recs if r["ed"] == ed]
    b = [r["budget"] for r in rs if r["budget"]]
    ed_stats.append(dict(ed=ed, label=ED_LABEL[ed], n=len(rs), budget=round(sum(b), 1) if b else None,
                         nb=len(b), domain=Counter(r["domain"] for r in rs if r["domain"]),
                         tf=Counter(TF_UNI.get(r["tf"], "") for r in rs if r["tf"]), tf_raw=Counter(r["tf"] for r in rs if r["tf"]),
                         prog=Counter(r["prog"] for r in rs), org=Counter(r["org"] for r in rs if r["org"])))
# edition x strategic field using project labels
pid_of = {}
for p in projects:
    for h in p["hist"]:
        pid_of[(h["ed"], h["name"])] = p
for st in ed_stats:
    c = Counter(); cb = Counter()
    for r in recs:
        if r["ed"] != st["ed"]: continue
        p = pid_of.get((r["ed"], r["name"]))
        if p:
            c[p["stratField"]] += 1
            if r["budget"]: cb[p["stratField"]] += r["budget"]
    st["strat"] = c; st["stratBudget"] = {k: round(v, 1) for k, v in cb.items()}

# ---------------- annual budget profile (spread total budget uniformly across years) using latest record per project
annual = defaultdict(lambda: defaultdict(float))
for p in projects:
    if p["budget"] and p["start"] and p["end"] and p["end"] >= p["start"]:
        yrs = list(range(int(p["start"]), int(p["end"]) + 1))
        for yv in yrs:
            annual[p["stratField"]][yv] += p["budget"] / len(yrs)
annual_out = {k: {str(y): round(v, 1) for y, v in sorted(d.items())} for k, d in annual.items()}

# ---------------- concept trends by start year
cc_year = defaultdict(Counter)
year_tot = Counter()
for p in projects:
    if p["start"]:
        year_tot[p["start"]] += 1
        for c in p["cc"]:
            cc_year[c][p["start"]] += 1
years = list(range(2014, 2031))
trend = {}
for cid, nm, cat, rx in CONCEPTS:
    ys = [cc_year[cid][y] / year_tot[y] if year_tot[y] >= 10 else None for y in years]
    pts = [(y, v) for y, v in zip(years, ys) if v is not None and 2016 <= y <= 2026]
    slope = 0.0
    if len(pts) >= 4:
        xs = np.array([a for a, b in pts], float); vs = np.array([b for a, b in pts], float)
        slope = float(np.polyfit(xs, vs, 1)[0])
    recent = sum(cc_year[cid][y] for y in range(2023, 2027)); past = sum(cc_year[cid][y] for y in range(2016, 2023))
    rt = sum(year_tot[y] for y in range(2023, 2027)); pt = sum(year_tot[y] for y in range(2016, 2023))
    share_r = recent / rt if rt else 0; share_p = past / pt if pt else 0
    trend[cid] = dict(share=[None if v is None else round(v, 4) for v in ys], slope=round(slope, 5),
                      recent=round(share_r, 4), past=round(share_p, 4), momentum=round((share_r + 0.005) / (share_p + 0.005), 3),
                      nProj=sum(1 for p in projects if cid in p["cc"]),
                      nNeeds=sum(1 for n in needs if cid in n["cc"]),
                      nNeedsOpen=sum(1 for n in needs if cid in n["cc"] and n["status"] == "○"),
                      nCivil=sum(1 for c in civil if cid in c["cc"]))
yearTot = {str(y): year_tot[y] for y in years}

# ---------------- concept graph (co-occurrence, PMI-lite)
co = Counter()
cnt = Counter()
for p in projects:
    s = sorted(set(p["cc"]))
    for c in s: cnt[c] += 1
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            co[(s[i], s[j])] += 1
N = len(projects)
edges = []
for (a, b), v in co.items():
    if v < 4: continue
    lift = v * N / (cnt[a] * cnt[b])
    if lift < 1.3: continue
    edges.append(dict(s=a, t=b, w=v, lift=round(lift, 2)))
print("concept edges", len(edges))

# ---------------- forecast: strategic field pipeline
fc = {}
for f in FIELDS:
    ns = [n for n in needs if n["field"] == f]
    per = Counter(); per_open = Counter(); meth = Counter()
    for n in ns:
        pp = n["period"]
        bucket = "단기" if pp.startswith("단") else ("중기" if pp.startswith("중") else "장기")
        per[bucket] += 1
        if n["status"] == "○": per_open[bucket] += 1
        meth[n["method"]] += 1
    starts = Counter(p["start"] for p in projects if p["stratField"] == f and p["start"])
    pts = [(y, starts[y]) for y in range(2017, 2027)]
    xs = np.array([a for a, b in pts], float); vs = np.array([b for a, b in pts], float)
    k, b0 = np.polyfit(xs, vs, 1)
    proj = {str(y): max(0, round(float(k * y + b0), 1)) for y in range(2027, 2031)}
    active26 = [p for p in projects if p["stratField"] == f and p["current"]]
    fc[f] = dict(needs=len(ns), byPeriod=per, open=per_open, method=meth, starts={str(y): starts[y] for y in range(2014, 2031)},
                 slope=round(float(k), 2), projStarts=proj, active=len(active26),
                 activeBudget=round(sum(p["budget"] or 0 for p in active26), 1),
                 civil=sum(1 for c in civil if c["strategic"] == f))

# ---------------- country levels (국가별 국방과학기술 수준조사서 요약본, 2024)
levels = dict(
    countries=[["미국", 100, 1, 100, 1, 100, 1], ["프랑스", 90, 2, 89, 2, 89, 2], ["러시아", 90, 2, 89, 2, 89, 2],
               ["독일", 89, 4, 87, 4, 88, 4], ["영국", 89, 4, 87, 4, 87, 5], ["중국", 85, 6, 85, 6, 86, 6],
               ["이스라엘", 84, 7, 83, 7, 84, 7], ["일본", 84, 7, 81, 8, 82, 8], ["한국", 80, 9, 79, 9, 82, 8],
               ["이탈리아", 80, 9, 78, 10, 79, 10], ["인도", 73, 11, 71, 11, 73, 11], ["스페인", 70, 12, 68, 12, 70, 12]],
    korea=[["지휘통제", 82, 8, 81, 6, 83, 7, "지휘통제·통신"], ["전술통신", 82, 8, 80, 8, 81, 7, "지휘통제·통신"],
           ["레이더", 79, 10, 79, 10, 81, 10, "감시·정찰"], ["SAR", 76, 10, 75, 10, 80, 10, "감시·정찰"],
           ["EO/IR", 79, 10, 78, 9, 81, 9, "감시·정찰"], ["수중감시", 79, 10, 78, 9, 80, 8, "감시·정찰"],
           ["전자전", 76, 10, 76, 10, 80, 9, "감시·정찰"], ["기동전투", 88, 7, 86, 7, 88, 7, "기동"],
           ["지상무인", 80, 7, 80, 7, 82, 5, "기동"], ["개인전투", 77, 8, 76, 8, 78, 8, "기동"],
           ["수상함", 82, 8, 82, 8, 83, 8, "함정"], ["잠수함", 84, 8, 85, 8, 86, 8, "함정"],
           ["해양무인", 77, 9, 77, 9, 77, 9, "함정"], ["고정익", 75, 10, 75, 10, 78, 8, "항공"],
           ["회전익", 79, 10, 78, 10, 79, 10, "항공"], ["공중무인", 83, 8, 82, 8, 83, 8, "항공"],
           ["화포", 88, 5, 87, 4, 89, 4, "화력"], ["탄약", 82, 8, 81, 8, 85, 7, "화력"],
           ["유도무기", 83, 9, 82, 9, 83, 9, "화력"], ["수중유도무기", 84, 8, 84, 8, 86, 7, "화력"],
           ["방공무기", 82, 10, 81, 9, 84, 7, "방호"], ["화생방", 78, 9, 77, 8, 78, 8, "방호"],
           ["사이버무기", 81, 9, 79, 9, 81, 8, "사이버"], ["우주무기", 70, 10, 69, 10, 71, 10, "우주"],
           ["국방M&S", 78, 6, 77, 6, 80, 6, "기타"], ["국방SW", 74, 10, 73, 9, 79, 8, "기타"]])

# ---------------- write
ccmeta = [dict(id=cid, name=nm, cat=cat, rx=rx) for cid, nm, cat, rx in CONCEPTS]
json.dump(projects, open(f"{OUT}/projects.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(dict(L1=taxo["L1"], L2=taxo["L2"], L3=taxo["L3"]), open(f"{OUT}/taxonomy.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump([dict(id=n["id"], l1=n["l1"], l2=n["l2"], l3=n["l3"], l3n=n["l3name"], name=n["name"], spec=n["spec"], period=n["period"],
                method=n["method"], status=n["status"], field=n["field"], cc=n["cc"]) for n in needs],
          open(f"{OUT}/needs.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(civil, open(f"{OUT}/civil.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(parts, open(f"{OUT}/parts.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(support, open(f"{OUT}/support.json", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(dict(editions=ed_stats, annual=annual_out, trend=trend, yearTot=yearTot, edges=edges, concepts=ccmeta,
               forecast=fc, levels=levels, fields=FIELDS, edLabel=ED_LABEL, cv=round(float(np.mean(accs)), 3),
               conceptCount=dict(cnt)),
          open(f"{OUT}/stats.json", "w"), ensure_ascii=False, separators=(",", ":"))
print("done", len(projects), Counter(p["stratField"] for p in projects), Counter(p["stratSrc"] for p in projects))
