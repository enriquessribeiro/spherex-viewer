"""Adaptador do arquivo IRSA (NASA/IPAC) para o pipeline.

Consulta as exposições do SPHEREx via TAP (ADQL) e baixa recortes pelo serviço
de cutouts. Detalhes do acesso em docs/02-dados-spherex.md §4.
"""

from __future__ import annotations

import csv
import io
from pathlib import PurePosixPath

import httpx

from pipeline.archive import Exposure

IRSA_BASE_URL = "https://irsa.ipac.caltech.edu"
DEFAULT_COLLECTIONS = ("spherex_dr1", "spherex_qr3")

_QUERY = """
SELECT o.collection, p.energy_bandpassname, p.time_bounds_lower, a.uri
FROM spherex.plane p
JOIN spherex.observation o ON p.obsid = o.obsid
JOIN spherex.artifact a ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
  AND o.collection IN ({collections})
  AND a.producttype = 'science'
ORDER BY p.time_bounds_lower
"""


class IrsaArchive:
    def __init__(
        self,
        client: httpx.Client | None = None,
        collections: tuple[str, ...] = DEFAULT_COLLECTIONS,
        base_url: str = IRSA_BASE_URL,
    ):
        self._client = client or httpx.Client(timeout=120)
        self._collections = collections
        self._base_url = base_url

    def query(self, ra: float, dec: float) -> list[Exposure]:
        adql = _QUERY.format(
            ra=ra, dec=dec, collections=", ".join(f"'{c}'" for c in self._collections)
        )
        response = self._client.post(
            f"{self._base_url}/TAP/sync",
            data={"QUERY": adql, "LANG": "ADQL", "FORMAT": "csv"},
        )
        response.raise_for_status()
        return [_exposure_from_row(row) for row in csv.DictReader(io.StringIO(response.text))]


def _exposure_from_row(row: dict[str, str]) -> Exposure:
    # level2_2025W19_1B_0241_1D1_spx_l2b-v27-2026-197.fits → 2025W19_1B_0241_1D1
    name = PurePosixPath(row["uri"]).name
    exposure_id = name.removeprefix("level2_").split("_spx_")[0]
    return Exposure(
        id=exposure_id,
        detector=row["energy_bandpassname"].removeprefix("SPHEREx-"),
        mjd=float(row["time_bounds_lower"]),
        uri=row["uri"],
        collection=row["collection"],
    )
