"""Fronteira 1 — pipeline científico com arquivo sintético (docs/06-testes.md §2.1)."""

import math

import numpy as np

import pytest
from pytest import approx

from pipeline.field import NoCoverage, build_field
from tests.helpers import centroid
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

# Posição do WISE 0855 (fornecida no desafio), usada só como ponto do céu.
RA0, DEC0 = 133.79513, -7.24515

# Campo de 6' com pixel de 6,15" → grade 59 x 59; centro no pixel 29 (base 0).
CENTRO_PX = 29
PIXEL_ARCSEC = 6.15


def posicao_no_ceu(leste_px: float, norte_px: float) -> tuple[float, float]:
    """Ponto do céu deslocado do centro do campo, em pixels de 6,15" (leste, norte)."""
    dec = DEC0 + norte_px * PIXEL_ARCSEC / 3600
    ra = RA0 + leste_px * PIXEL_ARCSEC / 3600 / math.cos(math.radians(DEC0))
    return ra, dec


def test_estrela_parada_aparece_no_centro_do_quadro_em_cada_epoca():
    archive = SyntheticArchive(
        sources=[SyntheticSource(ra=RA0, dec=DEC0)],
        exposures=[
            SyntheticExposure(det="D6", mjd=60800.0),
            SyntheticExposure(det="D6", mjd=60980.0),
        ],
    )

    field = build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)

    assert len(field.epochs) == 2
    for epoch in field.epochs:
        x, y = centroid(epoch.frames["D6"].data)
        assert x == approx(CENTRO_PX, abs=0.1)
        assert y == approx(CENTRO_PX, abs=0.1)


def test_estrela_fica_no_mesmo_pixel_com_apontamentos_girados_e_deslocados():
    # Estrela 10 px a leste e 5 px ao norte do centro.
    # Norte para cima e leste à esquerda → esperado x = 29 - 10, y = 29 + 5.
    ra, dec = posicao_no_ceu(leste_px=10, norte_px=5)
    archive = SyntheticArchive(
        sources=[SyntheticSource(ra=ra, dec=dec)],
        exposures=[
            SyntheticExposure(det="D6", mjd=60800.0, rotation_deg=0.0),
            SyntheticExposure(det="D6", mjd=60980.0, rotation_deg=37.0, offset_px=(2.4, -1.7)),
        ],
    )

    field = build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)

    for epoch in field.epochs:
        x, y = centroid(epoch.frames["D6"].data)
        assert x == approx(CENTRO_PX - 10, abs=0.1)
        assert y == approx(CENTRO_PX + 5, abs=0.1)


def test_estrela_com_movimento_proprio_aparece_deslocada_entre_epocas():
    # Em 180 dias a estrela anda 2 px para o norte e 1 px para o leste.
    anos = 180 / 365.25
    estrela = SyntheticSource(
        ra=RA0,
        dec=DEC0,
        pm_north_arcsec_yr=2 * PIXEL_ARCSEC / anos,
        pm_east_arcsec_yr=1 * PIXEL_ARCSEC / anos,
        ref_mjd=60800.0,
    )
    archive = SyntheticArchive(
        sources=[estrela],
        exposures=[
            SyntheticExposure(det="D6", mjd=60800.0),
            SyntheticExposure(det="D6", mjd=60980.0, rotation_deg=-22.0, offset_px=(0.6, 1.3)),
        ],
    )

    field = build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)

    x1, y1 = centroid(field.epochs[0].frames["D6"].data)
    x2, y2 = centroid(field.epochs[1].frames["D6"].data)
    assert (x1, y1) == approx((CENTRO_PX, CENTRO_PX), abs=0.1)
    assert (x2, y2) == approx((CENTRO_PX - 1, CENTRO_PX + 2), abs=0.1)


def _campo_com_exposicoes(exposicoes):
    archive = SyntheticArchive(sources=[SyntheticSource(ra=RA0, dec=DEC0)], exposures=exposicoes)
    return build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)


def test_exposicoes_proximas_no_tempo_formam_uma_epoca_em_ordem_cronologica():
    # Chegam fora de ordem, como pode acontecer numa consulta ao arquivo.
    field = _campo_com_exposicoes(
        [SyntheticExposure(det="D6", mjd=m) for m in (60981.0, 60800.0, 60802.0, 60980.0, 60801.0)]
    )

    assert [e.index for e in field.epochs] == [1, 2]
    assert [[x.mjd for x in e.exposures] for e in field.epochs] == [
        [60800.0, 60801.0, 60802.0],
        [60980.0, 60981.0],
    ]
    assert [e.frames["D6"].n_exposures for e in field.epochs] == [3, 2]


