"""Resolução de nomes de objetos pelo SIMBAD (TAP).

O servidor principal do CDS esteve fora do ar em 14/11/2026; o espelho de Harvard
responde com os mesmos dados, então é tentado primeiro.
"""

from __future__ import annotations

import csv
import io

import httpx

SIMBAD_TAP_URLS = (
    "https://simbad.harvard.edu/simbad/sim-tap/sync",
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
)
_QUERY = """
SELECT TOP 1 b.main_id, b.ra, b.dec, b.pmra, b.pmdec, b.plx_value
FROM basic b JOIN ident i ON i.oidref = b.oid
WHERE i.id = '{name}'
"""


def simbad_resolver(name: str, client: httpx.Client | None = None) -> dict | None:
    """Nome → posição (J2000) e movimento próprio, ou None se não encontrado."""
    client = client or httpx.Client(timeout=30)
    query = _QUERY.format(name=_normalize(name).replace("'", "''"))
    for url in SIMBAD_TAP_URLS:
        try:
            response = client.post(url, data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
        except httpx.HTTPError:
            continue
        if response.status_code != 200 or not response.text.startswith("main_id"):
            continue
        rows = list(csv.DictReader(io.StringIO(response.text)))
        if not rows:
            return None
        row = rows[0]
        return {
            "name": row["main_id"],
            "ra": float(row["ra"]), "dec": float(row["dec"]), "epoch": "J2000",
            "pm_ra_masyr": _float(row["pmra"]), "pm_dec_masyr": _float(row["pmdec"]),
            "parallax_mas": _float(row["plx_value"]),
            "source": "SIMBAD",
        }
    return None


def _normalize(name: str) -> str:
    """SIMBAD guarda identificadores com espaços simples (ex.: 'NAME Barnard's star')."""
    return " ".join(name.split())


def _float(value: str) -> float | None:
    return float(value) if value not in ("", None) else None
