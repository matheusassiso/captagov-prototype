"""Busca e cacheia dados da API pública do Transferegov (módulo Parcerias / ex-SICONV).

Documentação: https://api-publica.transferegov.gestao.gov.br/parcerias/docs
Sem autenticação, público, JSON.
"""
import json
import time
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://api-publica.transferegov.gestao.gov.br/parcerias"
# Portal público (SPA) — mesmo dado do BASE_URL, mas com requisitos/anexos/janela real
# de captação que a API de dados abertos não expõe. Também sem autenticação.
PORTAL_API = "https://parcerias.transferegov.sistema.gov.br/ep/api/atos-prep"
PORTAL_URL_PROGRAMA = "https://parcerias.transferegov.sistema.gov.br/ep-atos-prep-web/atos-prep/programa/detalhamento/{id}"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h — dado do governo não muda a cada minuto

# ponytail: as 79 cidades do MS (IBGE) + centroide calculado da malha municipal
# (média dos vértices do polígono — não é o centroide geométrico exato, mas é
# suficiente pra posicionar um marcador no mapa). Trocar de estado = gerar essa
# lista de novo pra outra UF (ver README).
CIDADES_MS = [
    {"ibge": 5000252, "nome": "Alcinópolis", "lat": -18.206853, "lon": -53.75745},
    {"ibge": 5000609, "nome": "Amambai", "lat": -23.148549, "lon": -54.974507},
    {"ibge": 5000708, "nome": "Anastácio", "lat": -20.764206, "lon": -55.71863},
    {"ibge": 5000807, "nome": "Anaurilândia", "lat": -22.117633, "lon": -52.773968},
    {"ibge": 5000856, "nome": "Angélica", "lat": -22.039616, "lon": -53.861178},
    {"ibge": 5000906, "nome": "Antônio João", "lat": -22.20401, "lon": -55.950195},
    {"ibge": 5001003, "nome": "Aparecida do Taboado", "lat": -20.010276, "lon": -51.357053},
    {"ibge": 5001102, "nome": "Aquidauana", "lat": -19.818067, "lon": -55.871687},
    {"ibge": 5001243, "nome": "Aral Moreira", "lat": -22.909628, "lon": -55.363259},
    {"ibge": 5001508, "nome": "Bandeirantes", "lat": -19.818811, "lon": -54.308761},
    {"ibge": 5001904, "nome": "Bataguassu", "lat": -21.773176, "lon": -52.594087},
    {"ibge": 5002001, "nome": "Batayporã", "lat": -22.469162, "lon": -53.186529},
    {"ibge": 5002100, "nome": "Bela Vista", "lat": -22.025152, "lon": -56.565135},
    {"ibge": 5002159, "nome": "Bodoquena", "lat": -20.468158, "lon": -56.655816},
    {"ibge": 5002209, "nome": "Bonito", "lat": -20.906411, "lon": -56.325131},
    {"ibge": 5002308, "nome": "Brasilândia", "lat": -21.106269, "lon": -52.436051},
    {"ibge": 5002407, "nome": "Caarapó", "lat": -22.607218, "lon": -54.824843},
    {"ibge": 5002605, "nome": "Camapuã", "lat": -19.341531, "lon": -53.857928},
    {"ibge": 5002704, "nome": "Campo Grande", "lat": -20.964366, "lon": -54.212556},
    {"ibge": 5002803, "nome": "Caracol", "lat": -21.958418, "lon": -57.117881},
    {"ibge": 5002902, "nome": "Cassilândia", "lat": -19.078351, "lon": -52.087947},
    {"ibge": 5002951, "nome": "Chapadão do Sul", "lat": -19.074612, "lon": -52.680286},
    {"ibge": 5003108, "nome": "Corguinho", "lat": -19.844553, "lon": -54.989366},
    {"ibge": 5003157, "nome": "Coronel Sapucaia", "lat": -23.325337, "lon": -55.384809},
    {"ibge": 5003207, "nome": "Corumbá", "lat": -18.796087, "lon": -56.888975},
    {"ibge": 5003256, "nome": "Costa Rica", "lat": -18.535308, "lon": -53.248173},
    {"ibge": 5003306, "nome": "Coxim", "lat": -18.229556, "lon": -54.689318},
    {"ibge": 5003454, "nome": "Deodápolis", "lat": -22.085784, "lon": -54.199792},
    {"ibge": 5003488, "nome": "Dois Irmãos do Buriti", "lat": -20.557657, "lon": -55.358961},
    {"ibge": 5003504, "nome": "Douradina", "lat": -21.992727, "lon": -54.578849},
    {"ibge": 5003702, "nome": "Dourados", "lat": -22.138535, "lon": -54.826794},
    {"ibge": 5003751, "nome": "Eldorado", "lat": -23.754553, "lon": -54.224388},
    {"ibge": 5003900, "nome": "Figueirão", "lat": -18.719493, "lon": -53.911527},
    {"ibge": 5003801, "nome": "Fátima do Sul", "lat": -22.330296, "lon": -54.463384},
    {"ibge": 5004007, "nome": "Glória de Dourados", "lat": -22.48224, "lon": -54.095144},
    {"ibge": 5004106, "nome": "Guia Lopes da Laguna", "lat": -21.630647, "lon": -55.928219},
    {"ibge": 5004304, "nome": "Iguatemi", "lat": -23.423712, "lon": -54.558843},
    {"ibge": 5004403, "nome": "Inocência", "lat": -19.675714, "lon": -52.055242},
    {"ibge": 5004502, "nome": "Itaporã", "lat": -21.937305, "lon": -54.832904},
    {"ibge": 5004601, "nome": "Itaquiraí", "lat": -23.318251, "lon": -54.094184},
    {"ibge": 5004700, "nome": "Ivinhema", "lat": -22.390538, "lon": -53.786551},
    {"ibge": 5004809, "nome": "Japorã", "lat": -23.793707, "lon": -54.545193},
    {"ibge": 5004908, "nome": "Jaraguari", "lat": -20.26435, "lon": -54.266391},
    {"ibge": 5005004, "nome": "Jardim", "lat": -21.639275, "lon": -56.263786},
    {"ibge": 5005103, "nome": "Jateí", "lat": -22.742671, "lon": -53.844664},
    {"ibge": 5005152, "nome": "Juti", "lat": -22.833599, "lon": -54.505782},
    {"ibge": 5005202, "nome": "Ladário", "lat": -19.095786, "lon": -57.560749},
    {"ibge": 5005251, "nome": "Laguna Carapã", "lat": -22.699342, "lon": -55.088551},
    {"ibge": 5005400, "nome": "Maracaju", "lat": -21.441721, "lon": -55.542036},
    {"ibge": 5005608, "nome": "Miranda", "lat": -20.201974, "lon": -56.506986},
    {"ibge": 5005681, "nome": "Mundo Novo", "lat": -23.915814, "lon": -54.277647},
    {"ibge": 5005707, "nome": "Naviraí", "lat": -23.079432, "lon": -54.029454},
    {"ibge": 5005806, "nome": "Nioaque", "lat": -21.188289, "lon": -55.770121},
    {"ibge": 5006002, "nome": "Nova Alvorada do Sul", "lat": -21.489291, "lon": -54.171276},
    {"ibge": 5006200, "nome": "Nova Andradina", "lat": -21.869127, "lon": -53.461885},
    {"ibge": 5006259, "nome": "Novo Horizonte do Sul", "lat": -22.617639, "lon": -53.760159},
    {"ibge": 5006309, "nome": "Paranaíba", "lat": -19.524856, "lon": -51.38319},
    {"ibge": 5006358, "nome": "Paranhos", "lat": -23.706573, "lon": -55.32562},
    {"ibge": 5006275, "nome": "Paraíso das Águas", "lat": -19.251088, "lon": -53.127706},
    {"ibge": 5006408, "nome": "Pedro Gomes", "lat": -17.827703, "lon": -54.156979},
    {"ibge": 5006606, "nome": "Ponta Porã", "lat": -22.014776, "lon": -55.715233},
    {"ibge": 5006903, "nome": "Porto Murtinho", "lat": -21.240472, "lon": -57.380001},
    {"ibge": 5007109, "nome": "Ribas do Rio Pardo", "lat": -20.691444, "lon": -53.578749},
    {"ibge": 5007208, "nome": "Rio Brilhante", "lat": -21.753672, "lon": -54.457931},
    {"ibge": 5007307, "nome": "Rio Negro", "lat": -19.44827, "lon": -54.995929},
    {"ibge": 5007406, "nome": "Rio Verde de Mato Grosso", "lat": -18.871587, "lon": -54.916564},
    {"ibge": 5007505, "nome": "Rochedo", "lat": -20.001403, "lon": -54.769732},
    {"ibge": 5007554, "nome": "Santa Rita do Pardo", "lat": -21.35069, "lon": -52.707745},
    {"ibge": 5007802, "nome": "Selvíria", "lat": -20.249337, "lon": -51.82126},
    {"ibge": 5007703, "nome": "Sete Quedas", "lat": -23.84922, "lon": -54.99916},
    {"ibge": 5007901, "nome": "Sidrolândia", "lat": -21.027752, "lon": -54.986637},
    {"ibge": 5007935, "nome": "Sonora", "lat": -17.689698, "lon": -54.413561},
    {"ibge": 5007695, "nome": "São Gabriel do Oeste", "lat": -19.129542, "lon": -54.448679},
    {"ibge": 5007950, "nome": "Tacuru", "lat": -23.678209, "lon": -54.940902},
    {"ibge": 5007976, "nome": "Taquarussu", "lat": -22.714342, "lon": -53.455745},
    {"ibge": 5008008, "nome": "Terenos", "lat": -20.420979, "lon": -55.100728},
    {"ibge": 5008305, "nome": "Três Lagoas", "lat": -20.377427, "lon": -52.247479},
    {"ibge": 5008404, "nome": "Vicentina", "lat": -22.515844, "lon": -54.46336},
    {"ibge": 5000203, "nome": "Água Clara", "lat": -20.07717, "lon": -52.83504},
]


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def _cached_get_url(url: str, params: dict, cache_key: str) -> dict | None:
    cache_file = _cache_path(cache_key)
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < CACHE_TTL_SECONDS:
        return json.loads(cache_file.read_text(encoding="utf-8"))

    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def _cached_get(path: str, params: dict, cache_key: str) -> dict:
    return _cached_get_url(f"{BASE_URL}{path}", params, cache_key)


