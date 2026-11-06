"""Testes com dados SINTÉTICOS (não são resultados reais)."""
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from processar import classificar  # noqa: E402

F, L, X = 22, 13, 99


def linhas(mun, t1, t2):
    out = []
    for nr, v in t1.items():
        out.append((1, mun, nr, v))
    for nr, v in t2.items():
        out.append((2, mun, nr, v))
    return out


def df(*grupos):
    rows = [r for g in grupos for r in g]
    return pd.DataFrame(rows, columns=["NR_TURNO", "CD_MUNICIPIO", "NR_CANDIDATO", "QT_VOTOS_NOMINAIS"])


def cat(res, mun):
    return res.set_index("CD_MUNICIPIO").loc[mun, "categoria"]


def test_categorias():
    d = df(
        linhas(1, {F: 40, L: 35, X: 25}, {F: 48, L: 52}),   # liderou e perdeu
        linhas(2, {F: 40, L: 35, X: 25}, {F: 55, L: 45}),   # manteve
        linhas(3, {F: 30, L: 45, X: 25}, {F: 51, L: 49}),   # virada a favor
        linhas(4, {F: 30, L: 45, X: 25}, {F: 40, L: 60}),   # perdeu ambos
        linhas(5, {F: 30, L: 25, X: 45}, {F: 40, L: 60}),   # 3º colocado liderou: não é critério A
        linhas(6, {F: 40, L: 40, X: 20}, {F: 50, L: 50}),   # empate
    )
    r = classificar(d, F, L)
    assert cat(r, 1) == "virada_contra"
    assert cat(r, 2) == "manteve"
    assert cat(r, 3) == "virada_a_favor"
    assert cat(r, 4) == "perdeu_ambos"
    assert cat(r, 5) == "perdeu_ambos"
    assert cat(r, 6) == "empate_2t"


def test_zonas_somadas_e_metricas():
    d = df(linhas(1, {F: 20, L: 10}, {F: 20, L: 30}), linhas(1, {F: 20, L: 10, X: 30}, {F: 0, L: 0}))
    r = classificar(d, F, L).set_index("CD_MUNICIPIO").loc[1]
    assert r["validos_1t"] == 90 and r["flavio_1t"] == 40
    assert r["categoria"] == "virada_contra"
    assert abs(r["pct_1t"] - 400 / 9) < 1e-9 and abs(r["pct_2t"] - 40) < 1e-9
    assert abs(r["margem_1t"] - 100 / 3) < 1e-9     # (40-20)/(40+20)
    assert abs(r["margem_2t"] + 20) < 1e-9          # (20-30)/(20+30)
