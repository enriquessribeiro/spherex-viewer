"""Arquivo SPHEREx sintético para testes.

Gera recortes FITS no mesmo formato dos Spectral Images do SPHEREx
(extensões IMAGE, FLAGS, VARIANCE, ZODI e WCS celeste no cabeçalho de IMAGE),
contendo fontes cujas posições e brilhos são plantados pelo teste.
Assim o valor esperado de cada teste vem do que plantamos, não do pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from pipeline.archive import Exposure

PIXEL_SCALE_DEG = 6.15 / 3600.0
PSF_SIGMA_PX = 1.0


@dataclass(frozen=True)
class SyntheticSource:
    """Fonte pontual plantada no céu sintético.

    (ra, dec) é a posição em ref_mjd. O movimento próprio é dado em segundos
    de arco por ano nas direções leste e norte, como nos catálogos.
    """

    ra: float
    dec: float
    flux: float = 100.0
    pm_east_arcsec_yr: float = 0.0
    pm_north_arcsec_yr: float = 0.0
    ref_mjd: float = 60800.0

    def position_at(self, mjd: float) -> tuple[float, float]:
        years = (mjd - self.ref_mjd) / 365.25
        dec = self.dec + self.pm_north_arcsec_yr * years / 3600
        ra = self.ra + self.pm_east_arcsec_yr * years / 3600 / math.cos(math.radians(self.dec))
        return ra, dec


@dataclass(frozen=True)
class SyntheticExposure:
    """Uma exposição sintética: detector, instante e geometria do apontamento.

    rotation_deg gira o detector em relação ao céu; offset_px desloca o centro
    do recorte (em pixels do detector), simulando apontamentos diferentes.
    """

    det: str
    mjd: float
    rotation_deg: float = 0.0
    offset_px: tuple[float, float] = (0.0, 0.0)
    zodi: float = 0.0  # luz zodiacal (MJy/sr), somada à IMAGE e registrada em ZODI


@dataclass
class SyntheticArchive:
    """Implementa a interface de arquivo do pipeline com dados plantados."""

    sources: list[SyntheticSource]
    exposures: list[SyntheticExposure]
    fetch_calls: list[str] = field(default_factory=list)

    def query(self, ra: float, dec: float) -> list[Exposure]:
        return [
            Exposure(id=f"syn{i:04d}_{e.det}", detector=e.det, mjd=e.mjd)
            for i, e in enumerate(self.exposures)
        ]

    def _spec(self, exposure: Exposure) -> SyntheticExposure:
        return self.exposures[int(exposure.id[3:7])]

    def fetch_cutout(
        self, exposure: Exposure, ra: float, dec: float, size_deg: float
    ) -> fits.HDUList:
        self.fetch_calls.append(exposure.id)
        spec = self._spec(exposure)
        n = math.ceil(size_deg / PIXEL_SCALE_DEG)
        theta = np.deg2rad(spec.rotation_deg)
        wcs = WCS(naxis=2)
        wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
        wcs.wcs.crval = [ra, dec]
        wcs.wcs.crpix = [(n + 1) / 2 + spec.offset_px[0], (n + 1) / 2 + spec.offset_px[1]]
        wcs.wcs.cdelt = [-PIXEL_SCALE_DEG, PIXEL_SCALE_DEG]
        wcs.wcs.pc = [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]

        image = np.full((n, n), spec.zodi, dtype=np.float32)
        yy, xx = np.mgrid[0:n, 0:n]
        for src in self.sources:
            x, y = wcs.world_to_pixel_values(*src.position_at(spec.mjd))
            image += src.flux * np.exp(
                -((xx - x) ** 2 + (yy - y) ** 2) / (2 * PSF_SIGMA_PX**2)
            ).astype(np.float32)

        header = wcs.to_header()
        header["BUNIT"] = "MJy/sr"
        return fits.HDUList(
            [
                fits.PrimaryHDU(),
                fits.ImageHDU(image, header=header, name="IMAGE"),
                fits.ImageHDU(np.zeros((n, n), dtype=np.int32), name="FLAGS"),
                fits.ImageHDU(np.ones((n, n), dtype=np.float32), name="VARIANCE"),
                fits.ImageHDU(np.full((n, n), spec.zodi, dtype=np.float32), name="ZODI"),
            ]
        )
