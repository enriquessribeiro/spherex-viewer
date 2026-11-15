// Carregamento pela API: servidor ocupado (429) não é erro, é espera.
import { afterEach, describe, expect, it, vi } from "vitest";
import { loadApiField, retryAfterMs } from "../src/data";

const resposta = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers });

afterEach(() => vi.unstubAllGlobals());

describe("API ocupada", () => {
  it("espera o Retry-After (com limites) e não falha", () => {
    expect(retryAfterMs(new Response(null, { headers: { "Retry-After": "30" } }))).toBe(30000);
    expect(retryAfterMs(new Response(null))).toBe(30000);
    expect(retryAfterMs(new Response(null, { headers: { "Retry-After": "1" } }))).toBe(5000);
    expect(retryAfterMs(new Response(null, { headers: { "Retry-After": "9999" } }))).toBe(120000);
  });

  it("429 → avisa e tenta de novo até ficar pronto", async () => {
    vi.useFakeTimers();
    const campo = { base_url: "fields/x/v/", epochs: [] };
    const respostas = [
      resposta(429, { error: { code: "BUSY", message: "ocupado" } }, { "Retry-After": "5" }),
      resposta(202, { stage: "downloading", progress: { done: 1, total: 4 }, poll_after_ms: 10 }),
      resposta(200, campo),
    ];
    vi.stubGlobal("fetch", vi.fn(async () => respostas.shift()!));
    const etapas: string[] = [];
    const pronto = loadApiField("https://api/api/v1/field?ra=1&dec=2&fov=6", (p) => etapas.push(p.stage), new AbortController().signal);
    await vi.runAllTimersAsync();
    const h = await pronto;
    expect(etapas).toEqual(["busy", "downloading"]);
    expect(h.base).toBe("https://api/api/v1/fields/x/v/");
    vi.useRealTimers();
  });

  it("outros erros continuam sendo erro, com a mensagem da API", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => resposta(502, { error: { code: "UPSTREAM_ERROR", message: "IRSA fora" } })));
    await expect(loadApiField("https://api/api/v1/field?ra=1", () => {}, new AbortController().signal)).rejects.toThrow("IRSA fora");
  });
});
