"""Cache em disco do arquivo (parte da fronteira 2: o que o pipeline vê é igual, só não repete downloads)."""

import numpy as np

from pipeline.cache import CachedArchive
from tests.synthetic import SyntheticArchive, SyntheticExposure, SyntheticSource

RA0, DEC0 = 133.79513, -7.24515


class Contador:
    """Arquivo sintético que conta quantas consultas recebeu."""

    def __init__(self):
        self.inner = SyntheticArchive(
            sources=[SyntheticSource(ra=RA0, dec=DEC0)],
            exposures=[SyntheticExposure(det="D6", mjd=60800.0), SyntheticExposure(det="D1", mjd=60801.0)],
        )
        self.queries = 0

    def query(self, ra, dec):
        self.queries += 1
        return self.inner.query(ra, dec)

    def fetch_cutout(self, exposure, ra, dec, size_deg):
        return self.inner.fetch_cutout(exposure, ra, dec, size_deg)


def test_recorte_repetido_vem_do_disco_mesmo_em_outro_processo(tmp_path):
    origem = Contador()
    exp = origem.query(RA0, DEC0)[0]

    primeiro = CachedArchive(origem, tmp_path).fetch_cutout(exp, RA0, DEC0, 0.15)
    # Nova instância = novo processo; só o disco é compartilhado.
    segundo = CachedArchive(origem, tmp_path).fetch_cutout(exp, RA0, DEC0, 0.15)

    assert origem.inner.fetch_calls == [exp.id]
    np.testing.assert_array_equal(primeiro["IMAGE"].data, segundo["IMAGE"].data)
    assert segundo["IMAGE"].header["BUNIT"] == "MJy/sr"


def test_outro_centro_ou_tamanho_e_outro_recorte(tmp_path):
    origem = Contador()
    exp = origem.query(RA0, DEC0)[0]
    cache = CachedArchive(origem, tmp_path)

    cache.fetch_cutout(exp, RA0, DEC0, 0.15)
    cache.fetch_cutout(exp, RA0 + 0.01, DEC0, 0.15)
    cache.fetch_cutout(exp, RA0, DEC0, 0.3)

    assert len(origem.inner.fetch_calls) == 3


def test_consulta_fica_em_cache_por_24_horas(tmp_path):
    origem = Contador()
    agora = [1_000_000.0]
    cache = CachedArchive(origem, tmp_path, query_ttl_s=24 * 3600, clock=lambda: agora[0])

    primeira = cache.query(RA0, DEC0)
    agora[0] += 23 * 3600
    assert cache.query(RA0, DEC0) == primeira
    assert origem.queries == 1

    agora[0] += 2 * 3600  # passou de 24 h desde a primeira consulta
    cache.query(RA0, DEC0)
    assert origem.queries == 2
