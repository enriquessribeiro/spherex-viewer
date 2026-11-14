"""Fronteira 4 — contrato de dados: field.json + quadros binários (docs/04-api.md §5)."""

import json
import math
from pathlib import Path

import jsonschema
import numpy as np
import pytest
from PIL import Image

from pipeline.field import build_field
from pipeline.output import data_version, field_id, write_field
from pipeline.targets import Target
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

SCHEMA = json.loads((Path(__file__).parents[2] / "schemas" / "field.schema.json").read_text())
RA0, DEC0 = 133.79513, -7.24515
N, CENTRO = 59, 29


def _estrela(leste_px=0.0, norte_px=0.0, **kw):
    dec = DEC0 + norte_px * 6.15 / 3600
    ra = RA0 + leste_px * 6.15 / 3600 / math.cos(math.radians(DEC0))
    return SyntheticSource(ra=ra, dec=dec, **kw)


def _campo(fontes=None, exposicoes=None):
    exposicoes = exposicoes or [
        SyntheticExposure(det="D6", mjd=60800.0),
        SyntheticExposure(det="D1", mjd=60800.2),
        SyntheticExposure(det="D6", mjd=60980.0),
    ]
    return build_field(RA0, DEC0, 6, SyntheticArchive(sources=fontes or [_estrela()], exposures=exposicoes))


def _ler(path: Path, dtype) -> np.ndarray:
    return np.frombuffer(path.read_bytes(), dtype=dtype).reshape(N, N)


def test_campo_gravado_segue_o_esquema(tmp_path):
    manifesto = write_field(_campo(), tmp_path)

    doc = json.loads(manifesto.read_text())
    jsonschema.validate(doc, SCHEMA)
    assert doc["field_id"] == "133.7951-7.2451_6"
    assert [sorted(e["frames"]) for e in doc["epochs"]] == [["D1", "D6"], ["D6"]]
    assert manifesto == tmp_path / doc["base_url"] / "field.json"


def test_quadro_binario_e_float32_little_endian_com_o_norte_na_primeira_linha(tmp_path):
    manifesto = write_field(_campo(fontes=[_estrela(norte_px=5)]), tmp_path)
    doc = json.loads(manifesto.read_text())
    arquivo = manifesto.parent / doc["epochs"][0]["frames"]["D6"]["frame"]

    assert arquivo.stat().st_size == N * N * 4
    quadro = _ler(arquivo, "<f4")
    linha, coluna = np.unravel_index(np.nanargmax(quadro), quadro.shape)
    assert (linha, coluna) == (CENTRO - 5, CENTRO)  # 5 px ao norte = 5 linhas acima do centro


def test_mascara_marca_saturado_no_bit_0_e_baixa_qualidade_no_bit_1(tmp_path):
    nucleo = tuple((dx, dy, 1, float("nan")) for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)])
    anel = tuple((dx, dy, 0, None) for dx in (-1, 0, 1, 2) for dy in (-1, 0, 1, 2)
                 if not (0 <= dx <= 1 and 0 <= dy <= 1))
    exposicoes = [SyntheticExposure(det="D2", mjd=60800.0 + i * 0.1, flagged=nucleo + anel) for i in range(2)]
    manifesto = write_field(_campo(exposicoes=exposicoes), tmp_path)
    doc = json.loads(manifesto.read_text())

    mascara = _ler(manifesto.parent / doc["epochs"][0]["frames"]["D2"]["mask"], "u1")
    perto = mascara[CENTRO - 3 : CENTRO + 4, CENTRO - 3 : CENTRO + 4]
    assert (perto & 1).any()  # saturado
    assert (perto & 2).any()  # baixa qualidade
    assert not mascara[:10, :10].any()


def test_png_do_quadro_tem_o_tamanho_da_grade(tmp_path):
    manifesto = write_field(_campo(), tmp_path)
    doc = json.loads(manifesto.read_text())

    png = Image.open(manifesto.parent / doc["epochs"][0]["frames"]["D6"]["png"])
    assert png.size == (N, N)
    assert png.mode == "L"


def test_identificador_do_campo_arredonda_coordenadas_quase_iguais():
    # -7.24515 não é exato em binário (-7.2451499...): arredonda para -7.2451, igual ao
    # toFixed(4) do JavaScript, para frontend e backend concordarem.
    assert field_id(133.79513, -7.24515, 6) == "133.7951-7.2451_6"
    assert field_id(133.795131, -7.245149, 6) == "133.7951-7.2451_6"
    assert field_id(5.0, 30.0, 12.5) == "5.0000+30.0000_12.5"


def test_versao_dos_dados_muda_quando_chegam_exposicoes_novas():
    base = [SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D6", mjd=60980.0)]
    antes = _campo(exposicoes=base)
    depois = _campo(exposicoes=base + [SyntheticExposure(det="D6", mjd=61160.0)])

    assert data_version(antes) == data_version(_campo(exposicoes=base))
    assert data_version(antes) != data_version(depois)


def test_alvo_gravado_traz_posicao_prevista_em_cada_epoca(tmp_path):
    alvo = Target(id="teste", name="Teste", ra=RA0, dec=DEC0, pm_dec_masyr=10000.0, ref_mjd=60800.0)
    manifesto = write_field(_campo(), tmp_path, target=alvo)
    doc = json.loads(manifesto.read_text())

    previstas = doc["target"]["predicted_positions"]
    assert [p["epoch"] for p in previstas] == [1, 2]
    # 10″/ano para o norte: em ~180 dias, ~4,9″ ao norte da posição inicial.
    assert (previstas[1]["dec"] - previstas[0]["dec"]) * 3600 == pytest.approx(10.0 * 180 / 365.25, rel=0.02)
