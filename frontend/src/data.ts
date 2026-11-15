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
  /** "busy": a API está processando outro campo (só um por vez no Render) e vamos tentar de novo. */
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

/** Lê a resposta como JSON sem confundir uma página de erro (ex.: 502 do proxy em HTML) com dado. */
async function readJson(response: Response): Promise<any> {
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(response.ok
      ? "o servidor respondeu algo que não é JSON"
      : `servidor indisponível (${response.status}); a API pode estar acordando, tente em 1 minuto`);
  }
}

/** GET de JSON da API, com a mensagem de erro do contrato ({ error: { message } }) quando houver. */
export async function fetchJson(url: string, signal: AbortSignal): Promise<any> {
  const response = await fetch(url, { signal });
  const body = await readJson(response);
  if (!response.ok) throw new Error(body?.error?.message ?? `erro ${response.status}`);
  return body;
}

/** Tempo máximo esperando um campo novo; o servidor desiste em 30 min (SPHEREX_JOB_TIMEOUT_S). */
export const MAX_FIELD_WAIT_MS = 35 * 60 * 1000;

/** Campo pela API: repete o pedido enquanto o servidor processa (202), informando o progresso. */
export async function loadApiField(
  fieldUrl: string, onProgress: (p: Progress) => void, signal: AbortSignal,
): Promise<FieldHandle> {
  const apiRoot = fieldUrl.slice(0, fieldUrl.indexOf("/api/v1/") + "/api/v1/".length);
  const giveUpAt = Date.now() + MAX_FIELD_WAIT_MS;
  for (;;) {
    if (Date.now() > giveUpAt) throw new Error("o processamento passou de 35 minutos");
    const response = await fetch(fieldUrl, { signal });
    const body = await readJson(response);
    if (response.status === 202) {
      onProgress({ stage: body.stage, done: body.progress.done, total: body.progress.total });
      await sleep(body.poll_after_ms ?? 2000, signal);
      continue;
    }
    if (response.status === 429) {
      // Ocupada com o campo de outra pessoa: espera o que ela pede (Retry-After) e tenta de novo.
      onProgress({ stage: "busy", done: 0, total: 0 });
      await sleep(retryAfterMs(response), signal);
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

/** Espera pedida pela API num 429 (cabeçalho Retry-After, em segundos), entre 5 s e 2 min. */
export function retryAfterMs(response: Pick<Response, "headers">): number {
  const seconds = Number(response.headers.get("Retry-After"));
  return Math.min(120, Math.max(5, Number.isFinite(seconds) && seconds > 0 ? seconds : 30)) * 1000;
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("cancelado", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort); // sem acumular um listener por consulta
      resolve();
    }, ms);
    signal.addEventListener("abort", onAbort, { once: true });
  });
}
