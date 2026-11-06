(async function () {
  const CATS = {
    virada_contra: { rot: "Liderou no 1º, perdeu no 2º", cor: "--virada" },
    manteve: { rot: "Liderou nos dois turnos", cor: "--manteve" },
    virada_a_favor: { rot: "Não liderou no 1º, venceu no 2º", cor: "--afavor" },
    perdeu_ambos: { rot: "Não liderou no 1º, perdeu no 2º", cor: "--ambos" },
    empate_2t: { rot: "Empate no 2º turno", cor: "--empate" },
  };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmtN = (n) => n.toLocaleString("pt-BR");
  const fmtP = (n) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
  const fmtD = (n) => (n > 0 ? "+" : "") + n.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " p.p.";

  let topo, dados;
  try {
    [topo, dados] = await Promise.all([
      d3.json("data/municipios.topojson"),
      d3.json("data/municipios.json"),
    ]);
  } catch (e) {
    document.querySelector("main").innerHTML =
      '<p class="aviso">Dados ainda não gerados. Rode <code>python scripts/processar.py</code> para criar <code>web/data/municipios.json</code>.</p>';
    return;
  }

  // Métricas derivadas
  const M = dados.municipios;
  for (const [id, r] of Object.entries(M)) {
    r.id = id;
    r.p1 = (r.f1 / r.v1) * 100;
    r.p2 = (r.f2 / r.v2) * 100;
    r.m1 = ((r.f1 - r.l1) / (r.f1 + r.l1)) * 100;
    r.m2 = ((r.f2 - r.l2) / (r.f2 + r.l2)) * 100;
    r.dm = r.m2 - r.m1;
  }
  document.getElementById("fonte").textContent =
    `Fonte: ${dados.fonte} (referência ${dados.data_referencia}); malha municipal IBGE.`;

  // KPIs
  const viradas = Object.values(M).filter((r) => r.c === "virada_contra");
  const totV2 = d3.sum(Object.values(M), (r) => r.v2);
  const vV2 = d3.sum(viradas, (r) => r.v2);
  document.getElementById("k-n").textContent = fmtN(viradas.length);
  document.getElementById("k-v").textContent = fmtN(vV2);
  document.getElementById("k-p").textContent = fmtP((vV2 / totV2) * 100);

  // Mapa
  const W = 800, H = 800;
  const svg = d3.select("#mapa").attr("viewBox", `0 0 ${W} ${H}`);
  const obj = topo.objects[Object.keys(topo.objects)[0]];
  // D3 usa orientação esférica: anéis no sentido "errado" viram o globo inteiro.
  const rewind = (geo) => {
    if (geo && d3.geoArea(geo) > 2 * Math.PI) {
      const rev = (polys) => polys.map((rings) => rings.map((r) => r.slice().reverse()));
      if (geo.type === "Polygon") geo.coordinates = rev([geo.coordinates])[0];
      if (geo.type === "MultiPolygon") geo.coordinates = rev(geo.coordinates);
    }
    return geo;
  };
  const feats = topojson.feature(topo, obj).features;
  feats.forEach((f) => rewind(f.geometry));
  const proj = d3.geoMercator().fitSize([W, H], { type: "FeatureCollection", features: feats });
  const path = d3.geoPath(proj);
  const g = svg.append("g");

  let modo = "destaque";
  const cor = (f) => {
    const r = M[f.id];
    if (!r) return css("--semdado");
    if (modo === "destaque") return r.c === "virada_contra" ? css("--virada") : css("--apagado");
    return css(CATS[r.c].cor);
  };

  const tip = document.getElementById("tooltip");
  const wrap = document.querySelector(".mapa-wrap");
  const paths = g.selectAll("path").data(feats).join("path")
    .attr("d", path).attr("fill", cor)
    .on("mousemove", (ev, f) => {
      const r = M[f.id];
      tip.hidden = false;
      tip.innerHTML = r
        ? `<b>${r.n} – ${r.uf}</b>${CATS[r.c].rot}<br>
           1º turno: Flávio ${fmtP(r.p1)} · Lula ${fmtP((r.l1 / r.v1) * 100)}<br>
           2º turno: Flávio ${fmtP(r.p2)} · Lula ${fmtP((r.l2 / r.v2) * 100)}<br>
           Margem Flávio×Lula: ${fmtD(r.m1)} → ${fmtD(r.m2)}<br>
           Válidos 2º turno: ${fmtN(r.v2)}`
        : "<b>Sem dados</b>";
      const b = wrap.getBoundingClientRect();
      let x = ev.clientX - b.left + 12, y = ev.clientY - b.top + 12;
      if (x + 260 > b.width) x -= 280;
      tip.style.left = x + "px"; tip.style.top = y + "px";
    })
    .on("mouseleave", () => (tip.hidden = true));

  // Contorno dos estados (agrupando por 2 primeiros dígitos do código IBGE)
  const ufs = d3.group(obj.geometries, (gm) => String(gm.id).slice(0, 2));
  for (const geoms of ufs.values()) {
    g.append("path").attr("class", "uf").attr("d", path(rewind(topojson.merge(topo, geoms))));
  }

  svg.call(d3.zoom().scaleExtent([1, 12]).on("zoom", (ev) => g.attr("transform", ev.transform)));

  function legenda() {
    const itens = modo === "destaque"
      ? [["virada_contra", css("--virada")], ["outros", css("--apagado")]]
      : Object.keys(CATS).map((k) => [k, css(CATS[k].cor)]);
    d3.select("#legenda").selectAll("li").data(itens).join("li")
      .html(([k, c]) => `<i style="background:${c}"></i>${k === "outros" ? "Demais municípios" : CATS[k].rot}`);
  }
  legenda();
  document.querySelectorAll('input[name="modo"]').forEach((el) =>
    el.addEventListener("change", (e) => { modo = e.target.value; paths.attr("fill", cor); legenda(); }));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { paths.attr("fill", cor); legenda(); });

  // Tabela
  const selUF = document.getElementById("uf");
  [...new Set(viradas.map((r) => r.uf))].sort().forEach((u) => selUF.add(new Option(u, u)));
  let ordem = { k: "dm", asc: true };
  function tabela() {
    const q = document.getElementById("busca").value.trim().toLowerCase();
    const linhas = viradas
      .filter((r) => (!selUF.value || r.uf === selUF.value) && (!q || r.n.toLowerCase().includes(q)))
      .sort((a, b) => {
        const va = a[ordem.k], vb = b[ordem.k];
        const c = typeof va === "string" ? va.localeCompare(vb, "pt-BR") : va - vb;
        return ordem.asc ? c : -c;
      });
    d3.select("#tabela tbody").selectAll("tr").data(linhas, (r) => r.id).join("tr")
      .html((r) => `<td>${r.n}</td><td>${r.uf}</td><td class="num">${fmtP(r.p1)}</td>
                    <td class="num">${fmtP(r.p2)}</td><td class="num">${fmtD(r.dm)}</td>`)
      .on("mouseenter", function (_, r) {
        this.classList.add("sel");
        paths.filter((f) => f.id === r.id).attr("stroke", css("--fg")).attr("stroke-width", 1.5).raise();
      })
      .on("mouseleave", function (_, r) {
        this.classList.remove("sel");
        paths.filter((f) => f.id === r.id).attr("stroke", null).attr("stroke-width", null);
      });
  }
  tabela();
  selUF.addEventListener("change", tabela);
  document.getElementById("busca").addEventListener("input", tabela);
  document.querySelectorAll("#tabela th").forEach((th) => th.addEventListener("click", () => {
    const k = th.dataset.k;
    ordem = { k, asc: ordem.k === k ? !ordem.asc : true };
    tabela();
  }));
})();
