"""Fronteira 2 — adaptador do IRSA com respostas reais gravadas (docs/06-testes.md §2.2)."""

from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from pipeline.field import group_epochs
from pipeline.irsa import IrsaArchive

FIXTURES = Path(__file__).parent / "fixtures" / "irsa"
RA0, DEC0 = 133.79513, -7.24515


def _cliente(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_consulta_gravada_do_wise0855_vira_258_exposicoes_em_4_epocas():
    consultas = []

    def handler(request: httpx.Request) -> httpx.Response:
        consultas.append(parse_qs(request.content.decode())["QUERY"][0])
        return httpx.Response(200, content=(FIXTURES / "wise0855_tap.csv").read_bytes())

    exposicoes = IrsaArchive(client=_cliente(handler)).query(RA0, DEC0)

    assert len(exposicoes) == 258
    assert Counter(e.detector for e in exposicoes) == {
        "D1": 36, "D2": 48, "D3": 45, "D4": 36, "D5": 48, "D6": 45,
    }
    assert [len(g) for g in group_epochs(exposicoes)] == [30, 110, 18, 100]
    # A consulta usa a posição pedida e as coleções configuradas.
    assert "133.79513" in consultas[0] and "-7.24515" in consultas[0]
    assert "spherex_dr1" in consultas[0] and "spherex_qr3" in consultas[0]


def test_exposicao_guarda_identificador_legivel_e_caminho_do_arquivo():
    def handler(request):
        return httpx.Response(200, content=(FIXTURES / "wise0855_tap.csv").read_bytes())

    primeira = IrsaArchive(client=_cliente(handler)).query(RA0, DEC0)[0]

    assert primeira.id == "2025W19_1B_0116_1D3"
    assert primeira.detector == "D3"
    assert primeira.mjd == pytest.approx(60800.700028)
    assert primeira.collection == "spherex_dr1"
    assert primeira.uri.endswith("level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits")
