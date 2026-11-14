"""Interface do arquivo de dados consumida pelo pipeline.

O pipeline não conhece o IRSA diretamente: recebe um objeto que implementa
`Archive`. Em produção é o adaptador do IRSA; nos testes, um arquivo sintético.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from astropy.io import fits


@dataclass(frozen=True)
class Exposure:
    """Metadados de uma exposição de um detector do SPHEREx."""

    id: str
    detector: str  # "D1" ... "D6"
    mjd: float
    uri: str = ""
    collection: str = ""


class Archive(Protocol):
    def query(self, ra: float, dec: float) -> list[Exposure]:
        """Exposições que cobrem a posição (graus, ICRS)."""
        ...

    def fetch_cutout(
        self, exposure: Exposure, ra: float, dec: float, size_deg: float
    ) -> fits.HDUList:
        """Recorte da exposição centrado em (ra, dec), com IMAGE, FLAGS, VARIANCE e ZODI."""
        ...
