// Mapa do céu inteiro do SPHEREx (Aladin Lite + HiPS do DR1 no IRSA).
// O Aladin (~2,4 MB, GPL-3) só é baixado quando o mapa chega perto da tela.
import { fieldCorners } from "../core/sky";
import type { ManifestTarget } from "../core/source";

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
      this.status.textContent = "Carregando o mapa do céu…";
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
        });
        if (import.meta.env.DEV) (window as any).__skymap = this; // inspeção nos testes de navegador
        this.drawTargets();
        this.aladin.on("click", (p: { ra: number; dec: number; isDragging: boolean }) => {
          if (!p.isDragging) this.status.textContent = `Ponto: RA ${p.ra.toFixed(4)}°, Dec ${p.dec.toFixed(4)}°`;
        });
        this.status.textContent = "Arraste para girar o céu; role para aproximar. Clique num alvo para ver as épocas.";
        if (this.pending) this.showField(this.pending.ra, this.pending.dec, this.pending.fov);
      } catch (err) {
        this.status.textContent = `O mapa do céu não carregou (${(err as Error).message}). O resto do site funciona normalmente.`;
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
  showField(ra: number, dec: number, fov: number): void {
    this.pending = { ra, dec, fov };
    if (!this.aladin) return;
    if (!this.fieldOverlay) {
      this.fieldOverlay = this.A.graphicOverlay({ color: INK_BLUE, lineWidth: 2, name: "Campo aberto" });
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

  /** Centraliza o mapa no campo aberto, com zoom suficiente para ver o quadrado. */
  goToField(): void {
    if (!this.aladin || !this.pending) return;
    this.aladin.gotoRaDec(this.pending.ra, this.pending.dec);
    this.aladin.setFoV(Math.max(1, (this.pending.fov / 60) * 12));
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
      name: "Alvos do desafio",
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
