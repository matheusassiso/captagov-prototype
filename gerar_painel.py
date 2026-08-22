"""Gera docs/index.html — painel único, autocontido, com o dado da API embutido.

Mesmo padrão do atf-georadar: roda uma vez, gera um HTML que abre por
duplo-clique (sem Flask, sem porta, sem instalar nada pra quem só quer ver).
Chart.js + Leaflet vêm de CDN (precisa de internet pra carregar essas libs e
os tiles do mapa; o DADO em si já vem embutido, sem fetch nenhum).

Rodar: python gerar_painel.py
"""
import json
from datetime import date
from pathlib import Path

import data_fetch as df

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "index.html"


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
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0f1512;--panel:#16201b;--panel2:#1c2820;--text:#e8ede9;--muted:#93a397;
  --accent:#7fd858;--accent2:#4fa8d8;--border:#26332b;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Inter,sans-serif;line-height:1.5}
header{padding:1.2rem 2rem;border-bottom:1px solid var(--border)}
header h1{margin:0;font-size:1.3rem}
header .sub{color:var(--muted);font-size:.85rem;margin-top:.2rem}
main{max-width:1200px;margin:0 auto;padding:1.5rem 2rem 3rem}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:1.5rem}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem}
.kpi .n{font-size:1.6rem;font-weight:700;color:var(--accent)}
.kpi .l{color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.03em}
.filtros{display:flex;flex-wrap:wrap;gap:.6rem;margin-bottom:1.5rem;align-items:center}
.filtros select,.filtros input{background:var(--panel);color:var(--text);border:1px solid var(--border);
  border-radius:6px;padding:.5rem .7rem;font-size:.85rem}
.filtros input[type=text]{flex:1;min-width:180px}
.btn{background:var(--panel2);color:var(--text);border:1px solid var(--border);border-radius:6px;
  padding:.5rem .8rem;font-size:.85rem;cursor:pointer}
.btn:hover{border-color:var(--accent)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:1rem}
.card h3{margin:0 0 .8rem;font-size:.9rem;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}
#mapa{height:340px;border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--border)}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase}
tr:hover td{background:var(--panel2)}
.acao{color:var(--accent);cursor:pointer;background:none;border:none;font-size:.85rem;padding:0}
.acao:hover{text-decoration:underline}
footer{max-width:1200px;margin:2rem auto;padding:0 2rem 2rem;color:var(--muted);font-size:.78rem}
.modal{display:none;position:fixed;inset:0;background:#000c;z-index:9999;align-items:center;justify-content:center;padding:1.5rem}
.modal.on{display:flex}
.modal-box{background:var(--panel);border:1px solid var(--border);border-radius:10px;max-width:700px;
  width:100%;max-height:85vh;overflow:auto;padding:1.5rem}
.modal-box pre{white-space:pre-wrap;font-size:.85rem;background:var(--panel2);padding:1rem;border-radius:8px}
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
<header>
  <h1>CaptaGov <span style="color:var(--muted);font-weight:400">protótipo</span></h1>
  <div class="sub">Oportunidade de repasse federal aberta x histórico de captação — 10 maiores cidades do MS · gerado em __GERADO_EM__</div>
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
    <div class="card"><h3>Valor histórico captado por cidade</h3><canvas id="chartValor" height="220"></canvas></div>
    <div class="card"><h3>Oportunidade aberta não usada por cidade</h3><canvas id="chartAbertas" height="220"></canvas></div>
  </div>

  <div class="card" style="margin-bottom:1.5rem">
    <h3>Mapa — tamanho do círculo = oportunidade aberta não usada</h3>
    <div id="mapa"></div>
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
const DATA = __DADOS_JSON__;
let filtro = {cidade:"", orgao:"", busca:""};

function fmtBRL(v){return "R$ " + Math.round(v).toLocaleString("pt-BR");}

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
    <div class="kpi"><div class="n">${fmtBRL(totalCaptado)}</div><div class="l">captado historicamente (10 cidades)</div></div>
    <div class="kpi"><div class="n">${DATA.totalProgramasAbertos}</div><div class="l">programas federais abertos agora</div></div>
    <div class="kpi"><div class="n">${totalAbertas}</div><div class="l">oportunidade não usada (soma das 10)</div></div>
    <div class="kpi"><div class="n">${DATA.cidades.length}</div><div class="l">cidades cobertas</div></div>`;
}

let charts = {};
function grafico(id,cfg){ if(charts[id]) charts[id].destroy(); charts[id]=new Chart(document.getElementById(id),cfg); }

function renderCharts(){
  const porValor = DATA.cidades.slice().sort((a,b)=>b.valorTotal-a.valorTotal);
  grafico("chartValor",{type:"bar",data:{labels:porValor.map(c=>c.nome),
    datasets:[{data:porValor.map(c=>c.valorTotal),backgroundColor:"#7fd858"}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:"#93a397"}},y:{ticks:{color:"#93a397",
      callback:v=>"R$"+(v/1e6).toFixed(0)+"M"}}}}});

  const porAbertas = DATA.cidades.slice().sort((a,b)=>b.nAbertas-a.nAbertas);
  grafico("chartAbertas",{type:"bar",data:{labels:porAbertas.map(c=>c.nome),
    datasets:[{data:porAbertas.map(c=>c.nAbertas),backgroundColor:"#4fa8d8"}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:"#93a397"}},y:{ticks:{color:"#93a397"}}}}});
}

let map, marcadores=[];
function renderMapa(){
  if(!map){
    map = L.map("mapa").setView([-20.7,-54.9],6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{attribution:"© OpenStreetMap"}).addTo(map);
  }
  marcadores.forEach(m=>map.removeLayer(m)); marcadores=[];
  DATA.cidades.forEach(c=>{
    const r = 6 + Math.sqrt(c.nAbertas)*5;
    const m = L.circleMarker([c.lat,c.lon],{radius:r,color:"#7fd858",fillColor:"#7fd858",fillOpacity:.5})
      .addTo(map).bindPopup(`<b>${c.nome}</b><br>${c.nAbertas} oportunidade(s) aberta(s)<br>${fmtBRL(c.valorTotal)} captado historicamente`);
    m.on("click",()=>{document.getElementById("fCidade").value=c.ibge; filtro.cidade=String(c.ibge); render();});
    marcadores.push(m);
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

popularFiltros();
render();
</script>
</body>
</html>
"""


def gerar():
    dados = montar_dados()
    dados_json = json.dumps(dados, ensure_ascii=False).replace("</script>", "<\\/script>")
    html = TEMPLATE.replace("__DADOS_JSON__", dados_json).replace("__GERADO_EM__", dados["geradoEm"])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"painel: {OUT} | {len(dados['cidades'])} cidades | {len(dados['oportunidades'])} oportunidades | "
          f"{len(dados['propostas'])} propostas históricas | {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    gerar()
