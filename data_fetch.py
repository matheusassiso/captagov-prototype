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

# ponytail: 10 maiores cidades do MS por população (IBGE) + centroide (Nominatim).
# Se quiser outro estado/lista, troca aqui — não há lógica genérica de "N maiores" ainda.
CIDADES_MS = [
    {"ibge": 5002704, "nome": "Campo Grande", "lat": -20.4640173, "lon": -54.6162947},
    {"ibge": 5003702, "nome": "Dourados", "lat": -22.2206145, "lon": -54.8122080},
    {"ibge": 5008305, "nome": "Três Lagoas", "lat": -20.7866799, "lon": -51.7061247},
    {"ibge": 5003207, "nome": "Corumbá", "lat": -19.0006027, "lon": -57.6507535},
    {"ibge": 5006606, "nome": "Ponta Porã", "lat": -22.5286917, "lon": -55.7234260},
    {"ibge": 5005707, "nome": "Naviraí", "lat": -23.0622152, "lon": -54.2018319},
    {"ibge": 5006200, "nome": "Nova Andradina", "lat": -22.2477565, "lon": -53.3480621},
    {"ibge": 5007901, "nome": "Sidrolândia", "lat": -20.9361042, "lon": -54.9640262},
    {"ibge": 5001102, "nome": "Aquidauana", "lat": -20.4739690, "lon": -55.7821375},
    {"ibge": 5005400, "nome": "Maracaju", "lat": -21.6163005, "lon": -55.1646050},
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


def get_programas_abertos() -> list[dict]:
    """Programas com situação 'Disponibilizado' e que aceitam candidatura direta
    (Beneficiário Espontâneo ou Específico) — não depende de indicação de parlamentar.

    ponytail: só existem ~176 programas no total, cabem numa página. Se a API
    crescer muito isso precisa virar paginação de verdade.
    """
    data = _cached_get("/programa", {"tamanho_da_pagina": 200, "pagina": 1}, "programas_p1")
    programas = data["data"]
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
