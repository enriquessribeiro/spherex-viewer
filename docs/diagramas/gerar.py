#!/usr/bin/env python3
"""Gera o diagrama de raia do SPHEREx Viewer em .drawio (só biblioteca padrão).

Layout determinístico: raias horizontais (papéis), tempo da esquerda para a direita,
colunas de passo fixo. Cada nó é filho da sua raia (coordenadas relativas), então mover
uma raia leva os nós junto. Arestas têm âncoras explícitas para não cruzarem nós.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

# Paleta do DESIGN.md (mundo "Placas do comparador")
GLASS = "#f2efe7"
GLASS_DEEP = "#e7e2d5"
GLASS_BRIGHT = "#fbf9f4"
INK = "#141414"
INK_SOFT = "#3d3a34"
INK_MUTED = "#5e584c"
PENCIL = "#c4302b"
INK_BLUE = "#2b4c9c"
API_TINT = "#eef0f6"
MANILA = "#9c8f74"
RULE = "#bdb39b"

PITCH = 240
NODE_W = 190
NODE_H = 72
LANE_X = 40
LANE_PAD = 30
COLS = 14  # c0..c13
LANE_W = LANE_PAD + (COLS - 1) * PITCH + NODE_W + LANE_PAD  # 3370


def esc(text: str) -> str:
    return html.escape(text, quote=True).replace("\n", "&#xa;")


def lane_style(fill: str, planned: bool) -> str:
    dash = "dashed=1;dashPattern=6 4;" if planned else ""
    return (
        "swimlane;html=1;startSize=30;horizontal=1;container=1;collapsible=0;"
        "pointerEvents=0;rounded=0;arcSize=0;"
        f"fillColor={fill};strokeColor={RULE};swimlaneFillColor={fill};"
        "fontStyle=1;fontSize=12;fontColor=#3d3a34;align=left;spacingLeft=12;"
        "verticalAlign=middle;convertToSvg=1;" + dash
    )


KIND_STROKE = {
    "front": RULE,
    "api": INK_BLUE,
    "pipeline": INK_SOFT,
    "store": MANILA,
    "external": INK_MUTED,
    "start": INK,
    "result": PENCIL,
}
KIND_FILL = {
    "front": GLASS_BRIGHT,
    "api": API_TINT,
    "pipeline": GLASS_DEEP,
    "store": GLASS_BRIGHT,
    "external": GLASS,
    "start": GLASS_BRIGHT,
    "result": GLASS_BRIGHT,
}


def box_style(kind: str, planned: bool = False) -> str:
    dash = "dashed=1;dashPattern=6 4;" if planned or kind == "external" else ""
    width = "strokeWidth=2;" if kind in ("start", "result") else "strokeWidth=1;"
    return (
        "rounded=1;arcSize=8;whiteSpace=wrap;html=1;"
        f"fillColor={KIND_FILL[kind]};strokeColor={KIND_STROKE[kind]};{width}{dash}"
        "fontSize=11;fontColor=#141414;verticalAlign=middle;align=center;"
        "spacing=6;convertToSvg=1;"
    )


def shape_style(shape: str, planned: bool) -> str:
    dash = "dashed=1;dashPattern=6 4;" if planned else ""
    if shape == "diamond":
        return (
            "rhombus;whiteSpace=wrap;html=1;"
            f"fillColor={GLASS_BRIGHT};strokeColor={INK_SOFT};strokeWidth=1;{dash}"
            "fontSize=11;fontColor=#141414;convertToSvg=1;"
        )
    if shape == "cyl":
        return (
            "shape=cylinder3;size=12;boundedLbl=1;whiteSpace=wrap;html=1;"
            f"fillColor={GLASS_BRIGHT};strokeColor={MANILA};{dash}"
            "fontSize=11;fontColor=#3d3a34;convertToSvg=1;"
        )
    raise ValueError(shape)


def edge_style(color: str = INK_SOFT, dashed: bool = False, thick: bool = False,
               extra: str = "") -> str:
    dash = "dashed=1;dashPattern=6 4;" if dashed else ""
    weight = "strokeWidth=2;" if thick else "strokeWidth=1;"
    return (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
        f"strokeColor={color};{weight}{dash}endArrow=blockThin;endFill=1;endSize=6;"
        "fontSize=10;fontColor=#3d3a34;labelBackgroundColor=#f2efe7;"
        "labelBorderColor=none;convertToSvg=1;" + extra
    )


class Page:
    def __init__(self, name: str, title: str, subtitle: str,
                 lanes: list[tuple[str, int, bool]]):
        self.name = name
        self.title = title
        self.subtitle = subtitle
        self._seq = 2
        self.lanes: list[dict] = []
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.notes: list[dict] = []
        y = 110
        for label, height, planned in lanes:
            self.lanes.append({"id": self._id("lane"), "value": esc(label),
                               "h": height, "y": y, "planned": planned})
            y += height
        self.bottom = y + 40

    def _id(self, prefix: str) -> str:
        value = f"{prefix}{self._seq}"
        self._seq += 1
        return value

    def node(self, key: str, lane: int, col: int, label: str, kind: str = "front",
             track: int = 0, w: int = NODE_W, h: int = NODE_H, planned: bool = False,
             shape: str = "box") -> dict:
        style = shape_style(shape, planned) if shape != "box" else box_style(kind, planned)
        node = {"id": self._id("n"), "value": esc(label), "style": style,
                "parent": self.lanes[lane]["id"],
                "x": LANE_PAD + col * PITCH, "y": 42 + track, "w": w, "h": h}
        self.nodes[key] = node
        return node

    def link(self, src: str, dst: str, label: str = "", color: str = INK_SOFT,
             dashed: bool = False, thick: bool = False, extra: str = "",
             points: list[tuple[float, float]] | None = None) -> None:
        self.edges.append({
            "id": self._id("e"), "value": esc(label),
            "source": self.nodes[src]["id"], "target": self.nodes[dst]["id"],
            "style": edge_style(color, dashed, thick, extra), "points": points or [],
        })

    def note(self, lane: int, col: int, label: str, w: int = 620, h: int = 60,
             track: int = 20) -> None:
        self.notes.append({
            "id": self._id("note"), "value": esc(label),
            "style": ("text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;"
                      "fontSize=11;fontColor=#5e584c;strokeColor=none;fillColor=none;"
                      "convertToSvg=1;"),
            "parent": self.lanes[lane]["id"], "x": LANE_PAD + col * PITCH,
            "y": 42 + track, "w": w, "h": h,
        })

    # ---- geometria absoluta (para âncoras e waypoints)
    def ax(self, key: str) -> float:
        return LANE_X + self.nodes[key]["x"]

    def ay(self, key: str) -> float:
        lane = next(lane for lane in self.lanes
                    if lane["id"] == self.nodes[key]["parent"])
        return lane["y"] + self.nodes[key]["y"]

    def cx(self, key: str) -> float:
        return self.ax(key) + self.nodes[key]["w"] / 2

    def cy(self, key: str) -> float:
        return self.ay(key) + self.nodes[key]["h"] / 2

    def retarget(self, src: str, dst: str, points: list[tuple[float, float]],
                 style: str | None = None) -> None:
        for e in self.edges:
            if e["source"] == self.nodes[src]["id"] and e["target"] == self.nodes[dst]["id"]:
                e["points"] = points
                if style:
                    e["style"] = style

    def xml(self) -> str:
        out = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="drawio" version="26.0.0">',
            f'  <diagram name="{esc(self.name)}" id="{self._id("page")}">',
            f'    <mxGraphModel dx="1600" dy="1000" grid="0" gridSize="10" guides="1" '
            f'tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" '
            f'pageWidth="{LANE_W + 80}" pageHeight="{self.bottom + 20}" math="0" shadow="0">',
            "      <root>",
            '        <mxCell id="0" />',
            '        <mxCell id="1" parent="0" />',
            f'        <mxCell id="ttl" value="{esc(self.title)}" style="text;html=1;align=left;'
            f'verticalAlign=bottom;fontSize=20;fontStyle=1;fontColor={INK};convertToSvg=1;" '
            f'vertex="1" parent="1"><mxGeometry x="{LANE_X}" y="30" width="1400" height="30" '
            'as="geometry" /></mxCell>',
            f'        <mxCell id="sub" value="{esc(self.subtitle)}" style="text;html=1;align=left;'
            f'verticalAlign=top;fontSize=11;fontColor={INK_MUTED};convertToSvg=1;" vertex="1" '
            f'parent="1"><mxGeometry x="{LANE_X}" y="62" width="2600" height="30" '
            'as="geometry" /></mxCell>',
        ]

        for i, lane in enumerate(self.lanes):
            fill = GLASS if i % 2 == 0 else "#eee9dd"
            out.append(
                f'        <mxCell id="{lane["id"]}" value="{lane["value"]}" '
                f'style="{lane_style(fill, lane["planned"])}" vertex="1" parent="1">'
                f'<mxGeometry x="{LANE_X}" y="{lane["y"]}" width="{LANE_W}" '
                f'height="{lane["h"]}" as="geometry" /></mxCell>'
            )

        for node in self.nodes.values():
            out.append(
                f'        <mxCell id="{node["id"]}" value="{node["value"]}" '
                f'style="{node["style"]}" vertex="1" parent="{node["parent"]}">'
                f'<mxGeometry x="{node["x"]}" y="{node["y"]}" width="{node["w"]}" '
                f'height="{node["h"]}" as="geometry" /></mxCell>'
            )

        for note in self.notes:
            out.append(
                f'        <mxCell id="{note["id"]}" value="{note["value"]}" '
                f'style="{note["style"]}" vertex="1" parent="{note["parent"]}">'
                f'<mxGeometry x="{note["x"]}" y="{note["y"]}" width="{note["w"]}" '
                f'height="{note["h"]}" as="geometry" /></mxCell>'
            )

        for e in self.edges:
            pts = ""
            if e["points"]:
                inner = "".join(f'<mxPoint x="{round(x)}" y="{round(y)}" />'
                                for x, y in e["points"])
                pts = f'<Array as="points">{inner}</Array>'
            out.append(
                f'        <mxCell id="{e["id"]}" value="{e["value"]}" style="{e["style"]}" '
                f'edge="1" parent="1" source="{e["source"]}" target="{e["target"]}">'
                f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
            )

        out += ["      </root>", "    </mxGraphModel>", "  </diagram>", "</mxfile>"]
        return "\n".join(out)


# ------------------------------------------------------------------ página 1
def page_live() -> Page:
    p = Page(
        "1. Consulta ao vivo",
        "O que acontece quando alguém abre o site",
        "Caminho ao vivo de uma coordenada fora da lista. Alvos pré-processados entram "
        "na linha tracejada (sem backend, sem rede). Tempo corre da esquerda para a direita.",
        [
            ("Visitante · navegador", 110, False),
            ("Frontend estático · GitHub Pages", 300, False),
            ("API FastAPI · Render (free)", 260, False),
            ("Pipeline científico · Python (astropy + reproject)", 220, False),
            ("Cache em disco", 170, False),
            ("IRSA · NASA / Caltech", 210, False),
        ],
    )

    # raia 0
    p.node("open", 0, 0, "Abre o link\n?ra=…&dec=…&fov=…&det=…\nou busca por nome",
           "start", h=60)

    # raia 1 — frontend
    p.node("state", 1, 1, "parseState → ViewState\n(o estado mora na URL:\nlink e embed)",
           track=96)
    p.node("choose", 1, 2, "chooseSource\nmesma posição\n(< 1″)?", track=70, w=170, h=96,
           shape="diamond")
    p.node("static", 1, 3, "manifest.json →\nfield.json do alvo\n(sem rede, sem backend)",
           track=0)
    p.node("req", 1, 4, "GET /api/v1/field\n(202 → consulta → 200)", track=150)
    p.node("decode", 1, 11, "fetch 3 arquivos\nem paralelo\ndecode .f32 + .u8\ntotal ≈ 14 KB",
           track=96, h=84)
    p.node("render", 1, 12, "asinh · zoom 1–4×\nnegativo · marca prevista\n(movimento próprio)",
           track=96, h=84)
    p.node("result", 1, 13, "anima · pisca · diferença\n(b − a) / √(var_a + var_b)",
           "result", track=84, h=84)

    # raia 2 — API
    p.node("resolve", 2, 3, "GET /api/v1/resolve\nnome → RA/Dec\n(SIMBAD: Harvard → CDS)",
           "api", track=118)
    p.node("validate", 2, 4, "valida faixa\n400 INVALID_COORDS\n400 FOV_TOO_SMALL/LARGE",
           "api", track=48, h=84)
    p.node("fid", 2, 5, "field_id = ra+dec+fov\n(0,0001° ≈ 0,36″)\nreaproveita o cache",
           "api", track=48, h=84)
    p.node("job", 2, 6, "FieldJobs\npronto? há vaga?", "api", track=30, w=170, h=96,
           shape="diamond")
    p.node("errors", 2, 8, "404 NO_COVERAGE\n502 UPSTREAM_ERROR\n429 BUSY", "api",
           track=150, h=56)
    p.node("ready", 2, 11, "200 field.json\nCache-Control: 1 h\ndata_version imutável",
           "api", track=48, h=84)

    # raia 3 — pipeline (o trabalho assíncrono)
    p.node("grid", 3, 6, "grade TAN centrada\npixel 6,15″ · n = fov·60/6,15\nrecorte 1,5 × campo",
           "pipeline", track=8)
    p.node("query", 3, 7, "TAP / ADQL\nCONTAINS(POINT, poly)\ndata · detector · URI",
           "pipeline", track=8)
    p.node("download", 3, 8, "4 downloads paralelos\n6 tentativas, 2–32 s\nPSF descartada",
           "pipeline", track=8)
    p.node("reproject", 3, 9, "reprojeta p/ grade comum\nflags em 2 níveis\nnúcleo saturado → máscara",
           "pipeline", track=8)
    p.node("coadd", 3, 10, "épocas (gap > 10 d)\ncoadd 1/var² − fundo 3σ\nlimites: p1 … máximo",
           "pipeline", track=8)
    p.node("write", 3, 11, "write_field\nfield.json + .f32/.u8/.png\nsobe pro cache de renders",
           "pipeline", track=8, h=84)

    # raia 4 — cache
    p.node("cache", 4, 9, "queries 24 h\nexposures permanente\n≈ 60 KB por recorte",
           "store", track=20, h=76, shape="cyl")
    p.note(4, 0, "Sem banco de dados: as imagens já são arquivos, e o índice é o próprio IRSA.\n"
                 "Chave do cache = URI + centro + tamanho · escrita atômica · FITS bruto descartado.")

    # raia 5 — IRSA
    p.node("tap", 5, 7, "TAP sync · ADQL · CSV\nirsa.ipac.caltech.edu\n258 exposições (WISE 0855)",
           "external", track=20, h=66)
    p.node("cutout", 5, 8, "cutout HTTP ~4 MB · ~6 s\n?center=…&size=…", "external",
           track=96, h=56)
    p.note(5, 0, "Arquivo público do Caltech — não é nosso, só consumimos.\n"
                 "WISE 0855: 258 exposições entre mai/2025 e mai/2026, agrupadas em 4 épocas.")

    # arestas
    p.link("open", "state", thick=True)
    p.link("state", "choose")
    p.link("choose", "static", "alvo da lista", extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;"
                                                 "entryX=0.5;entryY=1;entryDx=0;entryDy=0;")
    p.link("choose", "req", "coordenada", extra="exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                                                  "entryX=0;entryY=0.5;entryDx=0;entryDy=0;")
    p.link("choose", "resolve", "nome", extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                                              "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
    p.link("resolve", "validate", "RA / Dec")
    p.link("req", "validate", "GET /field", extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                                                  "entryX=0.25;entryY=0;entryDx=0;entryDy=0;")
    p.link("validate", "fid")
    p.link("fid", "job")
    p.link("job", "errors", "sem cobertura /\nIRSA fora / fila cheia", INK_MUTED,
           dashed=True, extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                              "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
    p.link("job", "ready", "200 (trabalho já feito)", INK_BLUE,
           extra="exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;"
                 "entryDx=0;entryDy=0;")
    p.link("job", "grid", "inicia o trabalho", INK_BLUE,
           extra="exitX=0.75;exitY=1;exitDx=0;exitDy=0;entryX=0.75;entryY=0;"
                 "entryDx=0;entryDy=0;")
    p.link("job", "req", "202 · progresso done/total\npoll a cada 2 s", INK_BLUE,
           extra="exitX=0.25;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0.65;"
                 "entryDx=0;entryDy=0;")
    p.link("grid", "query")
    p.link("query", "download")
    p.link("query", "tap", "ADQL → CSV", INK_MUTED,
           extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;"
                 "entryDx=0;entryDy=0;")
    p.link("download", "cutout", "pede recorte", INK_MUTED,
           extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;"
                 "entryDx=0;entryDy=0;")
    p.link("cutout", "cache", "grava .npz", INK_MUTED, dashed=True,
           extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;"
                 "entryDx=0;entryDy=0;")
    p.link("cache", "reproject", "reaproveita", MANILA, dashed=True,
           extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;"
                 "entryDx=0;entryDy=0;")
    p.link("download", "reproject")
    p.link("reproject", "coadd")
    p.link("coadd", "write")
    p.link("write", "ready", "field.json pronto",
           extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;")
    p.link("ready", "decode", "",
           extra="exitX=0.35;exitY=0;exitDx=0;exitDy=0;entryX=0.35;entryY=1;entryDx=0;entryDy=0;")
    p.link("decode", "render")
    p.link("render", "result")
    p.link("static", "decode", "mesmos JSON + .f32", MANILA, dashed=True,
           extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0.5;"
                 "entryDx=0;entryDy=0;")

    # 202: desce para a sub-faixa da raia da API, volta à esquerda e entra no nó de pedido
    api_lane = p.lanes[2]
    sub_y = api_lane["y"] + 226
    entry_y = p.ay("req") + 0.5 * p.nodes["req"]["h"]
    straight = (edge_style(INK_BLUE).replace("edgeStyle=orthogonalEdgeStyle;", "edgeStyle=none;")
                + "exitX=0.25;exitY=1;exitDx=0;exitDy=0;"
                  "entryX=0;entryY=0.5;entryDx=0;entryDy=0;")
    p.retarget(
        "job", "req",
        [(p.ax("job") + 42, sub_y), (p.ax("req") - 22, sub_y), (p.ax("req") - 22, entry_y)],
        style=straight,
    )

    # atalho estático: corre na altura do nó de decode, acima do pedido à API
    p.retarget("static", "decode",
               [(p.cx("static"), p.cy("decode")), (p.ax("decode") - 16, p.cy("decode"))])
    return p


# ------------------------------------------------------------------ página 2
def page_scheduled() -> Page:
    p = Page(
        "2. Atualização agendada",
        "Fase 5 — o robô que mantém os alvos prontos (planejado, ainda não no repositório)",
        "Bordas tracejadas = ainda não existe: hoje só o test.yml roda. O mesmo pipeline da "
        "API roda no runner, e a validação científica pode bloquear a publicação.",
        [
            ("GitHub · gatilho", 140, False),
            ("Runner Ubuntu · GitHub Actions", 320, False),
            ("Pipeline científico · build_static", 210, False),
            ("Cache do Actions", 180, False),
            ("IRSA · NASA / Caltech", 170, False),
            ("Validação científica · pytest -m science", 240, False),
            ("GitHub Pages · publicação", 180, False),
        ],
    )
    planned = True

    p.node("cron", 0, 0, "cron 0 6 */3 * *\nou push na main\nou “Run workflow”", "start",
           planned=planned, h=62)
    p.note(0, 2, "Nada nesta página existe ainda: o update-data.yml entra na fase 5.\n"
                 "A execução fica registrada e auditável na aba Actions.", w=620, track=26,
           h=54)

    p.node("setup", 1, 1, "checkout\nsetup-python 3.12\nrestore actions/cache", track=10,
           planned=planned)
    p.node("build", 1, 2, "build_static\n--targets targets.yaml\n(5 alvos)", track=10,
           planned=planned)
    p.node("manifest", 1, 10, "manifest.json\ngenerated_at\nlatest_exposure_mjd", track=10,
           planned=planned, h=84)
    p.node("artifact", 1, 11, "upload-pages-artifact\nfrontend/ + data/", track=10,
           planned=planned)

    p.node("targets", 2, 3, "targets.yaml → Target\ncentro = posição propagada\npelo movimento próprio",
           "pipeline", track=8, planned=planned)
    p.node("field", 2, 4, "build_field\n(mesmo pipeline da API)", "pipeline", track=8,
           planned=planned)
    p.node("write", 2, 7, "write_field\nfield.json + .f32/.u8/.png", "pipeline", track=8,
           planned=planned)

    p.node("rcache", 3, 5, "cache/exposures\nsó o que falta baixar", "store", track=30,
           h=76, shape="cyl", planned=planned)
    p.note(3, 0, "actions/cache guarda os recortes entre execuções.\n"
                 "O GitHub apaga cache sem uso há 7 dias — daí o cron de 3 em 3 dias.", w=620,
           track=40)

    p.node("irsa", 4, 6, "TAP + cutouts\nsó exposições novas", "external", track=24,
           h=66, planned=planned)
    p.note(4, 0, "Primeira execução: ~1.950 recortes, ~60 min.\n"
                 "Com o cache cheio: consulta + exposições novas, 1–3 min.", w=620, track=30)

    p.node("science", 5, 8, "pytest -m science\nposições, movimento próprio,\népocas e S/R",
           "pipeline", track=10, planned=planned, h=70)
    p.node("gate", 5, 9, "passou?", "pipeline", track=20, w=150, h=86, shape="diamond",
           planned=planned)
    p.node("fail", 5, 10, "falha → não publica\n(o relatório fica no run)", "pipeline",
           track=140, planned=planned, h=56)
    p.note(5, 0, "A validação não é um relatório: se ela falha, o deploy não acontece.\n"
                 "Tolerâncias medidas com os 5 alvos reais (docs/06-testes.md).", w=620, track=40)

    p.node("deploy", 6, 12, "deploy-pages\n<user>.github.io/spherex-viewer\nabre na hora, sem backend",
           "result", track=34, planned=planned, h=84)

    p.link("cron", "setup", thick=True)
    p.link("setup", "build")
    p.link("build", "targets", extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                                     "entryX=0;entryY=0.5;entryDx=0;entryDy=0;")
    p.link("targets", "field")
    p.link("field", "rcache", "consulta o que falta", MANILA, dashed=True,
           extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;")
    p.link("rcache", "irsa", "o que falta", INK_MUTED, dashed=True,
           extra="exitX=0.6;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
    p.link("irsa", "write", "recortes novos",
           extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;")
    p.link("field", "write")
    p.link("write", "science", "5 campos", color=INK_BLUE,
           extra="exitX=0.25;exitY=1;exitDx=0;exitDy=0;entryX=0.25;entryY=0;entryDx=0;entryDy=0;")
    p.link("science", "gate")
    p.link("gate", "fail", "não", INK_MUTED, dashed=True,
           extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;")
    p.link("gate", "manifest", "sim", INK_BLUE,
           extra="exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;")
    p.link("manifest", "artifact")
    p.link("artifact", "deploy", "artefato", extra="exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                                                   "entryX=0.5;entryY=0;entryDx=0;entryDy=0;")
    return p


# ------------------------------------------------------------------ página 3
def page_legend() -> str:
    rows = [
        ("Frontend (navegador / site estático)", GLASS_BRIGHT, RULE, False),
        ("API FastAPI (Render)", API_TINT, INK_BLUE, False),
        ("Pipeline científico (Python)", GLASS_DEEP, INK_SOFT, False),
        ("Cache / arquivo em disco", GLASS_BRIGHT, MANILA, False),
        ("Serviço externo (IRSA)", GLASS, INK_MUTED, True),
        ("Resultado para o visitante", GLASS_BRIGHT, PENCIL, False),
        ("Fase 5 — planejado (não existe ainda)", GLASS_BRIGHT, INK_SOFT, True),
    ]
    cells: list[str] = []
    for i, (label, fill, stroke, dashed) in enumerate(rows):
        dash = "dashed=1;dashPattern=6 4;" if dashed else ""
        y = 140 + i * 42
        cells.append(
            f'<mxCell id="sw{i}" value="" style="rounded=1;arcSize=8;html=1;fillColor={fill};'
            f'strokeColor={stroke};strokeWidth=1;{dash}" vertex="1" parent="1">'
            f'<mxGeometry x="40" y="{y}" width="52" height="24" as="geometry" /></mxCell>'
        )
        cells.append(
            f'<mxCell id="sl{i}" value="{esc(label)}" style="text;html=1;align=left;'
            f'verticalAlign=middle;fontSize=12;fontColor=#3d3a34;convertToSvg=1;" vertex="1" '
            f'parent="1"><mxGeometry x="106" y="{y}" width="330" height="24" '
            'as="geometry" /></mxCell>'
        )

    blocks = [
        ("Números medidos no pipeline real", [
            "258 exposições do WISE 0855 entre mai/2025 e mai/2026, em 4 épocas.",
            "Cada recorte: ~4 MB e ~6 s; ~95% do peso é a extensão PSF, descartada.",
            "Cache de exposições: ~60 KB por recorte (~370 MB para 1.950).",
            "Primeira execução do Action: ~60 min. Com cache cheio: 1–3 min.",
            "Quadro entregue ao navegador: 60×60 float32 ≈ 14 KB.",
            "Pixel do SPHEREx: 6,15″. Barnard's Star anda ~1,5–2 px por semestre.",
            "Recorte 1,5 × o campo: cobre a diagonal (√2 ≈ 1,41) sem perder a borda.",
            "Flags em 2 níveis: 5 bits sempre fora; 4 bits só se não houver pixel limpo.",
        ]),
        ("Regras que o desenho respeita", [
            "Um único formato de dados para os dois caminhos (API e Pages).",
            "O pesado fica no servidor; contraste, blink e diferença ficam no navegador.",
            "Validação científica bloqueia a publicação — não é só um relatório.",
            "Erro transitório do IRSA é esquecido: o próximo pedido tenta de novo.",
            "Fonte: docs/03-arquitetura.md, 04-api.md, 05-hospedagem.md e o código.",
        ]),
    ]

    y = 140
    for title, items in blocks:
        cells.append(
            f'<mxCell id="h{y}" value="{esc(title)}" style="text;html=1;align=left;'
            f'verticalAlign=top;fontSize=14;fontStyle=1;fontColor=#141414;convertToSvg=1;" '
            f'vertex="1" parent="1"><mxGeometry x="490" y="{y}" width="560" height="24" '
            'as="geometry" /></mxCell>'
        )
        y += 30
        for item in items:
            cells.append(
                f'<mxCell id="b{y}" value="{esc("· " + item)}" style="text;html=1;align=left;'
                f'verticalAlign=top;fontSize=11;fontColor=#5e584c;convertToSvg=1;" vertex="1" '
                f'parent="1"><mxGeometry x="490" y="{y}" width="560" height="34" '
                'as="geometry" /></mxCell>'
            )
            y += 34
        y += 20

    body = "\n".join(cells)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="3. Legenda e números" id="legend">
    <mxGraphModel dx="1200" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="1100" pageHeight="720" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="ttl" value="Legenda e números por trás do desenho" style="text;html=1;align=left;verticalAlign=bottom;fontSize=20;fontStyle=1;fontColor={INK};convertToSvg=1;" vertex="1" parent="1"><mxGeometry x="40" y="46" width="900" height="30" as="geometry" /></mxCell>
        <mxCell id="sub" value="Medidas tiradas do código e dos resultados reais (docs/08-resultados.md); não são estimativas de projeto." style="text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor={INK_MUTED};convertToSvg=1;" vertex="1" parent="1"><mxGeometry x="40" y="80" width="900" height="30" as="geometry" /></mxCell>
{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
'''


def inner(page_xml: str) -> str:
    """Extrai <diagram>…</diagram> de um mxfile de página única."""
    match = re.search(r"(<diagram\b.*?</diagram>)", page_xml, re.S)
    if not match:
        raise SystemExit("diagrama não encontrado")
    return match.group(1)


def main() -> None:
    here = Path(__file__).resolve().parent
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "fluxo-do-sistema.drawio"
    pages = [page_live(), page_scheduled()]
    body = "\n".join(inner(p.xml()) for p in pages) + "\n" + inner(page_legend())
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<mxfile host="drawio" version="26.0.0">\n' + body + "\n</mxfile>\n")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print(f"escrito {out} ({len(xml)} bytes, {len(pages) + 1} páginas)")


if __name__ == "__main__":
    main()
