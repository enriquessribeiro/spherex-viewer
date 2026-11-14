"""Instância de produção: IRSA real com cache em disco e resolvedor SIMBAD.

    uv run uvicorn api.main:app

Variáveis de ambiente:
    SPHEREX_CACHE_DIR  pasta do cache de recortes e consultas (padrão: cache)
    SPHEREX_DATA_DIR   pasta dos campos gerados (padrão: <cache>/fields-data)
    SPHEREX_MAX_JOBS   campos processados ao mesmo tempo (padrão: 2)
    SPHEREX_JOB_TIMEOUT_S  tempo máximo de um campo em segundos (padrão: 1800); depois, 502
    SPHEREX_FOV_MAX    lado máximo do campo em arcmin (padrão: 30). A memória cresce com o
                       quadrado do campo: em servidores de 512 MB, usar 10.
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
    fov_max=float(os.environ.get("SPHEREX_FOV_MAX", "30")),
    job_timeout_s=float(os.environ.get("SPHEREX_JOB_TIMEOUT_S", "1800")),
)
