"""Fronteira 6 — validação científica com dados reais dos alvos do desafio (docs/06-testes.md §2.6).

Roda o pipeline completo (IRSA real + cache em backend/cache). Os valores esperados vêm
do SIMBAD (targets.yaml), não do pipeline. Tolerâncias calibradas e justificadas em
docs/06-testes.md e docs/08-resultados.md.

    uv run pytest -m science
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from pipeline.cache import CachedArchive
from pipeline.field import Field, build_field
from pipeline.irsa import IrsaArchive
from pipeline.targets import Target, load_targets
from tests.science.measure import aperture_snr, brightest_stars, fit_position

pytestmark = pytest.mark.science

BACKEND = Path(__file__).parents[2]
TARGETS = {t.id: t for t in load_targets(BACKEND.parent / "targets.yaml")}

# Tolerâncias (ver docs/06-testes.md §2.6)
T_POSICAO_PX = 0.5  # erro máximo da posição medida × prevista (WISE 0855: 0,12-0,27 px observado)
T_MOVIMENTO_PX = 0.25  # erro máximo do deslocamento medido × previsto (WISE 0855: 0,09 px observado)
T_PARADA_PX = 0.3  # deslocamento máximo de estrelas de campo entre épocas
SNR_MIN = 5.0  # só épocas em que o alvo é detectado com folga entram na astrometria


@lru_cache(maxsize=None)
def campo(target_id: str) -> Field:
    target = TARGETS[target_id]
    ra, dec = target.field_center()
    archive = CachedArchive(IrsaArchive(), BACKEND / "cache")
    return build_field(ra, dec, target.fov_arcmin, archive)


def prevista_px(field: Field, target: Target, epoch_index: int, det: str) -> tuple[float, float]:
    """Pixel previsto do alvo no quadro: posição propagada até o MJD médio das exposições."""
    epoch = field.epochs[epoch_index]
    mjd = float(np.mean([e.mjd for e in epoch.exposures if e.detector == det]))
    x, y = field.wcs.world_to_pixel_values(*target.position_at(mjd))
    return float(x), float(y)


def epocas_detectadas(field: Field, target: Target, det: str) -> list[int]:
    indices = []
    for i, epoch in enumerate(field.epochs):
        frame = epoch.frames.get(det)
        if frame is None:
            continue
        x, y = prevista_px(field, target, i, det)
        if aperture_snr(frame.data, frame.variance, x, y) >= SNR_MIN:
            indices.append(i)
    return indices


# Alvos que se movem e o detector em que são medidos.
MOVEIS = [("wise0855", "D6"), ("barnard", "D2")]


@pytest.mark.parametrize("target_id, det", MOVEIS)
def test_alvo_aparece_na_posicao_prevista_pelo_movimento_proprio(target_id, det):
    field, target = campo(target_id), TARGETS[target_id]
    epocas = epocas_detectadas(field, target, det)
    assert len(epocas) >= 2, f"{target_id} detectado em {len(epocas)} épocas em {det}"

    for i in epocas:
        frame = field.epochs[i].frames[det]
        px, py = prevista_px(field, target, i, det)
        mx, my = fit_position(frame.data, px, py)
        assert np.hypot(mx - px, my - py) < T_POSICAO_PX, f"época {i + 1}"


@pytest.mark.parametrize("target_id, det", MOVEIS)
def test_alvo_se_desloca_entre_epocas_como_previsto(target_id, det):
    field, target = campo(target_id), TARGETS[target_id]
    primeira, ultima = epocas_detectadas(field, target, det)[0], epocas_detectadas(field, target, det)[-1]

    medidas = []
    previstas = []
    for i in (primeira, ultima):
        px, py = prevista_px(field, target, i, det)
        previstas.append((px, py))
        medidas.append(fit_position(field.epochs[i].frames[det].data, px, py))
    delta_previsto = np.subtract(previstas[1], previstas[0])
    delta_medido = np.subtract(medidas[1], medidas[0])

    assert np.hypot(*delta_previsto) > 2 * T_MOVIMENTO_PX  # o movimento é mensurável
    assert np.hypot(*(delta_medido - delta_previsto)) < T_MOVIMENTO_PX


def _estrelas_de_campo(field: Field, target: Target, det: str, n: int = 5) -> list[tuple[int, int]]:
    """Estrelas brilhantes do campo, longe do alvo e sem pixels mascarados no núcleo."""
    referencia = max(
        (e.frames[det] for e in field.epochs if det in e.frames), key=lambda f: f.n_exposures
    )
    alvo = [prevista_px(field, target, i, det) for i, e in enumerate(field.epochs) if det in e.frames]
    candidatas = brightest_stars(referencia.data, n=3 * n, exclude=alvo)
    limpas = []
    for x, y in candidatas:
        nucleos = [e.frames[det].data[y - 1 : y + 2, x - 1 : x + 2] for e in field.epochs if det in e.frames]
        if all(np.isfinite(nucleo).all() for nucleo in nucleos):
            limpas.append((x, y))
    return limpas[:n]


@pytest.mark.parametrize("target_id", ["wise0855", "barnard", "epsindib", "rwaur", "rdra"])
def test_estrelas_de_campo_ficam_paradas_entre_epocas(target_id):
    """Prova de alinhamento: estrelas distantes não podem 'andar' de uma época para outra."""
    field, target, det = campo(target_id), TARGETS[target_id], "D2"
    estrelas = _estrelas_de_campo(field, target, det)
    assert len(estrelas) >= 3

    for x, y in estrelas:
        posicoes = np.array(
            [fit_position(e.frames[det].data, x, y) for e in field.epochs if det in e.frames]
        )
        desvio = np.hypot(*(posicoes - posicoes.mean(axis=0)).T).max()
        assert desvio < T_PARADA_PX, f"estrela em ({x}, {y}) desviou {desvio:.2f} px"
