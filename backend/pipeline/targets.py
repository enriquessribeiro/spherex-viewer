"""Alvos pré-configurados (targets.yaml) e propagação de posição por movimento próprio."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

DAYS_PER_YEAR = 365.25

# Época de referência para o centro dos campos dos alvos: ~nov/2025, meio do
# primeiro ano de dados do SPHEREx. Objetos rápidos ficam perto do centro em todas as épocas.
REFERENCE_MJD = 61000.0


@dataclass(frozen=True)
class Target:
    id: str
    name: str
    ra: float  # graus, ICRS, na época ref_mjd
    dec: float
    pm_ra_masyr: float = 0.0  # mu_alpha* (já inclui cos(dec)), como no SIMBAD/Gaia
    pm_dec_masyr: float = 0.0
    ref_mjd: float = 51544.5  # J2000
    fov_arcmin: float = 6.0
    description: str = ""  # o que o astro é, para quem não é astrônomo (card do site)
    look_for: str = ""  # o que observar na placa
    default_detector: str = "D2"  # detector em que o site abre (anãs frias: D6)

    def field_center(self) -> tuple[float, float]:
        """Centro do campo publicado: posição propagada até REFERENCE_MJD."""
        return self.position_at(REFERENCE_MJD)

    def position_at(self, mjd: float) -> tuple[float, float]:
        """Posição propagada linearmente pelo movimento próprio até `mjd`."""
        years = (mjd - self.ref_mjd) / DAYS_PER_YEAR
        dec = self.dec + self.pm_dec_masyr * years / 3.6e6
        ra = self.ra + self.pm_ra_masyr * years / 3.6e6 / math.cos(math.radians(self.dec))
        return ra % 360.0, dec


def load_targets(path: str | Path) -> list[Target]:
    data = yaml.safe_load(Path(path).read_text())
    return [Target(**t) for t in data["targets"]]
