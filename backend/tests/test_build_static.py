"""Dados estáticos dos alvos (docs/04-api.md §6): manifest.json + campos no formato do contrato."""

import json
from pathlib import Path

import jsonschema

from pipeline.build_static import build_static
from pipeline.targets import Target
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

SCHEMAS = Path(__file__).parents[2] / "schemas"
MANIFEST_SCHEMA = json.loads((SCHEMAS / "manifest.schema.json").read_text())
FIELD_SCHEMA = json.loads((SCHEMAS / "field.schema.json").read_text())

ALVOS = [
    Target(id="fria", name="Anã fria", ra=133.79513, dec=-7.24515, default_detector="D6",
           description="Só aparece em D6"),
    Target(id="comum", name="Estrela comum", ra=269.452, dec=4.693),
]


def _arquivo():
    exposicoes = [
        SyntheticExposure(det="D2", mjd=60800.0),
        SyntheticExposure(det="D6", mjd=60800.1),
        SyntheticExposure(det="D2", mjd=60980.0),
        SyntheticExposure(det="D6", mjd=60980.1),
    ]
    # A fonte sintética fica sempre no centro do recorte pedido, qualquer que seja o alvo.
    return _CentroArchive(exposicoes)


class _CentroArchive:
    def __init__(self, exposicoes):
        self.exposicoes = exposicoes

    def _inner(self, ra, dec):
        return SyntheticArchive(sources=[SyntheticSource(ra=ra, dec=dec)], exposures=self.exposicoes)

    def query(self, ra, dec):
        return self._inner(ra, dec).query(ra, dec)

    def fetch_cutout(self, exposure, ra, dec, size_deg):
        return self._inner(ra, dec).fetch_cutout(exposure, ra, dec, size_deg)


def test_manifesto_lista_os_alvos_com_campos_validos(tmp_path):
    manifesto = build_static(ALVOS, _arquivo(), tmp_path)

    doc = json.loads(manifesto.read_text())
    jsonschema.validate(doc, MANIFEST_SCHEMA)
    assert manifesto == tmp_path / "manifest.json"
    assert [t["id"] for t in doc["targets"]] == ["fria", "comum"]
    for entrada in doc["targets"]:
        campo = json.loads((tmp_path / entrada["field"]).read_text())
        jsonschema.validate(campo, FIELD_SCHEMA)
        assert campo["target"]["id"] == entrada["id"]
        assert (tmp_path / entrada["thumbnail"]).exists()


def test_miniatura_usa_o_detector_padrao_do_alvo_na_ultima_epoca(tmp_path):
    doc = json.loads(build_static(ALVOS, _arquivo(), tmp_path).read_text())

    fria, comum = doc["targets"]
    assert fria["default_detector"] == "D6"
    assert fria["thumbnail"].endswith("frames/2/D6.png")
    assert comum["default_detector"] == "D2"
    assert comum["thumbnail"].endswith("frames/2/D2.png")


def test_miniatura_evita_epoca_com_poucas_exposicoes(tmp_path):
    # Como na Barnard's Star real: a última época tem uma única exposição (mais ruidosa).
    exposicoes = [SyntheticExposure(det="D2", mjd=60800.0 + i * 0.1) for i in range(3)] + [
        SyntheticExposure(det="D2", mjd=60980.0)
    ]
    doc = json.loads(build_static([ALVOS[1]], _CentroArchive(exposicoes), tmp_path).read_text())

    assert doc["targets"][0]["thumbnail"].endswith("frames/1/D2.png")
