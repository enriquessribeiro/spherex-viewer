"""Medições independentes usadas pelos testes para verificar os quadros."""

import numpy as np


def centroid(image: np.ndarray, half_window: int = 3) -> tuple[float, float]:
    """Centroide (x, y) da fonte mais brilhante, em pixels base 0.

    Média ponderada pelo brilho numa janela em volta do pixel de máximo.
    Implementação propositalmente simples e independente do pipeline.
    """
    data = np.nan_to_num(image, nan=0.0)
    y0, x0 = np.unravel_index(np.argmax(data), data.shape)
    ys = slice(max(y0 - half_window, 0), y0 + half_window + 1)
    xs = slice(max(x0 - half_window, 0), x0 + half_window + 1)
    win = data[ys, xs]
    yy, xx = np.mgrid[ys, xs]
    total = win.sum()
    return float((xx * win).sum() / total), float((yy * win).sum() / total)
