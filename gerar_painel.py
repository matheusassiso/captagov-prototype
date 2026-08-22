"""Gera docs/index.html — painel único, autocontido, com o dado da API embutido.

Mesmo padrão do atf-georadar: roda uma vez, gera um HTML que abre por
duplo-clique (sem Flask, sem porta, sem instalar nada pra quem só quer ver).
Chart.js vem de CDN (precisa de internet pra carregar essa lib; o DADO e a
malha do mapa em si já vêm embutidos, sem fetch nenhum em tempo de uso).

Rodar: python gerar_painel.py
"""
import json
import math
from datetime import date
from pathlib import Path

import requests

import data_fetch as df

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "index.html"

MALHA_URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/50"
             "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima")
MAPA_LARGURA = 760


def montar_svg_mapa() -> tuple[str, int, int]:
    """Baixa a malha municipal do MS (IBGE, cacheada) e gera <path> SVG por
    município, projetado com correção de latitude (equiretangular simples —
    suficiente pra um estado do tamanho do MS, não precisa de projeção cônica).
    """
    cache_file = df.CACHE_DIR / "malha_ms.json"
    if cache_file.exists():
        malha = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        resp = requests.get(MALHA_URL, timeout=30)
        resp.raise_for_status()
        malha = resp.json()
        df.CACHE_DIR.mkdir(exist_ok=True)
        cache_file.write_text(json.dumps(malha), encoding="utf-8")

    lons, lats = [], []
    for f in malha["features"]:
        geom = f["geometry"]
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for pol in poligonos:
            for anel in pol:
                for lon, lat in anel:
                    lons.append(lon); lats.append(lat)

    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    corr = math.cos(math.radians((lat_min + lat_max) / 2))
    escala = MAPA_LARGURA / ((lon_max - lon_min) * corr)
    altura = round((lat_max - lat_min) * escala)

    def proj(lon, lat):
        x = (lon - lon_min) * corr * escala
        y = (lat_max - lat) * escala
        return f"{x:.1f},{y:.1f}"

    paths = []
    for f in malha["features"]:
        codarea = f["properties"]["codarea"]
        geom = f["geometry"]
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        d = []
        for pol in poligonos:
            for anel in pol:
                d.append("M" + "L".join(proj(lon, lat) for lon, lat in anel) + "Z")
        paths.append(f'<path data-ibge="{codarea}" d="{"".join(d)}"></path>')

    return "\n".join(paths), MAPA_LARGURA, altura


