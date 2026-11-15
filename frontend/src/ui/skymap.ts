// Mapa do céu inteiro do SPHEREx (Aladin Lite + HiPS do DR1 no IRSA).
// O Aladin (~2,4 MB, GPL-3) só é baixado quando o mapa chega perto da tela.
import { fieldCorners } from "../core/sky";
import type { ManifestTarget } from "../core/source";
import { t } from "../i18n";

export const SPHEREX_HIPS = "https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube";

// O cubo HiPS tem 102 canais (0–101), em ordem crescente de comprimento de onda, 17 por
// detector; os canais 50 e 51 são vazios no DR1. O Aladin converte canal ↔ frequência de forma
// inconsistente (setSliceNumber(0) busca o arquivo _102, que não existe), então o canal é
// escolhido pela frequência, mirando o centro do canal.
export const CHANNELS_PER_DETECTOR = 17;
/** Canal do meio de cada detector (D1 = 8 … D6 = 93). */
export function detectorChannel(det: number): number {
  return (det - 1) * CHANNELS_PER_DETECTOR + Math.floor(CHANNELS_PER_DETECTOR / 2);
}

/** Catálogos de outros telescópios, pelo VizieR (CDS): "esse ponto já é conhecido?". */
export const CATALOGS = {
  // Só as colunas úteis: com todas, o Gaia vinha com 3,3 MB e 10 s para 4000 estrelas.
  gaia: { vizier: "I/355/gaiadr3", name: "Gaia DR3", color: "#f2efe7", shape: "circle",
    columns: "Source,RA_ICRS,DE_ICRS,Gmag,BP-RP,pmRA,pmDE,Plx" },
  wise: { vizier: "II/328/allwise", name: "AllWISE", color: "#d9b25f", shape: "square",
    columns: "AllWISE,RAJ2000,DEJ2000,W1mag,W2mag,W3mag,W4mag" },
} as const;
export type CatalogKey = keyof typeof CATALOGS;

/** Acima deste campo de visão (graus) os catálogos não são pedidos: seriam milhões de estrelas. */
export const CATALOG_MAX_FOV_DEG = 1;
const CATALOG_LIMIT = 2000;
/** Espelhos do VizieR. O endereço que o Aladin usa (vizier.unistra.fr) esteve fora em 14/11/2026;
 * o de Harvard responde com os mesmos dados e libera CORS, então vai primeiro (como no SIMBAD). */
export const VIZIER_MIRRORS = ["https://vizier.cfa.harvard.edu", "https://vizier.cds.unistra.fr"];

/** Consulta cone do VizieR em VOTable, no formato que o Aladin lê. */
export function vizierConeUrl(
  mirror: string, catalog: string, columns: string, ra: number, dec: number, radiusDeg: number, limit: number,
): string {
  // Ordenado pela distância: se bater no limite, cortam-se as estrelas da borda, não as do centro.
  const q = new URLSearchParams({
    "-source": catalog, "-c": `${ra.toFixed(6)} ${dec.toFixed(6)}`, "-c.rd": radiusDeg.toFixed(4),
    "-out.max": String(limit), "-out": columns, "-sort": "_r", "-out.add": "_r",
  });
  return `${mirror}/viz-bin/votable?${q}`;
}

/** Raio da busca no catálogo: cobre a vista (meia diagonal) sem passar de 0,75°. */
export function catalogRadiusDeg(fovDeg: number): number {
  return Math.min((fovDeg / 2) * Math.SQRT2, 0.75);
}

const PENCIL = "#c4302b";
const INK_BLUE = "#2b4c9c";

export interface SkyMapHandlers {
  /** Usuário escolheu um alvo da lista no mapa. */
  onTarget(id: string): void;
  /** Usuário pediu as épocas de um ponto qualquer. */
  onPoint(ra: number, dec: number): void;
}

export class SkyMap {
  private aladin: any = null;
  private A: any = null;
  private fieldOverlay: any = null;
  private pending: { ra: number; dec: number; fov: number } | null = null;
  private targets: ManifestTarget[] = [];
  private loading: Promise<void> | null = null;
  private detector = 1;
  private catalogs = new Set<CatalogKey>();
  private catalogLayers: any[] = [];
  private catalogTimer: number | undefined;
  private catalogGeneration = 0;

