// Fronteira 5 — tradução da interface: escolha do idioma, textos com variáveis e cobertura do HTML.
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import { STATIC_EN, fmtDate, fmtNum, pickLang, setLang, t } from "../src/i18n";

afterEach(() => setLang("pt"));

describe("idioma", () => {
  it("a URL manda; depois o que foi guardado; depois o navegador", () => {
    expect(pickLang("en", "pt", ["pt-BR"])).toBe("en");
    expect(pickLang(undefined, "en", ["pt-BR"])).toBe("en");
    expect(pickLang(undefined, null, ["pt-BR", "en"])).toBe("pt");
    expect(pickLang(undefined, null, ["en-US"])).toBe("en");
    expect(pickLang(undefined, "xx", ["de-DE"])).toBe("en");
    expect(pickLang(undefined, null, [])).toBe("pt");
  });

  it("texto com variáveis em cada idioma", () => {
    expect(t("fact.plateOf", { i: 3, n: 4 })).toBe("3 de 4");
    setLang("en");
    expect(t("fact.plateOf", { i: 3, n: 4 })).toBe("3 of 4");
    expect(t("status.downloading", { done: 5, total: 258 })).toContain("5 of 258");
  });

  it("números e datas no formato do idioma", () => {
    expect(fmtNum(0.75, 2)).toBe("0,75");
    expect(fmtDate(2025, 11, 11)).toBe("11 dez 2025");
    setLang("en");
    expect(fmtNum(0.75, 2)).toBe("0.75");
    expect(fmtDate(2025, 11, 11)).toBe("11 Dec 2025");
  });

  it("todo texto marcado no index.html tem tradução", () => {
    const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
    const keys = [
      ...[...html.matchAll(/data-i18n(?:-html)?="([^"]+)"/g)].map((m) => m[1]),
      ...[...html.matchAll(/data-i18n-attr="([^"]+)"/g)].flatMap((m) => m[1].split(",").map((p) => p.split(":")[1].trim())),
    ];
    expect(keys.length).toBeGreaterThan(50);
    expect(keys.filter((k) => !(k in STATIC_EN))).toEqual([]);
  });
});
