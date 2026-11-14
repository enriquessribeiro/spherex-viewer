"""Instância de produção: IRSA real com cache em disco e resolvedor SIMBAD.

    uv run uvicorn api.main:app

Variáveis de ambiente:
    SPHEREX_CACHE_DIR  pasta do cache de recortes e consultas (padrão: cache)
    SPHEREX_DATA_DIR   pasta dos campos gerados (padrão: <cache>/fields-data)
    SPHEREX_MAX_JOBS   campos processados ao mesmo tempo (padrão: 2)
"""

import os
from pathlib import Path

from api.app import create_app
from api.simbad import simbad_resolver
from pipeline.cache import CachedArchive
from pipeline.irsa import IrsaArchive

_cache = Path(os.environ.get("SPHEREX_CACHE_DIR", "cache"))
app = create_app(
    archive=CachedArchive(IrsaArchive(), _cache),
    data_dir=Path(os.environ.get("SPHEREX_DATA_DIR", _cache / "fields-data")),
    resolver=simbad_resolver,
    max_jobs=int(os.environ.get("SPHEREX_MAX_JOBS", "2")),
)