def get_todos_programas() -> list[dict]:
    """Todos os programas cadastrados (abertos, em elaboração, inativos — os 176).
    Usado pra resolver nome do órgão repassador de proposta antiga cujo programa
    já não está mais aberto hoje.

    ponytail: só existem ~176 programas no total, cabem numa página. Se a API
    crescer muito isso precisa virar paginação de verdade.
    """
    data = _cached_get("/programa", {"tamanho_da_pagina": 200, "pagina": 1}, "programas_p1")
    return data["data"]


def get_programas_abertos() -> list[dict]:
    """Programas com situação 'Disponibilizado' e que aceitam candidatura direta
    (Beneficiário Espontâneo ou Específico) — não depende de indicação de parlamentar.
    """
    programas = get_todos_programas()
    diretos = [
        p for p in programas
        if p.get("situacao_programa") == "Disponibilizado"
        and p.get("qualificacao_beneficiario") in ("Beneficiário Espontâneo", "Beneficiário Específico")
    ]
    return diretos


def get_propostas_municipio(cd_ibge: int) -> list[dict]:
    """Propostas já enviadas por um município (histórico de captação).

    ponytail: cap de 200 por página cobre as 10 cidades do MS (a maior, Campo
    Grande, tem 128). Cidade com mais de 200 propostas precisaria paginar de verdade.
    """
    data = _cached_get(
        "/proposta",
        {"cd_ibge_recebedor": cd_ibge, "tamanho_da_pagina": 200, "pagina": 1},
        f"propostas_{cd_ibge}",
    )
    return data["data"]


