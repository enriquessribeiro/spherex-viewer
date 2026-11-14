"""Fronteira 1 — pipeline científico com arquivo sintético (docs/06-testes.md §2.1)."""

from pytest import approx

from pipeline.field import build_field
from tests.helpers import centroid
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

# Posição do WISE 0855 (fornecida no desafio), usada só como ponto do céu.
RA0, DEC0 = 133.79513, -7.24515

# Campo de 6' com pixel de 6,15" → grade 59 x 59; centro no pixel 29 (base 0).
CENTRO_PX = 29


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
