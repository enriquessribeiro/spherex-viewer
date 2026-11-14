"""Gera os dados estáticos dos alvos (docs/04-api.md §6, docs/05-hospedagem.md §6).

    uv run python -m pipeline.build_static --targets ../targets.yaml --out ../frontend/public/data

Saída: <out>/manifest.json + <out>/fields/<field_id>/<data_version>/... para cada alvo.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pipeline.archive import Archive
from pipeline.cache import CachedArchive
from pipeline.field import CUTOUT_FACTOR, build_field
from pipeline.irsa import IrsaArchive
from pipeline.output import SCHEMA_VERSION, spectrum_doc, write_field
from pipeline.spectrum import APERTURE_PX, measure_spectrum, neighbors_in_aperture
from pipeline.targets import Target, load_targets

log = logging.getLogger("build_static")


def build_static(targets: list[Target], archive: Archive, out: str | Path) -> Path:
    """Processa cada alvo, grava seu campo e o índice manifest.json. Devolve o caminho do índice."""
    out = Path(out)
    entries = []
    for target in targets:
        ra, dec = target.field_center()
        log.info("%s: campo de %s′ em (%.5f, %.5f)", target.id, target.fov_arcmin, ra, dec)
        field = build_field(ra, dec, target.fov_arcmin, archive)
        # Espectro: as mesmas exposições e o mesmo recorte do campo (vêm do cache).
        exposures = [e for epoch in field.epochs for e in epoch.exposures]
        points = measure_spectrum(archive, exposures, ra, dec, target.fov_arcmin / 60 * CUTOUT_FACTOR, target.position_at)
        spectrum = spectrum_doc(field, points, neighbors_in_aperture(field, target.position_at),
                                len(exposures), APERTURE_PX)
        log.info("%s: espectro com %d de %d exposições", target.id, len(points), len(exposures))
        field_json = write_field(field, out, target=target, spectrum=spectrum)
        doc = json.loads(field_json.read_text())
        log.info("%s: %d épocas, %d exposições indisponíveis",
                 target.id, len(doc["epochs"]), len(doc["failed_exposures"]))
        entry = {
            "id": target.id,
            "name": target.name,
            "ra": ra,
            "dec": dec,
            "fov_arcmin": target.fov_arcmin,
            "default_detector": target.default_detector,
            "field": doc["base_url"] + "field.json",
            "latest_exposure_mjd": doc["latest_exposure_mjd"],
            "thumbnail": doc["base_url"] + _thumbnail(doc, target.default_detector),
        }
        if target.description:
            entry["description"] = target.description
        entries.append(entry)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets": entries,
    }
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    return path


MIN_THUMBNAIL_EXPOSURES = 3  # épocas com 1-2 exposições são ruidosas demais para a vitrine


def _thumbnail(field_doc: dict, detector: str) -> str:
    """PNG do detector padrão na época mais recente com exposições suficientes.

    Sem época suficiente, usa a que tem mais exposições; sem o detector, qualquer um.
    """
    candidates = [
        (epoch["index"], epoch["frames"][detector])
        for epoch in field_doc["epochs"] if detector in epoch["frames"]
    ]
    if candidates:
        good = [c for c in candidates if c[1]["n_exposures"] >= MIN_THUMBNAIL_EXPOSURES]
        _, frame = good[-1] if good else max(candidates, key=lambda c: (c[1]["n_exposures"], c[0]))
        return frame["png"]
    last = field_doc["epochs"][-1]["frames"]
    return next(iter(last.values()))["png"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default="../targets.yaml")
    parser.add_argument("--out", default="../frontend/public/data")
    parser.add_argument("--cache", default="cache", help="pasta do cache de recortes e consultas")
    parser.add_argument("--only", nargs="*", help="ids dos alvos a processar (padrão: todos)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    targets = load_targets(args.targets)
    if args.only:
        targets = [t for t in targets if t.id in set(args.only)]
    path = build_static(targets, CachedArchive(IrsaArchive(), args.cache), args.out)
    log.info("índice gravado em %s", path)


if __name__ == "__main__":
    main()
