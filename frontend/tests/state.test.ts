// Fronteira 5 — estado compartilhável na URL e escolha da fonte de dados (docs/04-api.md §7).
import { describe, expect, it } from "vitest";
import { DEFAULT_STATE, parseState, serializeState, type ViewState } from "../src/core/state";
import { chooseSource, type Manifest } from "../src/core/source";

describe("estado na URL", () => {
  it("ida e volta sem perder nada", () => {
    const estado: ViewState = {
      ...DEFAULT_STATE, target: "wise0855", det: "D6", mode: "blink", a: 2, b: 4, fps: 3, stretch: "linear",
    };
    expect(parseState(serializeState(estado)).state).toEqual(estado);
  });

  it("coordenadas e embed", () => {
    const { state } = parseState("?ra=269.452&dec=4.693&fov=12&det=D2&embed=1");
    expect(state).toMatchObject({ ra: 269.452, dec: 4.693, fov: 12, det: "D2", embed: true });
    expect(state.target).toBeUndefined();
  });

  it("idioma escolhido vai para a URL; sem escolha, fica de fora", () => {
    expect(parseState("?target=barnard&lang=en").state.lang).toBe("en");
    expect(serializeState({ ...DEFAULT_STATE, target: "barnard", lang: "en" })).toBe("target=barnard&lang=en");
    expect(parseState("?target=barnard").state.lang).toBeUndefined();
    const { state, warnings } = parseState("?lang=fr");
    expect(state.lang).toBeUndefined();
    expect(warnings).toHaveLength(1);
  });

  it("valores padrão ficam fora da URL", () => {
    expect(serializeState({ ...DEFAULT_STATE, target: "barnard" })).toBe("target=barnard");
  });

  it("parâmetros inválidos caem no padrão com aviso", () => {
    const { state, warnings } = parseState("?fov=abc&det=D9&mode=dançar&fps=-1&ra=10");
    expect(state).toEqual(DEFAULT_STATE);
    expect(warnings.length).toBe(5); // fov, det, mode, fps, ra sem dec
  });

  it("fov fora de 1–30 arcmin é recusado", () => {
    expect(parseState("?fov=60").state.fov).toBe(DEFAULT_STATE.fov);
  });
});

describe("fonte dos dados", () => {
  const manifest: Manifest = {
    schema_version: 1, generated_at: "2026-11-14T00:00:00Z",
    targets: [{
      id: "wise0855", name: "WISE 0855", ra: 133.76002, dec: -7.24221, fov_arcmin: 6,
      default_detector: "D6", field: "fields/133.7600-7.2422_6/abc/field.json",
      latest_exposure_mjd: 61174.3, thumbnail: "fields/133.7600-7.2422_6/abc/frames/4/D6.png",
    }],
  };
  const API = "https://api.exemplo.org";

  it("alvo da lista → arquivos estáticos", () => {
    expect(chooseSource({ ...DEFAULT_STATE, target: "wise0855" }, manifest, API)).toEqual({
      kind: "static", fieldUrl: "data/fields/133.7600-7.2422_6/abc/field.json", targetId: "wise0855",
    });
  });

  it("coordenada igual ao centro de um alvo (< 1″) → estático", () => {
    const fonte = chooseSource({ ...DEFAULT_STATE, ra: 133.76002, dec: -7.24221, fov: 6 }, manifest, API);
    expect(fonte.kind).toBe("static");
  });

  it("coordenada qualquer → API", () => {
    expect(chooseSource({ ...DEFAULT_STATE, ra: 10.5, dec: 41.2, fov: 6 }, manifest, API)).toEqual({
      kind: "api", fieldUrl: `${API}/api/v1/field?ra=10.5&dec=41.2&fov=6`,
    });
  });

  it("nome → resolver pela API; sem API configurada → indisponível", () => {
    expect(chooseSource({ ...DEFAULT_STATE, name: "R Dra" }, manifest, API)).toEqual({
      kind: "resolve", resolveUrl: `${API}/api/v1/resolve?name=R%20Dra`,
    });
    expect(chooseSource({ ...DEFAULT_STATE, ra: 10.5, dec: 41.2 }, manifest, null).kind).toBe("unavailable");
  });

  it("sem nada pedido → primeiro alvo da lista", () => {
    expect(chooseSource(DEFAULT_STATE, manifest, API)).toMatchObject({ kind: "static", targetId: "wise0855" });
  });
});
