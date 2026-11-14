"""Espectro sob demanda de um alvo (docs/04-api.md §4.8).

O SPHEREx observa por um filtro de variação linear: o comprimento de onda muda ao longo das linhas
do detector. Cada exposição vê o alvo num λ diferente, e juntando todas sai um espectro de
0,75 a 5 µm. Para cada exposição:

1. posição do alvo na data da exposição (objetos próximos andam vários ″/ano);
2. fotometria de abertura (raio APERTURE_PX) sobre IMAGE − ZODI, com o fundo local medido num anel;
3. comprimento de onda e largura de banda no pixel do alvo, pela tabela WCS-WAVE.

Limitação: a WCS-WAVE é "para visualização" segundo a documentação do SPHEREx (docs/02 §2);
serve para o gráfico do site, não para ciência de precisão. O fluxo é o da abertura, sem correção
pela PSF: a forma do espectro é confiável, o valor absoluto fica alguns % abaixo do total.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area
from scipy import ndimage

from pipeline.archive import Archive, ArchiveUnavailable, Exposure
from pipeline.field import HARD_MASK, PIXEL_SCALE_ARCSEC, SOFT_MASK, Field

log = logging.getLogger(__name__)

# 12″ (2 px). Uma abertura maior junta mais vizinhas e mais ruído: no WISE 0855 real há uma
# estrela a 9″; com 3 px o fluxo em D1–D3 era todo dela, e o S/R em D6 ficava abaixo de 2.
APERTURE_PX = 2.0
ANNULUS_PX = (5.0, 8.0)  # anel do fundo local
MIN_ANNULUS_PIXELS = 20
_SIP_PREFIXES = ("A_", "B_", "AP_", "BP_")


@dataclass(frozen=True)
class SpectrumPoint:
    wavelength_um: float
    bandwidth_um: float
    flux_ujy: float
    flux_err_ujy: float
    detector: str
    mjd: float
    exposure_id: str
    flagged: bool  # algum pixel da abertura tinha aviso de qualidade (TRANSIENT, NONLINEAR...)


def measure_spectrum(
    archive: Archive,
    exposures: Iterable[Exposure],
    ra: float,
    dec: float,
    size_deg: float,
    position_at: Callable[[float], tuple[float, float]],
) -> list[SpectrumPoint]:
    """Um ponto por exposição em que o alvo foi medido. (ra, dec, size_deg) é o recorte pedido ao
    arquivo, o mesmo do campo, para reaproveitar o cache. Exposições sem dado limpo são puladas."""
    points = []
    for exp in exposures:
        try:
            hdul = archive.fetch_cutout(exp, ra, dec, size_deg)
        except ArchiveUnavailable:
            continue
        try:
            point = _measure(hdul, exp, *position_at(exp.mjd))
        finally:
            hdul.close()
        if point is not None:
            points.append(point)
    return sorted(points, key=lambda p: p.wavelength_um)


def _measure(hdul: fits.HDUList, exp: Exposure, ra: float, dec: float) -> SpectrumPoint | None:
    if "WCS-WAVE" not in hdul:
        return None
    header = hdul["IMAGE"].header
    sky = WCS(header)
    x, y = (float(v) for v in sky.world_to_pixel_values(ra, dec))
    data = (hdul["IMAGE"].data - hdul["ZODI"].data).astype(np.float64)
    variance = hdul["VARIANCE"].data.astype(np.float64)
    flags = hdul["FLAGS"].data
    ny, nx = data.shape
    if not (APERTURE_PX <= x <= nx - 1 - APERTURE_PX and APERTURE_PX <= y <= ny - 1 - APERTURE_PX):
        return None

    yy, xx = np.mgrid[0:ny, 0:nx]
    r = np.hypot(xx - x, yy - y)
    aperture = r <= APERTURE_PX
    if not np.all(np.isfinite(data[aperture]) & np.isfinite(variance[aperture])):
        return None  # núcleo saturado (sem dado) ou pixel faltando: o fluxo sairia errado
    if np.any(flags[aperture] & HARD_MASK):
        return None  # pixel quente, morto...

    ring = (r >= ANNULUS_PX[0]) & (r <= ANNULUS_PX[1]) & np.isfinite(data) & np.isfinite(variance) \
        & ((flags & HARD_MASK) == 0)
    if ring.sum() < MIN_ANNULUS_PIXELS:
        return None
    _, background, _ = sigma_clipped_stats(data[ring], sigma=3.0, maxiters=5)

    pixel_sr = proj_plane_pixel_area(sky.celestial) * math.radians(1) ** 2
    to_ujy = pixel_sr * 1e12  # MJy/sr × sr = MJy → µJy
    n_ap = int(aperture.sum())
    flux = float(np.sum(data[aperture] - background)) * to_ujy
    # Ruído: variância dos pixels da abertura + a incerteza do fundo, que entra n_ap vezes.
    var_background = float(np.mean(variance[ring])) / int(ring.sum())
    err = math.sqrt(float(np.sum(variance[aperture])) + n_ap**2 * var_background) * to_ujy

    wavelength, bandwidth = _wavelength_at(hdul, x, y)
    if not (math.isfinite(wavelength) and wavelength > 0):
        return None
    return SpectrumPoint(
        wavelength_um=wavelength, bandwidth_um=bandwidth, flux_ujy=flux, flux_err_ujy=err,
        detector=exp.detector, mjd=exp.mjd, exposure_id=exp.id,
        flagged=bool(np.any(flags[aperture] & SOFT_MASK)),
    )


def _wavelength_at(hdul: fits.HDUList, x: float, y: float) -> tuple[float, float]:
    """λ e largura de banda (µm) no pixel (base 0), pela WCS "W" (tabela WCS-WAVE)."""
    # A WCS espectral não usa a distorção SIP do céu (docs/02); tirá-la evita o aviso do Astropy.
    header = hdul["IMAGE"].header.copy()
    for key in [k for k in header if k.startswith(_SIP_PREFIXES) or k in ("A_ORDER", "B_ORDER")]:
        del header[key]
    spectral = WCS(header, fobj=hdul, key="W")
    wavelength, bandwidth = spectral.pixel_to_world_values(x, y)
    return float(wavelength), float(bandwidth)


# Fonte detectada a menos disso do alvo é o próprio alvo (o centroide varia de época para época).
SELF_RADIUS_PX = 1.0
NEIGHBOR_SNR = 5.0


def neighbors_in_aperture(field: Field, position_at: Callable[[float], tuple[float, float]]) -> list[dict]:
    """Fontes que não são o alvo e caem na abertura (ou na borda dela), por detector.

    Com pixels de 6,15″, uma estrela a ~10″ entra na abertura e o fluxo medido passa a ser dela
    nos comprimentos de onda em que é mais brilhante que o alvo. Usa a época com mais exposições
    de cada detector (a mais profunda). Devolve a mais próxima por detector, para o site avisar.
    """
    found = []
    for det in sorted({d for e in field.epochs for d in e.frames}):
        epoch = max((e for e in field.epochs if det in e.frames), key=lambda e: e.frames[det].n_exposures)
        frame = epoch.frames[det]
        mjd = float(np.mean([x.mjd for x in epoch.exposures if x.detector == det]))
        x0, y0 = (float(v) for v in field.wcs.world_to_pixel_values(*position_at(mjd)))
        with np.errstate(invalid="ignore", divide="ignore"):
            snr = np.nan_to_num(frame.data / np.sqrt(frame.variance))
        peaks = (snr == ndimage.maximum_filter(snr, size=3)) & (snr > NEIGHBOR_SNR)
        rows, cols = (np.array(v, dtype=float) for v in zip(*[_centroid(frame.data, r, c) for r, c in zip(*np.nonzero(peaks))])) \
            if peaks.any() else (np.array([]), np.array([]))
        dist = np.hypot(cols - x0, rows - y0)
        near = (dist > SELF_RADIUS_PX) & (dist <= APERTURE_PX + 1.0)
        if near.any():
            k = int(np.argmin(np.where(near, dist, np.inf)))
            peak_snr = snr[int(round(rows[k])), int(round(cols[k]))]
            found.append({"detector": det, "distance_arcsec": round(float(dist[k]) * PIXEL_SCALE_ARCSEC, 1),
                          "snr": round(float(peak_snr), 1)})
    return found


def _centroid(data: np.ndarray, r: int, c: int) -> tuple[float, float]:
    """Centroide 3×3 em volta de um pico: a posição sem ficar presa à grade de pixels."""
    win = np.nan_to_num(data[max(r - 1, 0):r + 2, max(c - 1, 0):c + 2]).clip(min=0)
    if win.sum() <= 0:
        return float(r), float(c)
    yy, xx = np.mgrid[max(r - 1, 0):max(r - 1, 0) + win.shape[0], max(c - 1, 0):max(c - 1, 0) + win.shape[1]]
    return float((yy * win).sum() / win.sum()), float((xx * win).sum() / win.sum())
