"""Montagem de um campo: exposições → épocas → quadros alinhados numa grade comum."""

from __future__ import annotations

import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
from reproject import reproject_interp

from pipeline.archive import Archive, ArchiveUnavailable, Exposure

PIXEL_SCALE_ARCSEC = 6.15
EPOCH_GAP_DAYS = 10.0

# Bits de FLAGS (docs/02-dados-spherex.md), conferidos no cabeçalho de recortes reais.
# Defeito grave — sempre excluído: OVERFLOW, NONFUNC, MISSING_DATA, HOT, COLD.
HARD_BITS = (1, 6, 9, 10, 11)
# Suspeito — excluído se outra exposição tiver aquele ponto limpo; senão usado e marcado
# como low_quality. Em volta de estrelas brilhantes (Barnard's Star) TODAS as exposições
# vêm com TRANSIENT/SUR_ERROR, mas os valores são bons: mascarar apagaria a estrela.
SOFT_BITS = (0, 2, 15, 19)  # TRANSIENT, SUR_ERROR, NONLINEAR, OUTLIER
# SOURCE (21) não é mascarado (marca estrelas); PERSIST (17), CROSSTALK (20) e
# fantasmas/artefatos (22-28) viram overlay.
HARD_MASK = sum(1 << b for b in HARD_BITS)
SOFT_MASK = sum(1 << b for b in SOFT_BITS)
OVERFLOW_BIT = 1

# Downloads simultâneos do arquivo. O IRSA responde 503 com poucos pedidos paralelos,
# então o limite é baixo e o adaptador repete com espera (pipeline/irsa.py).
DEFAULT_MAX_WORKERS = 4

# Recorte pedido ao arquivo = 1,5 × o campo (com o detector girado, cobre a diagonal √2).
CUTOUT_FACTOR = 1.5

# Fração mínima de pixels válidos na vizinhança interpolada para aceitar o valor.
MIN_VALID_WEIGHT = 0.5


@dataclass
class Frame:
    """Quadro de uma época num detector, na grade do campo (linha 0 = sul)."""

    data: np.ndarray
    variance: np.ndarray
    n_exposures: int
    background: float = 0.0  # fundo residual removido de data (MJy/sr)
    # Pixels que só tinham dados com flag suspeito (ex.: anel de estrela brilhante).
    low_quality: np.ndarray | None = None
    # Núcleo de estrela brilhante que o SPHEREx não entrega (OVERFLOW): data é NaN.
    # O frontend deve pintá-lo com o brilho máximo, não como buraco.
    saturated: np.ndarray | None = None


@dataclass
class _Layer:
    """Uma exposição reprojetada: versão só com pixels limpos e versão aceitando suspeitos."""

    clean: tuple[np.ndarray, np.ndarray]  # (dados, variância)
    soft: tuple[np.ndarray, np.ndarray]
    overflow: np.ndarray  # fração de pixels OVERFLOW na vizinhança interpolada


class NoCoverage(Exception):
    """Nenhuma exposição do SPHEREx cobre a posição pedida."""


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
    failed_exposures: list[Exposure]


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


