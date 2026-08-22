# CaptaGov (protótipo)

## ➡️ [ABRIR O PAINEL](https://matheusassiso.github.io/captagov-prototype/) ⬅️

Cruza programa de repasse federal aberto (API pública Transferegov, ex-SICONV)
com o histórico de captação de cada uma das 79 cidades do MS — mostra qual
oportunidade a prefeitura ainda não usou, e gera uma minuta de plano de
trabalho de partida.

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
- Lista das 79 cidades do MS hardcoded, com lat/lon calculado a partir da
  malha municipal do IBGE (média dos vértices do polígono, não é o centroide
  geométrico exato — suficiente pra marcador no mapa). Trocar de estado =
  editar `CIDADES_MS` em `data_fetch.py` (buscar a malha da UF nova em
  `servicodados.ibge.gov.br/api/v3/malhas/estados/{UF}?formato=application/vnd.geo+json&intrarregiao=municipio`
  e recalcular).
- O painel (`docs/index.html`) carrega Chart.js de CDN — o *dado* e a malha do
  mapa (SVG, sem Leaflet/tile externo) já vêm embutidos no arquivo, só o gráfico
  depende de internet na primeira carga da página.
- Gráfico com mais de 10 itens mostra só o top 10 por padrão; "ver todas"
  expande pra barra horizontal com rolagem própria e o valor escrito direto
  do lado de cada barra (não dá pra "grudar" só o eixo numa caixa que rola —
  canvas é um desenho só — então o valor viaja junto com a barra).
- Mapa é SVG estático com a malha real dos municípios (IBGE, qualidade mínima
  pra ficar leve), colorido por valor captado ou por oportunidade aberta
  (toggle no card) — sem pan/zoom, sem tile do OpenStreetMap.
- Requisitos/anexos/janela real de captação e o link "edital" vêm de um
  segundo endpoint público: `parcerias.transferegov.sistema.gov.br/ep/api/atos-prep/programa/{id}`
  (o mesmo que o portal usa, sem login). Programa recente (cadastrado via
  integração de outro sistema, ex: emenda parlamentar) costuma vir sem esses
  campos preenchidos — nesse caso a ficha mostra só o que a API de dados
  abertos tem.
