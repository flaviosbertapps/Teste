# Mapa: onde Flávio liderou no 1º turno e perdeu no 2º (Presidente 2026)

Destaca os municípios em que Flávio Bolsonaro foi o **mais votado no 1º turno** e ficou **atrás de Lula no 2º turno**.
Planejamento e decisões: [PLANEJAMENTO.md](PLANEJAMENTO.md).

## Rodar localmente

```bash
pip install -r requirements.txt
python scripts/download.py      # TSE + correspondência TSE/IBGE + malha -> data/raw/
python scripts/processar.py     # -> data/out/*.csv e web/data/municipios.json
python -m http.server -d web 8000
```

`scripts/geo.sh` regenera `web/data/municipios.topojson` (já versionado; precisa de Node).

## Saídas
- `data/out/municipios.csv` — todos os municípios, com votos, %, margem Flávio×Lula por turno e categoria
- `data/out/viradas.csv` — apenas a categoria `virada_contra`
- `web/` — site estático (D3 embutido em `web/vendor/`)

## Publicação
O workflow `.github/workflows/pages.yml` baixa os dados, processa e publica `web/` no GitHub Pages a cada push na `main`.
Ative em *Settings → Pages → Source: GitHub Actions*.

## Limitações conhecidas
- A malha usada tem 5.564 polígonos; municípios criados depois de 2010 aparecem sem forma no mapa (mas estão nas tabelas).
- O script aborta se algum município do TSE não tiver código IBGE na tabela de correspondência.