def test_intervalo_igual_ao_limite_de_10_dias_nao_separa_epocas():
    juntas = _campo_com_exposicoes(
        [SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D6", mjd=60810.0)]
    )
    separadas = _campo_com_exposicoes(
        [SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D6", mjd=60810.01)]
    )

    assert len(juntas.epochs) == 1
    assert len(separadas.epochs) == 2


def test_epoca_sem_algum_detector_contem_apenas_os_detectores_observados():
    field = _campo_com_exposicoes(
        [
            SyntheticExposure(det="D1", mjd=60800.0),
            SyntheticExposure(det="D6", mjd=60800.1),
            SyntheticExposure(det="D6", mjd=60980.0),
        ]
    )

    assert set(field.epochs[0].frames) == {"D1", "D6"}
    assert set(field.epochs[1].frames) == {"D6"}


def test_luz_zodiacal_e_subtraida_do_quadro():
    # Como no SPHEREx real: IMAGE inclui a luz zodiacal e ZODI traz o modelo dela.
    field = _campo_com_exposicoes(
        [
            SyntheticExposure(det="D6", mjd=60800.0, zodi=5.0),
            SyntheticExposure(det="D6", mjd=60800.5, zodi=7.0, rotation_deg=15.0),
        ]
    )

    quadro = field.epochs[0].frames["D6"].data
    canto = quadro[:10, :10]  # longe da estrela no centro
    assert np.nanmedian(canto) == approx(0.0, abs=1e-3)


HOT, SOURCE = 10, 21


def test_pixel_com_defeito_e_ignorado_na_soma():
    # Pixel HOT com valor absurdo numa exposição, 8 px a oeste e 6 px ao sul do centro.
    field = _campo_com_exposicoes(
        [
            SyntheticExposure(det="D6", mjd=60800.0, flagged=((-8, -6, HOT, 1e4),)),
            SyntheticExposure(det="D6", mjd=60800.5),
        ]
    )

    quadro = field.epochs[0].frames["D6"].data
    # Oeste fica à direita: x = 29 + 8; sul fica abaixo: y = 29 - 6.
    vizinhanca = quadro[CENTRO_PX - 6 - 1 : CENTRO_PX - 6 + 2, CENTRO_PX + 8 - 1 : CENTRO_PX + 8 + 2]
    assert np.nanmax(vizinhanca) < 1.0


def test_pixel_marcado_como_fonte_conhecida_nao_e_mascarado():
    field = _campo_com_exposicoes(
        [
            SyntheticExposure(det="D6", mjd=60800.0, flagged=((0, 0, SOURCE, None),)),
            SyntheticExposure(det="D6", mjd=60800.5, flagged=((0, 0, SOURCE, None),)),
        ]
    )

    quadro = field.epochs[0].frames["D6"].data
    janela = quadro[CENTRO_PX - 5 : CENTRO_PX + 6, CENTRO_PX - 5 : CENTRO_PX + 6]
    # Fluxo total da gaussiana plantada (pico 100, sigma 1 px) = 2*pi*sigma^2*100.
    assert np.nansum(janela) == approx(2 * math.pi * 100.0, rel=0.02)


def _campo_vazio(exposicoes):
    archive = SyntheticArchive(sources=[], exposures=exposicoes)
    return build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)


def test_soma_pondera_cada_exposicao_pelo_inverso_da_variancia():
    field = _campo_vazio(
        [
            SyntheticExposure(det="D6", mjd=60800.0, bias=2.0, variance=1.0),
            SyntheticExposure(det="D6", mjd=60800.5, bias=4.0, variance=3.0),
        ]
    )

    frame = field.epochs[0].frames["D6"]
    # (2/1 + 4/3) / (1/1 + 1/3) = 2,5  (a média simples daria 3)
    assert np.nanmedian(frame.data) == approx(2.5, abs=1e-6)
    # 1 / (1/1 + 1/3) = 0,75
    assert np.nanmedian(frame.variance) == approx(0.75, abs=1e-6)


def test_variancia_do_quadro_cai_com_o_numero_de_exposicoes():
    field = _campo_vazio(
        [SyntheticExposure(det="D6", mjd=60800.0 + i * 0.1, variance=4.0) for i in range(9)]
    )

    # 9 exposições de variância 4 → 4/9 (ruído σ/√N)
    assert np.nanmedian(field.epochs[0].frames["D6"].variance) == approx(4 / 9, abs=1e-6)


def test_estrela_variavel_mantem_a_diferenca_de_brilho_com_o_contraste_do_campo():
    # Estrela variável (como R Draconis): brilho 100 na época 1 e 50 na época 2.
    field = _campo_com_exposicoes(
        [
            SyntheticExposure(det="D6", mjd=60800.0, flux_scale=1.0),
            SyntheticExposure(det="D6", mjd=60980.0, flux_scale=0.5),
        ]
    )

    limites = field.display["D6"]  # um único par de limites para todas as épocas do detector

    def brilho_exibido(epoca):
        pico = np.nanmax(field.epochs[epoca].frames["D6"].data)
        return np.clip((pico - limites.vmin) / (limites.vmax - limites.vmin), 0, 1)

    assert brilho_exibido(1) / brilho_exibido(0) == approx(0.5, abs=0.02)


def test_posicao_sem_exposicoes_gera_erro_de_cobertura():
    archive = SyntheticArchive(sources=[], exposures=[])

    with pytest.raises(NoCoverage):
        build_field(ra=RA0, dec=DEC0, fov_arcmin=6, archive=archive)


@pytest.mark.parametrize("fov, lado", [(1, 10), (6, 59), (30, 293)])
def test_grade_do_campo_tem_o_tamanho_do_contrato_da_api(fov, lado):
    field = build_field(
        ra=RA0, dec=DEC0, fov_arcmin=fov,
        archive=SyntheticArchive(sources=[], exposures=[SyntheticExposure(det="D6", mjd=60800.0)]),
    )

    assert field.n == lado
    assert field.epochs[0].frames["D6"].data.shape == (lado, lado)
