"""Fronteira 3 — API HTTP (docs/04-api.md), com arquivo sintético (sem rede)."""

import json
import threading
import time
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from pipeline.archive import ArchiveUnavailable
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

FIELD_SCHEMA = json.loads((Path(__file__).parents[2] / "schemas" / "field.schema.json").read_text())
RA0, DEC0 = 133.79513, -7.24515


class ArquivoControlado:
    """Arquivo sintético que só entrega recortes quando o teste libera; conta as consultas."""

    def __init__(self, exposicoes=None, falha=None):
        self.liberado = threading.Event()
        self.consultas = 0
        self.falha = falha
        self.exposicoes = exposicoes if exposicoes is not None else [
            SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D6", mjd=60980.0),
        ]

    def _inner(self, ra, dec):
        return SyntheticArchive(sources=[SyntheticSource(ra=ra, dec=dec)], exposures=self.exposicoes)

    def query(self, ra, dec):
        self.consultas += 1
        if self.falha:
            raise self.falha
        return self._inner(ra, dec).query(ra, dec)

    def fetch_cutout(self, exposure, ra, dec, size_deg):
        self.liberado.wait(timeout=10)
        return self._inner(ra, dec).fetch_cutout(exposure, ra, dec, size_deg)


def _cliente(tmp_path, arquivo, **kw):
    return TestClient(create_app(archive=arquivo, data_dir=tmp_path, **kw))


def _esperar_pronto(cliente, params, timeout=10):
    fim = time.time() + timeout
    while time.time() < fim:
        r = cliente.get("/api/v1/field", params=params)
        if r.status_code != 202:
            return r
        time.sleep(0.05)
    raise AssertionError("campo não ficou pronto")


PARAMS = {"ra": RA0, "dec": DEC0, "fov": 6}


def test_health(tmp_path):
    r = _cliente(tmp_path, ArquivoControlado()).get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_campo_novo_responde_202_com_progresso_e_depois_200_com_manifesto_valido(tmp_path):
    arquivo = ArquivoControlado()
    cliente = _cliente(tmp_path, arquivo)

    r = cliente.get("/api/v1/field", params=PARAMS)
    assert r.status_code == 202
    corpo = r.json()
    assert corpo["status"] == "processing" and corpo["field_id"] == "133.7951-7.2451_6"
    assert {"stage", "progress", "poll_after_ms"} <= set(corpo)
    assert r.headers["cache-control"] == "no-store"

    arquivo.liberado.set()
    r = _esperar_pronto(cliente, PARAMS)
    assert r.status_code == 200
    jsonschema.validate(r.json(), FIELD_SCHEMA)


def test_pedidos_simultaneos_do_mesmo_campo_compartilham_o_processamento(tmp_path):
    arquivo = ArquivoControlado()
    cliente = _cliente(tmp_path, arquivo)

    for _ in range(3):
        cliente.get("/api/v1/field", params=PARAMS)
    cliente.get("/api/v1/field", params={**PARAMS, "ra": RA0 + 0.00001})  # mesmo field_id
    arquivo.liberado.set()
    _esperar_pronto(cliente, PARAMS)

    assert arquivo.consultas == 1


def test_arquivos_do_campo_sao_servidos_com_cache_imutavel(tmp_path):
    arquivo = ArquivoControlado()
    arquivo.liberado.set()
    cliente = _cliente(tmp_path, arquivo)
    doc = _esperar_pronto(cliente, PARAMS).json()

    caminho = doc["base_url"] + doc["epochs"][0]["frames"]["D6"]["frame"]
    r = cliente.get(f"/api/v1/{caminho}")
    assert r.status_code == 200
    assert len(r.content) == doc["grid"]["n"] ** 2 * 4
    assert r.headers["content-type"] == "application/octet-stream"
    assert "immutable" in r.headers["cache-control"]


@pytest.mark.parametrize(
    "params, codigo",
    [
        ({"ra": RA0, "dec": 95}, "INVALID_COORDS"),
        ({"ra": 400, "dec": DEC0}, "INVALID_COORDS"),
        ({"ra": RA0, "dec": DEC0, "fov": 60}, "FOV_TOO_LARGE"),
        ({"ra": RA0, "dec": DEC0, "fov": 0.5}, "FOV_TOO_SMALL"),
        ({"ra": "abc", "dec": DEC0}, "INVALID_PARAM"),
    ],
)
def test_parametros_invalidos_respondem_400_com_codigo(tmp_path, params, codigo):
    r = _cliente(tmp_path, ArquivoControlado()).get("/api/v1/field", params=params)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == codigo


