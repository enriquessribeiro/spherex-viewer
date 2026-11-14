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


def _fits_real_com_epsf() -> bytes:
    """Recorte real gravado + uma extensão EPSF falsa, como vem do IRSA."""
    import io

    import numpy as np
    from astropy.io import fits

    hdul = fits.open(FIXTURES / "wise0855_D1_epoca1.fits")
    hdul.insert(5, fits.BinTableHDU.from_columns(
        [fits.Column(name="PSF", format="E", array=np.zeros(3))], name="EPSF"
    ))
    buffer = io.BytesIO()
    hdul.writeto(buffer)
    return buffer.getvalue()


def _exposicao_d1():
    from pipeline.archive import Exposure

    return Exposure(
        id="2025W19_1B_0241_1D1", detector="D1", mjd=60801.514,
        uri="ibe/data/spherex/dr1/level2/2025W19_1B/l2b-v27-2026-197/1/"
            "level2_2025W19_1B_0241_1D1_spx_l2b-v27-2026-197.fits",
        collection="spherex_dr1",
    )


def test_recorte_real_e_baixado_pela_url_de_cutout_e_lido_sem_a_epsf():
    pedidos = []

    def handler(request):
        pedidos.append(request.url)
        return httpx.Response(200, content=_fits_real_com_epsf())

    hdul = IrsaArchive(client=_cliente(handler)).fetch_cutout(_exposicao_d1(), RA0, DEC0, 0.15)

    url = pedidos[0]
    assert url.path == "/" + _exposicao_d1().uri
    assert url.params["center"] == "133.79513,-7.24515d"
    assert url.params["size"] == "0.15"
    nomes = [h.name for h in hdul]
    assert {"IMAGE", "FLAGS", "VARIANCE", "ZODI"} <= set(nomes)
    assert "EPSF" not in nomes
    assert hdul["IMAGE"].header["BUNIT"] == "MJy / sr"


def test_servidor_ocupado_e_tentado_de_novo_com_espera_crescente():
    respostas = iter([503, 503, 200])
    esperas = []

    def handler(request):
        status = next(respostas)
        conteudo = _fits_real_com_epsf() if status == 200 else b"Server busy, retry later."
        return httpx.Response(status, content=conteudo)

    archive = IrsaArchive(client=_cliente(handler), sleep=esperas.append)
    hdul = archive.fetch_cutout(_exposicao_d1(), RA0, DEC0, 0.15)

    assert "IMAGE" in [h.name for h in hdul]
    assert len(esperas) == 2
    assert esperas[1] > esperas[0]


def test_servidor_ocupado_sempre_gera_erro_de_arquivo_indisponivel():
    from pipeline.irsa import ArchiveUnavailable

    def handler(request):
        return httpx.Response(503, content=b"Server busy, retry later.")

    archive = IrsaArchive(client=_cliente(handler), sleep=lambda s: None, max_attempts=4)

    with pytest.raises(ArchiveUnavailable):
        archive.fetch_cutout(_exposicao_d1(), RA0, DEC0, 0.15)


SIA_HEADER = (FIXTURES / "wise0855_sia_dr1.csv").read_text().splitlines()[0] + "\n"


def _irsa_com_tap_fora(pedidos, sia_status=200):
    """IRSA como em 14/11/2026: TAP respondendo 502 e SIA no ar."""

    def handler(request: httpx.Request) -> httpx.Response:
        pedidos.append(request.url)
        if request.url.path == "/TAP/sync":
            return httpx.Response(502, content=b"Proxy Error")
        if sia_status != 200:
            return httpx.Response(sia_status, content=b"Proxy Error")
        if request.url.params["COLLECTION"] == "spherex_dr1":
            return httpx.Response(200, content=(FIXTURES / "wise0855_sia_dr1.csv").read_bytes())
        return httpx.Response(200, content=SIA_HEADER.encode())  # coleção sem dados nessa posição

    return IrsaArchive(client=_cliente(handler), sleep=lambda s: None)


def test_com_o_tap_fora_do_ar_a_consulta_usa_o_sia_e_devolve_as_mesmas_exposicoes():
    pedidos = []
    exposicoes = _irsa_com_tap_fora(pedidos).query(133.76002, -7.24221)

    # Valores esperados: o que o TAP devolveu para esta posição antes de cair.
    assert len(exposicoes) == 258
    assert Counter(e.detector for e in exposicoes) == {
        "D1": 36, "D2": 48, "D3": 45, "D4": 36, "D5": 48, "D6": 45,
    }
    assert [e.mjd for e in exposicoes] == sorted(e.mjd for e in exposicoes)
    primeira = exposicoes[0]
    assert (primeira.id, primeira.detector, primeira.collection) == ("2025W19_1B_0116_1D3", "D3", "spherex_dr1")
    assert primeira.mjd == pytest.approx(60800.700028)
    assert primeira.uri == (
        "ibe/data/spherex/dr1/level2/2025W19_1B/l2b-v27-2026-197/3/"
        "level2_2025W19_1B_0116_1D3_spx_l2b-v27-2026-197.fits"
    )
    # Uma consulta SIA por coleção configurada, com a posição pedida.
    sia = [u for u in pedidos if u.path == "/SIA"]
    assert sorted(u.params["COLLECTION"] for u in sia) == ["spherex_dr1", "spherex_qr3"]
    assert sia[0].params["POS"].startswith("circle 133.76002 -7.24221 ")


def test_com_o_tap_fora_do_ar_nao_se_gasta_mais_de_duas_tentativas_antes_do_sia():
    pedidos = []
    _irsa_com_tap_fora(pedidos).query(133.76002, -7.24221)

    assert len([u for u in pedidos if u.path == "/TAP/sync"]) == 2


def test_tap_e_sia_fora_do_ar_geram_erro_de_arquivo_indisponivel():
    from pipeline.irsa import ArchiveUnavailable

    with pytest.raises(ArchiveUnavailable):
        _irsa_com_tap_fora([], sia_status=502).query(133.76002, -7.24221)
