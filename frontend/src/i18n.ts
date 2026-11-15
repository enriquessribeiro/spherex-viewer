// Tradução da interface (português ⇄ inglês).
//
// Textos fixos do index.html: o português é o próprio HTML, e cada elemento marcado leva uma chave
//   data-i18n="chave"            → textContent
//   data-i18n-html="chave"       → innerHTML (texto com <strong>)
//   data-i18n-attr="attr:chave"  → atributos (vários separados por vírgula)
// e a tradução inglesa fica em STATIC_EN. Textos montados pelo código usam t("chave", {vars}),
// com as duas línguas em TEXTS.
import type { Lang } from "./core/state";

export type { Lang };

/** Idioma: o da URL (botão), senão o guardado no navegador, senão português para quem lê português e inglês para os outros. */
export function pickLang(fromUrl: Lang | undefined, stored: string | null, browser: readonly string[]): Lang {
  if (fromUrl) return fromUrl;
  if (stored === "pt" || stored === "en") return stored;
  const first = browser[0]?.toLowerCase() ?? "pt";
  return first.startsWith("pt") ? "pt" : "en";
}

let current: Lang = "pt";
export const getLang = (): Lang => current;
export function setLang(lang: Lang): void { current = lang; }

type Vars = Record<string, string | number>;

/** Texto montado pelo código, no idioma atual. Chave sem tradução cai no português. */
export function t(key: keyof typeof TEXTS, vars: Vars = {}): string {
  const entry = TEXTS[key];
  const text = entry[current] ?? entry.pt;
  return text.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? `{${name}}`));
}