def test_posicao_sem_cobertura_responde_404(tmp_path):
    arquivo = ArquivoControlado(exposicoes=[])
    r = _esperar_pronto(_cliente(tmp_path, arquivo), PARAMS)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NO_COVERAGE"


def test_arquivo_indisponivel_responde_502(tmp_path):
    arquivo = ArquivoControlado(falha=ArchiveUnavailable("IRSA 503"))
    r = _esperar_pronto(_cliente(tmp_path, arquivo), PARAMS)
    assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_ERROR"


def test_trabalhos_demais_respondem_429_busy(tmp_path):
    cliente = _cliente(tmp_path, ArquivoControlado(), max_jobs=1)
    assert cliente.get("/api/v1/field", params=PARAMS).status_code == 202

    r = cliente.get("/api/v1/field", params={**PARAMS, "ra": RA0 + 1})
    assert r.status_code == 429 and r.json()["error"]["code"] == "BUSY"
    assert "retry-after" in r.headers


def test_cors_liberado_para_embed(tmp_path):
    r = _cliente(tmp_path, ArquivoControlado()).get(
        "/api/v1/health", headers={"Origin": "https://exemplo.org"}
    )
    assert r.headers["access-control-allow-origin"] == "*"


def test_resolve_coordenadas_numericas_sem_chamada_externa(tmp_path):
    def resolvedor(nome):
        raise AssertionError("não deveria consultar serviço externo")

    cliente = _cliente(tmp_path, ArquivoControlado(), resolver=resolvedor)
    r = cliente.get("/api/v1/resolve", params={"name": "08h55m10.831s -07d14m42.53s"})
    assert r.status_code == 200
    assert r.json()["ra"] == pytest.approx(133.79513, abs=1e-5)
    assert r.json()["dec"] == pytest.approx(-7.24515, abs=1e-5)

    r = cliente.get("/api/v1/resolve", params={"name": "133.795 -7.245"})
    assert (r.json()["ra"], r.json()["dec"]) == (133.795, -7.245)


def test_resolve_nome_usa_o_resolvedor_e_404_se_desconhecido(tmp_path):
    def resolvedor(nome):
        return {"ra": 269.452, "dec": 4.693, "pm_ra_masyr": -801.6, "pm_dec_masyr": 10362.4} if "barnard" in nome.lower() else None

    cliente = _cliente(tmp_path, ArquivoControlado(), resolver=resolvedor)
    r = cliente.get("/api/v1/resolve", params={"name": "Barnard's star"})
    assert r.status_code == 200 and r.json()["pm_dec_masyr"] == 10362.4

    r = cliente.get("/api/v1/resolve", params={"name": "objeto inexistente"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_campo_maximo_e_configuravel_para_servidores_com_pouca_memoria(tmp_path):
    cliente = _cliente(tmp_path, ArquivoControlado(), fov_max=10)

    r = cliente.get("/api/v1/field", params={**PARAMS, "fov": 12})
    assert r.status_code == 400 and r.json()["error"]["code"] == "FOV_TOO_LARGE"
    assert "10" in r.json()["error"]["message"]
    assert cliente.get("/api/v1/config").json()["fov_arcmin"]["max"] == 10
    assert cliente.get("/api/v1/field", params={**PARAMS, "fov": 10}).status_code == 202


def test_fov_que_nao_e_um_numero_finito_responde_400(tmp_path):
    r = _cliente(tmp_path, ArquivoControlado()).get("/api/v1/field", params={**PARAMS, "fov": "nan"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_PARAM"


def test_campo_que_passa_do_tempo_maximo_responde_502_e_libera_a_vaga(tmp_path):
    """IRSA pendurado: o trabalho não pode ocupar a vaga para sempre nem deixar o site esperando."""
    agora = [0.0]
    arquivo = ArquivoControlado()  # nunca liberado: o recorte fica pendurado
    cliente = _cliente(tmp_path, arquivo, max_jobs=1, job_timeout_s=60, clock=lambda: agora[0])

    assert cliente.get("/api/v1/field", params=PARAMS).status_code == 202
    agora[0] = 61
    r = cliente.get("/api/v1/field", params=PARAMS)
    assert r.status_code == 502 and r.json()["error"]["code"] == "UPSTREAM_ERROR"
    assert "tempo" in r.json()["error"]["message"]
    # a vaga voltou: outro campo é aceito (202), não 429
    assert cliente.get("/api/v1/field", params={**PARAMS, "ra": RA0 + 1}).status_code == 202
    arquivo.liberado.set()
