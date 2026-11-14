"""Cache em disco para qualquer `Archive` (docs/05-hospedagem.md §3).

- Consultas: JSON em `queries/`, válidas por `query_ttl_s` (dados novos chegam semanalmente).
- Recortes: FITS em `exposures/`, permanentes (uma exposição não muda dentro de um release).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from astropy.io import fits

from pipeline.archive import Archive, Exposure

DEFAULT_QUERY_TTL_S = 24 * 3600


class CachedArchive:
    def __init__(
        self,
        archive: Archive,
        cache_dir: str | Path,
        query_ttl_s: float = DEFAULT_QUERY_TTL_S,
        clock: Callable[[], float] = time.time,
    ):
        self._archive = archive
        self._dir = Path(cache_dir)
        self._query_ttl_s = query_ttl_s
        self._clock = clock

    def query(self, ra: float, dec: float) -> list[Exposure]:
        path = self._dir / "queries" / f"{ra:.5f}{dec:+.5f}.json"
        if path.exists():
            cached = json.loads(path.read_text())
            if self._clock() - cached["saved_at"] < self._query_ttl_s:
                return [Exposure(**e) for e in cached["exposures"]]
        exposures = self._archive.query(ra, dec)
        _atomic_write(
            path,
            json.dumps({"saved_at": self._clock(), "exposures": [asdict(e) for e in exposures]}).encode(),
        )
        return exposures

    def fetch_cutout(
        self, exposure: Exposure, ra: float, dec: float, size_deg: float
    ) -> fits.HDUList:
        key = f"{exposure.uri or exposure.id}|{ra:.5f}|{dec:.5f}|{size_deg:g}"
        digest = hashlib.sha1(key.encode()).hexdigest()[:16]
        path = self._dir / "exposures" / f"{exposure.id}_{digest}.fits"
        if not path.exists():
            hdul = self._archive.fetch_cutout(exposure, ra, dec, size_deg)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = _tmp_path(path)
            hdul.writeto(tmp, overwrite=True)
            tmp.replace(path)
        return fits.open(path)


def _atomic_write(path: Path, content: bytes) -> None:
    """Escreve num arquivo temporário e renomeia: leitores nunca veem arquivo pela metade."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(path)
    tmp.write_bytes(content)
    tmp.replace(path)


def _tmp_path(path: Path) -> Path:
    """Nome temporário único por processo e thread (downloads são paralelos)."""
    return path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
