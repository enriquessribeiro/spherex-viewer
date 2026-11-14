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
from tests.science.measure import aperture_snr, brightest_stars, fit_flux, fit_gaussian, fit_position

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
MOVEIS = [("wise0855", "D6"), ("barnard", "D2"), ("epsindib", "D2")]


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


RAIO_EXCLUSAO_ALVO_PX = 12  # alvos brilhantes (R Dra) têm halo largo: não usar como "estrela de campo"


def _estrelas_de_campo(field: Field, target: Target, det: str, n: int = 5) -> list[tuple[int, int]]:
    """Estrelas brilhantes do campo, longe do alvo, sem pixels mascarados no núcleo e
    com ajuste gaussiano válido em todas as épocas."""
    frames = [e.frames[det] for e in field.epochs if det in e.frames]
    referencia = max(frames, key=lambda f: f.n_exposures)
    alvo = [prevista_px(field, target, i, det) for i, e in enumerate(field.epochs) if det in e.frames]
    candidatas = [
        (x, y) for x, y in brightest_stars(referencia.data, n=6 * n, exclude=[])
        if all(np.hypot(x - ax, y - ay) > RAIO_EXCLUSAO_ALVO_PX for ax, ay in alvo)
    ]
    limpas = []
    for x, y in candidatas:
        if not all(np.isfinite(f.data[y - 1 : y + 2, x - 1 : x + 2]).all() for f in frames):
            continue
        ajustes = [fit_gaussian(f.data, x, y) for f in frames]
        if all(fl > 0 and np.hypot(gx - x, gy - y) < 1.0 for gx, gy, fl in ajustes):
            limpas.append((x, y))
        if len(limpas) == n:
            break
    return limpas


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


# Variáveis: a mudança de brilho entre épocas precisa superar em muito a oscilação
# das estrelas de campo (fotometria relativa: cancela diferenças de calibração).
K_VARIAVEL = 5.0  # quantas vezes a dispersão das estrelas de campo
VARIACAO_MIN = 0.10  # e pelo menos 10% de mudança


def _maior_variacao(field: Field, det: str, posicao, estrelas) -> tuple[float, float, int, int]:
    """Maior variação de brilho entre épocas, relativa às estrelas de campo.

    Devolve (log da razão normalizada, dispersão robusta das estrelas de campo, época a, época b).
    `posicao(i)` dá o pixel do objeto medido na época i.
    """
    epocas = [i for i, e in enumerate(field.epochs) if det in e.frames and e.frames[det].n_exposures >= 3]
    assert len(epocas) >= 2 and len(estrelas) >= 3

    def fluxos(i):
        data = field.epochs[i].frames[det].data
        return fit_flux(data, *posicao(i)), np.array([fit_flux(data, x, y) for x, y in estrelas])

    medidas = {i: fluxos(i) for i in epocas}
    melhor = None
    for a in epocas:
        for b in epocas:
            if a >= b:
                continue
            log_campo = np.log(medidas[b][1] / medidas[a][1])
            calibracao = np.median(log_campo)  # diferença de calibração entre as épocas
            variacao = np.log(medidas[b][0] / medidas[a][0]) - calibracao
            # Dispersão robusta (MAD): uma estrela de campo que também varie não infla o critério.
            dispersao = 1.4826 * np.median(np.abs(log_campo - calibracao))
            if melhor is None or abs(variacao) > abs(melhor[0]):
                melhor = (variacao, dispersao, a, b)
    return melhor


def _e_variavel(variacao: float, dispersao: float) -> bool:
    return abs(variacao) > np.log(1 + VARIACAO_MIN) and abs(variacao) > K_VARIAVEL * dispersao


@pytest.mark.parametrize("target_id", ["rdra", "rwaur"])
def test_estrela_variavel_muda_de_brilho_entre_epocas(target_id):
    field, target, det = campo(target_id), TARGETS[target_id], "D2"
    estrelas = _estrelas_de_campo(field, target, det)

    variacao, dispersao, a, b = _maior_variacao(
        field, det, lambda i: prevista_px(field, target, i, det), estrelas
    )

    assert _e_variavel(variacao, dispersao), (
        f"épocas {a + 1}-{b + 1}: {np.exp(variacao):.2f}x, dispersão do campo {dispersao:.3f}"
    )


def _significancia(field: Field, det: str, posicao, comparacao) -> float:
    variacao, dispersao, _, _ = _maior_variacao(field, det, posicao, comparacao)
    return abs(variacao) / dispersao


@pytest.mark.parametrize("target_id", ["rdra", "rwaur"])
def test_controle_alvo_e_o_objeto_mais_variavel_do_campo(target_id):
    """O alvo precisa se destacar de TODAS as estrelas de campo, que podem incluir variáveis reais."""
    field, target, det = campo(target_id), TARGETS[target_id], "D2"
    estrelas = _estrelas_de_campo(field, target, det, n=8)

    alvo = _significancia(field, det, lambda i: prevista_px(field, target, i, det), estrelas[:5])
    campo_max = max(
        _significancia(field, det, lambda i, s=s: s, [e for e in estrelas if e != s]) for s in estrelas
    )

    assert alvo > campo_max, f"alvo {alvo:.1f}σ × estrela de campo mais variável {campo_max:.1f}σ"


FRACAO_MAX_CAMPO_VARIAVEL = 0.20  # observado: 4 de 36 (11%), ver docs/08-resultados.md


def test_controle_poucas_estrelas_de_campo_parecem_variaveis():
    """Controle negativo: se um defeito fizesse 'tudo variar', a fração de estrelas comuns
    classificadas como variáveis dispararia. Algumas podem ser variáveis reais (ex.: estrela
    jovem com emissão de raios X no campo de RW Aur; gigantes do bojo no campo da Barnard)."""
    classificadas, total = [], 0
    for target_id in ["wise0855", "barnard", "epsindib", "rwaur", "rdra"]:
        field, target, det = campo(target_id), TARGETS[target_id], "D2"
        estrelas = _estrelas_de_campo(field, target, det, n=8)
        for s in estrelas:
            total += 1
            variacao, dispersao, _, _ = _maior_variacao(field, det, lambda i, s=s: s, [e for e in estrelas if e != s])
            if _e_variavel(variacao, dispersao):
                classificadas.append((target_id, s, round(float(np.exp(variacao)), 2)))

    assert total >= 25
    assert len(classificadas) / total <= FRACAO_MAX_CAMPO_VARIAVEL, classificadas
