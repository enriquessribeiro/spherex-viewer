"""Resolvedor SIMBAD contra o serviço real (pytest -m live)."""

import pytest

from api.simbad import simbad_resolver

pytestmark = pytest.mark.live


def test_barnard_resolvido_com_movimento_proprio():
    r = simbad_resolver("NAME Barnard's star")
    assert r["ra"] == pytest.approx(269.452, abs=0.01)
    assert r["pm_dec_masyr"] == pytest.approx(10362.4, abs=1)


def test_nome_inexistente_devolve_none():
    assert simbad_resolver("objeto que nao existe 12345") is None


@pytest.mark.parametrize(
    "digitado, ra",
    [
        ("Barnard's star", 269.452),
        ("barnard's  star", 269.452),
        ("eps Ind B", 331.044),
        ("WISE J085510.83-071442.5", 133.819),
        ("R Dra", 248.168),
        ("RW Aur", 76.957),
    ],
)
def test_nomes_como_o_usuario_digita(digitado, ra):
    assert simbad_resolver(digitado)["ra"] == pytest.approx(ra, abs=0.01)
