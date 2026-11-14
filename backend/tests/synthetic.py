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
    # Espectro plantado: brilho multiplicado por spectrum(λ em µm). None = plano.
    spectrum: object = None
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
    # Pixels marcados em FLAGS: (leste_px, norte_px, bit, valor). A posição é no céu,
    # relativa ao centro do recorte; valor=None mantém o brilho, senão o substitui.
    flagged: tuple[tuple[float, float, int, float | None], ...] = ()
    variance: float = 1.0  # valor de VARIANCE, (MJy/sr)^2
    bias: float = 0.0  # brilho constante somado à IMAGE (não é luz zodiacal)
    flux_scale: float = 1.0  # multiplica o brilho das fontes (estrela variável)
    # Filtro de variação linear: comprimento de onda (µm) no centro do recorte e quanto muda por
    # pixel ao longo das linhas do detector (eixo y), como no SPHEREx. None = sem WCS-WAVE.
    wavelength_um: float | None = None
    wavelength_per_px: float = 0.0
    bandwidth_um: float = 0.03


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

        image = np.full((n, n), spec.zodi + spec.bias, dtype=np.float32)
        yy, xx = np.mgrid[0:n, 0:n]
        for src in self.sources:
            x, y = wcs.world_to_pixel_values(*src.position_at(spec.mjd))
            color = 1.0
            if src.spectrum is not None and spec.wavelength_um is not None:
                color = src.spectrum(_wavelength(spec, n, float(y)))
            image += color * spec.flux_scale * src.flux * np.exp(
                -((xx - x) ** 2 + (yy - y) ** 2) / (2 * PSF_SIGMA_PX**2)
            ).astype(np.float32)

        flags = np.zeros((n, n), dtype=np.int32)
        for east_px, north_px, bit, value in spec.flagged:
            sky_ra = ra + east_px * PIXEL_SCALE_DEG / math.cos(math.radians(dec))
            sky_dec = dec + north_px * PIXEL_SCALE_DEG
            x, y = (int(round(float(v))) for v in wcs.world_to_pixel_values(sky_ra, sky_dec))
            flags[y, x] |= 1 << bit
            if value is not None:
                image[y, x] = value

        header = wcs.to_header()
        header["BUNIT"] = "MJy/sr"
        hdus = [
            fits.PrimaryHDU(),
            fits.ImageHDU(image, header=header, name="IMAGE"),
            fits.ImageHDU(flags, name="FLAGS"),
            fits.ImageHDU(np.full((n, n), spec.variance, dtype=np.float32), name="VARIANCE"),
            fits.ImageHDU(np.full((n, n), spec.zodi, dtype=np.float32), name="ZODI"),
        ]
        if spec.wavelength_um is not None:
            _add_wcs_wave(hdus, spec, n)
        return fits.HDUList(hdus)


def _wavelength(spec: SyntheticExposure, n: int, y: float) -> float:
    """λ no pixel (linha y, base 0) do recorte: linear ao longo das linhas."""
    return spec.wavelength_um + spec.wavelength_per_px * (y - (n - 1) / 2)


def _add_wcs_wave(hdus: list, spec: SyntheticExposure, n: int) -> None:
    """Tabela WCS-WAVE no mesmo formato do SPHEREx (grade 9x9 de λ e largura de banda, WAVE-TAB)."""
    grid = np.round(np.linspace(0, n - 1, 9))  # nós inteiros (base 0): a tabela guarda índices inteiros
    values = np.zeros((9, 9, 2), dtype=np.float32)  # [y, x, (λ, banda)]
    for j, y in enumerate(grid):
        values[j, :, 0] = _wavelength(spec, n, y)
        values[j, :, 1] = spec.bandwidth_um
    table = fits.BinTableHDU.from_columns([
        fits.Column("X", "9J", array=[(grid + 1).astype(np.int32)]),  # índice FITS, base 1
        fits.Column("Y", "9J", array=[(grid + 1).astype(np.int32)]),
        fits.Column("VALUES", "162E", dim="(2,9,9)", array=[values]),
    ], name="WCS-WAVE")
    h = hdus[1].header
    for i, name in ((1, "Wavelength"), (2, "Bandwidth")):
        h[f"CTYPE{i}W"], h[f"CUNIT{i}W"], h[f"CNAME{i}W"] = "WAVE-TAB", "um", name
        h[f"CRPIX{i}W"], h[f"CDELT{i}W"], h[f"CRVAL{i}W"] = 0, 1, 0  # índice da tabela = pixel FITS (base 1)
        h[f"PS{i}_0W"], h[f"PS{i}_1W"], h[f"PS{i}_2W"], h[f"PV{i}_3W"] = "WCS-WAVE", "VALUES", ("X", "Y")[0], i
    h["WCSAXESW"] = 2
    h["PS2_2W"] = "Y"
    hdus.append(table)
