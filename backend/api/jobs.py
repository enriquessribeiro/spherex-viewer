"""Processamento assíncrono de campos: um trabalho por field_id, com progresso."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.archive import Archive, ArchiveUnavailable, Exposure
from pipeline.field import NoCoverage, build_field
from pipeline.output import write_field


@dataclass
class Job:
    field_id: str
    stage: str = "querying"  # querying → downloading → ready | error
    done: int = 0
    total: int = 0
    manifest: Path | None = None
    error: Exception | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def finished(self) -> bool:
        return self.stage in ("ready", "error")


class _ProgressArchive:
    """Conta as exposições consultadas e os recortes baixados para reportar progresso."""

    def __init__(self, archive: Archive, job: Job):
        self._archive, self._job = archive, job

    def query(self, ra: float, dec: float) -> list[Exposure]:
        exposures = self._archive.query(ra, dec)
        self._job.total, self._job.stage = len(exposures), "downloading"
        return exposures

    def fetch_cutout(self, exposure, ra, dec, size_deg):
        try:
            return self._archive.fetch_cutout(exposure, ra, dec, size_deg)
        finally:
            with self._job.lock:
                self._job.done += 1


class FieldJobs:
    def __init__(self, archive: Archive, data_dir: Path, max_jobs: int):
        self._archive, self._data_dir, self._max_jobs = archive, data_dir, max_jobs
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_jobs)

    def get_or_start(self, field_id: str, ra: float, dec: float, fov: float) -> Job | None:
        """Trabalho existente ou novo; None se já há trabalhos demais em andamento."""
        with self._lock:
            job = self._jobs.get(field_id)
            if job is not None:
                return job
            running = sum(not j.finished for j in self._jobs.values())
            if running >= self._max_jobs:
                return None
            job = self._jobs[field_id] = Job(field_id=field_id)
        self._pool.submit(self._run, job, ra, dec, fov)
        return job

    def forget(self, field_id: str) -> None:
        """Descarta o trabalho (ex.: após erro transitório, para o próximo pedido tentar de novo)."""
        with self._lock:
            self._jobs.pop(field_id, None)

    def _run(self, job: Job, ra: float, dec: float, fov: float) -> None:
        try:
            result = build_field(ra, dec, fov, _ProgressArchive(self._archive, job))
            job.manifest = write_field(result, self._data_dir)
            job.stage = "ready"
        except (NoCoverage, ArchiveUnavailable) as exc:
            job.error, job.stage = exc, "error"
        except Exception as exc:  # noqa: BLE001 — qualquer falha vira erro do trabalho, não derruba a API
            job.error, job.stage = exc, "error"
