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

from pipeline.archive import ArchiveUnavailable, Exposure

__all__ = ["ArchiveUnavailable", "IrsaArchive"]

IRSA_BASE_URL = "https://irsa.ipac.caltech.edu"
DEFAULT_COLLECTIONS = ("spherex_dr1", "spherex_qr3")

# O IRSA responde 503 "Server busy, retry later" mesmo com poucos pedidos simultâneos.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Com o TAP fora do ar, poucas tentativas antes de consultar pelo SIA.
TAP_ATTEMPTS_BEFORE_SIA = 2
# O SIA busca imagens que tocam um círculo; um raio de 3,6″ equivale a "contém o ponto".
SIA_RADIUS_DEG = 0.001

# Extensões que o pipeline não usa e que pesam (EPSF ~4 MB por recorte).
DROPPED_EXTENSIONS = ("EPSF", "PSF")


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
        max_attempts: int = 6,
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
        try:
            response = self._request(
                "POST", f"{self._base_url}/TAP/sync",
                data={"QUERY": adql, "LANG": "ADQL", "FORMAT": "csv"},
                max_attempts=TAP_ATTEMPTS_BEFORE_SIA,
            )
            rows = _csv_rows(response.text, TAP_COLUMNS, "TAP")
        except ArchiveUnavailable:
            # O TAP do IRSA pode cair sozinho (14/11/2026: TAP com 502, SIA e recortes no ar),
            # ou responder 200 com uma página de erro em HTML.
            return self._query_sia(ra, dec)
        return [_exposure_from_row(row) for row in rows]

    def _query_sia(self, ra: float, dec: float) -> list[Exposure]:
        """Mesma consulta pelo serviço SIA2: uma requisição por coleção."""
        exposures: list[Exposure] = []
        for collection in self._collections:
            response = self._request(
                "GET", f"{self._base_url}/SIA",
                params={
                    "COLLECTION": collection,
                    "POS": f"circle {ra} {dec} {SIA_RADIUS_DEG}",
                    "RESPONSEFORMAT": "CSV",
                },
            )
            for row in _csv_rows(response.text, SIA_COLUMNS, "SIA"):
                if row["dataproduct_subtype"] != "science":
                    continue
                exposures.append(_exposure_from_row({
                    "uri": row["access_url"].split("://", 1)[1].split("/", 1)[1],
                    "energy_bandpassname": row["energy_bandpassname"],
                    "time_bounds_lower": row["t_min"],
                    "collection": row["obs_collection"],
                }))
        return sorted(exposures, key=lambda e: e.mjd)

    def fetch_cutout(
        self, exposure: Exposure, ra: float, dec: float, size_deg: float
    ) -> fits.HDUList:
        response = self._request(
            "GET", f"{self._base_url}/{exposure.uri}",
            params={"center": f"{ra},{dec}d", "size": f"{size_deg:g}"},
        )
        try:
            hdul = fits.open(io.BytesIO(response.content))
            hdul.verify("silentfix")
        except Exception as exc:  # noqa: BLE001 — qualquer resposta que não seja FITS
            raise ArchiveUnavailable(f"{exposure.uri}: o recorte não é um FITS válido ({exc})") from exc
        for name in DROPPED_EXTENSIONS:
            if name in hdul:
                del hdul[name]
        return hdul

    def _request(self, method: str, url: str, max_attempts: int | None = None, **kwargs) -> httpx.Response:
        """Faz o pedido repetindo com espera exponencial quando o IRSA está ocupado."""
        attempts = max_attempts or self._max_attempts
        last_error = ""
        for attempt in range(attempts):
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
            if response.is_error:
                # Erro definitivo (404, 403...): não adianta repetir, mas é falha do arquivo,
                # não do nosso código — vira ArchiveUnavailable para a exposição ser pulada.
                raise ArchiveUnavailable(f"{url}: HTTP {response.status_code}: {response.text[:100]}")
            return response
        raise ArchiveUnavailable(f"{url}: {last_error} após {attempts} tentativas")


TAP_COLUMNS = {"collection", "energy_bandpassname", "time_bounds_lower", "uri"}
SIA_COLUMNS = {"dataproduct_subtype", "access_url", "energy_bandpassname", "t_min", "obs_collection"}


def _csv_rows(text: str, required: set[str], service: str) -> list[dict[str, str]]:
    """Linhas do CSV; uma resposta sem as colunas esperadas (ex.: HTML de erro) é falha do arquivo,
    não "nenhuma cobertura"."""
    reader = csv.DictReader(io.StringIO(text))
    if not required <= set(reader.fieldnames or ()):
        raise ArchiveUnavailable(f"{service}: resposta inesperada ({text[:80]!r})")
    return list(reader)


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
