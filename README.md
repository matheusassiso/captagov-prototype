# CaptaGov (protótipo)

## ➡️ [ABRIR O PAINEL](https://matheusassiso.github.io/captagov-prototype/) ⬅️

Cruza programa de repasse federal aberto (API pública Transferegov, ex-SICONV)
com o histórico de captação de cada uma das 10 maiores cidades do MS —
mostra qual oportunidade a prefeitura ainda não usou, e gera uma minuta de
plano de trabalho de partida.

Dado real, sem chave de API. Repositório privado, painel publicado (link acima
funciona sem login — mesmo esquema do atf-georadar). Pra atualizar o link com
dado novo: `python gerar_painel.py` e `git push`.

## Rodar

**Painel interativo (recomendado, pra mostrar/compartilhar)** — dois cliques em
`gerar_e_abrir.bat`. Gera `docs/index.html` com o dado já embutido (KPI,
gráfico, mapa do MS, filtro cruzado, ficha imprimível por oportunidade,
exportar CSV) e abre no navegador. Não precisa de servidor rodando — o
arquivo gerado abre sozinho depois, por duplo-clique, em qualquer PC, e dá
pra subir num GitHub Pages se quiser (como o `atf-georadar`). Só que o dado
fica congelado no momento em que rodou o gerador — pra atualizar, roda de novo.

**Servidor ao vivo (pra ver dado sempre atual)** — dois cliques em `rodar.bat`.
Abre `http://127.0.0.1:5000`, busca a API a cada visita nova (cache 24h).
Fecha a janela do servidor pra parar.

Os dois instalam sozinhos na primeira vez (criam `.venv`, instalam
Flask/requests). Manual, se preferir:
```
pip install -r requirements.txt
python gerar_painel.py   # gera docs/index.html
python app.py            # ou sobe o servidor em http://127.0.0.1:5000
```

## O que é amostra, não produto

- Minuta é texto simples a partir dos campos do programa — não é o formulário
  oficial de nenhum órgão repassador.
- "Oportunidade aberta" = programa com `situacao_programa=Disponibilizado` e
  `qualificacao_beneficiario` em (Espontâneo, Específico) — fora os que
  dependem de indicação de emenda parlamentar (outro fluxo, requer articulação
  política, não é candidatura direta).
- Só cobre o módulo "Parcerias" do Transferegov. Tem outros três módulos
  (Especiais, Fundo a Fundo, Discricionárias e Legais) não explorados ainda.
- Lista de cidades hardcoded (10 maiores do MS por população IBGE, com lat/lon
  do Nominatim/OSM). Trocar estado/lista = editar `CIDADES_MS` em `data_fetch.py`.
- O painel (`docs/index.html`) carrega Chart.js e Leaflet de CDN — o *dado* já
  vem embutido no arquivo (sem fetch), mas o mapa e os gráficos só desenham
  com internet na primeira carga da página.
