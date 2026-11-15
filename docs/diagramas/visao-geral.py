#!/usr/bin/env python3
"""Desenha o diagrama de atividade "visão geral" em SVG e PNG.

A fonte editável é atividade-visao-geral.puml (PlantUML). Este script desenha o mesmo
diagrama, no estilo do PlantUML (raias coloridas, caixas arredondadas, losangos sim/não),
sem depender de Java: escreve o SVG só com a biblioteca padrão e rasteriza com o Chrome
headless, como o para-png.py.

    python3 docs/diagramas/visao-geral.py              # SVG + PNG em 2×
    python3 docs/diagramas/visao-geral.py --no-png     # só o SVG

Variáveis de ambiente (iguais às do para-png.py):
    CHROME_BIN   binário do Chrome/Chromium (padrão: procura no PATH)
    CHROME_LIBS  LD_LIBRARY_PATH extra, quando o binário não acha as .so do sistema

Ao mudar um passo, mude os dois arquivos: o .puml e a lista abaixo.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1460, 1620
FONT = "Helvetica, Arial, 'Liberation Sans', sans-serif"
INK, MUTED = "#222222", "#555555"

# Raias: nome, x inicial, x final, cor de fundo.
LANES = [
    ("Visitante", 20, 300, "#EAF3FB"),
    ("Site (navegador)", 300, 800, "#F1ECF8"),
    ("API (Render)", 800, 1160, "#FDF2E6"),
    ("IRSA (NASA)", 1160, 1440, "#EAF6EE"),
]
LANE_TOP, LANE_BOTTOM = 70, 1500
V, S, A, I = 160, 550, 980, 1300  # centro de cada raia
S_SIM, S_AUX = 420, 680  # colunas internas da raia do site

parts: list[str] = []


def text(x: float, y: float, lines: str, size: int = 13, weight: str = "normal",
         anchor: str = "middle", color: str = INK) -> None:
    rows = lines.split("\n")
    first = y - (len(rows) - 1) * size * 0.6
    spans = "".join(
        f'<tspan x="{x}" y="{first + i * size * 1.2:.1f}">{escape(r)}</tspan>'
        for i, r in enumerate(rows))
    parts.append(f'<text font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
                 f'dominant-baseline="middle" fill="{color}">{spans}</text>')


def box(cx: float, cy: float, w: float, label: str, h: float = 50) -> None:
    parts.append(f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" rx="12" '
                 f'fill="#FFFFFF" stroke="{INK}" stroke-width="1.2"/>')
    text(cx, cy, label)


def diamond(cx: float, cy: float, w: float, label: str, h: float = 44) -> None:
    """Losango achatado, como o `if` do PlantUML: pontas à esquerda e à direita."""
    t = 16
    pts = [(cx - w / 2, cy), (cx - w / 2 + t, cy - h / 2), (cx + w / 2 - t, cy - h / 2),
           (cx + w / 2, cy), (cx + w / 2 - t, cy + h / 2), (cx - w / 2 + t, cy + h / 2)]
    parts.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="#FFFFFF" '
                 f'stroke="{INK}" stroke-width="1.2"/>')
    text(cx, cy, label)


def merge(cx: float, cy: float) -> None:
    r = 12
    parts.append(f'<polygon points="{cx - r},{cy} {cx},{cy - r} {cx + r},{cy} {cx},{cy + r}" '
                 f'fill="#FFFFFF" stroke="{INK}" stroke-width="1.2"/>')


def start(cx: float, cy: float) -> None:
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{INK}"/>')


def stop(cx: float, cy: float) -> None:
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="11" fill="#FFFFFF" stroke="{INK}" '
                 f'stroke-width="1.5"/><circle cx="{cx}" cy="{cy}" r="7" fill="{INK}"/>')


def arrow(*pts: tuple[float, float], label: str = "", at: tuple[float, float] | None = None,
          anchor: str = "start", dashed: bool = False) -> None:
    d = " ".join(f"{x},{y}" for x, y in pts)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    parts.append(f'<polyline points="{d}" fill="none" stroke="{INK}" stroke-width="1.2"'
                 f'{dash} marker-end="url(#seta)"/>')
    if label and at:
        text(at[0], at[1], label, size=12, anchor=anchor, color=MUTED)


def draw() -> str:
    parts.clear()
    # Raias.
    for name, x0, x1, fill in LANES:
        parts.append(f'<rect x="{x0}" y="{LANE_TOP}" width="{x1 - x0}" '
                     f'height="{LANE_BOTTOM - LANE_TOP}" fill="{fill}" stroke="{INK}" '
                     f'stroke-width="1"/>')
        parts.append(f'<line x1="{x0}" y1="{LANE_TOP + 40}" x2="{x1}" y2="{LANE_TOP + 40}" '
                     f'stroke="{INK}" stroke-width="1"/>')
        text((x0 + x1) / 2, LANE_TOP + 20, name, size=15, weight="bold")
    text(WIDTH / 2, 36, "SPHEREx Viewer — visão geral", size=20, weight="bold")

    # Início.
    start(V, 145)
    arrow((V, 155), (V, 180))
    box(V, 205, 220, "Abre o site ou um\nlink compartilhado")
    arrow((V, 230), (V, 285), (S - 140, 285))
    box(S, 285, 280, "Lê o estado da URL\n(alvo, coordenada, detector, modo)")
    arrow((S, 310), (S, 343))
    diamond(S, 365, 220, "Alvo pré-processado?")

    # Ramo "sim": campo publicado.
    arrow((S - 110, 365), (S_SIM, 365), (S_SIM, 420), label="sim", at=(S_SIM - 30, 355))
    box(S_SIM, 445, 200, "Carrega o campo publicado\n(GitHub Pages, sem fila)")

    # Ramo "não": API.
    arrow((S + 110, 365), (A, 365), (A, 420), label="não", at=(S + 120, 355))
    box(A, 445, 220, "Recebe GET /api/v1/field\ne valida a coordenada")
    arrow((A, 470), (A, 503))
    diamond(A, 525, 230, "Servidor ocupado (429)?")
    arrow((A - 115, 525), (S_AUX, 525), (S_AUX, 575), label="sim", at=(A - 150, 515))
    box(S_AUX, 600, 210, "Mostra “servidor ocupado”\ne espera o Retry-After")
    arrow((S_AUX - 105, 600), (560, 600), (560, 425), (A - 110, 425), dashed=True,
          label="tenta de novo", at=(568, 512))

    arrow((A, 547), (A, 625), label="não", at=(A + 8, 575))
    box(A, 650, 230, "Cria o trabalho\n(202 + progresso a cada 2 s)")
    arrow((A, 675), (A, 700), (I - 120, 700))
    box(I, 700, 240, "Lista as exposições (TAP ou SIA)\ne entrega os recortes")
    arrow((I, 725), (I, 780), (A + 100, 780))
    diamond(A, 780, 200, "IRSA respondeu?")
    arrow((A - 100, 780), (S_AUX, 780), (S_AUX, 815), label="não", at=(A - 135, 770))
    box(S_AUX, 840, 190, "Mostra aviso de\ninstabilidade (502)")
    arrow((S_AUX, 865), (S_AUX, 899))
    stop(S_AUX, 910)
    arrow((A, 802), (A, 845), label="sim", at=(A + 8, 822))
    box(A, 870, 240, "Alinha, descarta flags,\nsoma por época e grava o campo")

    # Junção.
    arrow((S_SIM, 470), (S_SIM, 990), (S - 12, 990))
    arrow((A, 895), (A, 990), (S + 12, 990))
    merge(S, 990)
    arrow((S, 1002), (S, 1045))
    box(S, 1070, 270, "Decodifica os quadros e ajusta\no contraste no alvo")
    arrow((S, 1095), (S, 1150), (V + 125, 1150))
    box(V, 1150, 250, "Anima, pisca, subtrai ou soma\nas épocas; troca o detector")
    arrow((V, 1175), (V, 1208))
    diamond(V, 1230, 200, "Quer o espectro?")
    arrow((V + 100, 1230), (S - 150, 1230), label="sim", at=(V + 110, 1220))
    box(S, 1230, 300, "Desenha o espectro de 0,75 a 5 µm\ne avisa sobre estrelas vizinhas")
    arrow((S, 1255), (S, 1310), (V + 12, 1310))
    arrow((V, 1252), (V, 1298), label="não", at=(V + 8, 1275))
    merge(V, 1310)
    arrow((V, 1322), (V, 1365))
    box(V, 1390, 200, "Copia o link para\ncompartilhar o estado")
    arrow((V, 1415), (V, 1449))
    stop(V, 1460)

    # Nota de rodapé.
    nx, ny, nw, nh = 20, 1520, 1420, 82
    parts.append(f'<path d="M{nx},{ny} h{nw - 16} l16,16 v{nh - 16} h-{nw} z" fill="#FBFBE6" '
                 f'stroke="{INK}" stroke-width="1"/>')
    text(nx + 16, ny + 20, "Também pode acontecer:", size=13, weight="bold", anchor="start")
    text(nx + 16, ny + 48,
         "coordenada inválida (400) · nenhuma exposição cobre o ponto (404) · o trabalho passa "
         "de 30 min (502) · uma exposição falha e vira lacuna declarada no campo · busca por nome "
         "passa pelo SIMBAD antes da API.\n"
         "Veja o fluxo detalhado em fluxo-do-sistema.drawio (consulta ao vivo e atualização "
         "agendada).", size=12, anchor="start", color=MUTED)

    defs = (f'<defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{INK}"/></marker></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
            f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT}">{defs}'
            f'<rect width="100%" height="100%" fill="#FFFFFF"/>{"".join(parts)}</svg>\n')


def find_chrome() -> str:
    explicit = os.environ.get("CHROME_BIN")
    if explicit:
        return explicit
    for name in ("chrome-headless-shell", "chromium", "chromium-browser",
                 "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("nenhum Chrome/Chromium no PATH; defina CHROME_BIN ou use --no-png")


def to_png(svg_path: Path, png_path: Path, scale: float) -> None:
    chrome = find_chrome()
    env = dict(os.environ)
    if os.environ.get("CHROME_LIBS"):
        env["LD_LIBRARY_PATH"] = os.environ["CHROME_LIBS"]
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "pagina.html"
        page.write_text(
            f'<!doctype html><html><body style="margin:0;zoom:{scale}">'
            f'{svg_path.read_text(encoding="utf-8")}</body></html>', encoding="utf-8")
        subprocess.run(
            [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={round(WIDTH * scale)},{round(HEIGHT * scale)}",
             f"--screenshot={png_path}", page.as_uri()],
            check=True, capture_output=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    svg = HERE / "atividade-visao-geral.svg"
    svg.write_text(draw(), encoding="utf-8")
    print(f"escrito {svg.name}")
    if not args.no_png:
        png = HERE / "atividade-visao-geral.png"
        to_png(svg, png, args.scale)
        print(f"escrito {png.name}")


if __name__ == "__main__":
    main()
