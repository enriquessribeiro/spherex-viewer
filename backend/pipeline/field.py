"""Montagem de um campo: exposições → épocas → quadros alinhados numa grade comum."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from astropy.wcs import WCS
from reproject import reproject_interp

from pipeline.archive import Archive, Exposure

PIXEL_SCALE_ARCSEC = 6.15
EPOCH_GAP_DAYS = 10.0

# Bits de FLAGS que indicam pixel inutilizável (docs/02-dados-spherex.md):
# TRANSIENT, HOT, COLD, NONLINEAR, OUTLIER. SOURCE (21) e fantasmas/artefatos
# (22-28) não são mascarados: SOURCE marca estrelas, os demais viram overlay.
BAD_PIXEL_BITS = (0, 10, 11, 15, 19)
BAD_PIXEL_MASK = sum(1 << b for b in BAD_PIXEL_BITS)


@dataclass
class Frame:
    """Quadro de uma época num detector, na grade do campo (linha 0 = sul)."""

    data: np.ndarray
    variance: np.ndarray
    n_exposures: int


@dataclass(frozen=True)
class DisplayLimits:
    """Limites de contraste (MJy/sr) comuns a todas as épocas de um detector."""

    vmin: float
    vmax: float


@dataclass
class Epoch:
    index: int
    exposures: list[Exposure]
    frames: dict[str, Frame]


@dataclass
class Field:
    ra: float
    dec: float
    fov_arcmin: float
    wcs: WCS
    n: int
    epochs: list[Epoch]
    display: dict[str, DisplayLimits]


def field_grid(ra: float, dec: float, fov_arcmin: float) -> tuple[WCS, int]:
    """Grade TAN centrada no campo, norte para cima, leste à esquerda."""
    n = math.ceil(fov_arcmin * 60 / PIXEL_SCALE_ARCSEC)
    scale_deg = PIXEL_SCALE_ARCSEC / 3600
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    wcs.wcs.cdelt = [-scale_deg, scale_deg]
    return wcs, n


def group_epochs(exposures: list[Exposure], gap_days: float = EPOCH_GAP_DAYS) -> list[list[Exposure]]:
    """Agrupa exposições ordenadas no tempo; um intervalo > gap_days inicia nova época."""
    groups: list[list[Exposure]] = []
    for exp in sorted(exposures, key=lambda e: e.mjd):
        if groups and exp.mjd - groups[-1][-1].mjd <= gap_days:
            groups[-1].append(exp)
        else:
            groups.append([exp])
    return groups


def build_field(ra: float, dec: float, fov_arcmin: float, archive: Archive) -> Field:
    wcs, n = field_grid(ra, dec, fov_arcmin)
    # Recorte um pouco maior que o campo para a reprojeção não perder as bordas.
    size_deg = fov_arcmin / 60 * 1.5

    epochs: list[Epoch] = []
    for index, group in enumerate(group_epochs(archive.query(ra, dec)), start=1):
        stacks: dict[str, list[tuple[np.ndarray, np.ndarray]]] = defaultdict(list)
        for exp in group:
            hdul = archive.fetch_cutout(exp, ra, dec, size_deg)
            stacks[exp.detector].append(_reproject_exposure(hdul, wcs, n))
        frames = {det: _coadd(layers) for det, layers in stacks.items()}
        epochs.append(Epoch(index=index, exposures=group, frames=frames))

    return Field(
        ra=ra, dec=dec, fov_arcmin=fov_arcmin, wcs=wcs, n=n,
        epochs=epochs, display=_display_limits(epochs),
    )


def _display_limits(epochs: list[Epoch]) -> dict[str, DisplayLimits]:
    """Limites por detector calculados juntando todas as épocas.

    vmin = percentil 1 (fundo); vmax = máximo, para não saturar estrelas
    brilhantes: a variação de brilho de variáveis como R Draconis precisa
    continuar visível. O frontend aplica esticamento asinh sobre esses limites.
    """
    pixels: dict[str, list[np.ndarray]] = defaultdict(list)
    for epoch in epochs:
        for det, frame in epoch.frames.items():
            pixels[det].append(frame.data[np.isfinite(frame.data)])
    limits = {}
    for det, chunks in pixels.items():
        values = np.concatenate(chunks)
        if values.size == 0:
            continue
        limits[det] = DisplayLimits(vmin=float(np.percentile(values, 1)), vmax=float(values.max()))
    return limits


def _reproject_exposure(hdul, wcs: WCS, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Imagem (sem luz zodiacal, pixels ruins = NaN) e variância na grade do campo."""
    image = hdul["IMAGE"]
    source_wcs = WCS(image.header)
    # IMAGE inclui a luz zodiacal; ZODI é o modelo dela (docs/02-dados-spherex.md).
    data = (image.data - hdul["ZODI"].data).astype(np.float64)
    data[(hdul["FLAGS"].data & BAD_PIXEL_MASK) != 0] = np.nan
    variance = hdul["VARIANCE"].data.astype(np.float64)
    data_out, _ = reproject_interp((data, source_wcs), wcs, shape_out=(n, n))
    var_out, _ = reproject_interp((variance, source_wcs), wcs, shape_out=(n, n))
    return data_out, var_out


def _coadd(layers: list[tuple[np.ndarray, np.ndarray]]) -> Frame:
    """Média ponderada pelo inverso da variância, ignorando NaN."""
    data = np.stack([d for d, _ in layers])
    variance = np.stack([v for _, v in layers])
    valid = np.isfinite(data) & np.isfinite(variance) & (variance > 0)
    weights = np.where(valid, 1.0 / np.where(valid, variance, 1.0), 0.0)
    total_weight = weights.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        coadd = (np.where(valid, data, 0.0) * weights).sum(axis=0) / total_weight
        coadd_var = 1.0 / total_weight
    coadd[total_weight == 0] = np.nan
    coadd_var[total_weight == 0] = np.nan
    return Frame(data=coadd, variance=coadd_var, n_exposures=len(layers))
