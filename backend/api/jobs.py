"""Processamento assíncrono de campos: um trabalho por field_id, com progresso."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.archive import Archive, ArchiveUnavailable, Exposure
from pipeline.field import NoCoverage, build_field
from pipeline.output import write_field

# Um campo novo leva de 5 a 20 min com o IRSA saudável (docs/10-desenvolvimento.md §5);
# acima disso o IRSA está pendurado e o trabalho é abandonado.
DEFAULT_JOB_TIMEOUT_S = 30 * 60


class JobTimeout(Exception):
    """O trabalho passou do tempo máximo. Não é ArchiveUnavailable de propósito: aquele faz a
    exposição ser pulada, e aqui o campo inteiro tem de parar (senão sairia incompleto)."""


@dataclass
class Job:
    field_id: str
    stage: str = "querying"  # querying → downloading → ready | error
    done: int = 0
    total: int = 0
    manifest: Path | None = None
    error: Exception | None = None
    deadline: float = float("inf")
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def finished(self) -> bool:
        return self.stage in ("ready", "error")


class _ProgressArchive:
    """Conta as exposições consultadas e os recortes baixados para reportar progresso."""

    def __init__(self, archive: Archive, job: Job, clock: Callable[[], float]):
        self._archive, self._job, self._clock = archive, job, clock

    def query(self, ra: float, dec: float) -> list[Exposure]:
        exposures = self._archive.query(ra, dec)
        self._job.total, self._job.stage = len(exposures), "downloading"
        return exposures

    def fetch_cutout(self, exposure, ra, dec, size_deg):
        if self._clock() > self._job.deadline:
            raise JobTimeout("tempo máximo do campo esgotado")
        try:
            return self._archive.fetch_cutout(exposure, ra, dec, size_deg)
        finally:
            with self._job.lock:
                self._job.done += 1


class FieldJobs:
    def __init__(self, archive: Archive, data_dir: Path, max_jobs: int,
                 timeout_s: float = DEFAULT_JOB_TIMEOUT_S, clock: Callable[[], float] = time.monotonic):
        self._archive, self._data_dir, self._max_jobs = archive, data_dir, max_jobs
        self._timeout_s, self._clock = timeout_s, clock
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def _expire(self, job: Job) -> None:
        """Trabalho pendurado além do prazo vira erro: a API responde 502 e a vaga é liberada.
        A thread presa termina sozinha quando o pedido ao IRSA desistir; o resultado é descartado."""
        if not job.finished and self._clock() > job.deadline:
            job.error = JobTimeout(f"tempo máximo do campo esgotado ({self._timeout_s / 60:g} min)")
            job.stage = "error"

    def get_or_start(self, field_id: str, ra: float, dec: float, fov: float) -> Job | None:
        """Trabalho existente ou novo; None se já há trabalhos demais em andamento."""
        with self._lock:
            for j in self._jobs.values():
                self._expire(j)
            job = self._jobs.get(field_id)
            if job is not None:
                return job
            running = sum(not j.finished for j in self._jobs.values())
            if running >= self._max_jobs:
                return None
            job = self._jobs[field_id] = Job(field_id=field_id, deadline=self._clock() + self._timeout_s)
        # Uma thread por trabalho (não um pool): uma thread presa no IRSA não pode bloquear a fila.
        threading.Thread(target=self._run, args=(job, ra, dec, fov), daemon=True).start()
        return job

    def forget(self, field_id: str) -> None:
        """Descarta o trabalho (ex.: após erro transitório, para o próximo pedido tentar de novo)."""
        with self._lock:
            self._jobs.pop(field_id, None)

    def _run(self, job: Job, ra: float, dec: float, fov: float) -> None:
        try:
            result = build_field(ra, dec, fov, _ProgressArchive(self._archive, job, self._clock))
            manifest = write_field(result, self._data_dir)
            if job.finished:  # expirou enquanto rodava: o erro já foi reportado
                return
            job.manifest, job.stage = manifest, "ready"
        except (NoCoverage, ArchiveUnavailable, JobTimeout) as exc:
            if not job.finished:
                job.error, job.stage = exc, "error"
        except Exception as exc:  # noqa: BLE001 — qualquer falha vira erro do trabalho, não derruba a API
            if not job.finished:
                job.error, job.stage = exc, "error"
