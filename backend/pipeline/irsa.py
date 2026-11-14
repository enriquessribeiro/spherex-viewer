"""Adaptador do arquivo IRSA (NASA/IPAC) para o pipeline.

Consulta as exposições do SPHEREx via TAP (ADQL) e baixa recortes pelo serviço
de cutouts. Detalhes do acesso em docs/02-dados-spherex.md §4.
"""

from __future__ import annotations

import csv
import io
import time
from collections.abc import Callable
from pathlib import PurePosixPath

import httpx
from astropy.io import fits

from pipeline.archive import Exposure

IRSA_BASE_URL = "https://irsa.ipac.caltech.edu"
DEFAULT_COLLECTIONS = ("spherex_dr1", "spherex_qr3")

# O IRSA responde 503 "Server busy, retry later" mesmo com poucos pedidos simultâneos.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Extensões que o pipeline não usa e que pesam (EPSF ~4 MB por recorte).
DROPPED_EXTENSIONS = ("EPSF", "PSF")


class ArchiveUnavailable(Exception):
    """O IRSA não respondeu com sucesso depois de todas as tentativas."""


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
        max_attempts: int = 5,
        backoff_s: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client or httpx.Client(timeout=120)
        self._collections = collections
        self._base_url = base_url
        self._max_attempts = max_attempts
        self._backoff_s = backoff_s
        self._sleep = sleep

    def query(self, ra: float, dec: float) -> list[Exposure]:
        adql = _QUERY.format(
            ra=ra, dec=dec, collections=", ".join(f"'{c}'" for c in self._collections)
        )
        response = self._request(
            "POST", f"{self._base_url}/TAP/sync",
            data={"QUERY": adql, "LANG": "ADQL", "FORMAT": "csv"},
        )
        return [_exposure_from_row(row) for row in csv.DictReader(io.StringIO(response.text))]

    def fetch_cutout(
        self, exposure: Exposure, ra: float, dec: float, size_deg: float
    ) -> fits.HDUList:
        response = self._request(
            "GET", f"{self._base_url}/{exposure.uri}",
            params={"center": f"{ra},{dec}d", "size": f"{size_deg:g}"},
        )
        hdul = fits.open(io.BytesIO(response.content))
        for name in DROPPED_EXTENSIONS:
            if name in hdul:
                del hdul[name]
        return hdul

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Faz o pedido repetindo com espera exponencial quando o IRSA está ocupado."""
        last_error = ""
        for attempt in range(self._max_attempts):
            if attempt:
                self._sleep(self._backoff_s * 2 ** (attempt - 1))
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last_error = repr(exc)
                continue
            if response.status_code in RETRYABLE_STATUS:
                last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                continue
            response.raise_for_status()
            return response
        raise ArchiveUnavailable(f"{url}: {last_error} após {self._max_attempts} tentativas")


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