def montar_dados() -> dict:
    programas_abertos = df.get_programas_abertos()

    cidades_out = []
    oportunidades_out = []
    propostas_out = []

    for c in df.CIDADES_MS:
        propostas = df.get_propostas_municipio(c["ibge"])
        gap = df.calcular_gap(c["ibge"], programas_abertos, propostas)
        valor_total = sum(df.valor_proposta(p) for p in propostas)

        cidades_out.append({
            "ibge": c["ibge"],
            "nome": c["nome"],
            "lat": c["lat"],
            "lon": c["lon"],
            "nPropostas": len(propostas),
            "valorTotal": valor_total,
            "nAbertas": len(gap),
        })

        for p in gap:
            detalhe = df.get_programa_detalhe(p["id_programa"])
            oportunidades_out.append({
                "ibgeCidade": c["ibge"],
                "nomeCidade": c["nome"],
                "idPrograma": p["id_programa"],
                "cdPrograma": p.get("cd_programa"),
                "nmPrograma": p.get("nm_programa"),
                "nmEnteRepassador": p.get("nm_ente_repassador"),
                "tpInstrumento": p.get("tp_instrumento"),
                "urlPortal": detalhe["url"] if detalhe else df.url_portal_programa(p["id_programa"]),
                "captacaoInicio": detalhe["captacaoInicio"] if detalhe else None,
                "captacaoFim": detalhe["captacaoFim"] if detalhe else None,
                "condicionantes": detalhe["condicionantes"] if detalhe else [],
                "anexos": detalhe["anexos"] if detalhe else [],
                "minuta": df.gerar_minuta(c["nome"], p),
            })

        for p in propostas:
            objeto = p.get("ds_objeto") or ""
            propostas_out.append({
                "ibgeCidade": c["ibge"],
                "nomeCidade": c["nome"],
                "objeto": objeto[:200],
                "situacao": p.get("situacao_proposta"),
                "valor": df.valor_proposta(p),
                "data": p.get("dt_proposta"),
            })

    orgaos = sorted({o["nmEnteRepassador"] for o in oportunidades_out if o["nmEnteRepassador"]})

    return {
        "geradoEm": date.today().isoformat(),
        "totalProgramasAbertos": len(programas_abertos),
        "cidades": cidades_out,
        "oportunidades": oportunidades_out,
        "propostas": propostas_out,
        "orgaos": orgaos,
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CaptaGov — Oportunidade de repasse federal (MS)</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
/* Paleta base — dourado (padrão), alinhada ao mesmo padrão CityPro/FLORA:
   fundo bem escuro, cards com cantos bem arredondados, badge em pílula. */
:root, :root[data-theme="dourado"]{
  --bg:#120f08;--panel:#1c1710;--panel2:#241d13;--text:#f2ede1;--muted:#a89a7d;
  --accent:#e0a52c;--accent2:#c97f2e;--border:#332a1a;--on-accent:#1c1508;
}
:root[data-theme="verde"]{
  --bg:#0c1a10;--panel:#142819;--panel2:#1b3320;--text:#eaf2e8;--muted:#8fae94;
  --accent:#c9cc4a;--accent2:#4a9660;--border:#22402a;--on-accent:#132008;
}
:root[data-theme="azul"]{
  --bg:#0a121c;--panel:#101d2c;--panel2:#152537;--text:#e7edf5;--muted:#8ba0bb;
  --accent:#4fa3e0;--accent2:#2f6fa8;--border:#1c3348;--on-accent:#071018;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Inter,sans-serif;line-height:1.5;transition:background .2s,color .2s}
header{padding:1.2rem 2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:.6rem}
.brand-mark{width:34px;height:34px;border-radius:10px 10px 10px 2px;background:linear-gradient(135deg,var(--accent),var(--accent2));flex:none}
header h1{margin:0;font-size:1.35rem;font-weight:800;letter-spacing:-.01em}
header .sub{color:var(--muted);font-size:.85rem;margin-top:.15rem}
.temas{display:flex;gap:.4rem;align-items:center;background:var(--panel);border:1px solid var(--border);
  border-radius:999px;padding:.3rem;flex:none}
.temas button{width:22px;height:22px;border-radius:999px;border:2px solid transparent;cursor:pointer;padding:0}
.temas button.on{border-color:var(--text)}
.temas button.t-dourado{background:#e0a52c}
.temas button.t-verde{background:#c9cc4a}
.temas button.t-azul{background:#4fa3e0}
main{max-width:1200px;margin:0 auto;padding:1.5rem 2rem 3rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:1.5rem}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:1.1rem 1.3rem}
.kpi .n{font-size:1.7rem;font-weight:800;color:var(--accent)}
.kpi .l{color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.03em}
.filtros{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:1.5rem;align-items:center}
.filtros select,.filtros input{background:var(--panel);color:var(--text);border:1px solid var(--border);
  border-radius:999px;padding:.5rem .9rem;font-size:.85rem}
.filtros input[type=text]{flex:1;min-width:180px}
.btn{background:var(--accent);color:var(--on-accent);border:none;border-radius:999px;font-weight:700;
  padding:.55rem 1rem;font-size:.85rem;cursor:pointer}
.btn:hover{filter:brightness(1.08)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:1.2rem}
.card-head{display:flex;align-items:center;justify-content:space-between;gap:.6rem;margin-bottom:.8rem}
.card-head h3{margin:0;font-size:.9rem;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;font-weight:700}
.card h3{margin:0 0 .8rem;font-size:.9rem;color:var(--muted);text-transform:uppercase;letter-spacing:.03em;font-weight:700}
.btn-ver{background:none;color:var(--accent);border:1px solid var(--border);border-radius:999px;
  padding:.3rem .8rem;font-size:.75rem;cursor:pointer;flex:none}
.btn-ver:hover{border-color:var(--accent)}
.chart-scroll{overflow-y:auto;overflow-x:hidden}
.mapa-toggle{display:flex;gap:.4rem}
.mapa-toggle .btn-ver.on{background:var(--accent);color:var(--on-accent);border-color:transparent}
#svgMapa{width:100%;height:auto;display:block}
#svgMapa path{stroke:var(--bg);stroke-width:1;cursor:pointer;transition:opacity .15s}
#svgMapa path:hover{opacity:.75}
#svgMapa text.rotulo{fill:var(--text);font-size:9px;font-weight:700;text-anchor:middle;
  pointer-events:none;paint-order:stroke;stroke:var(--bg);stroke-width:3px}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:700;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}
tr:hover td{background:var(--panel2)}
.acao{color:var(--accent);cursor:pointer;background:none;border:none;font-size:.85rem;padding:.15rem .5rem;
  border-radius:999px;font-weight:600}
.acao:hover{background:var(--panel2)}
footer{max-width:1200px;margin:2rem auto;padding:0 2rem 2rem;color:var(--muted);font-size:.78rem}
.modal{display:none;position:fixed;inset:0;background:#000c;z-index:9999;align-items:center;justify-content:center;padding:1.5rem}
.modal.on{display:flex}
.modal-box{background:var(--panel);border:1px solid var(--border);border-radius:20px;max-width:700px;
  width:100%;max-height:85vh;overflow:auto;padding:1.5rem}
.modal-box pre{white-space:pre-wrap;font-size:.85rem;background:var(--panel2);padding:1rem;border-radius:12px}
.modal-close{float:right;background:none;border:none;color:var(--muted);font-size:1.2rem;cursor:pointer}
@media print{
  body *{visibility:hidden}
  .modal-box,.modal-box *{visibility:visible}
  .modal{position:absolute;inset:auto;background:none}
  .modal-close,.no-print{display:none}
}
</style>
</head>
<body>
<script>
(function(){
  try{
    var t = localStorage.getItem("captagov_tema") || "dourado";
    document.documentElement.dataset.theme = t;
  }catch(e){}
})();
</script>
<header>
  <div class="brand">
    <div class="brand-mark"></div>
    <div>
      <h1>CaptaGov <span style="color:var(--muted);font-weight:400">protótipo</span></h1>
      <div class="sub">Oportunidade de repasse federal aberta x histórico de captação — as 79 cidades do MS · gerado em __GERADO_EM__</div>
    </div>
  </div>
  <div class="temas" id="temas" title="Tema">
    <button class="t-dourado" data-tema="dourado" title="Dourado"></button>
    <button class="t-verde" data-tema="verde" title="Verde"></button>
    <button class="t-azul" data-tema="azul" title="Azul"></button>
  </div>
</header>
<main>
  <div class="kpis" id="kpis"></div>

  <div class="filtros">
    <select id="fCidade"><option value="">Todas as cidades</option></select>
    <select id="fOrgao"><option value="">Todos os órgãos</option></select>
    <input type="text" id="fBusca" placeholder="buscar programa...">
    <button class="btn" onclick="exportarCSV()">⬇ CSV</button>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-head">
        <h3>Valor histórico captado por cidade</h3>
        <button class="btn-ver" id="btnVerValor" onclick="alternarChart('valor')">ver todas (79)</button>
      </div>
      <div class="chart-scroll" id="wrapValor"><div id="innerValor"><canvas id="chartValor"></canvas></div></div>
    </div>
    <div class="card">
      <div class="card-head">
        <h3>Oportunidade aberta não usada por cidade</h3>
        <button class="btn-ver" id="btnVerAbertas" onclick="alternarChart('abertas')">ver todas (79)</button>
      </div>
      <div class="chart-scroll" id="wrapAbertas"><div id="innerAbertas"><canvas id="chartAbertas"></canvas></div></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:1.5rem">
    <div class="card-head">
      <h3>Mapa — cor por <span id="mapaTituloMetrica">valor histórico captado</span></h3>
      <div class="mapa-toggle">
        <button class="btn-ver on" data-metrica="valor" onclick="alternarMapa('valor')">Valor captado</button>
        <button class="btn-ver" data-metrica="abertas" onclick="alternarMapa('abertas')">Oportunidade aberta</button>
      </div>
    </div>
    <svg id="svgMapa" viewBox="0 0 __MAPA_LARGURA__ __MAPA_ALTURA__">
__SVG_PATHS__
    </svg>
  </div>

  <div class="card" style="margin-bottom:1.5rem">
    <h3>Oportunidade aberta não usada <span id="contagem" style="color:var(--text);font-weight:400"></span></h3>
    <table>
      <thead><tr><th>Cidade</th><th>Programa</th><th>Órgão repassador</th><th>Instrumento</th><th>Prazo captação</th><th></th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>

  <div class="card" id="cardHistorico" style="display:none">
    <h3>Histórico de propostas — <span id="histCidade"></span></h3>
    <table>
      <thead><tr><th>Objeto</th><th>Situação</th><th>Valor</th><th>Data</th></tr></thead>
      <tbody id="tbodyHist"></tbody>
    </table>
  </div>
</main>
<footer>
  Dado real da API pública Transferegov (api-publica.transferegov.gestao.gov.br), módulo Parcerias,
  cruzado com requisitos/anexos/janela de captação do portal público
  (parcerias.transferegov.sistema.gov.br, sem login). "Oportunidade aberta" = programa com
  situação Disponibilizado e candidatura direta (Espontâneo/Específico) — fora emenda
  parlamentar. Minuta é rascunho automático, não é o formulário oficial de nenhum órgão repassador.
</footer>

<div class="modal" id="modal">
  <div class="modal-box">
    <button class="modal-close no-print" onclick="fecharModal()">✕</button>
    <div id="modalBody"></div>
    <button class="btn no-print" style="margin-top:1rem" onclick="window.print()">🖨 Imprimir / salvar PDF</button>
  </div>
</div>

<script>
Chart.defaults.animation = false; // sem animação de entrada — pinta na hora, não depende de requestAnimationFrame
const DATA = __DADOS_JSON__;
let filtro = {cidade:"", orgao:"", busca:""};

function fmtBRL(v){return "R$ " + Math.round(v).toLocaleString("pt-BR");}

function aplicarTema(t){
  document.documentElement.dataset.theme = t;
  try{ localStorage.setItem("captagov_tema", t); }catch(e){}
  document.querySelectorAll("#temas button").forEach(b=>b.classList.toggle("on", b.dataset.tema===t));
  renderCharts(); renderMapa(); // cores dependem do tema, Canvas/SVG não leem var(--accent) sozinhos
}
document.querySelectorAll("#temas button").forEach(b=>b.onclick=()=>aplicarTema(b.dataset.tema));

function popularFiltros(){
  const selCidade = document.getElementById("fCidade");
  DATA.cidades.slice().sort((a,b)=>a.nome.localeCompare(b.nome)).forEach(c=>{
    const o = document.createElement("option"); o.value=c.ibge; o.textContent=c.nome; selCidade.appendChild(o);
  });
  const selOrgao = document.getElementById("fOrgao");
  DATA.orgaos.forEach(o=>{
    const opt = document.createElement("option"); opt.value=o; opt.textContent=o.length>50?o.slice(0,50)+"…":o;
    selOrgao.appendChild(opt);
  });
  selCidade.onchange = ()=>{filtro.cidade=selCidade.value; render();};
  selOrgao.onchange = ()=>{filtro.orgao=selOrgao.value; render();};
  document.getElementById("fBusca").oninput = (e)=>{filtro.busca=e.target.value.toLowerCase(); render();};
}

function oportunidadesFiltradas(){
  return DATA.oportunidades.filter(o=>
    (!filtro.cidade || String(o.ibgeCidade)===String(filtro.cidade)) &&
    (!filtro.orgao || o.nmEnteRepassador===filtro.orgao) &&
    (!filtro.busca || (o.nmPrograma||"").toLowerCase().includes(filtro.busca))
  );
}

function renderKpis(){
  const totalCaptado = DATA.cidades.reduce((s,c)=>s+c.valorTotal,0);
  const totalAbertas = DATA.cidades.reduce((s,c)=>s+c.nAbertas,0);
  document.getElementById("kpis").innerHTML = `
    <div class="kpi"><div class="n">${fmtBRL(totalCaptado)}</div><div class="l">captado historicamente (${DATA.cidades.length} cidades)</div></div>
    <div class="kpi"><div class="n">${DATA.totalProgramasAbertos}</div><div class="l">programas federais abertos agora</div></div>
    <div class="kpi"><div class="n">${totalAbertas}</div><div class="l">oportunidade não usada (soma de todas)</div></div>
    <div class="kpi"><div class="n">${DATA.cidades.length}</div><div class="l">cidades cobertas</div></div>`;
}

function corTema(nomeVar){
  return getComputedStyle(document.documentElement).getPropertyValue(nomeVar).trim();
}

// Barra horizontal expandida rola dentro de uma caixa curta — o eixo de valor (embaixo do
// canvas inteiro) só apareceria depois de rolar tudo até o fim. Em vez de tentar deixar o
// eixo "grudado" (canvas é um desenho só, não dá pra fixar só um pedaço), desenha o valor
// direto do lado de cada barra — sempre visível junto da barra, não depende de rolar até o eixo.
//
// ponytail: nada disso passa pelo sistema de plugin do Chart.js (Chart.register) — QUALQUER
// leitura de chart.options.plugins.<id> (mesmo dentro do próprio Chart.js resolvendo as
// options do hook antes de chamar) lança "Cannot convert object to primitive value" pra um
// plugin não-nativo, e a lib engole essa exceção sozinha — o hook nunca roda, sem erro
// nenhum no console. Mais simples e confiável: desenha direto por cima logo depois que o
// gráfico é criado, e de novo se ele for redimensionado (onResize é uma option normal,
// não passa por options.plugins, não tem esse problema).
const FORMATOS_ROTULO = {
  moeda: v => "R$"+(v/1e6).toFixed(0)+"M",
  numero: v => v,
};
function desenharRotulosBarra(chart, tipoRotulo){
  const fmt = FORMATOS_ROTULO[tipoRotulo];
  if(!fmt) return;
  const {ctx} = chart;
  ctx.save();
  ctx.fillStyle = corTema("--text");
  ctx.font = "11px -apple-system,Segoe UI,sans-serif";
  ctx.textBaseline = "middle";
  chart.getDatasetMeta(0).data.forEach((barra,i)=>{
    ctx.fillText(fmt(chart.data.datasets[0].data[i]), barra.x+6, barra.y);
  });
  ctx.restore();
}

let charts = {};
function grafico(id,cfg,tipoRotulo){
  if(charts[id]) charts[id].destroy();
  if(tipoRotulo) cfg.options.onResize = c => desenharRotulosBarra(c, tipoRotulo);
  charts[id]=new Chart(document.getElementById(id),cfg);
  if(tipoRotulo) desenharRotulosBarra(charts[id], tipoRotulo);
}

let chartState = {valor:false, abertas:false}; // false = top 10 (colunas), true = todas (barra horizontal, com rolagem)
function alternarChart(qual){ chartState[qual] = !chartState[qual]; renderCharts(); }

function desenharChart(canvasId, wrapId, innerId, btnId, expandido, ordenado, valorFn, cor, fmtEixo, tipoRotulo){
  const muted = corTema("--muted");
  const lista = expandido ? ordenado : ordenado.slice(0,10);
  const wrap = document.getElementById(wrapId), inner = document.getElementById(innerId);
  document.getElementById(btnId).textContent = expandido ? "ver top 10" : `ver todas (${ordenado.length})`;

  if(expandido){
    // outer (wrap) fica com altura fixa + scroll; inner recebe a altura real do conteúdo —
    // se as duas alturas ficam no mesmo elemento o Chart.js lê o tamanho já cortado pelo
    // max-height e comprime tudo (autoSkip esconde a maioria dos rótulos).
    wrap.style.height = "480px";
    inner.style.height = Math.max(480, lista.length*24) + "px";
    grafico(canvasId,{type:"bar",data:{labels:lista.map(c=>c.nome),
      datasets:[{data:lista.map(valorFn),backgroundColor:cor}]},
      options:{indexAxis:"y",maintainAspectRatio:false,
        layout:{padding:{right:60}},
        plugins:{legend:{display:false}},
        scales:{x:{ticks:{color:muted,callback:fmtEixo}},
          y:{ticks:{color:muted,autoSkip:false}}}}}, tipoRotulo);
  }else{
    wrap.style.height = "260px";
    inner.style.height = "260px";
    grafico(canvasId,{type:"bar",data:{labels:lista.map(c=>c.nome),
      datasets:[{data:lista.map(valorFn),backgroundColor:cor}]},
      options:{maintainAspectRatio:false,
        plugins:{legend:{display:false}},
        scales:{x:{ticks:{color:muted}},y:{ticks:{color:muted,callback:fmtEixo}}}}});
  }
}

function renderCharts(){
  const accent = corTema("--accent"), accent2 = corTema("--accent2");
  desenharChart("chartValor","wrapValor","innerValor","btnVerValor",chartState.valor,
    DATA.cidades.slice().sort((a,b)=>b.valorTotal-a.valorTotal),
    c=>c.valorTotal, accent, v=>"R$"+(v/1e6).toFixed(0)+"M", "moeda");
  desenharChart("chartAbertas","wrapAbertas","innerAbertas","btnVerAbertas",chartState.abertas,
    DATA.cidades.slice().sort((a,b)=>b.nAbertas-a.nAbertas),
    c=>c.nAbertas, accent2, v=>v, "numero");
}

function hexParaRgb(hex){
  hex = hex.replace("#","");
  if(hex.length===3) hex = hex.split("").map(c=>c+c).join("");
  const n = parseInt(hex,16);
  return [(n>>16)&255,(n>>8)&255,n&255];
}
function misturarCor(hexA,hexB,t){
  const a=hexParaRgb(hexA), b=hexParaRgb(hexB);
  const m = a.map((v,i)=>Math.round(v+(b[i]-v)*t));
  return `rgb(${m[0]},${m[1]},${m[2]})`;
}

let mapaMetrica = "valor"; // "valor" ou "abertas"
function alternarMapa(m){
  mapaMetrica = m;
  document.querySelectorAll(".mapa-toggle button").forEach(b=>b.classList.toggle("on", b.dataset.metrica===m));
  document.getElementById("mapaTituloMetrica").textContent =
    m==="valor" ? "valor histórico captado" : "oportunidade aberta não usada";
  renderMapa();
}

function renderMapa(){
  const svg = document.getElementById("svgMapa");
  const panel2 = corTema("--panel2"), accent = corTema("--accent");
  const porIbge = {}; DATA.cidades.forEach(c=>porIbge[c.ibge]=c);
  const valorDe = c => mapaMetrica==="valor" ? c.valorTotal : c.nAbertas;
  const max = Math.max(...DATA.cidades.map(valorDe), 1);

  svg.querySelectorAll("path").forEach(p=>{
    const c = porIbge[p.dataset.ibge];
    const v = c ? valorDe(c) : 0;
    const t = Math.sqrt(v/max); // raiz quadrada realça diferença entre cidade pequena e Campo Grande
    p.setAttribute("fill", misturarCor(panel2, accent, t));
    p.onclick = c ? ()=>{ document.getElementById("fCidade").value=c.ibge; filtro.cidade=String(c.ibge); render(); } : null;
    let title = p.querySelector("title");
    if(!title){ title = document.createElementNS("http://www.w3.org/2000/svg","title"); p.appendChild(title); }
    title.textContent = c ? `${c.nome}: ${mapaMetrica==="valor"?fmtBRL(c.valorTotal):c.nAbertas+" oportunidade(s) aberta(s)"}` : "";
  });

  svg.querySelectorAll("text.rotulo").forEach(t=>t.remove());
  const top10 = DATA.cidades.slice().sort((a,b)=>valorDe(b)-valorDe(a)).slice(0,10);
  top10.forEach(c=>{
    const path = svg.querySelector(`path[data-ibge="${c.ibge}"]`);
    if(!path) return;
    const bbox = path.getBBox();
    const t = document.createElementNS("http://www.w3.org/2000/svg","text");
    t.setAttribute("class","rotulo");
    t.setAttribute("x", bbox.x+bbox.width/2);
    t.setAttribute("y", bbox.y+bbox.height/2);
    t.textContent = mapaMetrica==="valor" ? "R$"+(c.valorTotal/1e6).toFixed(0)+"M" : c.nAbertas;
    svg.appendChild(t);
  });
}

function renderTabela(){
  const linhas = oportunidadesFiltradas();
  document.getElementById("contagem").textContent = `(${linhas.length})`;
  document.getElementById("tbody").innerHTML = linhas.map((o,i)=>`<tr>
    <td>${o.nomeCidade}</td><td>${o.nmPrograma||""}</td><td>${o.nmEnteRepassador||""}</td>
    <td>${o.tpInstrumento||""}</td>
    <td>${o.captacaoFim||"-"}</td>
    <td style="white-space:nowrap">
      <button class="acao" onclick="abrirFicha(${DATA.oportunidades.indexOf(o)})">📋 ficha</button>
      &nbsp;<a class="acao" href="${o.urlPortal}" target="_blank" rel="noopener">🔗 edital</a>
    </td></tr>`).join("");
}

function abrirFicha(i){
  const o = DATA.oportunidades[i];
  document.getElementById("modalBody").innerHTML =
    `<h2>${o.nmPrograma}</h2><p style="color:var(--muted)">${o.nomeCidade} - MS</p>
     <p class="no-print"><a href="${o.urlPortal}" target="_blank" rel="noopener">🔗 abrir programa no Transferegov.br</a></p>
     <pre>${o.minuta}</pre>`;
  document.getElementById("modal").classList.add("on");
}
function fecharModal(){ document.getElementById("modal").classList.remove("on"); }

function exportarCSV(){
  const linhas = oportunidadesFiltradas();
  const cab = ["cidade","programa","codigo","orgao_repassador","instrumento","prazo_captacao","link_edital"];
  const corpo = linhas.map(o=>[o.nomeCidade,o.nmPrograma,o.cdPrograma,o.nmEnteRepassador,o.tpInstrumento,o.captacaoFim,o.urlPortal]
    .map(v=>`"${String(v||"").replace(/"/g,'""')}"`).join(";"));
  const csv = "﻿"+[cab.join(";"),...corpo].join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8;"}));
  a.download = `captagov-oportunidades-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

function renderHistorico(){
  const bloco = document.getElementById("cardHistorico");
  if(!filtro.cidade){ bloco.style.display="none"; return; }
  const c = DATA.cidades.find(c=>String(c.ibge)===String(filtro.cidade));
  const linhas = DATA.propostas.filter(p=>String(p.ibgeCidade)===String(filtro.cidade));
  bloco.style.display = "";
  document.getElementById("histCidade").textContent = `${c.nome} (${linhas.length} proposta(s))`;
  document.getElementById("tbodyHist").innerHTML = linhas.slice(0,50).map(p=>`<tr>
    <td>${p.objeto}${p.objeto.length>=200?"…":""}</td><td>${p.situacao||""}</td>
    <td>${fmtBRL(p.valor)}</td><td>${p.data||""}</td></tr>`).join("");
}

function render(){ renderKpis(); renderCharts(); renderMapa(); renderTabela(); renderHistorico(); }

document.querySelectorAll("#temas button").forEach(b=>
  b.classList.toggle("on", b.dataset.tema===(document.documentElement.dataset.theme||"dourado")));
popularFiltros();
render();
</script>
</body>
</html>
"""


def gerar():
    dados = montar_dados()
    dados_json = json.dumps(dados, ensure_ascii=False).replace("</script>", "<\\/script>")
    svg_paths, largura, altura = montar_svg_mapa()
    html = (TEMPLATE
            .replace("__DADOS_JSON__", dados_json)
            .replace("__GERADO_EM__", dados["geradoEm"])
            .replace("__SVG_PATHS__", svg_paths)
            .replace("__MAPA_LARGURA__", str(largura))
            .replace("__MAPA_ALTURA__", str(altura)))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"painel: {OUT} | {len(dados['cidades'])} cidades | {len(dados['oportunidades'])} oportunidades | "
          f"{len(dados['propostas'])} propostas históricas | {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    gerar()
