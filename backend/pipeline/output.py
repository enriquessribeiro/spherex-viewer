"""Gravação de um campo no formato do contrato (docs/04-api.md §5, schemas/field.schema.json).

O mesmo formato é servido pela API e publicado como dados estáticos no GitHub Pages:

    <raiz>/fields/<field_id>/<data_version>/
        field.json
        frames/<época>/<detector>.f32       quadro (float32 little-endian, N x N, norte na 1ª linha)
        frames/<época>/<detector>.var.f32   variância
        frames/<época>/<detector>.mask.u8   bit 0 = saturado, bit 1 = baixa qualidade
        frames/<época>/<detector>.png       quadro renderizado (asinh, limites do campo)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

from pipeline.field import Field, Frame
from pipeline.targets import Target

SCHEMA_VERSION = 1
# Muda quando o processamento muda: força nova data_version mesmo sem exposições novas.
PIPELINE_VERSION = "2"

MASK_SATURATED = 1
MASK_LOW_QUALITY = 2

DETECTOR_RANGES_UM = {
    "D1": (0.75, 1.09), "D2": (1.10, 1.62), "D3": (1.63, 2.41),
    "D4": (2.42, 3.82), "D5": (3.83, 4.41), "D6": (4.42, 5.00),
}
ASINH_SOFTENING = 10.0
_MJD0 = datetime(1858, 11, 17, tzinfo=UTC)


def field_id(ra: float, dec: float, fov_arcmin: float) -> str:
    """Identificador legível do campo; arredonda em 0,0001° (0,36″, bem menor que um pixel)."""
    return f"{ra:.4f}{dec:+.4f}_{fov_arcmin:g}"


def data_version(field: Field) -> str:
    """Hash das exposições usadas e da versão do pipeline: muda quando chega dado novo."""
    ids = sorted(f"{e.id}|{e.uri}" for epoch in field.epochs for e in epoch.exposures)
    failed = sorted(e.id for e in field.failed_exposures)
    key = json.dumps([PIPELINE_VERSION, field_id(field.ra, field.dec, field.fov_arcmin), ids, failed])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def write_field(field: Field, root: str | Path, target: Target | None = None,
                generated_at: datetime | None = None) -> Path:
    """Grava o campo e devolve o caminho do field.json."""
    fid, version = field_id(field.ra, field.dec, field.fov_arcmin), data_version(field)
    base_url = f"fields/{fid}/{version}/"
    out = Path(root) / base_url
    epochs_doc = []
    for epoch in field.epochs:
        frames_doc = {}
        for det, frame in sorted(epoch.frames.items()):
            prefix = f"frames/{epoch.index}/{det}"
            _write_frame(out, prefix, frame, field.display[det].vmin, field.display[det].vmax)
            mjds = [e.mjd for e in epoch.exposures if e.detector == det]
            frames_doc[det] = {
                "n_exposures": frame.n_exposures,
                "mjd_mean": float(np.mean(mjds)),
                "lambda_min_um": DETECTOR_RANGES_UM[det][0],
                "lambda_max_um": DETECTOR_RANGES_UM[det][1],
                "background": frame.background,
                "frame": f"{prefix}.f32",
                "variance": f"{prefix}.var.f32",
                "mask": f"{prefix}.mask.u8",
                "png": f"{prefix}.png",
            }
        mjd_start, mjd_end = epoch.exposures[0].mjd, epoch.exposures[-1].mjd
        epochs_doc.append({
            "index": epoch.index,
            "mjd_start": mjd_start, "mjd_end": mjd_end, "mjd_mid": (mjd_start + mjd_end) / 2,
            "date_start": _date(mjd_start), "date_end": _date(mjd_end),
            "frames": frames_doc,
            "exposures": [
                {"id": e.id, "det": e.detector, "mjd": e.mjd, **({"collection": e.collection} if e.collection else {})}
                for e in epoch.exposures
            ],
        })

    doc = {
        "schema_version": SCHEMA_VERSION,
        "field_id": fid,
        "data_version": version,
        "status": "ready",
        "generated_at": (generated_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "center": {"ra": field.ra, "dec": field.dec},
        "fov_arcmin": field.fov_arcmin,
        "grid": _grid_doc(field),
        "collections": sorted({e.collection for ep in field.epochs for e in ep.exposures if e.collection}),
        "latest_exposure_mjd": max(e.mjd for ep in field.epochs for e in ep.exposures),
        "base_url": base_url,
        "epochs": epochs_doc,
        "display": {
            det: {"stretch": "asinh", "vmin": lim.vmin, "vmax": lim.vmax} for det, lim in field.display.items()
        },
        "failed_exposures": [e.id for e in field.failed_exposures],
    }
    if target is not None:
        doc["target"] = _target_doc(target, epochs_doc)

    path = out / "field.json"
    path.write_text(json.dumps(doc, indent=1))
    return path


def _write_frame(out: Path, prefix: str, frame: Frame, vmin: float, vmax: float) -> None:
    (out / prefix).parent.mkdir(parents=True, exist_ok=True)
    # Na grade do pipeline a linha 0 é o sul; nos arquivos, a 1ª linha é o norte (topo da imagem).
    data = np.flipud(frame.data)
    (out / f"{prefix}.f32").write_bytes(data.astype("<f4").tobytes())
    (out / f"{prefix}.var.f32").write_bytes(np.flipud(frame.variance).astype("<f4").tobytes())
    mask = np.zeros(frame.data.shape, dtype=np.uint8)
    if frame.saturated is not None:
        mask[frame.saturated] |= MASK_SATURATED
    if frame.low_quality is not None:
        mask[frame.low_quality] |= MASK_LOW_QUALITY
    (out / f"{prefix}.mask.u8").write_bytes(np.flipud(mask).tobytes())
    Image.fromarray(_render(data, np.flipud(mask), vmin, vmax), mode="L").save(out / f"{prefix}.png")


def _render(data: np.ndarray, mask: np.ndarray, vmin: float, vmax: float) -> np.ndarray:
    """Escala de cinza com esticamento asinh; núcleo saturado com o brilho máximo."""
    scaled = np.clip((data - vmin) / max(vmax - vmin, 1e-12), 0, 1)
    scaled = np.arcsinh(ASINH_SOFTENING * scaled) / np.arcsinh(ASINH_SOFTENING)
    scaled = np.nan_to_num(scaled, nan=0.0)
    scaled[(mask & MASK_SATURATED) != 0] = 1.0
    return (scaled * 255).round().astype(np.uint8)


def _grid_doc(field: Field) -> dict:
    w = field.wcs.wcs
    return {
        "n": field.n,
        "pixel_scale_arcsec": abs(float(w.cdelt[1])) * 3600,
        "row_order": "north_first",
        "wcs": {
            "CTYPE1": w.ctype[0], "CTYPE2": w.ctype[1],
            "CRVAL1": float(w.crval[0]), "CRVAL2": float(w.crval[1]),
            "CRPIX1": float(w.crpix[0]), "CRPIX2": float(w.crpix[1]),
            "CDELT1": float(w.cdelt[0]), "CDELT2": float(w.cdelt[1]),
        },
    }


def _target_doc(target: Target, epochs_doc: list[dict]) -> dict:
    predicted = []
    for epoch in epochs_doc:
        ra, dec = target.position_at(epoch["mjd_mid"])
        predicted.append({"epoch": epoch["index"], "ra": ra, "dec": dec})
    doc = {
        "id": target.id, "name": target.name,
        "pm_ra_masyr": target.pm_ra_masyr, "pm_dec_masyr": target.pm_dec_masyr,
        "ref_mjd": target.ref_mjd, "predicted_positions": predicted,
    }
    if target.description:
        doc["description"] = target.description
    return doc


def _date(mjd: float) -> str:
    return (_MJD0 + timedelta(days=mjd)).date().isoformat()