  private readonly el: HTMLElement;
  private readonly status: HTMLElement;
  private readonly handlers: SkyMapHandlers;

  constructor(el: HTMLElement, status: HTMLElement, handlers: SkyMapHandlers) {
    this.el = el;
    this.status = status;
    this.handlers = handlers;
  }

  /** Carrega o Aladin quando o mapa se aproxima da área visível. */
  loadWhenVisible(): void {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        io.disconnect();
        this.load();
      }
    }, { rootMargin: "300px" });
    io.observe(this.el);
  }

  load(): Promise<void> {
    this.loading ??= (async () => {
      this.status.textContent = t("sky.loading");
      try {
        const mod: any = await import("aladin-lite");
        this.A = mod.default;
        await this.A.init;
        this.aladin = this.A.aladin(this.el, {
          survey: this.A.imageHiPS(SPHEREX_HIPS, {
            name: "SPHEREx DR1 (IRSA)",
            successCallback: () => this.setDetector(this.detector),
          }),
          projection: "SIN",
          cooFrame: "ICRS",
          fov: 180,
          // Abre no campo da placa; sem campo, no centro da Via Láctea (Sagitário).
          target: this.pending ? `${this.pending.ra} ${this.pending.dec}` : "266.4 -28.9",
          showReticle: true,
          reticleColor: PENCIL,
          showCooGrid: false,
          showLayersControl: false,
          showProjectionControl: false,
          showSettingsControl: false,
          showShareControl: false,
          showContextMenu: false,
          showSimbadPointerControl: false,
          showFullscreenControl: true,
          showZoomControl: true,
          showCooLocation: true,
          showFrame: false,
          log: false, // sem estatística de uso enviada ao CDS a cada visita
        });
        if (import.meta.env.DEV) (window as any).__skymap = this; // inspeção nos testes de navegador
        this.drawTargets();
        this.aladin.on("click", (p: { ra: number; dec: number; isDragging: boolean }) => {
          if (!p.isDragging) this.status.textContent = t("sky.point", { ra: p.ra.toFixed(4), dec: p.dec.toFixed(4) });
        });
        // Catálogos acompanham a vista: ao arrastar ou aproximar, busca de novo em volta do centro.
        const later = () => {
          clearTimeout(this.catalogTimer);
          if (this.catalogs.size) this.catalogTimer = window.setTimeout(() => this.refreshCatalogs(), 700);
        };
        this.aladin.on("positionChanged", later);
        this.aladin.on("zoomChanged", later);
        this.status.textContent = t("sky.hint");
        if (this.pending) this.showField(this.pending.ra, this.pending.dec, this.pending.fov, false); // já abriu nele
      } catch (err) {
        this.status.textContent = t("sky.fail", { msg: (err as Error).message });
        this.loading = null;
      }
    })();
    return this.loading;
  }

  setTargets(targets: ManifestTarget[]): void {
    this.targets = targets;
    this.drawTargets();
  }

  /** Marca o campo aberto na placa e leva o mapa até ele. */
  showField(ra: number, dec: number, fov: number, recenter = true): void {
    this.pending = { ra, dec, fov };
    if (!this.aladin) return;
    // Mapa já carregado (ex.: o campo da API chegou depois): gira o céu até o campo, mantendo o zoom.
    if (recenter) this.aladin.gotoRaDec(ra, dec);
    if (!this.fieldOverlay) {
      this.fieldOverlay = this.A.graphicOverlay({ color: INK_BLUE, lineWidth: 2, name: t("sky.openField") });
      this.aladin.addOverlay(this.fieldOverlay);
    }
    this.fieldOverlay.removeAll();
    this.fieldOverlay.add(this.A.polygon(fieldCorners(ra, dec, fov)));
  }

  /** Mostra o canal do meio do detector (1–6). */
  setDetector(det: number): void {
    this.detector = det;
    const layer = this.aladin?.getBaseImageLayer();
    if (!layer?.cubeDepth || !layer.emMin || !layer.emMax) return;
    const c = 299792458;
    const fmin = c / layer.emMax, fmax = c / layer.emMin;
    const channel = detectorChannel(det);
    layer.setFrequency({ value: fmin + ((channel + 0.5) / layer.cubeDepth) * (fmax - fmin) });
  }

  /** Liga ou desliga um catálogo (Gaia, AllWISE). */
  setCatalog(key: CatalogKey, on: boolean): void {
    if (on) this.catalogs.add(key);
    else this.catalogs.delete(key);
    this.refreshCatalogs();
  }

  private refreshCatalogs(): void {
    if (!this.aladin) return;
    for (const layer of this.catalogLayers) this.aladin.removeLayer(layer);
    this.catalogLayers = [];
    if (this.catalogs.size === 0) return;
    const fov = this.aladin.getFov()[0];
    if (fov > CATALOG_MAX_FOV_DEG) {
      this.status.textContent = t("sky.zoomIn");
      return;
    }
    const [ra, dec] = this.aladin.getRaDec();
    const names = [...this.catalogs].map((k) => CATALOGS[k].name).join(t("sky.and"));
    this.status.textContent = t("sky.searching", { names });
    const generation = ++this.catalogGeneration;
    for (const key of this.catalogs) this.loadCatalog(key, ra, dec, catalogRadiusDeg(fov), names, generation, 0);
  }

  /** Um catálogo pelo VizieR, tentando o espelho seguinte se um falhar. */
  private loadCatalog(key: CatalogKey, ra: number, dec: number, radius: number, names: string, generation: number, mirror: number): void {
    const c = CATALOGS[key];
    const url = vizierConeUrl(VIZIER_MIRRORS[mirror], c.vizier, c.columns, ra, dec, radius, CATALOG_LIMIT);
    const layer = this.A.catalogFromURL(url, {
      name: c.name, color: c.color, shape: c.shape, sourceSize: 10, onClick: "showPopup",
    }, () => {
      if (generation === this.catalogGeneration) {
        this.status.textContent = t("sky.found", { names });
      }
    }, () => {
      if (generation !== this.catalogGeneration) return;
      this.aladin.removeLayer(layer);
      this.catalogLayers = this.catalogLayers.filter((l) => l !== layer);
      if (mirror + 1 < VIZIER_MIRRORS.length) this.loadCatalog(key, ra, dec, radius, names, generation, mirror + 1);
      else this.status.textContent = t("sky.vizierFail", { name: c.name });
    }, false);
    this.aladin.addCatalog(layer);
    this.catalogLayers.push(layer);
  }

  /** Centraliza o mapa no campo aberto, com zoom suficiente para ver o quadrado. */
  goToField(): void {
    if (!this.aladin || !this.pending) return;
    this.aladin.gotoRaDec(this.pending.ra, this.pending.dec);
    this.aladin.setFoV(Math.max(0.25, (this.pending.fov / 60) * 6)); // abaixo de 1°: os catálogos aparecem
  }

  /** Idioma trocado: a mensagem de ajuda do mapa volta no idioma novo. */
  relabel(): void {
    this.status.textContent = this.aladin ? t("sky.hint") : this.status.textContent && t("sky.loading");
  }

  /** Centro atual do mapa (para "ver épocas aqui"). */
  center(): [number, number] | null {
    return this.aladin ? this.aladin.getRaDec() : null;
  }

  pick(): void {
    const c = this.center();
    if (c) this.handlers.onPoint(c[0], c[1]);
  }

  private drawTargets(): void {
    if (!this.aladin || this.targets.length === 0) return;
    const cat = this.A.catalog({
      name: t("sky.targets"),
      color: PENCIL,
      sourceSize: 18,
      shape: "circle",
      displayLabel: true,
      labelColumn: "name",
      labelColor: PENCIL,
      labelFont: "600 13px Archivo Variable, sans-serif",
    });
    this.aladin.addCatalog(cat);
    cat.addSources(this.targets.map((t) => this.A.source(t.ra, t.dec, { name: t.name, id: t.id })));
    this.aladin.on("objectClicked", (obj: any) => {
      const id = obj?.data?.id;
      if (id) this.handlers.onTarget(id);
    });
  }
}
