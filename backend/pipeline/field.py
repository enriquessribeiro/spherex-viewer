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


@dataclass
class Frame:
    """Quadro de uma época num detector, na grade do campo (linha 0 = sul)."""

    data: np.ndarray
    n_exposures: int


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
        stacks: dict[str, list[np.ndarray]] = defaultdict(list)
        for exp in group:
            hdul = archive.fetch_cutout(exp, ra, dec, size_deg)
            image = hdul["IMAGE"]
            reprojected, _ = reproject_interp(
                (image.data, WCS(image.header)), wcs, shape_out=(n, n)
            )
            stacks[exp.detector].append(reprojected)
        frames = {
            det: Frame(data=np.nanmean(images, axis=0), n_exposures=len(images))
            for det, images in stacks.items()
        }
        epochs.append(Epoch(index=index, exposures=group, frames=frames))

    return Field(ra=ra, dec=dec, fov_arcmin=fov_arcmin, wcs=wcs, n=n, epochs=epochs)
