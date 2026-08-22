"""CaptaGov (protótipo) — descobre repasse federal aberto que a prefeitura ainda não usou.

Roda local: python app.py, abre http://127.0.0.1:5000
Dado real, ao vivo, do Transferegov (API pública, sem chave).

ponytail: isso é a versão "sempre ao vivo" via servidor. Pra abrir/compartilhar
sem instalar nada, usa `python gerar_painel.py` — gera um HTML único com o
mesmo dado embutido, sem precisar do Flask rodando.
"""
from flask import Flask, abort, render_template, Response

import data_fetch as df

app = Flask(__name__)


def _cidade_por_ibge(cd_ibge: int) -> dict | None:
    return next((c for c in df.CIDADES_MS if c["ibge"] == cd_ibge), None)


def _resumo_cidade(cidade: dict, programas_abertos: list[dict]) -> dict:
    propostas = df.get_propostas_municipio(cidade["ibge"])
    gap = df.calcular_gap(cidade["ibge"], programas_abertos, propostas)
    valor_total = sum(df.valor_proposta(p) for p in propostas)
    return {
        "cd_ibge": cidade["ibge"],
        "nome": cidade["nome"],
        "n_propostas": len(propostas),
        "valor_total": valor_total,
        "n_oportunidades_abertas": len(gap),
    }


@app.route("/")
def index():
    programas_abertos = df.get_programas_abertos()
    cidades = [_resumo_cidade(c, programas_abertos) for c in df.CIDADES_MS]
    cidades.sort(key=lambda c: -c["n_oportunidades_abertas"])
    return render_template(
        "index.html",
        cidades=cidades,
        total_programas_abertos=len(programas_abertos),
    )


@app.route("/cidade/<int:cd_ibge>")
def cidade(cd_ibge: int):
    c = _cidade_por_ibge(cd_ibge)
    if c is None:
        abort(404)
    programas_abertos = df.get_programas_abertos()
    propostas = df.get_propostas_municipio(cd_ibge)
    gap = df.calcular_gap(cd_ibge, programas_abertos, propostas)
    gap.sort(key=lambda p: p.get("nm_programa") or "")
    return render_template(
        "cidade.html",
        nome=c["nome"],
        cd_ibge=cd_ibge,
        gap=gap,
        propostas=propostas,
    )


@app.route("/cidade/<int:cd_ibge>/minuta/<int:id_programa>")
def minuta(cd_ibge: int, id_programa: int):
    c = _cidade_por_ibge(cd_ibge)
    if c is None:
        abort(404)
    programas_abertos = df.get_programas_abertos()
    programa = next((p for p in programas_abertos if p["id_programa"] == id_programa), None)
    if programa is None:
        abort(404)

    texto = df.gerar_minuta(c["nome"], programa)
    return render_template("minuta.html", nome=c["nome"], cd_ibge=cd_ibge, programa=programa, texto=texto)


@app.route("/cidade/<int:cd_ibge>/minuta/<int:id_programa>/download")
def minuta_download(cd_ibge: int, id_programa: int):
    c = _cidade_por_ibge(cd_ibge)
    if c is None:
        abort(404)
    programas_abertos = df.get_programas_abertos()
    programa = next((p for p in programas_abertos if p["id_programa"] == id_programa), None)
    if programa is None:
        abort(404)

    texto = df.gerar_minuta(c["nome"], programa)
    return Response(
        texto,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=minuta_{c['nome']}_{id_programa}.txt"},
    )


if __name__ == "__main__":
    app.run(debug=True)
