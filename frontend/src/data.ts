// Carregamento dos dados: índice de alvos, campos (estáticos ou API) e quadros, com cache em memória.
import { decodeF32, decodeMask, type Grid, type MaskGrid } from "./core/frames";
import type { Manifest } from "./core/source";
import type { Detector, FieldDoc } from "./core/types";

export interface LoadedFrame {
  data: Grid;
  variance: Grid;
  mask: MaskGrid;
}

export interface FieldHandle {
  doc: FieldDoc;
  /** URL de base dos arquivos do campo (termina em /). */
  base: string;
}

export interface Progress {
  stage: string;
  done: number;
  total: number;
}

export async function loadManifest(url = "data/manifest.json"): Promise<Manifest | null> {
  try {
    const response = await fetch(url);
    return response.ok ? ((await response.json()) as Manifest) : null;
  } catch {
    return null;
  }
}

/** Campo estático: field.json fica dentro da pasta base do campo. */
export async function loadStaticField(fieldUrl: string): Promise<FieldHandle> {
  const response = await fetch(fieldUrl);
  if (!response.ok) throw new Error(`não foi possível carregar o campo (${response.status})`);
  const doc = (await response.json()) as FieldDoc;
  return { doc, base: fieldUrl.slice(0, fieldUrl.lastIndexOf("/") + 1) };
}

/** Campo pela API: repete o pedido enquanto o servidor processa (202), informando o progresso. */
export async function loadApiField(
  fieldUrl: string, onProgress: (p: Progress) => void, signal: AbortSignal,
): Promise<FieldHandle> {
  const apiRoot = fieldUrl.slice(0, fieldUrl.indexOf("/api/v1/") + "/api/v1/".length);
  for (;;) {
    const response = await fetch(fieldUrl, { signal });
    const body = await response.json();
    if (response.status === 202) {
      onProgress({ stage: body.stage, done: body.progress.done, total: body.progress.total });
      await sleep(body.poll_after_ms ?? 2000, signal);
      continue;
    }
    if (!response.ok) throw new Error(body?.error?.message ?? `erro ${response.status}`);
    const doc = body as FieldDoc;
    return { doc, base: apiRoot + doc.base_url };
  }
}

const frameCache = new Map<string, Promise<LoadedFrame>>();

export function loadFrame(field: FieldHandle, epochIndex: number, det: Detector): Promise<LoadedFrame> | null {
  const epoch = field.doc.epochs.find((e) => e.index === epochIndex);
  const frame = epoch?.frames[det];
  if (!frame) return null;
  const key = `${field.base}|${epochIndex}|${det}`;
  let cached = frameCache.get(key);
  if (!cached) {
    const n = field.doc.grid.n;
    const get = (path: string) => fetch(field.base + path).then((r) => {
      if (!r.ok) throw new Error(`arquivo ${path} indisponível (${r.status})`);
      return r.arrayBuffer();
    });
    cached = Promise.all([get(frame.frame), get(frame.variance), get(frame.mask)]).then(([d, v, m]) => ({
      data: decodeF32(d, n), variance: decodeF32(v, n), mask: decodeMask(m, n),
    }));
    cached.catch(() => frameCache.delete(key));
    frameCache.set(key, cached);
  }
  return cached;
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("cancelado", "AbortError"));
    });
  });
}
