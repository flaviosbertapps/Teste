"""Baixa os dados brutos para data/raw/.

- Votação por município/zona (TSE, Presidente 2026, ambos os turnos)
- Correspondência código TSE <-> código IBGE
- Malha municipal (GeoJSON)
"""
import pathlib
import sys
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

FONTES = {
    "votacao_candidato_munzona_2026.zip":
        "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2026.zip",
    "tse_ibge.csv":
        "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv",
    "mun.geojson":
        "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json",
}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    falhas = 0
    for nome, url in FONTES.items():
        destino = RAW / nome
        if destino.exists() and destino.stat().st_size > 0:
            print(f"[cache] {nome}")
            continue
        print(f"[baixando] {url}")
        try:
            urllib.request.urlretrieve(url, destino)
        except Exception as e:  # noqa: BLE001
            print(f"[ERRO] {nome}: {e}", file=sys.stderr)
            destino.unlink(missing_ok=True)
            falhas += 1
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
