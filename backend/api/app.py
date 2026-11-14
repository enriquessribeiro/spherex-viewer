"""Aplicação FastAPI (docs/04-api.md).

    uv run uvicorn api.main:app --reload
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.coords import parse_coordinates
from api.jobs import FieldJobs
from pipeline.archive import Archive, ArchiveUnavailable
from pipeline.field import DEFAULT_MAX_WORKERS, NoCoverage
from pipeline.output import field_id

API_VERSION = "0.1.0"
FOV_MIN_ARCMIN, FOV_MAX_ARCMIN, FOV_DEFAULT_ARCMIN = 1.0, 30.0, 6.0
POLL_AFTER_MS = 2000
RETRY_AFTER_S = 30
IMMUTABLE = "public, max-age=31536000, immutable"
CONTENT_TYPES = {".f32": "application/octet-stream", ".u8": "application/octet-stream",
                 ".png": "image/png", ".json": "application/json"}

Resolver = Callable[[str], dict | None]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def create_app(archive: Archive, data_dir: str | Path, resolver: Resolver | None = None,
               max_jobs: int = 2) -> FastAPI:
    data_dir = Path(data_dir).resolve()
    jobs = FieldJobs(archive, data_dir, max_jobs)
    started = time.time()

    app = FastAPI(title="SPHEREx Viewer API", version=API_VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"error": {"code": exc.code, "message": exc.message}},
                            status_code=exc.status, headers=exc.headers)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": API_VERSION, "uptime_s": round(time.time() - started)}

    @app.get("/api/v1/config")
    def config():
        return {
            "fov_arcmin": {"min": FOV_MIN_ARCMIN, "max": FOV_MAX_ARCMIN, "default": FOV_DEFAULT_ARCMIN},
            "max_parallel_downloads": DEFAULT_MAX_WORKERS,
            "poll_after_ms": POLL_AFTER_MS,
        }

    @app.get("/api/v1/field")
    def get_field(ra: str, dec: str, fov: str = str(FOV_DEFAULT_ARCMIN)):
        ra_deg, dec_deg, fov_arcmin = _number(ra, "ra"), _number(dec, "dec"), _number(fov, "fov")
        if not (0 <= ra_deg < 360 and -90 <= dec_deg <= 90):
            raise ApiError(400, "INVALID_COORDS", "RA deve estar em [0, 360) e Dec em [-90, 90]")
        if fov_arcmin > FOV_MAX_ARCMIN:
            raise ApiError(400, "FOV_TOO_LARGE", f"fov máximo é {FOV_MAX_ARCMIN:g} arcmin")
        if fov_arcmin < FOV_MIN_ARCMIN:
            raise ApiError(400, "FOV_TOO_SMALL", f"fov mínimo é {FOV_MIN_ARCMIN:g} arcmin")

        fid = field_id(ra_deg, dec_deg, fov_arcmin)
        job = jobs.get_or_start(fid, ra_deg, dec_deg, fov_arcmin)
        if job is None:
            raise ApiError(429, "BUSY", "servidor processando trabalhos demais; tente de novo",
                           {"Retry-After": str(RETRY_AFTER_S)})
        if job.stage == "ready":
            return JSONResponse(json.loads(job.manifest.read_text()),
                                headers={"Cache-Control": "public, max-age=3600"})
        if job.stage == "error":
            if isinstance(job.error, NoCoverage):
                raise ApiError(404, "NO_COVERAGE", str(job.error))
            jobs.forget(fid)  # erro transitório: o próximo pedido tenta de novo
            if isinstance(job.error, ArchiveUnavailable):
                raise ApiError(502, "UPSTREAM_ERROR", str(job.error))
            raise ApiError(500, "INTERNAL", "erro inesperado ao processar o campo")
        return JSONResponse(
            {"field_id": fid, "status": "processing", "stage": job.stage,
             "progress": {"done": job.done, "total": job.total}, "poll_after_ms": POLL_AFTER_MS},
            status_code=202, headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/v1/fields/{path:path}")
    def field_file(path: str):
        target = (data_dir / "fields" / path).resolve()
        if not target.is_file() or data_dir not in target.parents:
            raise ApiError(404, "NOT_FOUND", "arquivo não encontrado")
        return FileResponse(target, media_type=CONTENT_TYPES.get(target.suffix, "application/octet-stream"),
                            headers={"Cache-Control": IMMUTABLE})

    @app.get("/api/v1/resolve")
    def resolve(name: str):
        coords = parse_coordinates(name)
        if coords is not None:
            return {"query": name, "ra": coords[0], "dec": coords[1], "source": "coordinates"}
        found = resolver(name) if resolver else None
        if not found:
            raise ApiError(404, "NOT_FOUND", f"objeto não encontrado: {name}")
        return {"query": name, **found}

    return app


def _number(value: str, name: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ApiError(400, "INVALID_PARAM", f"{name} deve ser um número") from None
