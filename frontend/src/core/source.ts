// De onde vêm os dados de um campo: arquivos estáticos (alvos) ou API (qualquer coordenada).
import type { ViewState } from "./state";
import type { Detector } from "./types";

export interface ManifestTarget {
  id: string;
  name: string;
  description?: string;
  look_for?: string;
  description_en?: string;
  look_for_en?: string;
  ra: number;
  dec: number;
  fov_arcmin: number;
  default_detector: Detector;
  field: string;
  latest_exposure_mjd: number;
  thumbnail: string;
  /** O mesmo alvo publicado em outros tamanhos de campo. */
  alt_fields?: { fov_arcmin: number; field: string }[];
}

export interface Manifest {
  schema_version: 1;
  generated_at: string;
  targets: ManifestTarget[];
}

export type Source =
  | { kind: "static"; fieldUrl: string; targetId: string }
  | { kind: "api"; fieldUrl: string }
  | { kind: "resolve"; resolveUrl: string }
  | { kind: "unavailable"; reason: UnavailableReason };

/** Por que não dá para abrir (a interface traduz). */
export type UnavailableReason = "coords-without-api" | "name-without-api" | "no-targets";

export const DATA_ROOT = "data/";
const SAME_POSITION_DEG = 1 / 3600; // 1″

/** Tamanhos de campo do alvo que abrem na hora (arquivos estáticos), do padrão para os extras. */
export function staticFovs(t: ManifestTarget): number[] {
  return [t.fov_arcmin, ...(t.alt_fields ?? []).map((a) => a.fov_arcmin)];
}

/** Arquivo do alvo no tamanho pedido; sem esse tamanho publicado, o do campo padrão. */
function fieldFor(t: ManifestTarget, fov: number): string {
  return t.alt_fields?.find((a) => a.fov_arcmin === fov)?.field ?? t.field;
}

export function chooseSource(state: ViewState, manifest: Manifest | null, apiBase: string | null): Source {
  const targets = manifest?.targets ?? [];
  const asStatic = (t: ManifestTarget): Source => ({ kind: "static", fieldUrl: DATA_ROOT + fieldFor(t, state.fov), targetId: t.id });

  if (state.target) {
    const t = targets.find((x) => x.id === state.target);
    if (t) return asStatic(t);
  }
  if (state.ra !== undefined && state.dec !== undefined) {
    const t = targets.find(
      (x) => staticFovs(x).includes(state.fov) &&
        Math.abs(x.dec - state.dec!) < SAME_POSITION_DEG &&
        Math.abs(x.ra - state.ra!) * Math.cos((x.dec * Math.PI) / 180) < SAME_POSITION_DEG,
    );
    if (t) return asStatic(t);
    if (!apiBase) return { kind: "unavailable", reason: "coords-without-api" };
    const q = new URLSearchParams({ ra: String(state.ra), dec: String(state.dec), fov: String(state.fov) });
    return { kind: "api", fieldUrl: `${apiBase}/api/v1/field?${q}` };
  }
  if (state.name) {
    if (!apiBase) return { kind: "unavailable", reason: "name-without-api" };
    return { kind: "resolve", resolveUrl: `${apiBase}/api/v1/resolve?name=${encodeURIComponent(state.name)}` };
  }
  if (targets.length > 0) return asStatic(targets[0]);
  return { kind: "unavailable", reason: "no-targets" };
}
