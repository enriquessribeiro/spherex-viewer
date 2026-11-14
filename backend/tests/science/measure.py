"""Medidas simples e independentes do pipeline, usadas na validação científica."""

from __future__ import annotations

import numpy as np


def centroid_near(image: np.ndarray, x0: float, y0: float, radius: int = 2) -> tuple[float, float]:
    """Centroide (x, y) ponderado pelo brilho positivo numa janela em volta de (x0, y0)."""
    xi, yi = int(round(x0)), int(round(y0))
    ys, xs = slice(yi - radius, yi + radius + 1), slice(xi - radius, xi + radius + 1)
    window = np.nan_to_num(image[ys, xs]).clip(min=0)
    yy, xx = np.mgrid[ys, xs]
    return float((xx * window).sum() / window.sum()), float((yy * window).sum() / window.sum())


def aperture_snr(image: np.ndarray, variance: np.ndarray, x0: float, y0: float, radius: float = 1.5) -> float:
    """Sinal/ruído da soma numa abertura circular (o fundo já foi removido pelo pipeline)."""
    yy, xx = np.mgrid[: image.shape[0], : image.shape[1]]
    inside = ((xx - x0) ** 2 + (yy - y0) ** 2 <= radius**2) & np.isfinite(image) & np.isfinite(variance)
    return float(image[inside].sum() / np.sqrt(variance[inside].sum()))


def aperture_flux(image: np.ndarray, x0: float, y0: float, radius: float = 3.0) -> float:
    """Soma do brilho numa abertura circular (MJy/sr × pixels)."""
    yy, xx = np.mgrid[: image.shape[0], : image.shape[1]]
    inside = ((xx - x0) ** 2 + (yy - y0) ** 2 <= radius**2) & np.isfinite(image)
    return float(image[inside].sum())


def brightest_stars(image: np.ndarray, n: int, exclude: list[tuple[float, float]], min_sep: float = 6) -> list[tuple[int, int]]:
    """Picos locais mais brilhantes, longe das bordas e das posições excluídas."""
    data = np.nan_to_num(image, nan=-np.inf)
    size = data.shape[0]
    found: list[tuple[int, int]] = []
    for flat in np.argsort(data, axis=None)[::-1]:
        y, x = np.unravel_index(flat, data.shape)
        if not (4 <= x < size - 4 and 4 <= y < size - 4):
            continue
        if any(np.hypot(x - ex, y - ey) < min_sep for ex, ey in exclude + found):
            continue
        found.append((int(x), int(y)))
        if len(found) == n:
            break
    return found
