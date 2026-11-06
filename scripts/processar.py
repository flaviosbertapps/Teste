"""Processa a votação para Presidente 2026 por município e classifica cada um.

Critério principal ("virada_contra"):
  - 1º turno: Flávio Bolsonaro foi o candidato MAIS VOTADO no município;
  - 2º turno: Lula teve mais votos que Flávio no município.

Saídas:
  data/out/municipios.csv   todos os municípios com métricas
  data/out/viradas.csv      apenas os de categoria "virada_contra"
  web/data/municipios.json  dados consumidos pelo front-end (chave = código IBGE)

Uso:
  python scripts/processar.py [--votacao CAMINHO_ZIP_OU_CSV] [--crosswalk CSV]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import pathlib
import re
import sys
import zipfile

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "out"
WEB = ROOT / "web" / "data"

CD_CARGO_PRESIDENTE = 1
COLS = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "CD_CARGO",
        "NR_CANDIDATO", "NM_URNA_CANDIDATO", "QT_VOTOS_NOMINAIS"]

PADRAO_FLAVIO = r"FL[AÁ]VIO\s+BOLSONARO"
PADRAO_LULA = r"\bLULA\b"


# ---------------------------------------------------------------- leitura

def _ler_csv(buf) -> pd.DataFrame:
    return pd.read_csv(buf, sep=";", encoding="latin-1", usecols=lambda c: c in COLS,
                       dtype={"SG_UF": str, "NM_MUNICIPIO": str, "NM_URNA_CANDIDATO": str})


def ler_votacao(caminho: pathlib.Path) -> pd.DataFrame:
    """Lê o ZIP do TSE (ou um CSV avulso). Prefere o arquivo _BR (nacional);
    caso não exista, concatena os arquivos por UF."""
    if caminho.suffix.lower() == ".csv":
        return _ler_csv(caminho)
    with zipfile.ZipFile(caminho) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        br = [n for n in csvs if re.search(r"_BR(ASIL)?\.csv$", n, re.I)]
        alvo = br or csvs
        partes = [_ler_csv(io.BytesIO(z.read(n))) for n in alvo]
    return pd.concat(partes, ignore_index=True)


# ---------------------------------------------------------------- núcleo

def identificar(df: pd.DataFrame, padrao: str, rotulo: str) -> int:
    nomes = df.loc[df["NM_URNA_CANDIDATO"].str.contains(padrao, case=False, regex=True, na=False),
                   ["NR_CANDIDATO", "NM_URNA_CANDIDATO"]].drop_duplicates()
    nums = nomes["NR_CANDIDATO"].unique()
    if len(nums) != 1:
        raise SystemExit(f"Não foi possível identificar {rotulo} de forma única: {nomes.to_dict('records')}")
    print(f"{rotulo}: nº {nums[0]} ({nomes['NM_URNA_CANDIDATO'].iloc[0]})")
    return int(nums[0])


def classificar(df: pd.DataFrame, nr_flavio: int, nr_lula: int) -> pd.DataFrame:
    """Recebe linhas TSE (já filtradas para Presidente, sem exterior) e devolve
    um DataFrame com uma linha por município (CD_MUNICIPIO TSE)."""
    g = (df.groupby(["NR_TURNO", "CD_MUNICIPIO", "NR_CANDIDATO"], as_index=False)["QT_VOTOS_NOMINAIS"].sum())

    def turno(n: int) -> pd.DataFrame:
        t = g[g["NR_TURNO"] == n]
        piv = t.pivot_table(index="CD_MUNICIPIO", columns="NR_CANDIDATO",
                            values="QT_VOTOS_NOMINAIS", fill_value=0, aggfunc="sum")
        res = pd.DataFrame(index=piv.index)
        res["validos"] = piv.sum(axis=1)
        res["flavio"] = piv.get(nr_flavio, 0)
        res["lula"] = piv.get(nr_lula, 0)
        res["max_outros"] = piv.drop(columns=[nr_flavio], errors="ignore").max(axis=1)
        return res

    t1, t2 = turno(1), turno(2)
    m = t1.add_suffix("_1t").join(t2.add_suffix("_2t"), how="outer")
    if m.isna().any().any():
        faltando = m[m.isna().any(axis=1)].index.tolist()
        raise SystemExit(f"Municípios presentes em só um dos turnos: {faltando[:20]}")

    m["pct_1t"] = m["flavio_1t"] / m["validos_1t"] * 100
    m["pct_2t"] = m["flavio_2t"] / m["validos_2t"] * 100
    m["pct_lula_1t"] = m["lula_1t"] / m["validos_1t"] * 100
    m["pct_lula_2t"] = m["lula_2t"] / m["validos_2t"] * 100
    # Margem só entre os dois finalistas (comparável entre turnos), em pontos percentuais
    m["margem_1t"] = (m["flavio_1t"] - m["lula_1t"]) / (m["flavio_1t"] + m["lula_1t"]) * 100
    m["margem_2t"] = (m["flavio_2t"] - m["lula_2t"]) / (m["flavio_2t"] + m["lula_2t"]) * 100
    m["delta_margem"] = m["margem_2t"] - m["margem_1t"]

    liderou_1t = m["flavio_1t"] > m["max_outros_1t"]          # critério A: 1º lugar isolado
    venceu_2t = m["flavio_2t"] > m["lula_2t"]
    perdeu_2t = m["flavio_2t"] < m["lula_2t"]
    m["categoria"] = "perdeu_ambos"
    m.loc[liderou_1t & venceu_2t, "categoria"] = "manteve"
    m.loc[liderou_1t & perdeu_2t, "categoria"] = "virada_contra"
    m.loc[~liderou_1t & venceu_2t, "categoria"] = "virada_a_favor"
    m.loc[m["flavio_2t"] == m["lula_2t"], "categoria"] = "empate_2t"
    return m.drop(columns=["max_outros_1t", "max_outros_2t"]).reset_index()


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--votacao", type=pathlib.Path, default=RAW / "votacao_candidato_munzona_2026.zip")
    ap.add_argument("--crosswalk", type=pathlib.Path, default=RAW / "tse_ibge.csv")
    ap.add_argument("--fonte-data", default=dt.date.today().isoformat(),
                    help="data de referência do download (aparece na página)")
    a = ap.parse_args(argv)

    df = ler_votacao(a.votacao)
    df = df[(df["CD_CARGO"] == CD_CARGO_PRESIDENTE) & (df["SG_UF"] != "ZZ")]
    if df.empty:
        raise SystemExit("Nenhuma linha de Presidente encontrada no arquivo.")
    nr_f = identificar(df, PADRAO_FLAVIO, "Flávio Bolsonaro")
    nr_l = identificar(df, PADRAO_LULA, "Lula")

    nomes = df.groupby("CD_MUNICIPIO").agg(uf=("SG_UF", "first"), nome=("NM_MUNICIPIO", "first"))
    m = classificar(df, nr_f, nr_l).join(nomes, on="CD_MUNICIPIO")

    cw = pd.read_csv(a.crosswalk, dtype={"codigo_ibge": str})
    # Municípios ausentes da tabela pública (ex.: criados após 2020), mantidos à mão
    extra = ROOT / "data" / "crosswalk_extra.csv"
    if extra.exists():
        cw = pd.concat([cw, pd.read_csv(extra, dtype={"codigo_ibge": str})]).drop_duplicates("codigo_tse", keep="last")
    m = m.merge(cw[["codigo_tse", "codigo_ibge"]], left_on="CD_MUNICIPIO", right_on="codigo_tse", how="left")
    sem_par = m[m["codigo_ibge"].isna()]
    if not sem_par.empty:
        raise SystemExit(f"{len(sem_par)} município(s) sem código IBGE: "
                         f"{sem_par[['CD_MUNICIPIO', 'uf', 'nome']].to_dict('records')[:20]}")

    # Sanidade
    print(f"Municípios: {len(m)} (esperado ~5.570)")
    for t in (1, 2):
        print(f"Válidos {t}º turno: {int(m[f'validos_{t}t'].sum()):,}".replace(",", "."))
    print(m["categoria"].value_counts().to_string())

    OUT.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    cols = ["codigo_ibge", "CD_MUNICIPIO", "uf", "nome", "categoria",
            "validos_1t", "flavio_1t", "lula_1t", "pct_1t", "pct_lula_1t",
            "validos_2t", "flavio_2t", "lula_2t", "pct_2t", "pct_lula_2t",
            "margem_1t", "margem_2t", "delta_margem"]
    m = m[cols].rename(columns={"CD_MUNICIPIO": "codigo_tse"}).sort_values(["uf", "nome"])
    m.to_csv(OUT / "municipios.csv", index=False, float_format="%.2f")
    m[m["categoria"] == "virada_contra"].to_csv(OUT / "viradas.csv", index=False, float_format="%.2f")

    registros = {}
    for r in m.itertuples(index=False):
        registros[r.codigo_ibge] = {
            "n": r.nome, "uf": r.uf, "c": r.categoria,
            "v1": int(r.validos_1t), "f1": int(r.flavio_1t), "l1": int(r.lula_1t),
            "v2": int(r.validos_2t), "f2": int(r.flavio_2t), "l2": int(r.lula_2t),
        }
    payload = {"fonte": "TSE — votacao_candidato_munzona_2026", "data_referencia": a.fonte_data,
               "municipios": registros}
    (WEB / "municipios.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                                         encoding="utf-8")
    print(f"OK -> {OUT} e {WEB / 'municipios.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
