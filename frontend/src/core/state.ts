// Estado da visualização ⇄ query string (docs/04-api.md §7): links compartilháveis e embed.
import type { Stretch } from "./stretch";
import { DETECTORS, type Detector } from "./types";

export type Mode = "play" | "blink" | "diff" | "sum";

export interface ViewState {
  target?: string;
  ra?: number;
  dec?: number;
  name?: string;
  fov: number;
  det?: Detector;
  mode: Mode;
  a?: number;
  b?: number;
  fps: number;
  stretch: Stretch;
  embed: boolean;
  /** Falsa cor: D6, D3 e D1 nos canais R, G e B. */
  color: boolean;
}

export const DEFAULT_STATE: ViewState = { fov: 6, mode: "play", fps: 2, stretch: "asinh", embed: false, color: false };
export const FOV_MIN = 1;
export const FOV_MAX = 30;

const MODES: Mode[] = ["play", "blink", "diff", "sum"];
const STRETCHES: Stretch[] = ["linear", "asinh", "log", "sqrt"];

export function parseState(search: string): { state: ViewState; warnings: string[] } {
  const p = new URLSearchParams(search);
  const state: ViewState = { ...DEFAULT_STATE };
  const warnings: string[] = [];

  const num = (key: string, ok: (v: number) => boolean): number | undefined => {
    const raw = p.get(key);
    if (raw === null) return undefined;
    const v = Number(raw);
    if (raw.trim() === "" || !Number.isFinite(v) || !ok(v)) {
      warnings.push(`parâmetro ${key}=${raw} inválido; usando o padrão`);
      return undefined;
    }
    return v;
  };
  const choice = <T extends string>(key: string, options: T[]): T | undefined => {
    const raw = p.get(key);
    if (raw === null) return undefined;
    if (!options.includes(raw as T)) {
      warnings.push(`parâmetro ${key}=${raw} inválido; usando o padrão`);
      return undefined;
    }
    return raw as T;
  };

  const target = p.get("target");
  if (target) state.target = target;
  const name = p.get("name");
  if (name) state.name = name;

  const ra = num("ra", (v) => v >= 0 && v < 360);
  const dec = num("dec", (v) => v >= -90 && v <= 90);
  if (ra !== undefined && dec !== undefined) {
    state.ra = ra;
    state.dec = dec;
  } else if (ra !== undefined || dec !== undefined) {
    warnings.push("ra e dec precisam vir juntos; ignorados");
  }

  state.fov = num("fov", (v) => v >= FOV_MIN && v <= FOV_MAX) ?? DEFAULT_STATE.fov;
  const det = choice("det", DETECTORS);
  if (det) state.det = det;
  state.mode = choice("mode", MODES) ?? DEFAULT_STATE.mode;
  const a = num("a", (v) => Number.isInteger(v) && v >= 1);
  const b = num("b", (v) => Number.isInteger(v) && v >= 1);
  if (a !== undefined) state.a = a;
  if (b !== undefined) state.b = b;
  state.fps = num("fps", (v) => v > 0 && v <= 30) ?? DEFAULT_STATE.fps;
  state.stretch = choice("stretch", STRETCHES) ?? DEFAULT_STATE.stretch;
  state.embed = p.get("embed") === "1";
  state.color = p.get("color") === "1";
  return { state, warnings };
}

/** Query string sem os valores padrão (links curtos). */
export function serializeState(state: ViewState): string {
  const p = new URLSearchParams();
  if (state.target) p.set("target", state.target);
  if (state.name) p.set("name", state.name);
  if (state.ra !== undefined && state.dec !== undefined) {
    p.set("ra", String(state.ra));
    p.set("dec", String(state.dec));
  }
  if (state.fov !== DEFAULT_STATE.fov) p.set("fov", String(state.fov));
  if (state.det) p.set("det", state.det);
  if (state.mode !== DEFAULT_STATE.mode) p.set("mode", state.mode);
  if (state.a !== undefined) p.set("a", String(state.a));
  if (state.b !== undefined) p.set("b", String(state.b));
  if (state.fps !== DEFAULT_STATE.fps) p.set("fps", String(state.fps));
  if (state.stretch !== DEFAULT_STATE.stretch) p.set("stretch", state.stretch);
  if (state.embed) p.set("embed", "1");
  if (state.color) p.set("color", "1");
  return p.toString();
}
