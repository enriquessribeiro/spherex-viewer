#!/usr/bin/env python3
"""Gera um PNG por página do fluxo-do-sistema.drawio — sem o app do draw.io.

Como funciona: o viewer do diagrams.net renderiza cada página como **um único `<svg>`
cujo conteúdo já está em coordenadas de modelo**, com um `translate/scale` por cima
(apenas o scroll da janela). Extraindo esse SVG do DOM, trocando esse transform por
identidade e dando ao `<svg>` um `viewBox` do tamanho da página, o navegador rasteriza
o vetor na escala pedida. É rasterização vetorial de verdade, não screenshot: o texto
sai nítido em qualquer escala.

Requer um navegador Chromium/Chrome headless. Nada de draw.io instalado.

    python3 docs/diagramas/para-png.py                     # 2× ao lado do .drawio
    python3 docs/diagramas/para-png.py --scale 4            # 4×
    python3 docs/diagramas/para-png.py --out /tmp/pngs      # outro destino

Variáveis de ambiente:
    CHROME_BIN   binário do Chrome/Chromium (padrão: procura no PATH)
    CHROME_LIBS  LD_LIBRARY_PATH extra, quando o binário não acha as .so do sistema
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import zlib
from pathlib import Path

VIEWER = "https://viewer.diagrams.net/"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>png</title>
<style>html,body{{margin:0;padding:0;background:#fff}}</style></head>
<body>{svg}</body></html>
"""


def find_chrome() -> str:
    explicit = os.environ.get("CHROME_BIN")
    if explicit:
        return explicit
    for name in ("chrome-headless-shell", "chromium", "chromium-browser",
                 "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit("nenhum Chrome/Chromium no PATH; defina CHROME_BIN")


def run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    libs = os.environ.get("CHROME_LIBS")
    if libs:
        env["LD_LIBRARY_PATH"] = libs
    return subprocess.run(args, capture_output=True, text=True, env=env, **kwargs)


def viewer_url(xml: str) -> str:
    """Empacota o .drawio no fragmento da URL do viewer (deflate + base64)."""
    pre = urllib.parse.quote(xml, safe="!~*'()")
    deflate = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    packed = deflate.compress(pre.encode("utf-8")) + deflate.flush()
    return VIEWER + "?lightbox=1&page={page}#R" + base64.b64encode(packed).decode()


def pages(mxfile: str) -> list[tuple[str, int, int]]:
    """[(nome, largura, altura)] de cada <diagram>, lido do mxGraphModel."""
    found = []
    for block in re.finditer(r"<diagram\b[^>]*>.*?</diagram>", mxfile, re.S):
        chunk = block.group(0)
        name = re.search(r'name="([^"]*)"', chunk.split(">", 1)[0])
        width = re.search(r'pageWidth="([\d.]+)"', chunk)
        height = re.search(r'pageHeight="([\d.]+)"', chunk)
        found.append((name.group(1) if name else "sem-nome",
                      int(float(width.group(1))) if width else 1600,
                      int(float(height.group(1))) if height else 1200))
    return found


def slug(text: str) -> str:
    """'2. Atualização agendada' -> 'atualizacao-agendada'."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    plain = re.sub(r"^\s*\d+[.)]\s*", "", plain)
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drawio", nargs="?", default=here / "fluxo-do-sistema.drawio")
    parser.add_argument("--out", default=None, help="diretório dos PNGs")
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()

    src = Path(args.drawio).resolve()
    out_dir = Path(args.out) if args.out else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    url = viewer_url(src.read_text(encoding="utf-8"))

    for index, (name, width, height) in enumerate(pages(src.read_text(encoding="utf-8"))):
        dom = run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                   "--window-size=1600,1200", "--virtual-time-budget=20000", "--dump-dom",
                   url.format(page=index)], timeout=180).stdout
        match = re.search(r"<svg\b.*?</svg>", dom, re.S)
        if not match:
            print(f"  [{index}] {name}: SVG não encontrado no DOM", file=sys.stderr)
            continue

        svg = match.group(0)
        body = svg[svg.index(">") + 1:]
        # O transform do viewer carrega o scroll: o conteúdo já está em coordenadas de modelo.
        body = re.sub(r'<g transform="translate\([-\d.]+,[-\d.]+\) scale\([-\d.]+\)">',
                      '<g transform="translate(0,0) scale(1)">', body, count=1)
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{round(width * args.scale)}" height="{round(height * args.scale)}" '
                f'viewBox="0 0 {width} {height}" style="background:#fff;display:block">')

        html_path = out_dir / f"page-{index}.html"
        html_path.write_text(PAGE.format(svg=head + body), encoding="utf-8")

        target = out_dir / f"{index + 1:02d}-{slug(name)}.png"
        run([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--allow-file-access-from-files",
             f"--window-size={round(width * args.scale)},{round(height * args.scale)}",
             "--virtual-time-budget=8000", f"--screenshot={target}", html_path.as_uri()],
            timeout=180)
        html_path.unlink(missing_ok=True)
        kb = target.stat().st_size // 1024 if target.exists() else 0
        print(f"  [{index}] {name}: {width}x{height} -> "
              f"{round(width * args.scale)}x{round(height * args.scale)} "
              f"| {target.name} ({kb} KB)")


if __name__ == "__main__":
    main()