def valor_proposta(proposta: dict) -> float:
    """Valor da proposta. ponytail: nr_vlr_total vem sempre null nesse dataset
    (módulo Parcerias/Saúde) — o valor real está em vl_total_planejamento_gastos."""
    return proposta.get("nr_vlr_total") or proposta.get("vl_total_planejamento_gastos") or 0


def calcular_gap(cd_ibge: int, programas_abertos: list[dict], propostas: list[dict]) -> list[dict]:
    """Programas abertos que este município ainda não usou (não tem proposta vinculada)."""
    ids_usados = {p.get("id_programa") for p in propostas}
    return [p for p in programas_abertos if p["id_programa"] not in ids_usados]


def url_portal_programa(id_programa: int) -> str:
    return PORTAL_URL_PROGRAMA.format(id=id_programa)


def get_programa_detalhe(id_programa: int) -> dict | None:
    """Detalhe rico do programa via o portal (não a API de dados abertos):
    requisitos/condicionantes, anexos (edital, resolução...) e a janela real
    de captação. Retorna None se o id não existir nesse endpoint (404)."""
    data = _cached_get_url(
        f"{PORTAL_API}/programa/{id_programa}", {}, f"portal_programa_{id_programa}"
    )
    if data is None:
        return None
    return {
        "url": url_portal_programa(id_programa),
        "captacaoInicio": data.get("dtaInicioRecebPropEspfic"),
        "captacaoFim": data.get("dtaFimRecebPropEspfic"),
        "recebendoProposta": data.get("recebendoProposta"),
        "condicionantes": [
            r["descricaoRequisito"] for r in (data.get("requisitos") or [])
            if r.get("descricaoRequisito")
        ],
        "anexos": [
            a["anexo"]["descricaoAnexo"] or a["anexo"]["nomeArquivo"]
            for a in (data.get("anexos") or []) if a.get("anexo")
        ],
        "areasAtuacao": [a.get("descricao") for a in (data.get("areasAtuacao") or [])],
    }


