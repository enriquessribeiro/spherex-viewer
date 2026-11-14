"""Fronteira 1 — pipeline científico com arquivo sintético (docs/06-testes.md §2.1)."""

import math

from pytest import approx

from pipeline.field import build_field
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
