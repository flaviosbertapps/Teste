# Planejamento — Mapa "Virada no 2º turno" (Flávio Bolsonaro, Presidente 2026)

> Status: **rascunho para aprovação**. Nenhum código escrito ainda.

## 0. Premissas a validar antes de codar

1. **Eleição alvo:** Presidente da República, 2026 (1º turno 04/10, 2º turno 25/10). Se Flávio não foi ao 2º turno, o projeto não tem objeto — confirmar.
2. **Definição de "ficou à frente" no 1º turno** (escolher uma):
   - **A (recomendada):** Flávio foi o **mais votado** no município (1º lugar entre todos os candidatos).
   - B: Flávio teve mais votos que o **adversário do 2º turno** (mesmo sem ser o 1º colocado).
3. **Definição de "ficou atrás" no 2º turno:** adversário teve mais votos válidos que Flávio no município.
4. **Atenção — "perdeu terreno" ≠ "perdeu a liderança":** no 2º turno só há dois candidatos, então o percentual de Flávio quase sempre **sobe** (ex.: 38% → 47%). Comparar % bruto 1º×2º turno é enganoso. Proposta de métricas:
   - `pct_1t` e `pct_2t` sobre votos válidos (exibidas, mas não usadas para classificar);
   - **margem head-to-head no 1º turno**: `(Flávio − adversário) / (Flávio + adversário)`, comparável com a margem do 2º turno;
   - `delta_margem = margem_2t − margem_1t` — essa sim mede "perda de terreno".
5. **Exterior** (votos em embaixadas) fica fora do mapa — não há polígono municipal.

## 1. Fonte dos dados

| Dado | Fonte | Observação |
|---|---|---|
| Votos por município/zona, por candidato, por turno | TSE Dados Abertos — `votacao_candidato_munzona_2026` (CSV, `;`, Latin-1) | Agregar zonas → município. Filtrar `CD_CARGO = 1` (Presidente) e `NR_TURNO` 1 e 2 |
| Código TSE ↔ código IBGE | Tabela de correspondência TSE/IBGE (ex.: repositório `betafcc/Municipios-Brasileiros-TSE` ou cruzamento por nome+UF) | TSE usa código próprio; a malha usa IBGE (7 dígitos). **Principal risco de erro do projeto** |
| Geometria dos municípios | IBGE — malha municipal (API `servicodados.ibge.gov.br/api/v3/malhas`) ou `geobr` | Simplificar para TopoJSON (~1–3 MB) |

Riscos: dados do TSE podem ser revisados após totalização (registrar data do download); municípios novos/renomeados quebram o cruzamento — o script deve **falhar alto** se algum município ficar sem par.

## 2. Arquitetura

```
/
├── scripts/
│   ├── 01_download.py        # baixa CSVs do TSE e malha IBGE (cache em data/raw/)
│   ├── 02_processar.py       # agrega, calcula métricas, classifica
│   └── 03_geo.py             # gera TopoJSON simplificado com dados embutidos
├── data/
│   ├── raw/                  # (gitignored) arquivos originais
│   └── out/
│       ├── municipios.csv    # todos os municípios com métricas
│       ├── viradas.csv       # só os que se encaixam no critério
│       └── mapa.topojson     # geometria + atributos para o front
├── web/
│   ├── index.html
│   ├── app.js
│   └── style.css
└── tests/
    └── test_processar.py     # checagens de consistência
```

Stack: **Python** (pandas, geopandas, mapshaper/topojson) para dados; front **estático** (HTML + D3 ou MapLibre) sem backend — pode ser publicado no GitHub Pages.

## 3. Script de processamento — lógica

1. Ler CSV TSE, filtrar Presidente, excluir exterior (`SG_UF = 'ZZ'`).
2. Agrupar por `(turno, CD_MUNICIPIO, candidato)` somando `QT_VOTOS_NOMINAIS`.
3. Por município e turno: total de válidos, votos de Flávio, votos do adversário, colocação de Flávio.
4. Calcular `pct_1t`, `pct_2t`, `margem_1t_h2h`, `margem_2t`, `delta_margem`.
5. Classificar:
   - `virada_contra` = liderou no 1º (critério A ou B) **e** perdeu no 2º ← destaque do mapa
   - `manteve`, `virada_a_favor`, `perdeu_ambos` — para contexto.
6. Cruzar com código IBGE; abortar se houver município sem correspondência.
7. Exportar CSVs e TopoJSON.

**Checagens (testes):** soma nacional de votos bate com o total oficial do TSE por turno; nº de municípios = 5.570; nenhum município com válidos = 0.

## 4. Front-end

- Mapa coroplético: `virada_contra` em cor forte; demais em cinza claro (opção de alternar para ver as 4 categorias).
- Tooltip: município/UF, % 1º turno, % 2º turno, margem head-to-head 1º→2º, votos absolutos.
- Painel lateral: total de municípios na categoria, eleitorado somado, tabela ordenável e filtro por UF.
- Nota metodológica visível explicando o critério e a fonte (evita leitura enganosa do % bruto).
- Responsivo; TopoJSON carregado sob demanda.

**Aviso de interpretação:** nº de municípios não é peso eleitoral — muitos municípios pequenos podem dominar visualmente o mapa. Sugestão: mostrar também o eleitorado somado, ou oferecer versão em pontos proporcionais.

## 5. Etapas de execução (após aprovação)

1. Download e inspeção dos CSVs reais (confirmar colunas/nomes de 2026).
2. Script de processamento + testes.
3. Geração do TopoJSON.
4. Front-end.
5. Revisão dos números contra totais oficiais do TSE.

## 6. Decisões pendentes

- [ ] Critério A ou B para "ficou à frente"?
- [ ] Adversário do 2º turno (para nomear nas legendas)?
- [ ] D3 (mais leve, controle total) ou MapLibre (zoom/pan mais fluido)? Recomendo **D3**.
- [ ] Publicar no GitHub Pages?