def gerar_minuta(nome_cidade: str, programa: dict) -> str:
    """Rascunho de plano de trabalho a partir dos campos do programa.

    ponytail: template de texto simples, não é o formulário oficial de nenhum
    órgão repassador — isso exigiria mapear o padrão de cada ministério.
    Serve pra mostrar o ponto de partida, não pra protocolar.
    """
    detalhe = get_programa_detalhe(programa["id_programa"])

    bloco_link = f"\nEDITAL/PROGRAMA NO PORTAL: {detalhe['url']}\n" if detalhe else ""

    bloco_captacao = ""
    if detalhe and (detalhe["captacaoInicio"] or detalhe["captacaoFim"]):
        bloco_captacao = (
            f"\nJANELA DE CAPTAÇÃO: {detalhe['captacaoInicio'] or '?'} a "
            f"{detalhe['captacaoFim'] or '?'}\n"
        )

    bloco_condicionantes = "(nenhum requisito publicado nesse programa até o momento)"
    if detalhe and detalhe["condicionantes"]:
        bloco_condicionantes = "\n".join(f"- {c}" for c in detalhe["condicionantes"])

    bloco_anexos = ""
    if detalhe and detalhe["anexos"]:
        lista = "\n".join(f"- {a}" for a in detalhe["anexos"])
        bloco_anexos = f"\n9. DOCUMENTOS/ANEXOS DO PROGRAMA (baixar no portal)\n{lista}\n"

    return f"""MINUTA DE PLANO DE TRABALHO (rascunho automático — revisar antes de usar)
Gerado em {date.today().isoformat()}

MUNICÍPIO PROPONENTE: {nome_cidade} - MS

PROGRAMA: {programa.get('nm_programa')}
CÓDIGO: {programa.get('cd_programa')}
ÓRGÃO REPASSADOR: {programa.get('nm_ente_repassador')}
INSTRUMENTO: {programa.get('tp_instrumento')}
{bloco_link}{bloco_captacao}
1. OBJETO
[Adaptar ao projeto específico do município a partir do objetivo do programa abaixo]

2. OBJETIVO DO PROGRAMA (referência oficial)
{programa.get('ds_objetivo') or '(não informado pela fonte)'}

3. PROBLEMA QUE O PROGRAMA ENDEREÇA
{programa.get('ds_problema') or '(não informado pela fonte)'}

4. PÚBLICO-ALVO
{programa.get('ds_publico_alvo') or '(não informado pela fonte)'}

5. RESULTADO ESPERADO
{programa.get('ds_resultado_esperado') or '(não informado pela fonte)'}

6. JUSTIFICATIVA LOCAL
[Preencher: por que {nome_cidade} precisa deste recurso — dado local, diagnóstico, demanda]

7. CRONOGRAMA E METAS
[Preencher junto com a secretaria responsável]

8. CONDICIONANTES PARA RECEPÇÃO DE RECURSOS (do portal, cláusula suspensiva)
{bloco_condicionantes}
{bloco_anexos}
---
Fonte dos dados do programa: API pública Transferegov (api-publica.transferegov.gestao.gov.br)
Este documento é um ponto de partida gerado automaticamente. Não substitui análise técnica
nem o formulário oficial exigido pelo órgão repassador.
"""