def build_field(
    ra: float,
    dec: float,
    fov_arcmin: float,
    archive: Archive,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> Field:
    wcs, n = field_grid(ra, dec, fov_arcmin)
    # Recorte um pouco maior que o campo para a reprojeção não perder as bordas.
    size_deg = fov_arcmin / 60 * CUTOUT_FACTOR

    exposures = archive.query(ra, dec)
    if not exposures:
        raise NoCoverage(f"nenhuma exposição SPHEREx cobre ra={ra}, dec={dec}")

    def load(exp: Exposure) -> _Layer | None:
        # Uma exposição indisponível é pulada; não deve derrubar o campo inteiro.
        try:
            return _reproject_exposure(archive.fetch_cutout(exp, ra, dec, size_deg), wcs, n)
        except ArchiveUnavailable:
            return None

    groups = group_epochs(exposures)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # map preserva a ordem: o resultado não depende do paralelismo.
        layers = iter(pool.map(load, [exp for group in groups for exp in group]))
        epochs: list[Epoch] = []
        failed: list[Exposure] = []
        for group in groups:
            stacks: dict[str, list[_Layer]] = defaultdict(list)
            loaded: list[Exposure] = []
            for exp in group:
                layer = next(layers)
                if layer is None:
                    failed.append(exp)
                    continue
                stacks[exp.detector].append(layer)
                loaded.append(exp)
            if loaded:
                frames = {det: _coadd(stack) for det, stack in stacks.items()}
                epochs.append(Epoch(index=len(epochs) + 1, exposures=loaded, frames=frames))

    if not epochs:
        raise ArchiveUnavailable(f"nenhuma das {len(exposures)} exposições pôde ser baixada")

    return Field(
        ra=ra, dec=dec, fov_arcmin=fov_arcmin, wcs=wcs, n=n,
        epochs=epochs, display=_display_limits(epochs), failed_exposures=failed,
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


def _reproject_exposure(hdul, wcs: WCS, n: int) -> _Layer:
    """Exposição na grade do campo, sem luz zodiacal, com máscaras de qualidade."""
    image = hdul["IMAGE"]
    source_wcs = WCS(image.header)
    # IMAGE inclui a luz zodiacal; ZODI é o modelo dela (docs/02-dados-spherex.md).
    data = (image.data - hdul["ZODI"].data).astype(np.float64)
    variance = hdul["VARIANCE"].data.astype(np.float64)
    flags = hdul["FLAGS"].data
    finite = np.isfinite(data) & np.isfinite(variance)
    usable = finite & ((flags & HARD_MASK) == 0)
    clean = usable & ((flags & SOFT_MASK) == 0)

    def reproject(array: np.ndarray) -> np.ndarray:
        out, _ = reproject_interp((array, source_wcs), wcs, shape_out=(n, n))
        return out

    def normalized(valid: np.ndarray, required_weight: np.ndarray | float):
        # Interpolação normalizada: pixels inválidos entram com peso zero em vez de virar
        # NaN, senão a interpolação bilinear espalharia cada NaN para ~4 pixels vizinhos.
        weight = reproject(valid.astype(np.float64))
        with np.errstate(invalid="ignore", divide="ignore"):
            data_out = reproject(np.where(valid, data, 0.0)) / weight
            var_out = reproject(np.where(valid, variance, 0.0)) / weight
        covered = np.isfinite(weight) & (weight >= MIN_VALID_WEIGHT) & (weight >= required_weight - 1e-9)
        data_out[~covered] = np.nan
        var_out[~covered] = np.nan
        return (data_out, var_out), np.nan_to_num(weight)

    soft, soft_weight = normalized(usable, MIN_VALID_WEIGHT)
    # O valor limpo só vale onde nenhum pixel suspeito entra na interpolação; senão
    # pixels de borda usariam só os vizinhos limpos (mais fracos, na asa de uma estrela).
    clean_layer, _ = normalized(clean, soft_weight)
    overflow = reproject((((flags >> OVERFLOW_BIT) & 1) == 1).astype(np.float64))
    return _Layer(clean=clean_layer, soft=soft, overflow=np.nan_to_num(overflow))


def _weighted_mean(pairs: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Média ponderada por 1/variância ignorando NaN; devolve (média, variância, peso total)."""
    data = np.stack([d for d, _ in pairs])
    variance = np.stack([v for _, v in pairs])
    valid = np.isfinite(data) & np.isfinite(variance) & (variance > 0)
    weights = np.where(valid, 1.0 / np.where(valid, variance, 1.0), 0.0)
    total_weight = weights.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = (np.where(valid, data, 0.0) * weights).sum(axis=0) / total_weight
        mean_var = 1.0 / total_weight
    mean[total_weight == 0] = np.nan
    mean_var[total_weight == 0] = np.nan
    return mean, mean_var, total_weight


def _coadd(layers: list[_Layer]) -> Frame:
    """Soma ponderada por 1/variância; pixels suspeitos só onde não há dado limpo."""
    data, variance, clean_weight = _weighted_mean([layer.clean for layer in layers])
    soft_data, soft_var, soft_weight = _weighted_mean([layer.soft for layer in layers])
    low_quality = (clean_weight == 0) & (soft_weight > 0)
    data[low_quality] = soft_data[low_quality]
    variance[low_quality] = soft_var[low_quality]
    saturated = np.isnan(data) & (np.max([layer.overflow for layer in layers], axis=0) >= MIN_VALID_WEIGHT)
    # Fundo residual (o que o modelo ZODI não explica): mediana com corte sigma,
    # que ignora as estrelas. Sem isso a diferença entre épocas fica dominada pelo desnível.
    background = _background(data)
    return Frame(
        data=data - background, variance=variance, n_exposures=len(layers),
        background=background, low_quality=low_quality, saturated=saturated,
    )


def _background(image: np.ndarray) -> float:
    values = image[np.isfinite(image)]
    if values.size == 0:
        return 0.0
    _, median, _ = sigma_clipped_stats(values, sigma=3.0, maxiters=5)
    return float(median)