/** Número com a vírgula ou o ponto decimal do idioma. */
export function fmtNum(v: number, digits = 0): string {
  return v.toLocaleString(current === "pt" ? "pt-BR" : "en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

const MONTHS: Record<Lang, string[]> = {
  pt: ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
};
export const monthName = (m: number): string => MONTHS[current][m];

/** "11 dez 2025" / "11 Dec 2025". */
export function fmtDate(y: number, m: number, d: number): string {
  return `${d} ${monthName(m)} ${y}`;
}

// ---------------------------------------------------------------------------- textos do código

export const TEXTS = {
  "det.D1": { pt: "Infravermelho mais curto: estrelas comuns aparecem bem.", en: "Shortest infrared: ordinary stars show up well." },
  "det.D2": { pt: "Estrelas e a banda de absorção da água.", en: "Stars and the water absorption band." },
  "det.D3": { pt: "Anãs frias começam a aparecer (metano em ~2,2 µm).", en: "Cool dwarfs start to show up (methane at ~2.2 µm)." },
  "det.D4": { pt: "Gelo de água e metano.", en: "Water ice and methane." },
  "det.D5": { pt: "Dióxido de carbono (CO₂).", en: "Carbon dioxide (CO₂)." },
  "det.D6": { pt: "Infravermelho mais longo: anãs marrons frias, como WISE 0855, brilham aqui.", en: "Longest infrared: cold brown dwarfs, like WISE 0855, shine here." },
  "det.none": { pt: "Sem imagens deste detector neste campo", en: "No images from this detector in this field" },

  "mode.play": { pt: "Passa pelas épocas em ordem, como um filme curto.", en: "Plays the epochs in order, like a short film." },
  "mode.blink": { pt: "Alterna entre duas épocas, como o comparador que achou Plutão em 1930.", en: "Switches between two epochs, like the blink comparator that found Pluto in 1930." },
  "mode.diff": { pt: "Subtrai uma época da outra: o que ficou parado some.", en: "Subtracts one epoch from the other: whatever stayed still disappears." },
  "mode.sum": { pt: "Soma todas as épocas: o céu fica mais profundo, e o que se move vira um rastro.", en: "Adds all epochs: the sky gets deeper, and anything that moves becomes a trail." },

  "status.near": {
    pt: "A coordenada digitada fica a {dist}′ de {name}, que se move rápido: mostrando o objeto onde ele está nas imagens do SPHEREx.",
    en: "The coordinate you typed is {dist}′ from {name}, which moves fast: showing the object where it is in the SPHEREx images.",
  },
  "status.unavailable": { pt: "Não dá para abrir isso aqui: {reason}. Escolha um dos alvos ao lado.", en: "This can't be opened here: {reason}. Pick one of the targets." },
  "reason.coords-without-api": { pt: "coordenadas fora da lista de alvos e sem API configurada", en: "coordinates outside the target list, and no API is configured" },
  "reason.name-without-api": { pt: "busca por nome precisa da API", en: "searching by name needs the API" },
  "reason.no-targets": { pt: "nenhum alvo disponível", en: "no targets available" },
  "status.resolving": { pt: "Procurando “{name}” no catálogo SIMBAD…", en: "Looking up “{name}” in the SIMBAD catalog…" },
  "status.loading": { pt: "Carregando a placa…", en: "Loading the plate…" },
  "status.busy": {
    pt: "O servidor está processando o campo de outra pessoa (um por vez, no plano gratuito). Tentando de novo em instantes…",
    en: "The server is processing someone else's field (one at a time on the free plan). Trying again shortly…",
  },
  "status.downloading": {
    pt: "Baixando imagens do SPHEREx: {done} de {total}. Na primeira vez pode levar alguns minutos.",
    en: "Downloading SPHEREx images: {done} of {total}. The first time can take a few minutes.",
  },
  "status.querying": { pt: "Consultando o arquivo da NASA (IRSA)…", en: "Querying the NASA archive (IRSA)…" },
  "status.loadError": { pt: "Não foi possível carregar: {msg}. Tente de novo ou escolha um dos alvos.", en: "Could not load: {msg}. Try again or pick one of the targets." },
  "status.frameError": { pt: "Não foi possível baixar esta época: {msg}.", en: "Could not download this epoch: {msg}." },

  "err.field": { pt: "não foi possível carregar o campo ({status})", en: "the field could not be loaded ({status})" },
  "err.notJson": { pt: "o servidor respondeu algo que não é JSON", en: "the server replied with something that is not JSON" },
  "err.down": { pt: "servidor indisponível ({status}); a API pode estar acordando, tente em 1 minuto", en: "server unavailable ({status}); the API may be waking up, try again in a minute" },
  "err.timeout": { pt: "o processamento passou de 35 minutos", en: "processing took longer than 35 minutes" },

  "inscr.diff": { pt: "{det} · diferença em σ · {fov}", en: "{det} · difference in σ · {fov}" },
  "inscr.sum": { pt: "{dets} · soma de {n} épocas · {fov}", en: "{dets} · sum of {n} epochs · {fov}" },
  "fact.interval": { pt: "Intervalo", en: "Interval" },
  "fact.days": { pt: "{n} dias", en: "{n} days" },
  "fact.epochs": { pt: "Épocas", en: "Epochs" },
  "fact.exposures": { pt: "Exposições", en: "Exposures" },
  "fact.plate": { pt: "Placa", en: "Plate" },
  "fact.plateOf": { pt: "{i} de {n}", en: "{i} of {n}" },
  "fact.color": { pt: "Cor", en: "Color" },
  "fact.colorValue": { pt: "D1 azul · D3 verde · D6 vermelho", en: "D1 blue · D3 green · D6 red" },
  "fact.detector": { pt: "Detector", en: "Detector" },
  "fact.flagged": { pt: "Pixels marcados", en: "Marked pixels" },
  "target.lookFor": { pt: "O que ver:", en: "What to look for:" },
  "target.fallback": { pt: "alvo", en: "target" },

  "pair.option": { pt: "{date} ({n} exp.)", en: "{date} ({n} exp.)" },
  "ruler.count": { pt: "{n} exp.", en: "{n} exp." },
  "ruler.without": { pt: "sem {det}", en: "no {det}" },
  "ruler.aria": { pt: "{span}, {n} exposições", en: "{span}, {n} exposures" },
  "ruler.ariaWithout": { pt: "{span}, sem este detector", en: "{span}, without this detector" },
  "ruler.missing1": { pt: "Marcas claras: 1 época sem imagens em {det}.", en: "Light marks: 1 epoch without images in {det}." },
  "ruler.missingN": { pt: "Marcas claras: {n} épocas sem imagens em {det}.", en: "Light marks: {n} epochs without images in {det}." },
  "ruler.jul": { pt: "jul", en: "Jul" },
  "fov.api": { pt: "Campo maior pega objetos mais rápidos, mas é processado na hora pela API (alguns minutos).", en: "A larger field catches faster objects, but the API processes it on the spot (a few minutes)." },
  "fov.noApi": { pt: "Outros tamanhos de campo precisam da API, que não está configurada neste site.", en: "Other field sizes need the API, which is not configured on this site." },
  "play.pause": { pt: "Pausar", en: "Pause" },
  "play.play": { pt: "Animar", en: "Play" },
  "copy.done": { pt: "Link copiado", en: "Link copied" },
  "copy.fail": { pt: "Copie da barra de endereço", en: "Copy it from the address bar" },
  "copy.label": { pt: "Copiar link", en: "Copy link" },
  "skymap.noApi": { pt: "Fora da lista de alvos, os dados vêm da API, que não está configurada neste site.", en: "Outside the target list, data comes from the API, which is not configured on this site." },
  "lang.button": { pt: "English", en: "Português" },
  "lang.aria": { pt: "Read this page in English", en: "Ler esta página em português" },

  "sp.title": { pt: "Espectro de {name}", en: "Spectrum of {name}" },
  "sp.saturated": {
    pt: "Sem espectro: {name} é brilhante demais para o SPHEREx e satura o detector. O núcleo vem sem valor em {bad} de {total} exposições, e a fotometria precisa dele. Os alvos fracos (WISE 0855, Epsilon Indi B) têm espectro.",
    en: "No spectrum: {name} is too bright for SPHEREx and saturates the detector. The core has no value in {bad} of {total} exposures, and the photometry needs it. The faint targets (WISE 0855, Epsilon Indi B) have spectra.",
  },
  "sp.intro": {
    pt: "Cada ponto é uma exposição: o filtro do SPHEREx muda de comprimento de onda ao longo do detector, então cada imagem mede o alvo numa cor diferente. {measured} de {total} exposições medidas, numa abertura de {aperture}″.",
    en: "Each dot is one exposure: the SPHEREx filter changes wavelength across the detector, so each image measures the target in a different color. {measured} of {total} exposures measured, in a {aperture}″ aperture.",
  },
  "sp.warn": {
    pt: "Atenção: uma estrela a {dist}″ cai na abertura em {dets}. Nesses detectores o fluxo pode ser dela, não de {name}: o pixel do SPHEREx tem 6,15″ e não separa os dois.",
    en: "Note: a star {dist}″ away falls inside the aperture in {dets}. In those detectors the flux may come from that star rather than from {name}: the SPHEREx pixel is 6.15″ and cannot separate the two.",
  },
  "sp.yes": { pt: "sim", en: "yes" },
  "sp.flagged": { pt: "pixel com aviso de qualidade", en: "pixel with a quality warning" },
  "sp.flux": { pt: "fluxo (µJy)", en: "flux (µJy)" },
  "sp.wavelength": { pt: "comprimento de onda (µm)", en: "wavelength (µm)" },

  "sky.loading": { pt: "Carregando o mapa do céu…", en: "Loading the sky map…" },
  "sky.point": { pt: "Ponto: RA {ra}°, Dec {dec}°", en: "Point: RA {ra}°, Dec {dec}°" },
  "sky.hint": { pt: "Arraste para girar o céu; role para aproximar. Clique num alvo para ver as épocas.", en: "Drag to spin the sky; scroll to zoom. Click a target to see its epochs." },
  "sky.fail": { pt: "O mapa do céu não carregou ({msg}). O resto do site funciona normalmente.", en: "The sky map did not load ({msg}). The rest of the site works normally." },
  "sky.zoomIn": { pt: "Aproxime o mapa (campo menor que 1°) para ver as estrelas do Gaia e do AllWISE.", en: "Zoom in (field smaller than 1°) to see the Gaia and AllWISE stars." },
  "sky.and": { pt: " e ", en: " and " },
  "sky.searching": { pt: "Buscando {names} no VizieR…", en: "Searching VizieR for {names}…" },
  "sky.found": { pt: "{names}: estrelas já catalogadas. Clique numa para ver os dados.", en: "{names}: stars already cataloged. Click one to see its data." },
  "sky.vizierFail": { pt: "O VizieR não respondeu ({name}). Tente de novo em alguns minutos.", en: "VizieR did not respond ({name}). Try again in a few minutes." },
  "sky.openField": { pt: "Campo aberto", en: "Open field" },
  "sky.targets": { pt: "Alvos do desafio", en: "Challenge targets" },
} satisfies Record<string, { pt: string; en: string }>;

// ---------------------------------------------------------------------------- textos do HTML

export const STATIC_EN: Record<string, string> = {
  "meta.description": "See what moves in the infrared sky of NASA's SPHEREx telescope, epoch by epoch.",
  "brand.sub": "what moves in the infrared sky",
  "search.label": "Search for an object or coordinate",
  "search.placeholder": "R Dra or 133.76 -7.24",
  "search.go": "Go",
  "copy.label": "Copy link",

  "intro.title": "What changed in the sky from one photo to the next?",
  "intro.lede": "NASA's SPHEREx space telescope photographs the whole sky in infrared every six months. Here you see the photos of the same patch of sky in sequence, like a short film. Distant stars stay put; things close to us change position, and some stars change brightness. Pluto was discovered in 1930 by comparing photos just like these.",
  "intro.steps": "How to read",
  "intro.step1": "<strong>Pick a target</strong> from the list of challenge targets, or search for a name or coordinate at the top of the page.",
  "intro.step2": "<strong>Watch the epochs go by.</strong> Each frame is the same patch of sky on a different date. The fixed crosshair in the center helps you notice what moves; the red circle marks where the object should be.",
  "intro.step3": "<strong>Compare.</strong> Blink alternates between two dates. Difference erases what stayed the same and leaves only what changed.",

  "plate.aria": "SPHEREx plate",
  "zoom.aria": "Zoom",
  "plate.loading": "Loading…",
  "transport.aria": "Animation",
  "transport.title": "Epochs",
  "transport.prev": "Previous epoch",
  "transport.next": "Next epoch",
  "transport.pause": "Pause",
  "transport.speed": "Speed",
  "ruler.aria": "Epoch timeline: position = real date, height = number of exposures",
  "ruler.hint": "Position = real date · height = number of exposures.",

  "targets.title": "Challenge targets",
  "controls.aria": "Controls",
  "compare.title": "Compare",
  "modes.aria": "Mode",
  "mode.play": "Play",
  "mode.blink": "Blink",
  "mode.diff": "Difference",
  "mode.sum": "Sum",
  "pair.from": "From",
  "pair.to": "to",
  "legend.brighter": "appeared or got brighter",
  "legend.fainter": "disappeared or got fainter",
  "det.title": "Detector",
  "det.hint": "wavelength",
  "det.aria": "Detector",
  "image.title": "Image",
  "image.contrast": "Contrast",
  "image.sky": "Sky appearance",
  "image.negative": "Negative",
  "image.positive": "Positive",
  "image.color": "False color",
  "image.colorHint": "D1 blue · D3 green · D6 red",
  "image.flags": "Mark unreliable pixels",
  "image.flagsHelp": "In manila: saturated core (SPHEREx does not deliver the value) or a pixel that only had measurements with a quality warning.",
  "image.marks": "Crosshair and predicted position",
  "image.field": "Field",
  "image.fieldAria": "Field size",
  "about.text": "Each frame adds up all the photos SPHEREx took of this patch of sky in the same epoch, so it looks sharper.",
  "about.credit": "Data: NASA/JPL-Caltech/IPAC, SPHEREx mission (IRSA), releases DR1 and QR3. Positions: SIMBAD.",

  "sp.heading": "Spectrum",
  "sp.now": "epoch on the plate",
  "sp.other": "other epochs",
  "sp.median": "median",
  "sp.flaggedKey": "flagged pixel",
  "sp.table": "Show the points as a table",
  "sp.thFlux": "flux (µJy)",
  "sp.thErr": "error",
  "sp.thDet": "detector",
  "sp.thDate": "date",
  "sp.thFlag": "flag",

  "sky.title": "The whole SPHEREx sky",
  "sky.lede": "Mosaic of the first year of observations (DR1). Spin the sky, zoom in and pick a spot: the plate above shows how it changed from one epoch to the next. The mosaic adds up the whole year, so it does not show motion itself.",
  "sky.detAria": "Map detector",
  "sky.catalogsAria": "Catalogs from other telescopes",
  "sky.circles": "circles",
  "sky.squares": "squares",
  "sky.goField": "Go to the open field",
  "sky.here": "See epochs at the map center",
  "sky.credit": "Map: Aladin Lite (CDS, Strasbourg). Images: SPHEREx All-Sky Cube DR1, NASA/JPL-Caltech/IPAC (IRSA).",
};

// ---------------------------------------------------------------------------- aplicar no DOM

const original = new WeakMap<Element, Record<string, string>>();

/** Troca os textos marcados do HTML para o idioma atual (o português original é guardado na primeira vez). */
export function applyStatic(root: ParentNode = document): void {
  const swap = (el: Element, slot: string, key: string, read: () => string, write: (v: string) => void) => {
    const saved = original.get(el) ?? {};
    if (!(slot in saved)) { saved[slot] = read(); original.set(el, saved); }
    write(current === "en" ? STATIC_EN[key] ?? saved[slot] : saved[slot]);
  };
  for (const el of root.querySelectorAll<HTMLElement>("[data-i18n]")) {
    swap(el, "text", el.dataset.i18n!, () => el.textContent ?? "", (v) => { el.textContent = v; });
  }
  for (const el of root.querySelectorAll<HTMLElement>("[data-i18n-html]")) {
    swap(el, "html", el.dataset.i18nHtml!, () => el.innerHTML, (v) => { el.innerHTML = v; });
  }
  for (const el of root.querySelectorAll<HTMLElement>("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr!.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      swap(el, `@${attr}`, key, () => el.getAttribute(attr) ?? "", (v) => el.setAttribute(attr, v));
    }
  }
}
