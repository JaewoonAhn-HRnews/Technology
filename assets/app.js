/* 국방기술 아틀라스 — 정적 사이트 앱 (데이터: ./data/*.json) */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n, d = 0) => (n == null || isNaN(n) ? "–" : Number(n).toLocaleString("ko-KR", { maximumFractionDigits: d, minimumFractionDigits: d }));
  const sum = (a) => a.reduce((x, y) => x + (y || 0), 0);
  const D = {};
  const charts = {};
  const rendered = new Set();
  let current = "overview";

  const FIELDS = ["인공지능", "유·무인 복합", "양자", "우주", "에너지", "첨단소재", "사이버·네트워크", "센서·전자기전", "추진", "WMD 대응"];
  const FCODE = { "인공지능": "AI", "유·무인 복합": "MUM", "양자": "QNT", "우주": "SPC", "에너지": "ENG", "첨단소재": "MAT", "사이버·네트워크": "CYB", "센서·전자기전": "SEN", "추진": "PRP", "WMD 대응": "WMD", "해당없음": "–" };
  const DOMS = ["지휘통제·통신", "감시·정찰", "기동", "함정", "항공", "우주", "화력", "방호", "사이버", "기타"];
  const GROUPS = [
    { name: "지능·자율", f: ["인공지능", "유·무인 복합"] },
    { name: "네트워크·센서", f: ["사이버·네트워크", "센서·전자기전"] },
    { name: "우주·양자", f: ["우주", "양자"] },
    { name: "에너지·소재·추진", f: ["에너지", "첨단소재", "추진"] },
    { name: "화력·방어·플랫폼", f: ["WMD 대응", "플랫폼"] },
  ];
  const groupOf = (f) => GROUPS.findIndex((g) => g.f.includes(f));
  const ED_SHORT = (e) => "’" + e.slice(2) + "판";

  /* ---------- theme ---------- */
  const isDark = () => {
    const t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  };
  const cssv = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  function T() {
    const dark = isDark();
    return {
      dark, ink: cssv("--ink"), ink2: cssv("--ink-2"), muted: cssv("--muted"), line: cssv("--line"), accent: cssv("--accent"),
      surface: cssv("--surface"), s2: cssv("--surface-2"), good: cssv("--good"), warn: cssv("--warn"), crit: cssv("--crit"),
      font: cssv("--font-body"), mono: cssv("--font-mono"),
      cat: dark ? ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"] : ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
      seq: dark ? ["#17212a", "#16304f", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"] : ["#f1f5fa", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#104281"],
      ord3: dark ? ["#6da7ec", "#2a78d6", "#184f95"] : ["#86b6ef", "#2a78d6", "#104281"],
      soft: dark ? "#25405f" : "#b7d3f6",
    };
  }
  function baseOpt(t) {
    return {
      textStyle: { fontFamily: t.font, color: t.ink2 },
      animationDuration: 500,
      tooltip: { backgroundColor: t.surface, borderColor: t.line, textStyle: { color: t.ink, fontFamily: t.font, fontSize: 12.5 }, extraCssText: "box-shadow:0 4px 18px rgba(0,0,0,.12)" },
    };
  }
  const axisCat = (t, data, extra = {}) => Object.assign({ type: "category", data, axisLine: { lineStyle: { color: t.line } }, axisTick: { show: false }, axisLabel: { color: t.ink2, fontSize: 11.5 } }, extra);
  const axisVal = (t, extra = {}) => Object.assign({ type: "value", splitLine: { lineStyle: { color: t.line, opacity: 0.6 } }, axisLabel: { color: t.muted, fontSize: 11, fontFamily: t.mono } }, extra);

  function mk(id, opt) {
    const el = document.getElementById(id);
    if (!el || !window.echarts) return null;
    if (charts[id]) charts[id].dispose();
    const c = echarts.init(el, null, { renderer: "canvas" });
    c.setOption(opt);
    charts[id] = c;
    return c;
  }
  window.addEventListener("resize", () => Object.values(charts).forEach((c) => c && !c.isDisposed() && c.resize()));

  function rerender() {
    rendered.clear();
    show(current, true);
  }
  if (window.matchMedia) window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", rerender);
  new MutationObserver(rerender).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  $("#themeBtn").addEventListener("click", () => {
    document.documentElement.setAttribute("data-theme", isDark() ? "light" : "dark");
  });

  /* ---------- bar helpers ---------- */
  function hbar(id, labels, values, opt = {}) {
    const t = T();
    const o = baseOpt(t);
    o.grid = { left: 8, right: 46, top: 6, bottom: 6, containLabel: true };
    o.xAxis = axisVal(t, { splitLine: { show: false }, axisLabel: { show: false } });
    o.yAxis = axisCat(t, labels, { inverse: true, axisLabel: { color: t.ink2, fontSize: 11.5, width: opt.labelW || 120, overflow: "truncate" } });
    o.tooltip.trigger = "axis"; o.tooltip.axisPointer = { type: "shadow" };
    o.tooltip.valueFormatter = (v) => fmt(v, opt.dec || 0) + (opt.unit || "");
    o.series = [{ type: "bar", data: values, barMaxWidth: 16, itemStyle: { color: opt.color || t.accent, borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", color: t.ink2, fontFamily: t.mono, fontSize: 11, formatter: (p) => fmt(p.value, opt.dec || 0) } }];
    const c = mk(id, o);
    if (c && opt.onClick) c.on("click", (p) => opt.onClick(p.name));
    return c;
  }
  function vbar(id, labels, values, opt = {}) {
    const t = T();
    const o = baseOpt(t);
    o.grid = { left: 8, right: 8, top: 26, bottom: 4, containLabel: true };
    o.xAxis = axisCat(t, labels);
    o.yAxis = axisVal(t);
    o.tooltip.trigger = "axis"; o.tooltip.axisPointer = { type: "shadow" };
    o.tooltip.valueFormatter = (v) => fmt(v, opt.dec || 0) + (opt.unit || "");
    o.series = [{ type: "bar", data: values.map((v, i) => ({ value: v, itemStyle: { color: opt.colorAt ? opt.colorAt(i, t) : t.accent } })), barMaxWidth: 34,
      itemStyle: { borderRadius: [4, 4, 0, 0] }, label: { show: opt.labels !== false, position: "top", color: t.ink2, fontFamily: t.mono, fontSize: 11, formatter: (p) => (p.value == null ? "" : fmt(p.value, opt.dec || 0)) } }];
    return mk(id, o);
  }
  function heat(id, xs, ys, matrix, opt = {}) {
    const t = T();
    const o = baseOpt(t);
    let max = 0;
    const data = [];
    ys.forEach((y, yi) => xs.forEach((x, xi) => { const v = matrix[yi][xi] || 0; max = Math.max(max, v); data.push([xi, yi, v]); }));
    o.grid = { left: 8, right: 10, top: 8, bottom: 40, containLabel: true };
    o.xAxis = axisCat(t, xs, { splitArea: { show: false }, axisLabel: { color: t.ink2, fontSize: 11, interval: 0, rotate: opt.rotate || 0 } });
    o.yAxis = axisCat(t, ys, { inverse: true });
    o.visualMap = { min: 0, max: max || 1, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemWidth: 10, itemHeight: 120, text: [fmt(max), "0"], textStyle: { color: t.muted, fontSize: 11 }, inRange: { color: t.seq } };
    o.tooltip.formatter = (p) => `${esc(ys[p.value[1]])} · ${esc(xs[p.value[0]])}<br><b>${fmt(p.value[2], opt.dec || 0)}</b>${opt.unit || ""}`;
    o.series = [{ type: "heatmap", data, itemStyle: { borderColor: t.surface, borderWidth: 2, borderRadius: 3 },
      label: { show: true, fontSize: 10.5, fontFamily: t.mono, formatter: (p) => (p.value[2] ? fmt(p.value[2], opt.dec || 0) : ""), color: t.ink },
      emphasis: { itemStyle: { borderColor: t.ink, borderWidth: 1 } } }];
    const c = mk(id, o);
    // label color contrast: dark text on light cells, light text on dark cells
    if (c) {
      const th = max * 0.55;
      c.setOption({ series: [{ data: data.map((d) => ({ value: d, label: { color: (t.dark ? d[2] < th : d[2] > th) ? (t.dark ? t.ink : "#ffffff") : (t.dark ? "#0b1622" : t.ink) } })) }] });
      if (opt.onClick) c.on("click", (p) => opt.onClick(ys[p.value[1]], xs[p.value[0]]));
    }
    return c;
  }
  // small multiples: one grid per key, shared y scale
  function multiples(id, keys, xs, getVals, opt = {}) {
    const t = T();
    const el = document.getElementById(id);
    const w = el.clientWidth || 900;
    const cols = w < 560 ? 2 : 5;
    const rows = Math.ceil(keys.length / cols);
    const o = baseOpt(t);
    o.grid = []; o.xAxis = []; o.yAxis = []; o.series = []; o.title = [];
    let max = 0;
    keys.forEach((k) => getVals(k).forEach((s) => s.data.forEach((v) => { if (v != null) max = Math.max(max, v); })));
    max = Math.ceil(max / (opt.round || 1)) * (opt.round || 1);
    const cw = 100 / cols, rh = 100 / rows;
    keys.forEach((k, i) => {
      const c = i % cols, r = Math.floor(i / cols);
      o.title.push({ text: k, left: `${c * cw + 1}%`, top: `${r * rh + 0.5}%`, textStyle: { fontSize: 12.5, fontWeight: 600, color: t.ink, fontFamily: t.font } });
      o.grid.push({ left: `${c * cw + 3.5}%`, width: `${cw - 6}%`, top: `${r * rh + 7}%`, height: `${rh - 14}%`, containLabel: false });
      o.xAxis.push({ gridIndex: i, type: "category", data: xs, boundaryGap: opt.bar ? true : false, axisLine: { lineStyle: { color: t.line } }, axisTick: { show: false },
        axisLabel: { color: t.muted, fontSize: 10, fontFamily: t.mono, interval: (idx) => idx === 0 || idx === xs.length - 1 || xs[idx] === opt.mark, formatter: (v) => "’" + String(v).slice(2) } });
      o.yAxis.push({ gridIndex: i, type: "value", max, min: 0, splitNumber: 2, splitLine: { lineStyle: { color: t.line, opacity: 0.5 } }, axisLabel: { show: c === 0, color: t.muted, fontSize: 10, fontFamily: t.mono } });
      getVals(k).forEach((s) => {
        o.series.push(Object.assign({ type: opt.bar ? "bar" : "line", xAxisIndex: i, yAxisIndex: i, data: s.data, name: k, showSymbol: false, symbolSize: 6, smooth: false,
          lineStyle: { width: 2, color: s.color || t.accent, type: s.dash ? "dashed" : "solid" }, itemStyle: { color: s.color || t.accent, borderRadius: [2, 2, 0, 0] },
          areaStyle: s.area ? { color: s.color || t.accent, opacity: 0.12 } : undefined, barMaxWidth: 8 }, s.extra || {}));
      });
    });
    o.tooltip.trigger = "axis";
    o.tooltip.valueFormatter = (v) => (v == null ? "–" : fmt(v, opt.dec || 0) + (opt.unit || ""));
    o.axisPointer = { link: [{ xAxisIndex: "all" }] };
    el.style.height = Math.max(rows * 190, 300) + "px";
    return mk(id, o);
  }
  function sparkSVG(vals, w = 120, h = 30) {
    const v = vals.map((x) => (x == null ? 0 : x));
    const m = Math.max(...v, 1e-9);
    const pts = v.map((x, i) => [(i / (v.length - 1)) * (w - 4) + 2, h - 3 - (x / m) * (h - 7)]);
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const last = pts[pts.length - 1];
    return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true" style="display:block;max-width:100%"><path d="${d} L${last[0].toFixed(1)} ${h - 2} L2 ${h - 2} Z" fill="var(--accent)" opacity="0.12"></path><path d="${d}" fill="none" stroke="var(--accent)" stroke-width="1.6"></path><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.4" fill="var(--accent)"></circle></svg>`;
  }

  /* ---------- data load ---------- */
  async function load() {
    const names = ["projects", "stats", "taxonomy", "needs", "civil", "parts", "support", "global"];
    const res = await Promise.all(names.map((n) => fetch(`data/${n}.json`).then((r) => { if (!r.ok) throw new Error(n); return r.json(); })));
    names.forEach((n, i) => (D[n] = res[i]));
    D.P = D.projects;
    D.byId = Object.fromEntries(D.P.map((p) => [p.id, p]));
    D.cc = Object.fromEntries(D.stats.concepts.map((c) => [c.id, Object.assign({}, c, D.stats.trend[c.id] || {})]));
    D.L1 = Object.fromEntries(D.taxonomy.L1.map((x) => [x.id, x]));
    D.L2 = Object.fromEntries(D.taxonomy.L2.map((x) => [x.id, x]));
    D.civilByP = {};
    D.civil.forEach((c) => (c.rel || []).forEach(([pid, s]) => { (D.civilByP[pid] = D.civilByP[pid] || []).push([c, s]); }));
    D.cur = D.P.filter((p) => p.current);
    D.ccRx = D.stats.concepts.map((c) => [c.id, new RegExp(c.rx, "i")]);
  }

  /* ---------- routing ---------- */
  const RENDER = {};
  function show(v, force) {
    if (!RENDER[v]) v = "overview";
    current = v;
    $$(".view").forEach((s) => (s.hidden = s.id !== "v-" + v));
    $$("#nav a").forEach((a) => { if (a.dataset.v === v) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    if (!rendered.has(v) || force) {
      rendered.add(v);
      requestAnimationFrame(() => RENDER[v]());
    } else {
      if (v === "projects") drawP();
      Object.values(charts).forEach((c) => c && !c.isDisposed() && c.resize());
    }
  }
  window.addEventListener("hashchange", () => { show(location.hash.slice(1) || "overview"); window.scrollTo(0, 0); });

  /* ---------- 00 overview ---------- */
  RENDER.overview = function () {
    const st = D.stats, eds = st.editions;
    const cur = D.cur, curB = sum(cur.map((p) => p.budget));
    const needsOpen = D.needs.filter((n) => n.status === "○").length;
    const recs = sum(eds.map((e) => e.n));
    $("#kpis").innerHTML = [
      [eds.length, "기획서 판", "’17~’26 발간 (’20판 제외)"], [fmt(recs), "과제 기록", "판별 수록 합계"], [fmt(D.P.length), "고유 과제", "명칭 변경 이력까지 계보 연결"],
      [fmt(cur.length), "’26판 현행 과제", `총사업비 ${fmt(curB / 10000, 1)}조원`], [fmt(D.needs.length), "기술개발소요", `미확보 ${fmt(needsOpen)}건 (’26~’40)`],
      [fmt(D.civil.length), "민간보유기술", "’25 국방활용가능 조사"], [fmt(D.parts.length), "소재·부품 과제", "’26~’30 착수예상"],
    ].map(([v, l, s]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div><div class="s">${s}</div></div>`).join("");
    vbar("c-ed-n", eds.map((e) => ED_SHORT(e.ed)), eds.map((e) => e.n), { unit: "건" });
    vbar("c-ed-b", eds.map((e) => ED_SHORT(e.ed)), eds.map((e) => (e.budget ? Math.round(e.budget) : null)), { unit: "억원" });
    // insights
    const lin = D.P.filter((p) => p.eds.length >= 3).length;
    const tr = Object.values(D.cc).filter((c) => c.nProj >= 15).sort((a, b) => b.momentum - a.momentum);
    const fc = st.forecast;
    const openTop = FIELDS.map((f) => [f, sum(Object.values(fc[f].open || {}))]).sort((a, b) => b[1] - a[1]);
    const curByF = {};
    cur.forEach((p) => (curByF[p.stratField] = (curByF[p.stratField] || 0) + (p.budget || 0)));
    const topF = Object.entries(curByF).filter(([k]) => k !== "해당없음").sort((a, b) => b[1] - a[1]);
    const ko = st.levels.korea.slice().sort((a, b) => a[5] - b[5]);
    const items = [
      ["계보", `고유 과제 ${fmt(D.P.length)}개 중 ${fmt(lin)}개(${fmt((lin / D.P.length) * 100)}%)가 3개 판 이상 연속 수록됩니다. 과제는 보통 여러 해 기획서에 반복 등장하므로 중복 점검은 판 단위가 아닌 계보 단위로 해야 합니다.`],
      ["규모", `’26판 현행 과제의 총사업비는 ${fmt(curB)}억원입니다. 국방전략기술 분야로는 ${topF.slice(0, 3).map(([k, v]) => `${k} ${fmt(v)}억원`).join(", ")} 순으로 큽니다.`],
      ["상승", `최근 착수 과제에서 비중이 가장 빠르게 커진 기술개념은 ${tr.slice(0, 5).map((c) => `${c.name}(×${fmt(c.momentum, 1)})`).join(", ")}입니다.`],
      ["소요", `’26~’40 기술개발소요 중 아직 확보되지 않은 소요가 가장 많은 분야는 ${openTop.slice(0, 3).map(([f, v]) => `${f} ${fmt(v)}건`).join(", ")}입니다. 신규 과제 기획 여지가 큰 영역입니다.`],
      ["수준", `한국 국방과학기술 수준은 미국 대비 82%로 12개국 중 공동 8위(2024)입니다. 무기체계별로는 ${ko.slice(0, 3).map((k) => `${k[0]} ${k[5]}%`).join(", ")}가 가장 낮습니다.`],
    ];
    $("#ov-ins").innerHTML = items.map(([k, v]) => `<li><span class="k">${k}</span><span>${v}</span></li>`).join("");
  };

  /* ---------- 01 years ---------- */
  let selEd = "2026";
  RENDER.years = function () {
    const eds = D.stats.editions;
    const chips = $("#ed-chips");
    chips.innerHTML = eds.map((e) => `<button class="chip" type="button" data-ed="${e.ed}" aria-pressed="${e.ed === selEd}">${esc(e.label)}</button>`).join("");
    chips.onclick = (ev) => { const b = ev.target.closest("[data-ed]"); if (!b) return; selEd = b.dataset.ed; RENDER.years(); };
    const e = eds.find((x) => x.ed === selEd);
    const top = (o, n = 12) => Object.entries(o).filter(([k]) => k).sort((a, b) => b[1] - a[1]).slice(0, n);
    const d = top(e.domain);
    hbar("c-y-dom", d.map((x) => x[0]), d.map((x) => x[1]), { unit: "건", labelW: 90 });
    const tf = top(e.tf_raw);
    hbar("c-y-tf", tf.map((x) => x[0]), tf.map((x) => x[1]), { unit: "건", labelW: 90 });
    const pg = top(e.prog);
    hbar("c-y-prog", pg.map((x) => x[0]), pg.map((x) => x[1]), { unit: "건", labelW: 120 });
    const ys = Object.keys(D.stats.yearTot).map(Number).filter((y) => y >= 2010);
    const cnt = {}; D.P.forEach((p) => { if (p.start) cnt[p.start] = (cnt[p.start] || 0) + 1; });
    const yr = []; for (let y = 2010; y <= 2033; y++) yr.push(y);
    vbar("c-y-start", yr.map(String), yr.map((y) => cnt[y] || 0), { unit: "건", colorAt: (i, t) => (yr[i] > 2026 ? t.soft : t.accent) });
    const xs = eds.map((x) => ED_SHORT(x.ed));
    heat("c-y-hdom", xs, DOMS, DOMS.map((dm) => eds.map((x) => x.domain[dm] || 0)), { unit: "건" });
    const SF = FIELDS.concat(["해당없음"]);
    heat("c-y-hstr", xs, SF, SF.map((f) => eds.map((x) => (x.strat || {})[f] || 0)), { unit: "건" });
  };

  /* ---------- 02 tech ---------- */
  RENDER.tech = function () {
    const fc = D.stats.forecast;
    const yrs = []; for (let y = 2014; y <= 2030; y++) yrs.push(String(y));
    $("#fcards").innerHTML = FIELDS.map((f) => {
      const all = D.P.filter((p) => p.stratField === f), cur = all.filter((p) => p.current);
      const s = fc[f];
      return `<button class="fcard" type="button" data-f="${esc(f)}"><div class="top"><span class="nm">${esc(f)}</span><span class="code">${FCODE[f]}</span></div>
        <div class="row"><span>’26판 현행 / 누적 과제</span><b>${fmt(cur.length)} / ${fmt(all.length)}</b></div>
        <div class="row"><span>현행 총사업비</span><b>${fmt(sum(cur.map((p) => p.budget)))}억</b></div>
        <div class="row"><span>기술개발소요(미확보)</span><b>${fmt(s.needs)} (${fmt(sum(Object.values(s.open)))})</b></div>
        <div class="row"><span>민간보유기술</span><b>${fmt(s.civil)}</b></div>
        <div class="spark">${sparkSVG(yrs.map((y) => s.starts[y] || 0), 220, 38)}</div><div class="sub">착수연도별 과제 수 ’14→’30</div></button>`;
    }).join("");
    $("#fcards").onclick = (ev) => { const b = ev.target.closest("[data-f]"); if (!b) return; PF.str = b.dataset.f; PF.page = 0; location.hash = "#projects"; };
    const eds = D.stats.editions;
    const TFU = ["센서·제어", "정보통신", "기계(추진·플랫폼)", "탄약/에너지", "소재", "화생방"];
    heat("c-t-tf", eds.map((x) => ED_SHORT(x.ed)), TFU, TFU.map((k) => eds.map((x) => x.tf[k] || 0)), { unit: "건" });
    // L1 needs stacked
    const t = T();
    const L1 = D.taxonomy.L1;
    const tot = {}, open = {};
    D.needs.forEach((n) => { tot[n.l1] = (tot[n.l1] || 0) + 1; if (n.status === "○") open[n.l1] = (open[n.l1] || 0) + 1; });
    const o = baseOpt(t);
    const labels = L1.map((x) => `${x.id} ${x.name}`);
    o.grid = { left: 8, right: 40, top: 26, bottom: 6, containLabel: true };
    o.legend = { top: 0, left: 0, textStyle: { color: t.ink2, fontSize: 12 }, itemWidth: 12, itemHeight: 10 };
    o.xAxis = axisVal(t);
    o.yAxis = axisCat(t, labels, { inverse: true, axisLabel: { color: t.ink2, fontSize: 11, width: 150, overflow: "truncate" } });
    o.tooltip.trigger = "axis"; o.tooltip.axisPointer = { type: "shadow" };
    o.series = [
      { name: "미확보", type: "bar", stack: "a", data: L1.map((x) => open[x.id] || 0), itemStyle: { color: t.accent }, barMaxWidth: 12 },
      { name: "확보", type: "bar", stack: "a", data: L1.map((x) => (tot[x.id] || 0) - (open[x.id] || 0)), itemStyle: { color: t.soft, borderRadius: [0, 3, 3, 0] }, barMaxWidth: 12,
        label: { show: true, position: "right", color: t.ink2, fontFamily: t.mono, fontSize: 10.5, formatter: (p) => fmt(tot[L1[p.dataIndex].id] || 0) } },
    ];
    document.getElementById("c-t-l1").style.height = "640px";
    mk("c-t-l1", o);
    renderCCTable();
    $("#cc-sort").onchange = renderCCTable;
  };
  function renderCCTable() {
    const k = $("#cc-sort").value;
    let rows = Object.values(D.cc).filter((c) => c.nProj >= 8);
    if (k === "low") rows.sort((a, b) => a.momentum - b.momentum); else rows.sort((a, b) => (b[k] || 0) - (a[k] || 0));
    rows = rows.slice(0, 30);
    const years = Object.keys(D.stats.yearTot);
    const i0 = years.indexOf("2016"), i1 = years.indexOf("2026");
    $("#cc-tbl").innerHTML = `<thead><tr><th>기술개념</th><th>상위 분류</th><th class="n">과제</th><th class="n">과거 비중</th><th class="n">최근 비중</th><th class="n">상승지수</th><th class="n">미확보 소요</th><th class="n">민간기술</th><th>착수 비중 ’16→’26</th></tr></thead><tbody>` +
      rows.map((c) => {
        const m = c.momentum;
        const pill = m >= 1.6 ? '<span class="pill good">상승</span>' : m <= 0.7 ? '<span class="pill warn">하락</span>' : '<span class="pill info">유지</span>';
        return `<tr><td><span class="pname">${esc(c.name)}</span></td><td><span class="tag">${esc(c.cat)}</span></td><td class="n">${fmt(c.nProj)}</td><td class="n">${fmt(c.past * 100, 1)}%</td><td class="n">${fmt(c.recent * 100, 1)}%</td>
        <td class="n">×${fmt(m, 2)} ${pill}</td><td class="n">${fmt(c.nNeedsOpen)}</td><td class="n">${fmt(c.nCivil)}</td><td>${sparkSVG((c.share || []).slice(i0, i1 + 1), 120, 26)}</td></tr>`;
      }).join("") + "</tbody>";
  }

  /* ---------- 03 systems ---------- */
  RENDER.systems = function () {
    const SF = FIELDS.concat(["해당없음"]);
    const ps = D.P.filter((p) => p.eds.some((e) => e >= "2021"));
    const M = DOMS.map((d) => SF.map((f) => ps.filter((p) => p.domain === d && p.stratField === f).length));
    heat("c-s-hm", SF.map((f) => FCODE[f] === "–" ? "해당없음" : f), DOMS, M, { rotate: 40, unit: "건", onClick: (dom, f) => { PF.dom = dom; PF.str = f; PF.page = 0; location.hash = "#projects"; } });
    // levels
    const t = T();
    const K = D.stats.levels.korea.slice().sort((a, b) => b[5] - a[5]);
    const o = baseOpt(t);
    o.grid = { left: 8, right: 40, top: 26, bottom: 4, containLabel: true };
    o.legend = { top: 0, left: 0, textStyle: { color: t.ink2, fontSize: 12 }, itemWidth: 12, itemHeight: 10 };
    o.xAxis = axisVal(t, { min: 60, max: 100 });
    o.yAxis = axisCat(t, K.map((k) => k[0]), { inverse: true });
    o.tooltip.trigger = "axis"; o.tooltip.axisPointer = { type: "shadow" };
    o.tooltip.formatter = (ps2) => { const k = K[ps2[0].dataIndex]; return `<b>${esc(k[0])}</b> (${esc(k[7])})<br>2018: ${k[1]}% · ${k[2]}위<br>2021: ${k[3]}% · ${k[4]}위<br>2024: <b>${k[5]}%</b> · ${k[6]}위`; };
    o.series = [
      { name: "2024 수준(%)", type: "bar", data: K.map((k) => k[5]), barMaxWidth: 10, itemStyle: { color: t.accent, borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: "right", fontFamily: t.mono, fontSize: 10.5, color: t.ink2, formatter: (p) => `${p.value} · ${K[p.dataIndex][6]}위` } },
      { name: "2018 수준(%)", type: "scatter", data: K.map((k) => k[1]), symbolSize: 8, itemStyle: { color: t.surface, borderColor: t.ink2, borderWidth: 2 } },
    ];
    document.getElementById("c-s-lv").style.height = "620px";
    mk("c-s-lv", o);
    $("#lv-tbl").innerHTML = `<thead><tr><th>국가</th><th class="n">2018</th><th class="n">2021</th><th class="n">2024</th><th class="n">순위(’24)</th><th>수준</th></tr></thead><tbody>` +
      D.stats.levels.countries.map((c) => `<tr${c[0] === "한국" ? ' style="font-weight:700"' : ""}><td>${esc(c[0])}</td><td class="n">${c[1]}</td><td class="n">${c[3]}</td><td class="n">${c[5]}</td><td class="n">${c[6]}</td><td><div class="bar"><i style="width:${c[5]}%"></i></div></td></tr>`).join("") + "</tbody>";
    const bySys = {};
    D.parts.forEach((x) => (bySys[x.system] = (bySys[x.system] || 0) + 1));
    const top = Object.entries(bySys).sort((a, b) => b[1] - a[1]).slice(0, 16);
    hbar("c-s-parts", top.map((x) => x[0]), top.map((x) => x[1]), { unit: "건", labelW: 140 });
    const draw = () => {
      const q = $("#parts-q").value.trim().toLowerCase();
      const rows = D.parts.filter((x) => !q || (x.system + x.name + x.domain).toLowerCase().includes(q));
      $("#parts-tbl").innerHTML = `<thead><tr><th>과제번호</th><th>체계분야</th><th>적용 무기체계</th><th>과제명</th><th>유형</th><th class="n">착수</th><th class="n">기간(월)</th><th class="n">정부지원(억)</th></tr></thead><tbody>` +
        rows.map((x) => `<tr><td class="mono" style="font-size:12px">${esc(x.id)}</td><td>${esc(x.domain)}</td><td>${esc(x.system)}</td><td>${esc(x.name)}</td><td class="fname">${esc(x.type)}</td><td class="n">${x.start}</td><td class="n">${x.months}</td><td class="n">${fmt(x.budget, 1)}</td></tr>`).join("") + "</tbody>";
    };
    $("#parts-q").oninput = draw; draw();
  };

  /* ---------- 04 projects ---------- */
  const PF = { q: "", scope: "all", dom: "", str: "", prog: "", sort: "start", page: 0 };
  const PAGE = 40;
  function filtered() {
    const q = PF.q.trim().toLowerCase();
    let rows = D.P.filter((p) => {
      if (PF.scope === "cur" && !p.current) return false;
      if (PF.scope === "past" && p.current) return false;
      if (PF.dom && p.domain !== PF.dom) return false;
      if (PF.str && p.stratField !== PF.str) return false;
      if (PF.prog && p.prog !== PF.prog) return false;
      if (q) { const s = (p.name + " " + p.aliases.join(" ") + " " + p.ov + " " + p.items).toLowerCase(); if (!q.split(/\s+/).every((w) => s.includes(w))) return false; }
      return true;
    });
    const k = PF.sort;
    rows.sort((a, b) => k === "budget" ? (b.budget || 0) - (a.budget || 0) : k === "eds" ? b.eds.length - a.eds.length : k === "name" ? a.name.localeCompare(b.name, "ko") : (b.start || 0) - (a.start || 0));
    return rows;
  }
  function stratTag(p) {
    if (p.stratField === "해당없음") return `<span class="tag ${p.stratSrc === "추정" ? "est" : ""}" title="${p.stratSrc}">해당없음</span>`;
    return `<span class="tag ${p.stratSrc === "추정" ? "est" : ""}" title="${p.stratSrc === "추정" ? "텍스트 분류 추정" : "기획서 표기"}">${esc(p.stratField)}${p.stratSrc === "추정" ? " *" : ""}</span>`;
  }
  RENDER.projects = function () {
    const opts = (el, vals, all) => { el.innerHTML = `<option value="">${all}</option>` + vals.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join(""); };
    opts($("#p-dom"), DOMS, "전체");
    opts($("#p-str"), FIELDS.concat(["해당없음"]), "전체");
    const progs = {}; D.P.forEach((p) => (progs[p.prog] = (progs[p.prog] || 0) + 1));
    opts($("#p-prog"), Object.keys(progs).sort((a, b) => progs[b] - progs[a]), "전체");
    const bind = (id, key) => { const el = $(id); el.value = PF[key]; el.oninput = el.onchange = () => { PF[key] = el.value; PF.page = 0; drawP(); }; };
    bind("#p-q", "q"); bind("#p-scope", "scope"); bind("#p-dom", "dom"); bind("#p-str", "str"); bind("#p-prog", "prog"); bind("#p-sort", "sort");
    $("#p-prev").onclick = () => { if (PF.page > 0) { PF.page--; drawP(); } };
    $("#p-next").onclick = () => { PF.page++; drawP(); };
    $("#p-csv").onclick = exportCSV;
    $("#p-tbl").onclick = (ev) => { const tr = ev.target.closest("tr[data-id]"); if (tr) openP(tr.dataset.id); };
    drawP();
  };
  function drawP() {
    ["dom", "str", "prog", "scope", "sort"].forEach((k) => { const el = $("#p-" + k); if (el && el.value !== PF[k]) el.value = PF[k]; });
    const rows = filtered();
    const pages = Math.max(1, Math.ceil(rows.length / PAGE));
    PF.page = Math.min(PF.page, pages - 1);
    const sl = rows.slice(PF.page * PAGE, PF.page * PAGE + PAGE);
    $("#p-info").innerHTML = `<span><b class="num">${fmt(rows.length)}</b>건 · 총사업비 <b class="num">${fmt(sum(rows.map((p) => p.budget)))}</b>억원 (최신 판 기준)</span><span>${PF.page + 1} / ${pages} 쪽 · <span class="tag est">점선</span> = 국방전략기술 추정</span>`;
    $("#p-tbl").innerHTML = `<thead><tr><th>과제명</th><th>무기체계</th><th>국방전략기술</th><th>사업 유형</th><th class="n">기간</th><th class="n">총사업비(억)</th><th>수록 판</th></tr></thead><tbody>` +
      sl.map((p) => `<tr class="click" data-id="${p.id}"><td><div class="pname">${esc(p.name)}</div>${p.aliases.length ? `<div class="sub">구 명칭 ${esc(p.aliases[0])}${p.aliases.length > 1 ? ` 외 ${p.aliases.length - 1}` : ""}</div>` : ""}</td>
        <td>${esc(p.domain || "–")}</td><td>${stratTag(p)}</td><td><span class="sub">${esc(p.prog)}</span></td>
        <td class="n">${p.start ? `${p.start}–${p.end || ""}` : "–"}</td><td class="n">${p.budget ? fmt(p.budget, 1) : "–"}</td>
        <td><span class="tags">${p.eds.map((e) => `<span class="tag code">${e.slice(2)}</span>`).join("")}</span></td></tr>`).join("") + "</tbody>";
  }
  function exportCSV() {
    const rows = filtered();
    const head = ["id", "과제명", "구명칭", "무기체계분야", "기술분야", "국방전략기술분야", "분류출처", "국방전략기술(L1)", "사업유형", "주관", "착수", "종료", "총사업비(억원)", "수록판", "개요"];
    const q = (s) => `"${String(s == null ? "" : s).replace(/"/g, '""')}"`;
    const lines = [head.map(q).join(",")].concat(rows.map((p) => [p.id, p.name, p.aliases.join(" / "), p.domain, p.tf, p.stratField, p.stratSrc, p.l1 ? `${p.l1} ${D.L1[p.l1] ? D.L1[p.l1].name : ""}` : "", p.prog, p.org, p.start, p.end, p.budget, p.eds.join(" "), p.ov].map(q).join(",")));
    const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "국방기술과제_목록.csv"; document.body.appendChild(a); a.click(); a.remove();
  }

  /* ---------- drawer ---------- */
  function openP(id) {
    const p = D.byId[id];
    if (!p) return;
    const dr = $("#drawer");
    const l1 = p.l1 && D.L1[p.l1];
    const sims = (p.sim || []).map(([pid, s]) => [D.byId[pid], s]).filter((x) => x[0]);
    const needs = (p.needsRel || []).map(([k, s]) => [D.needs[k], s]).filter((x) => x[0]);
    const civ = (D.civilByP[p.id] || []).sort((a, b) => b[1] - a[1]).slice(0, 4);
    dr.innerHTML = `<button class="close" type="button" id="dr-close">닫기</button>
      <div><div class="eyebrow">${p.id} · ${p.current ? "’26판 현행" : "종료 또는 미수록"}</div><h2 style="font-size:21px">${esc(p.name)}</h2>
      ${p.aliases.length ? `<p class="note">이전 명칭: ${p.aliases.map(esc).join(" · ")}</p>` : ""}</div>
      <dl class="kv">
        <dt>무기체계 분야</dt><dd>${esc(p.domain || "–")}</dd><dt>기술분야</dt><dd>${esc(p.tf || "–")}</dd>
        <dt>국방전략기술</dt><dd>${stratTag(p)} ${l1 ? `<span class="tag code">${l1.id}</span> ${esc(l1.name)}` : ""}${p.stratSrc === "추정" ? `<div class="sub">추정 후보: ${p.stratPred.map(([k, v]) => `${esc(k)} ${fmt(v * 100)}%`).join(" · ")}</div>` : ""}</dd>
        <dt>사업 유형</dt><dd>${esc(p.prog)} ${p.org ? `<span class="sub">· 주관 ${esc(p.org)}</span>` : ""}</dd>
        <dt>사업기간</dt><dd class="num">${p.start ? `${p.start}–${p.end || ""}${p.months ? ` (${p.months}개월)` : ""}` : "–"}</dd>
        <dt>총사업비</dt><dd class="num">${p.budget ? fmt(p.budget, 2) + " 억원" : "–"}</dd>
        <dt>기술개념</dt><dd><span class="tags">${(p.cc || []).map((c) => `<span class="tag">${esc(D.cc[c] ? D.cc[c].name : c)}</span>`).join("") || "–"}</span></dd>
      </dl>
      ${p.ov ? `<div><h3>개요</h3><p style="margin:0">${esc(p.ov)}</p></div>` : ""}
      ${p.items ? `<div><h3>연구항목</h3><p style="margin:0" class="sub">${esc(p.items)}</p></div>` : ""}
      ${p.sub && p.sub.length ? `<div><h3>세부과제</h3><ul style="margin:0;padding-left:18px">${p.sub.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>` : ""}
      <div><h3>기획서 수록 이력</h3><div class="timeline">${p.hist.map((h) => `<div class="t"><b class="mono">${esc(D.stats.edLabel[h.ed] || h.ed)}</b> · ${esc(h.prog)}${h.budget ? ` · ${fmt(h.budget, 1)}억` : ""}${h.start ? ` · ${h.start}–${h.end}` : ""}${h.name !== p.name ? `<div class="sub">${esc(h.name)}</div>` : ""}</div>`).join("")}</div></div>
      <div><h3>유사 과제</h3>${sims.length ? `<div class="results">${sims.map(([q, s]) => `<div class="res" data-open="${q.id}" style="cursor:pointer"><div class="score">${fmt(s * 100)}<small>유사도</small></div><div class="body"><div class="pname">${esc(q.name)}</div><div class="sub">${esc(q.domain)} · ${q.start || "–"}–${q.end || ""} · ${q.eds.map((e) => "’" + e.slice(2)).join(" ")}</div></div></div>`).join("")}</div>` : '<p class="note">유사도 0.30 이상 과제가 없습니다.</p>'}</div>
      <div><h3>연계 기술개발소요 (’26~’40)</h3>${needs.length ? `<ul style="margin:0;padding-left:18px">${needs.map(([n, s]) => `<li>${esc(n.name)} <span class="sub">· ${esc(D.L1[n.l1] ? D.L1[n.l1].name : "")} · ${esc(n.period)} · ${esc(n.method)} · ${n.status === "●" ? "확보" : "미확보"} · ${fmt(s * 100)}</span></li>`).join("")}</ul>` : '<p class="note">연계 소요가 뚜렷하지 않습니다.</p>'}</div>
      ${civ.length ? `<div><h3>연계 민간보유기술</h3><ul style="margin:0;padding-left:18px">${civ.map(([c, s]) => `<li>${esc(c.title)} <span class="sub">· ${esc(c.weapon)} · ${fmt(s * 100)}</span></li>`).join("")}</ul></div>` : ""}`;
    dr.hidden = false; $("#scrim").hidden = false;
    dr.scrollTop = 0;
    $("#dr-close").onclick = closeP;
    dr.onclick = (ev) => { const r = ev.target.closest("[data-open]"); if (r) openP(r.dataset.open); };
    $("#dr-close").focus();
  }
  function closeP() { $("#drawer").hidden = true; $("#scrim").hidden = true; }
  $("#scrim").addEventListener("click", closeP);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeP(); });

  /* ---------- 05 budget ---------- */
  RENDER.budget = function () {
    const t = T();
    const yrs = []; for (let y = 2014; y <= 2033; y++) yrs.push(String(y));
    const A = D.stats.annual;
    multiples("c-b-sm", FIELDS, yrs, (f) => [{ data: yrs.map((y) => (A[f] && A[f][y] != null ? Math.round(A[f][y]) : 0)), area: true }], { unit: "억원/년", mark: "2026", round: 100 });
    const cur = D.cur;
    const by = (k) => { const o = {}; cur.forEach((p) => (o[p[k] || "미분류"] = (o[p[k] || "미분류"] || 0) + (p.budget || 0))); return Object.entries(o).sort((a, b) => b[1] - a[1]); };
    const d = by("domain"); hbar("c-b-dom", d.map((x) => x[0]), d.map((x) => Math.round(x[1])), { unit: "억원", labelW: 90 });
    const g = by("prog"); hbar("c-b-prog", g.map((x) => x[0]), g.map((x) => Math.round(x[1])), { unit: "억원", labelW: 150 });
    const top = D.P.filter((p) => p.budget).sort((a, b) => b.budget - a.budget).slice(0, 25);
    $("#b-top").innerHTML = `<thead><tr><th>과제명</th><th>무기체계</th><th>국방전략기술</th><th>사업 유형</th><th class="n">기간</th><th class="n">총사업비(억)</th></tr></thead><tbody>` +
      top.map((p) => `<tr class="click" data-id="${p.id}"><td class="pname">${esc(p.name)}</td><td>${esc(p.domain)}</td><td>${stratTag(p)}</td><td class="sub">${esc(p.prog)}</td><td class="n">${p.start}–${p.end}</td><td class="n">${fmt(p.budget, 1)}</td></tr>`).join("") + "</tbody>";
    $("#b-top").onclick = (ev) => { const tr = ev.target.closest("tr[data-id]"); if (tr) openP(tr.dataset.id); };
  };

  /* ---------- similarity engine ---------- */
  const SIM = { ready: false };
  const normTxt = (s) => (s || "").toLowerCase().replace(/[^0-9a-z가-힣\s]/g, " ").replace(/\s+/g, " ").trim();
  function feats(s) {
    const m = new Map();
    for (const w of normTxt(s).split(" ")) {
      if (!w) continue;
      const p = " " + w + " ";
      for (let n = 2; n <= 3; n++) for (let i = 0; i + n <= p.length; i++) { const g = p.substr(i, n); if (g.trim()) m.set(g, (m.get(g) || 0) + 1); }
    }
    return m;
  }
  function buildIndex(texts) {
    const N = texts.length, df = new Map(), F = texts.map(feats);
    F.forEach((m) => m.forEach((_, g) => df.set(g, (df.get(g) || 0) + 1)));
    const idf = new Map(); df.forEach((v, g) => idf.set(g, Math.log((N + 1) / (v + 1)) + 1));
    const post = new Map();
    F.forEach((m, d) => {
      let nn = 0; const w = [];
      m.forEach((tf, g) => { const x = (1 + Math.log(tf)) * idf.get(g); w.push([g, x]); nn += x * x; });
      nn = Math.sqrt(nn) || 1;
      w.forEach(([g, x]) => { let a = post.get(g); if (!a) post.set(g, (a = [])); a.push(d, x / nn); });
    });
    return { N, idf, post };
  }
  function query(ix, s) {
    const m = feats(s); let nn = 0; const q = [];
    m.forEach((tf, g) => { const id = ix.idf.get(g); if (!id) return; const x = (1 + Math.log(tf)) * id; q.push([g, x]); nn += x * x; });
    nn = Math.sqrt(nn) || 1;
    const sc = new Float32Array(ix.N);
    q.forEach(([g, x]) => { const a = ix.post.get(g); if (!a) return; const qw = x / nn; for (let i = 0; i < a.length; i += 2) sc[a[i]] += qw * a[i + 1]; });
    return sc;
  }
  function ensureSim() {
    if (SIM.ready) return;
    const docs = [];
    D.P.forEach((p) => docs.push({ type: "과제", ref: p, title: p.name + " " + p.aliases.join(" "), full: [p.name, p.aliases.join(" "), p.ov, p.items].join(" ") }));
    D.needs.forEach((n) => docs.push({ type: "기술개발소요", ref: n, title: n.name, full: n.name + " " + n.spec + " " + (n.l3n || "") }));
    D.civil.forEach((c) => docs.push({ type: "민간보유기술", ref: c, title: c.title, full: [c.title, c.ov, c.keywords.join(" ")].join(" ") }));
    D.parts.forEach((x) => docs.push({ type: "소재·부품", ref: x, title: x.name, full: x.name + " " + x.system }));
    SIM.docs = docs;
    SIM.title = buildIndex(docs.map((d) => d.title));
    SIM.full = buildIndex(docs.map((d) => d.full));
    SIM.ready = true;
  }
  const conceptsOf = (s) => D.ccRx.filter(([, rx]) => rx.test(s)).map(([id]) => id);
  function check(title, ov, scope, k = 12) {
    ensureSim();
    const a = query(SIM.title, title), b = query(SIM.full, title + " " + title + " " + (ov || ""));
    const res = [];
    for (let i = 0; i < SIM.docs.length; i++) {
      const d = SIM.docs[i];
      if (scope === "proj" && d.type !== "과제") continue;
      if (scope === "cur" && !(d.type === "과제" && d.ref.current)) continue;
      const s = 0.45 * a[i] + 0.55 * b[i];
      if (s > 0.12) res.push([s, i]);
    }
    res.sort((x, y) => y[0] - x[0]);
    return res.slice(0, k).map(([s, i]) => ({ s, d: SIM.docs[i] }));
  }
  const level = (s) => (s >= 0.5 ? ["crit", "중복 의심"] : s >= 0.36 ? ["warn", "유사"] : ["info", "관련"]);

  /* ---------- 06 dup ---------- */
  let dupMode = "one";
  RENDER.dup = function () {
    $("#dup-mode").onclick = (ev) => {
      const b = ev.target.closest("[data-m]"); if (!b) return; dupMode = b.dataset.m;
      $$("#dup-mode .chip").forEach((c) => c.setAttribute("aria-pressed", c.dataset.m === dupMode));
      $("#dup-one").hidden = dupMode !== "one"; $("#dup-batch").hidden = dupMode !== "batch";
    };
    $("#d-run").onclick = runDup;
    runDup();
  };
  function sharedWords(a, b) {
    const STOP = new Set(["기술", "개발", "연구", "기반", "위한", "시스템", "및", "통한", "대한", "기술개발", "설계", "적용", "활용", "과제"]);
    const A = new Set(normTxt(a).split(" ").filter((w) => w.length >= 2 && !STOP.has(w)));
    return normTxt(b).split(" ").filter((w, i, arr) => w.length >= 2 && A.has(w) && arr.indexOf(w) === i).slice(0, 6);
  }
  function docLine(d) {
    const r = d.ref;
    if (d.type === "과제") return { name: r.name, meta: `${r.domain || "–"} · ${r.stratField}${r.stratSrc === "추정" ? "*" : ""} · ${r.start || "–"}–${r.end || ""} · ${r.budget ? fmt(r.budget, 1) + "억" : "예산 –"} · ${r.current ? "’26판 현행" : "판 " + r.eds.map((e) => "’" + e.slice(2)).join(" ")}`, id: r.id, cc: r.cc };
    if (d.type === "기술개발소요") return { name: r.name, meta: `${D.L1[r.l1] ? D.L1[r.l1].id + " " + D.L1[r.l1].name : ""} · ${r.period} · ${r.method} · ${r.status === "●" ? "확보" : "미확보"}`, sub: r.spec, cc: r.cc };
    if (d.type === "민간보유기술") return { name: r.title, meta: `${r.weapon || ""} · ${r.strategic || ""} · 키워드 ${r.keywords.slice(0, 4).join(", ")}`, sub: r.ov.slice(0, 140) + (r.ov.length > 140 ? "…" : ""), cc: r.cc };
    return { name: r.name, meta: `${r.domain} · ${r.system} · ${r.start} 착수예상 · ${fmt(r.budget, 1)}억`, cc: r.cc };
  }
  function runDup() {
    const out = $("#d-out");
    const scope = $("#d-scope").value;
    if (dupMode === "one") {
      const title = $("#d-title").value.trim(), ov = $("#d-ov").value.trim();
      if (!title) { out.innerHTML = '<p class="note">과제명을 입력하세요.</p>'; return; }
      $("#d-status").textContent = "계산 중…";
      setTimeout(() => {
        const r = check(title, ov, scope, 14);
        const qcc = conceptsOf(title + " " + ov);
        const topS = r.length ? r[0].s : 0;
        const [lv, lab] = level(topS);
        const nCrit = r.filter((x) => x.s >= 0.5).length, nWarn = r.filter((x) => x.s >= 0.36 && x.s < 0.5).length;
        const fieldGuess = (() => { const c = {}; r.slice(0, 8).forEach((x) => { const f = x.d.type === "과제" ? x.d.ref.stratField : x.d.type === "기술개발소요" ? x.d.ref.field : x.d.ref.strategic; if (f && f !== "해당없음") c[f] = (c[f] || 0) + x.s; }); return Object.entries(c).sort((a, b) => b[1] - a[1])[0]; })();
        out.innerHTML = `<div class="verdict ${lv === "info" ? "good" : lv}"><b>${lv === "crit" ? "중복 가능성이 높습니다" : lv === "warn" ? "유사 과제가 있습니다" : "뚜렷한 중복은 보이지 않습니다"}</b> · 최고 유사도 <span class="num">${fmt(topS * 100)}</span>
          <div class="sub">중복 의심(50 이상) ${nCrit}건 · 유사(36~50) ${nWarn}건${fieldGuess ? ` · 가까운 국방전략기술 분야: ${esc(fieldGuess[0])}` : ""}${qcc.length ? ` · 입력 기술개념: ${qcc.map((c) => esc(D.cc[c].name)).join(", ")}` : ""}</div></div>` +
          r.map((x) => {
            const L = docLine(x.d), [cls, lb] = level(x.s);
            const shared = (L.cc || []).filter((c) => qcc.includes(c));
            const words = sharedWords(title + " " + ov, L.name + " " + (L.sub || ""));
            return `<div class="res"${L.id ? ` data-open="${L.id}" style="cursor:pointer"` : ""}><div class="score">${fmt(x.s * 100)}<small><span class="pill ${cls}">${lb}</span></small></div><div class="body">
              <div><span class="tag">${x.d.type}</span> <span class="pname">${esc(L.name)}</span></div><div class="sub">${esc(L.meta)}</div>${L.sub ? `<div class="sub">${esc(L.sub)}</div>` : ""}
              ${shared.length || words.length ? `<div class="tags">${shared.map((c) => `<span class="tag">${esc(D.cc[c].name)}</span>`).join("")}${words.map((w) => `<span class="tag code">${esc(w)}</span>`).join("")}</div>` : ""}</div></div>`;
          }).join("");
        out.onclick = (ev) => { const e = ev.target.closest("[data-open]"); if (e) openP(e.dataset.open); };
        $("#d-status").textContent = `${fmt(SIM.docs.length)}건과 비교했습니다. 점수는 0~100 (과제명 45% + 내용 55% 가중 코사인 유사도).`;
      }, 20);
    } else {
      const lines = $("#d-batch").value.split("\n").map((l) => l.trim()).filter(Boolean);
      $("#d-status").textContent = "계산 중…";
      setTimeout(() => {
        const rows = lines.map((l) => { const [ti, ...rest] = l.split("|"); const r = check(ti.trim(), rest.join(" ").trim(), scope, 3); return { ti: ti.trim(), r }; });
        out.innerHTML = `<div class="tbl-wrap"><table><thead><tr><th>계획 과제</th><th class="n">최고 유사도</th><th>판정</th><th>가장 가까운 항목</th><th>차순위</th></tr></thead><tbody>` +
          rows.map(({ ti, r }) => { const s = r[0] ? r[0].s : 0, [cls, lb] = level(s); const L = r[0] ? docLine(r[0].d) : null, L2 = r[1] ? docLine(r[1].d) : null;
            return `<tr><td class="pname">${esc(ti)}</td><td class="n">${fmt(s * 100)}</td><td><span class="pill ${cls}">${lb}</span></td><td>${L ? `<span class="tag">${r[0].d.type}</span> ${esc(L.name)}<div class="sub">${esc(L.meta)}</div>` : "–"}</td><td>${L2 ? `${esc(L2.name)} <span class="sub">(${fmt(r[1].s * 100)})</span>` : "–"}</td></tr>`; }).join("") + "</tbody></table></div>";
        $("#d-status").textContent = `${rows.length}개 계획 과제를 점검했습니다.`;
      }, 20);
    }
  }

  /* ---------- 07 ontology ---------- */
  let ontoMode = "graph";
  RENDER.onto = function () {
    const st = D.stats;
    $("#schema").innerHTML = [
      ["기획서 판", "Edition · 9", "수록 → 과제"], ["과제", `Project · ${fmt(D.P.length)}`, "적용 → 무기체계 분야(10)<br>속함 → 기술분야(8·6)<br>기여 → 국방전략기술"],
      ["국방전략기술", "10 분야 · 30 기술 · 99 세부 · 302 구성", "구체화 → 기술개발소요"], ["기술개발소요", `Need · ${fmt(D.needs.length)}`, "시기(단·중·장기) · 추진방안 · 확보여부"],
      ["기술개념", `Concept · ${st.concepts.length}`, "언급 ← 과제·소요·민간기술<br>함께 쓰임 ↔ 기술개념"], ["민간보유기술", `CivilTech · ${D.civil.length}`, "활용 가능 → 과제<br>연계 → 국방전략기술"],
      ["소재·부품 과제", `Part · ${D.parts.length}`, "국산화 → 적용 무기체계"], ["유사 관계", "similarTo", "과제 ↔ 과제 (코사인 0.30 이상)"],
    ].map(([a, b, c]) => `<div class="cls"><b>${a}</b><span class="sub mono">${b}</span><span class="rel">${c}</span></div>`).join("");
    $("#onto-mode").onclick = (ev) => { const b = ev.target.closest("[data-m]"); if (!b) return; ontoMode = b.dataset.m; $$("#onto-mode .chip").forEach((c) => c.setAttribute("aria-pressed", c.dataset.m === ontoMode)); drawOnto(); };
    drawOnto();
  };
  function drawOnto() {
    const t = T();
    const st = D.stats;
    const o = baseOpt(t);
    if (ontoMode === "graph") {
      $("#onto-legend").innerHTML = GROUPS.map((g, i) => `<span><i style="background:${t.cat[i]}"></i>${g.name}</span>`).join("") + '<span class="sub">원 크기 = 언급 과제 수</span>';
      const nodes = st.concepts.filter((c) => (D.cc[c.id].nProj || 0) >= 3).map((c) => {
        const g = Math.max(0, groupOf(c.cat)), n = D.cc[c.id].nProj;
        return { id: c.id, name: c.name, value: n, symbolSize: 8 + Math.sqrt(n) * 2.6, category: g, itemStyle: { color: t.cat[g], borderColor: t.surface, borderWidth: 1.5 },
          label: { show: n >= 25, color: t.ink, fontSize: 11, fontFamily: t.font } };
      });
      const ids = new Set(nodes.map((n) => n.id));
      const maxW = Math.max(...st.edges.map((e) => e.w));
      const links = st.edges.filter((e) => ids.has(e.s) && ids.has(e.t)).map((e) => ({ source: e.s, target: e.t, value: e.w, lineStyle: { width: 0.6 + (e.w / maxW) * 5, color: t.muted, opacity: 0.35 } }));
      o.tooltip.formatter = (p) => p.dataType === "edge" ? `${esc(D.cc[p.data.source].name)} ↔ ${esc(D.cc[p.data.target].name)}<br>함께 언급 과제 <b>${p.data.value}</b>건` : `<b>${esc(p.data.name)}</b><br>과제 ${p.data.value}건 · ${esc(D.cc[p.data.id].cat)}`;
      o.series = [{ type: "graph", layout: "force", roam: true, draggable: true, data: nodes, links, categories: GROUPS.map((g) => ({ name: g.name })),
        force: { repulsion: 210, edgeLength: [40, 160], gravity: 0.08, friction: 0.2 }, emphasis: { focus: "adjacency", label: { show: true }, lineStyle: { opacity: 0.8 } },
        labelLayout: { hideOverlap: true } }];
      const c = mk("c-onto", o);
      if (c) c.on("click", (p) => { if (p.dataType === "node") conceptSide(p.data.id); });
    } else {
      $("#onto-legend").innerHTML = '<span class="sub">안쪽부터 10대 분야 → 30대 국방전략기술 → 세부기술. 면적 = 기술개발소요 수. 조각을 누르면 소요와 연계 과제가 표시됩니다.</span>';
      const nByL2 = {}, nByL1 = {};
      D.needs.forEach((n) => { if (n.l2) nByL2[n.l2] = (nByL2[n.l2] || 0) + 1; nByL1[n.l1] = (nByL1[n.l1] || 0) + 1; });
      const data = FIELDS.map((f, fi) => {
        const g = groupOf(f);
        return { name: f, itemStyle: { color: t.cat[g] }, children: D.taxonomy.L1.filter((x) => x.field === f).map((l1) => {
          const kids = D.taxonomy.L2.filter((x) => x.l1 === l1.id).map((l2) => ({ name: l2.name, value: nByL2[l2.id] || 1, id: l2.id }));
          const assigned = sum(kids.map((k) => k.value));
          if ((nByL1[l1.id] || 0) > assigned) kids.push({ name: "(세부 미지정)", value: nByL1[l1.id] - assigned, id: "x" + l1.id });
          return { name: l1.name, id: l1.id, children: kids };
        }) };
      });
      o.tooltip.formatter = (p) => `${esc(p.treePathInfo.slice(1).map((x) => x.name).join(" › "))}<br>기술개발소요 <b>${fmt(p.value)}</b>건`;
      o.series = [{ type: "sunburst", data, radius: ["8%", "95%"], sort: null, itemStyle: { borderColor: t.surface, borderWidth: 1.5 },
        label: { color: t.dark ? "#0b1622" : "#ffffff", fontSize: 10.5, minAngle: 6 },
        levels: [{}, { r0: "8%", r: "30%", label: { rotate: "tangential", fontSize: 12, fontWeight: 600 } }, { r0: "30%", r: "62%", itemStyle: { opacity: 0.82 }, label: { align: "right" } }, { r0: "62%", r: "95%", itemStyle: { opacity: 0.6 }, label: { position: "outside", show: false } }] }];
      const c = mk("c-onto", o);
      if (c) c.on("click", (p) => { const id = p.data && p.data.id; if (id && D.L1[id]) l1Side(id); else if (id && D.L2[id]) l1Side(D.L2[id].l1, id); });
    }
  }
  function sideProjects(list) {
    return `<div class="results">${list.map((p) => `<div class="res" data-open="${p.id}" style="cursor:pointer;grid-template-columns:52px minmax(0,1fr)"><div class="score" style="font-size:14px">${p.start || "–"}<small>${p.current ? "현행" : "과거"}</small></div><div class="body"><div class="pname">${esc(p.name)}</div><div class="sub">${esc(p.domain)} · ${p.budget ? fmt(p.budget, 1) + "억" : "–"}</div></div></div>`).join("")}</div>`;
  }
  function conceptSide(cid) {
    const c = D.cc[cid];
    const ps = D.P.filter((p) => p.cc.includes(cid)).sort((a, b) => (b.current - a.current) || ((b.start || 0) - (a.start || 0))).slice(0, 10);
    const nb = D.stats.edges.filter((e) => e.s === cid || e.t === cid).map((e) => [e.s === cid ? e.t : e.s, e.w, e.lift]).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const ns = D.needs.filter((n) => n.cc.includes(cid) && n.status === "○").slice(0, 6);
    const cv = D.civil.filter((x) => x.cc.includes(cid)).slice(0, 5);
    const side = $("#onto-side");
    side.innerHTML = `<div class="eyebrow">Concept · ${esc(c.cat)}</div><h3 style="font-size:18px">${esc(c.name)}</h3>
      <dl class="kv"><dt>언급 과제</dt><dd class="num">${fmt(c.nProj)}</dd><dt>상승지수</dt><dd class="num">×${fmt(c.momentum, 2)}</dd><dt>기술개발소요</dt><dd class="num">${fmt(c.nNeeds)} (미확보 ${fmt(c.nNeedsOpen)})</dd><dt>민간기술</dt><dd class="num">${fmt(c.nCivil)}</dd></dl>
      <div><h3>함께 쓰이는 개념</h3><div class="tags">${nb.map(([id, w]) => `<button class="chip" type="button" data-cc="${id}">${esc(D.cc[id].name)} · ${w}</button>`).join("")}</div></div>
      <div><h3>관련 과제</h3>${sideProjects(ps)}</div>
      ${ns.length ? `<div><h3>미확보 기술개발소요</h3><ul style="margin:0;padding-left:18px">${ns.map((n) => `<li>${esc(n.name)} <span class="sub">· ${esc(n.period)} · ${esc(n.method)}</span></li>`).join("")}</ul></div>` : ""}
      ${cv.length ? `<div><h3>민간보유기술</h3><ul style="margin:0;padding-left:18px">${cv.map((x) => `<li>${esc(x.title)}</li>`).join("")}</ul></div>` : ""}`;
    side.onclick = (ev) => { const a = ev.target.closest("[data-open]"); if (a) return openP(a.dataset.open); const b = ev.target.closest("[data-cc]"); if (b) conceptSide(b.dataset.cc); };
  }
  function l1Side(l1id, l2id) {
    const l1 = D.L1[l1id];
    const ns = D.needs.filter((n) => n.l1 === l1id && (!l2id || n.l2 === l2id));
    const per = {}; ns.forEach((n) => (per[n.period] = (per[n.period] || 0) + 1));
    const ps = D.P.filter((p) => p.l1 === l1id).sort((a, b) => (b.current - a.current) || ((b.start || 0) - (a.start || 0))).slice(0, 10);
    const side = $("#onto-side");
    side.innerHTML = `<div class="eyebrow">${l1.id} · ${esc(l1.field)}</div><h3 style="font-size:18px">${esc(l1.name)}${l2id && D.L2[l2id] ? ` › ${esc(D.L2[l2id].name)}` : ""}</h3>
      <p class="sub" style="margin:0">${esc((l2id && D.L2[l2id] ? D.L2[l2id].desc : l1.desc).slice(0, 260))}</p>
      <dl class="kv"><dt>기술개발소요</dt><dd class="num">${fmt(ns.length)} (미확보 ${fmt(ns.filter((n) => n.status === "○").length)})</dd><dt>시기</dt><dd>${Object.entries(per).map(([k, v]) => `${esc(k)} ${v}`).join(" · ")}</dd><dt>연계 과제</dt><dd class="num">${fmt(D.P.filter((p) => p.l1 === l1id).length)}</dd></dl>
      <div><h3>기술개발소요</h3><ul style="margin:0;padding-left:18px">${ns.slice(0, 14).map((n) => `<li>${esc(n.name)} <span class="sub">· ${esc(n.period)} · ${esc(n.method)} · ${n.status === "●" ? "확보" : "미확보"}</span></li>`).join("")}</ul>${ns.length > 14 ? `<p class="note">외 ${ns.length - 14}건</p>` : ""}</div>
      <div><h3>연계 과제</h3>${ps.length ? sideProjects(ps) : '<p class="note">연계 과제가 없습니다. 신규 기획 후보 영역입니다.</p>'}</div>`;
    side.onclick = (ev) => { const a = ev.target.closest("[data-open]"); if (a) openP(a.dataset.open); };
  }

  /* ---------- 08 forecast ---------- */
  RENDER.forecast = function () {
    const t = T();
    const fc = D.stats.forecast;
    const o = baseOpt(t);
    const P3 = ["단기", "중기", "장기"];
    o.grid = { left: 8, right: 40, top: 28, bottom: 4, containLabel: true };
    o.legend = { top: 0, left: 0, textStyle: { color: t.ink2, fontSize: 12 }, itemWidth: 12, itemHeight: 10 };
    o.xAxis = axisVal(t); o.yAxis = axisCat(t, FIELDS, { inverse: true });
    o.tooltip.trigger = "axis"; o.tooltip.axisPointer = { type: "shadow" };
    o.series = P3.map((k, i) => ({ name: k, type: "bar", stack: "a", data: FIELDS.map((f) => fc[f].byPeriod[k] || 0), barMaxWidth: 16, itemStyle: { color: t.ord3[i], borderColor: t.surface, borderWidth: 1 },
      label: i === 2 ? { show: true, position: "right", fontFamily: t.mono, fontSize: 10.5, color: t.ink2, formatter: (p) => fmt(fc[FIELDS[p.dataIndex]].needs) } : undefined }));
    mk("c-f-pipe", o);
    const yrs = []; for (let y = 2017; y <= 2030; y++) yrs.push(String(y));
    multiples("c-f-trend", FIELDS, yrs, (f) => [
      { data: yrs.map((y) => (+y <= 2026 ? fc[f].starts[y] || 0 : null)), extra: { showSymbol: false } },
      { data: yrs.map((y) => (+y === 2026 ? fc[f].starts[y] || 0 : +y > 2026 ? fc[f].projStarts[y] : null)), dash: true, color: t.muted },
    ], { unit: "건", mark: "2026" });
    const up = Object.values(D.cc).filter((c) => c.nProj >= 12).sort((a, b) => b.momentum - a.momentum).slice(0, 14);
    hbar("c-f-up", up.map((c) => c.name), up.map((c) => +c.momentum.toFixed(2)), { dec: 2, unit: "배", labelW: 150 });
    const G = D.global;
    const rowsUS = FIELDS.map((f) => {
      const ns = G.nssts2026.enabling.filter((x) => x[1] === f).map((x) => x[0]);
      const nd = G.ndsts2023.cta.filter((x) => x[1] === f).map((x) => x[0]);
      const sg = G.signals.items.filter((x) => x[2] === f).length;
      return { f, ns, nd, sg, score: ns.length + nd.length + sg * 0.5 };
    });
    $("#f-us").innerHTML = `<thead><tr><th>분야</th><th>NSSTS 2026 핵심기술</th><th>NDSTS 2023 CTA</th><th class="n">최근 신호</th></tr></thead><tbody>` +
      rowsUS.map((r) => `<tr><td class="pname fname">${esc(r.f)}</td><td>${r.ns.map((x) => `<span class="tag">${esc(x)}</span>`).join(" ") || '<span class="sub">–</span>'}</td><td>${r.nd.map((x) => `<span class="tag">${esc(x)}</span>`).join(" ") || '<span class="sub">–</span>'}</td><td class="n">${r.sg}</td></tr>`).join("") + "</tbody>";
    // summary
    const usMap = Object.fromEntries(rowsUS.map((r) => [r.f, r]));
    const sumRows = FIELDS.map((f) => {
      const s = fc[f];
      const open = sum(Object.values(s.open)), openR = s.needs ? open / s.needs : 0;
      const cur = D.cur.filter((p) => p.stratField === f);
      const curB = sum(cur.map((p) => p.budget));
      const longN = s.byPeriod["장기"] || 0;
      const us = usMap[f].score;
      const civ = s.civil;
      let score = 0; score += openR > 0.8 ? 1 : 0; score += s.slope > 0.3 ? 1 : s.slope < -0.3 ? -1 : 0; score += us >= 2 ? 1 : 0; score += (s.needs / Math.max(1, cur.length)) > 8 ? 1 : 0;
      const verdict = score >= 3 ? ["good", "확대 유력"] : score >= 2 ? ["info", "확대 예상"] : score >= 1 ? ["warn", "선별 추진"] : ["warn", "유지·재편"];
      const ups = Object.values(D.cc).filter((c) => c.cat === f && c.nProj >= 8).sort((a, b) => b.momentum - a.momentum).slice(0, 2).map((c) => c.name);
      const txt = `현행 ${cur.length}개 과제(${fmt(curB)}억) 대비 기술개발소요 ${s.needs}건, 이 중 ${fmt(openR * 100)}%가 미확보이고 장기 소요가 ${longN}건입니다. 신규 착수는 연 ${s.slope >= 0 ? "+" : ""}${fmt(s.slope, 1)}건 추세${ups.length ? `, 상승 개념은 ${ups.join("·")}` : ""}.${civ ? ` 활용 가능한 민간기술 ${civ}건.` : ""}`;
      return { f, verdict, txt, est: s.projStarts["2030"] };
    });
    $("#f-sum").innerHTML = `<thead><tr><th>분야</th><th>전망</th><th class="n">’30 착수 추정</th><th>근거</th></tr></thead><tbody>` +
      sumRows.map((r) => `<tr><td class="pname fname">${esc(r.f)}</td><td><span class="pill ${r.verdict[0]}">${r.verdict[1]}</span></td><td class="n">${fmt(r.est, 0)}건</td><td>${esc(r.txt)}</td></tr>`).join("") + "</tbody>";
    $("#f-sig").innerHTML = G.signals.items.map((x) => `<li><span class="k">${esc(FCODE[x[2]] || "")}</span><span><b>${esc(x[0])}</b><br><span class="sub">${esc(x[1])}</span></span></li>`).join("");
  };

  /* ---------- 09 about ---------- */
  RENDER.about = function () {
    const src = [
      ["’17~’31 / ’18~’32 / ’19~’33 핵심기술기획서(일반본)", "국방기술품질원", "핵심기술과제 목록·개요·기간·8대 기술분야"],
      ["’21~’35 ~ ’26~’40 국방기술기획서(일반본) 6개 판", "국방기술진흥연구소", "과제카드(무기체계·기술분야·개요·연구항목·사업기간·예산·주관·사업구분), ’26판 국방전략기술 표기"],
      ["’26~’40 국방기술기획서 제2장", "국방기술진흥연구소", "10대 분야·30 국방전략기술·99 세부기술·302 구성기술, 기술개발소요 2,068건(시기·추진방안·확보여부, 중복 제거)"],
      ["2025 국방활용가능 민간보유기술", "국방기술진흥연구소", "민간기술 167건(개요·키워드·적용 무기체계·연계 국방전략기술)"],
      ["’26~’30 무기체계 소재·부품 기획서", "국방기술진흥연구소", "착수예상 소재·부품 과제 210건(적용 무기체계·지원금)"],
      ["’25~’34 국방전력지원체계 소요기획서(공개본)", "국방기술진흥연구소", "전력지원체계 분야별 주요 과제(참고)"],
      ["국가별 국방과학기술 수준조사서(요약본, 2024)", "국방기술진흥연구소", "12개국·26개 무기체계 기술수준과 순위(2018·2021·2024)"],
      ["National Security S&T Strategy (2026.8) / National Defense S&T Strategy (2023)", "미 OSTP / 미 국방부", "미국 우선순위 기술 영역"],
      ["국방 AI(AI+IT) 뉴스레터 제74호", "2026.10.4~10", "최근 해외 동향 신호"],
    ];
    $("#src-tbl").innerHTML = `<thead><tr><th>자료</th><th>발간</th><th>추출 내용</th></tr></thead><tbody>` + src.map((r) => `<tr><td class="pname">${esc(r[0])}</td><td class="sub">${esc(r[1])}</td><td>${esc(r[2])}</td></tr>`).join("") + "</tbody>";
    const m = [
      ["추출", "PDF 텍스트 좌표와 표 괘선을 이용해 과제카드·목록을 구조화했습니다. ’26판 카드 461건은 기획서의 분야별 집계(무기체계 10개·기술 6개 분야)와 건수가 일치합니다."],
      ["계보", "과제명 정규화 일치, ‘(구. …)’ 이전 명칭, 연속 판 사이 문자 3-gram 유사도 0.72 이상을 결합해 같은 과제를 하나로 묶었습니다."],
      ["분류", `’26판 국방전략기술 표기와 기술개발소요·민간기술 라벨로 학습한 문자 n-gram 로지스틱 회귀로 이전 판 과제의 분야를 추정했습니다(교차검증 정확도 ${fmt(D.stats.cv * 100)}%, ‘해당없음’ 포함 11개 범주). 추정값은 점선 태그와 * 로 구분합니다.`],
      ["온톨로지", `기술개념 ${D.stats.concepts.length}개를 정규식 사전으로 정의하고 과제·소요·민간기술에 연결했습니다. 개념 간 연결선은 같은 과제에서 4회 이상 함께 등장하고 향상도(lift) 1.3 이상인 쌍입니다.`],
      ["예산", "총사업비를 착수~종료연도에 균등 배분한 추정치입니다. 공개본에 수록되지 않은 과제와 ’17~’19판 예산은 빠져 있습니다."],
      ["중복", "과제명(45%)과 내용(55%)의 문자 2·3-gram TF-IDF 코사인 유사도입니다. 50 이상은 중복 의심, 36~50은 유사로 표시합니다. 최종 판단은 연구항목·목표 성능을 직접 비교해 내려야 합니다."],
      ["갱신", "새 기획서가 나오면 저장소의 scripts/ 파이프라인을 다시 실행해 data/*.json을 재생성하면 됩니다(README 참조)."],
    ];
    $("#method").innerHTML = m.map(([k, v]) => `<li><span class="k">${k}</span><span>${esc(v)}</span></li>`).join("");
  };

  /* ---------- boot ---------- */
  load().then(() => {
    $("#boot").hidden = true;
    show(location.hash.slice(1) || "overview");
  }).catch((e) => {
    $("#boot").textContent = "데이터 파일을 불러오지 못했습니다(" + e.message + "). data 폴더가 index.html과 같은 위치에 있는지 확인하세요.";
  });
})();
