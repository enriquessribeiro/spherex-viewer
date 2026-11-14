---
name: SPHEREx Viewer
description: As épocas do SPHEREx como placas fotográficas de vidro no comparador de piscar.
colors:
  glass: "#f2efe7"
  glass-deep: "#e7e2d5"
  glass-bright: "#fbf9f4"
  sleeve: "#ddd6c4"
  ink: "#141414"
  ink-soft: "#3d3a34"
  ink-muted: "#5e584c"
  pencil: "#c4302b"
  pencil-deep: "#9e2420"
  ink-blue: "#2b4c9c"
  manila: "#9c8f74"
  rule: "#bdb39b"
typography:
  display:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 1rem + 1.2vw, 2.1rem)"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 112"
  headline:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 118"
  title:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 700
    lineHeight: 1.25
    fontVariation: "'wdth' 105"
  body:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum' 1"
  body-small:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "'tnum' 1"
  label:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
    letterSpacing: "0.06em"
    fontVariation: "'wdth' 78"
  control:
    fontFamily: "Archivo Variable, Archivo, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    fontVariation: "'wdth' 92"
rounded:
  hairline: "2px"
  base: "3px"
spacing:
  gap: "clamp(1rem, 0.6rem + 1.2vw, 1.75rem)"
  group: "1.6rem"
  stack: "0.55rem"
  tight: "0.4rem"
components:
  button:
    backgroundColor: "{colors.glass-bright}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.base}"
    padding: "0.5rem 0.9rem"
  button-hover:
    backgroundColor: "{colors.glass-deep}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.glass}"
    typography: "{typography.control}"
    rounded: "{rounded.base}"
    padding: "0.5rem 0.9rem"
  button-primary-hover:
    backgroundColor: "{colors.ink-soft}"
  segmented-option:
    backgroundColor: "{colors.glass-bright}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    padding: "0.45rem 0.85rem"
  segmented-option-checked:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.glass}"
  input-search:
    backgroundColor: "{colors.glass-bright}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.base}"
    padding: "0.55rem 0.75rem 0.55rem 2.2rem"
  target-card:
    backgroundColor: "{colors.glass-bright}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    padding: "0.4rem 0.6rem 0.4rem 0.4rem"
  target-card-pressed:
    backgroundColor: "{colors.glass-deep}"
  plate-facts:
    backgroundColor: "{colors.sleeve}"
    textColor: "{colors.ink}"
    typography: "{typography.body-small}"
    padding: "0.35rem 0.65rem"
  plate-inscription:
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0.15rem 0.45rem"
---

# Design System: SPHEREx Viewer

## Overview

**Creative North Star: "Placas do comparador"**

Cada época do SPHEREx é uma placa fotográfica de vidro posta no comparador de piscar, o aparelho que achou Plutão em 1930. A tela é a bancada do astrônomo: o vidro claro e levemente quente é o fundo de tudo, o céu aparece em negativo (estrelas em tinta preta sobre vidro), e as únicas marcas coloridas são as que uma pessoa faria à mão sobre a placa: o círculo e a seta em lápis de cera vermelho onde o objeto deveria estar. Etiquetas de envelope em manila e uma régua do tempo proporcional às datas reais completam o material.

A densidade é de instrumento, não de vitrine: a placa quadrada domina, os controles ficam numa coluna estreita com rótulos pequenos em caixa alta, e todo número usa algarismos tabulares para que datas, intervalos e faixas em µm não dancem ao trocar de época. O mundo recusa o padrão da categoria: o azul-marinho de "espaço" com brilhos e acentos neon.

Profundidade é física e mínima: a placa é o único objeto que se ergue da bancada; o resto é papel, vidro e traço fino.

**Key Characteristics:**
- Fundo de vidro claro (`glass`) em toda a tela; céu em negativo por padrão.
- Tinta de negativo (`ink`) para texto, estrelas e estados selecionados.
- Lápis vermelho (`pencil`) reservado a marcas de descoberta e ao que "apareceu".
- Azul-tinta (`ink-blue`) para o que "sumiu", a mira, o foco e a seleção de texto.
- Uma só família (Archivo Variable), modulada pelo eixo de largura em vez de por troca de fonte.
- Cantos quase retos (3px), bordas de 1px, sem gradientes nem brilhos.

## Colors

Uma paleta de material de arquivo: vidro, tinta, papel manila e dois pigmentos de anotação, cada um com um único trabalho.

### Primary
- **Tinta de Negativo** (`ink`): texto principal, estrelas no céu em negativo, borda da placa, fundo do botão primário e de toda opção marcada (segmentado, detector). É a "cor de ação" do sistema: selecionar algo é pintá-lo de tinta.

### Secondary
- **Lápis de Cera Vermelho** (`pencil`): o círculo e a seta à mão sobre a posição prevista, o traço da época atual na régua do tempo, os pixels que "apareceram ou ficaram mais brilhantes" na diferença e a borda de erro do aviso da placa.
- **Lápis Vermelho Fundo** (`pencil-deep`): a versão legível do lápis quando ele vira texto (data da época atual na régua, mensagem de erro).

### Tertiary
- **Azul-Tinta** (`ink-blue`): os pixels que "sumiram ou ficaram mais fracos" na diferença, a mira fixa no centro da placa, o par A/B na régua, o anel de foco do teclado e a seleção de texto.

### Neutral
- **Vidro da Placa** (`glass`): fundo da página, do cabeçalho e da placa; céu vazio no negativo; cor do texto sobre tinta.
- **Vidro Fosco** (`glass-deep`): hover de botões e opções, alvo selecionado, trilho da barra de rolagem.
- **Vidro Polido** (`glass-bright`): a face de todo controle que se toca (botões, campos, cartões de alvo, detectores, selects, aviso da placa); um passo mais claro que o fundo, para que o controle pareça uma lâmina sobre a bancada. No CSS: `--glass-bright`.
- **Envelope** (`sleeve`): faixa de fatos sob a placa (intervalo, detector, exposições) e trilho da faixa em µm dos detectores.
- **Manila** (`manila`): borda superior da etiqueta da placa, moldura da inscrição e do zoom, marcas de mês na régua, segmento da faixa em µm, sublinhado de links, polegar da barra de rolagem.
- **Linha de Régua** (`rule`): bordas de 1px em repouso (campos, cartões, botões discretos, divisórias do segmentado, cabeçalho) e controles desativados.
- **Tinta Média** (`ink-soft`): bordas de botões, títulos de seção, régua e marcas de ano, hover do botão primário.
- **Tinta Apagada** (`ink-muted`): texto secundário (descrições, ajudas, rótulos dos fatos, datas da régua, placeholders, créditos).

### Named Rules
**A Regra da Cor Única para Mudança.** Vermelho e azul só significam mudança ou descoberta. Nada decorativo, nenhum ícone, nenhum fundo de seção usa `pencil` ou `ink-blue`; e a diferença sempre vem com legenda textual ao lado das amostras.

**A Regra do Manila Mudo.** Manila (contraste 2,8:1 sobre o vidro) é cor de traço, borda e etiqueta física, nunca de texto. Texto secundário usa `ink-muted` (6,1:1).

**A Regra da Seleção em Tinta.** O estado "escolhido" é sempre inverter para tinta sobre vidro (`ink` de fundo, `glass` no texto); não existe cor de marca para seleção.

## Typography

**Display Font:** Archivo Variable (com Archivo, system-ui, sans-serif), auto-hospedada via @fontsource com o eixo de largura
**Body Font:** a mesma
**Label/Mono Font:** a mesma, comprimida pelo eixo de largura

**Character:** Uma grotesca de instrumento usada como um tipógrafo usaria uma família de tipos de madeira: larga e pesada para o nome do objeto, estreita e espaçada para os rótulos de etiqueta. O eixo `wdth` (78% a 118%) faz o trabalho que em outros sistemas faria uma segunda fonte.

### Hierarchy
- **Display** (800, clamp de 1,5rem a 2,1rem, 1,05, largura 112%): o nome do alvo na etiqueta da placa. Um por tela.
- **Headline** (800, 1,5rem, 1,05, largura 118%): o nome do produto no cabeçalho.
- **Title** (700, 0,9375rem, 1,25, largura 105%): nome do alvo no cartão, nome do detector (D1–D6, em 800).
- **Body** (400, 0,9375rem, 1,5): texto corrido e valores; ajudas curtas limitadas a 34–46ch.
- **Body small** (400, 0,8125rem): descrições, fatos da placa, legendas, régua.
- **Label** (700, 0,8125rem, 0,06em, caixa alta, largura 78%): títulos de grupo de controles e rótulos dos fatos da etiqueta, em `ink-soft` ou `ink-muted`.
- **Control** (600, 0,9375rem, largura 90–92%): texto de botões e opções segmentadas.

### Named Rules
**A Regra dos Algarismos Tabulares.** `font-variant-numeric: tabular-nums` no corpo inteiro; datas, contagens de exposição e faixas em µm não mudam de largura ao trocar de época.

**A Regra da Largura, Não da Família.** Hierarquia vem de peso e do eixo de largura da Archivo; não introduzir uma segunda família.

## Layout

A tela é uma bancada em duas colunas, centrada até 96rem: à esquerda a placa quadrada, dimensionada por `clamp(20rem, 100vh − 20,5rem, 62vw)` para caber com a etiqueta e a régua na primeira dobra; à direita uma coluna de controles de 18 a 27rem. O espaçamento externo e entre colunas é um único passo fluido (`gap`, 1 a 1,75rem). Dentro da coluna, grupos de controle se separam por 1,6rem e seus itens por 0,4–0,55rem.

Abaixo de 960px a bancada vira uma coluna só, o grupo "Comparar" sobe para antes da lista de alvos e os alvos passam a uma grade `auto-fill` de 15rem. Abaixo de 640px o cabeçalho quebra em duas linhas (busca em largura total), o botão de copiar link vira só ícone e a margem fica fixa em 1rem. No modo `embed` (iframe) só a placa e sua etiqueta permanecem.

A régua do tempo é proporcional às datas reais: posição horizontal = data, altura do traço = número de exposições; marcas de mês curtas em manila, de ano mais altas em `ink-soft`.

## Elevation & Depth

O sistema é plano, com uma exceção física: a placa. Ela é uma lâmina de vidro pousada na bancada, com uma luz de 1px no topo e uma sombra difusa embaixo. O aviso de carregamento/erro sobre a placa usa uma sombra irmã, mais curta. Todo o resto (botões, cartões, campos) é plano, separado por bordas de 1px e por variações de vidro.

### Shadow Vocabulary
- **Placa pousada** (`box-shadow: 0 1px 0 #fffdf8 inset, 0 10px 28px -14px rgb(20 20 20 / 0.45)`): só no quadro da placa.
- **Aviso sobre a placa** (`box-shadow: 0 8px 22px -12px rgb(20 20 20 / 0.4)`): só no cartão de status centrado na placa.
- **Contorno de seleção** (`box-shadow: 0 0 0 1px ink inset`): engrossa a borda do cartão de alvo selecionado para 2px sem mexer no layout.

### Named Rules
**A Regra da Placa Única.** Só a placa e o que está sobre ela ganham sombra. Controles nunca se erguem; estado é dado por tinta, vidro fosco ou borda.

## Shapes

Cantos quase retos: 3px (`base`) em botões, campos, cartões, segmentados, detectores e no anel de foco; 2px (`hairline`) em peças pequenas (inscrição, amostras da legenda, faixa em µm). A placa em si tem canto vivo e borda de 1px em tinta. Bordas são sempre de 1px; a única exceção é o filete superior de 2px em manila da faixa de fatos, que lembra a dobra do envelope da placa.

As marcas de lápis são a única geometria orgânica: um círculo levemente irregular que passa um pouco do ponto inicial e termina em espiral leve, e uma seta curva vinda do canto superior direito, com traço de 2,5px sobre halo de vidro de 6px.

## Components

### Buttons
Lâminas de vidro polido com borda de tinta, firmes e sem enfeite.
- **Shape:** cantos quase retos (3px), borda de 1px em `ink-soft`.
- **Default:** fundo `glass-bright`, texto `ink`, 600 com largura 92%, padding 0,5rem 0,9rem, ícone Lucide de 18px (traço 1,75) a 0,45rem do rótulo.
- **Primary:** inverte para tinta (`ink` de fundo, `glass` no texto); um por área (o Animar/Pausar).
- **Quiet:** borda em `rule` em vez de `ink-soft` (copiar link).
- **Icon:** padding quadrado de 0,5rem, sempre com `aria-label`.
- **Hover / Focus:** hover troca o fundo para `glass-deep` (primário: `ink-soft`) em 160ms com `cubic-bezier(0.16, 1, 0.3, 1)`; foco é anel de 2px em `ink-blue` a 2px de distância.
- **Disabled:** texto `ink-muted`, borda `rule`, opacidade 0,7.

### Segmented control
Grupo de rádio com borda externa em `ink-soft`, divisórias internas em `rule` e opção marcada invertida em tinta. Usado para modo (Animar/Piscar/Diferença), aparência do céu (Negativo/Positivo) e zoom; sobre a placa o zoom fica com moldura manila e fundo de vidro a 90%.

### Cards / Containers
- **Cartão de alvo:** miniatura quadrada de 3,5rem (pixelada, borda `ink-soft`) + nome (Title) + descrição (Body small, `ink-muted`). Fundo `glass-bright`, borda `rule`, 3px; hover escurece a borda para `ink-soft`; selecionado ganha fundo `glass-deep` e contorno de tinta de 2px.
- **Botão de detector:** grade de 2 colunas; nome D1–D6 à esquerda, faixa em µm à direita e, embaixo, uma barra de 4px em `sleeve` com o trecho do detector em `manila`, em escala real de 0,75 a 5,00 µm. Marcado inverte para tinta, com a barra em `ink-soft` e o trecho em `glass`.

### Inputs / Fields
- **Style:** fundo `glass-bright`, borda 1px `rule`, 3px; a busca tem ícone de lupa em `ink-muted` dentro do campo à esquerda.
- **Focus:** borda passa a `ink-blue` e o anel de foco encosta no campo (offset 0).
- **Selects e sliders** herdam a mesma face; sliders e checkbox usam `accent-color: ink`.

### Navigation
Um cabeçalho fino em vidro com filete inferior `rule`: marca à esquerda (Headline + subtítulo em largura 80%, `ink-muted`), busca flexível até 30rem e o botão discreto de copiar link à direita.

### Etiqueta da placa (signature)
A legenda da placa imita a etiqueta do envelope: nome do alvo em Display à esquerda, data ou intervalo de época em 600 à direita, e uma faixa de fatos em `sleeve` com filete superior manila de 2px, rótulos em Label (`ink-muted`) e valores em 600. No canto superior esquerdo da placa, uma inscrição pequena (detector, campo, A/B no Piscar) em moldura manila sobre vidro a 88%.

### Marcas de lápis (signature)
Círculo e seta desenhados à mão em `pencil` (2,5px, opacidade 0,92) sobre halo de `glass` (6px), com raio fixo de ~22px de tela em qualquer zoom; acompanham a posição prevista do objeto época a época. Na diferença, a posição anterior aparece como círculo tracejado (3 4) a 55%. A mira fixa é uma cruz aberta em `ink-blue` de 1,5px no centro da placa.

### Régua do tempo (signature)
Linha de base em `ink-soft`; cada época é um traço de 4px cuja altura é o número de exposições, com data e contagem acima. Hover: traço em tinta, 6px. Par A/B: `ink-blue`, 6px. Época atual: `pencil`, 7px, com a data em `pencil-deep`.

## Do's and Don'ts

### Do:
- **Do** manter o fundo em `glass` e o céu em negativo (estrelas em `ink`) como estado padrão.
- **Do** reservar `pencil` às marcas de descoberta, à época atual e ao que "apareceu"; `ink-blue` ao que "sumiu", à mira e ao foco.
- **Do** acompanhar qualquer uso de vermelho/azul como dado com legenda textual.
- **Do** renderizar a diferença em unidades de ruído: abaixo de 2σ o pixel fica vidro, a partir de 5σ cor cheia.
- **Do** usar algarismos tabulares e o eixo de largura da Archivo para hierarquia.
- **Do** marcar seleção invertendo para tinta sobre vidro, e foco com anel de 2px em `ink-blue`.
- **Do** manter cantos em 3px (2px em peças pequenas) e bordas de 1px.
- **Do** escalar a régua do tempo pelas datas reais e a faixa do detector pela escala real em µm.

### Don't:
- **Don't** usar o visual de "espaço" da categoria: fundo azul-marinho ou preto, brilhos, nebulosas, acentos neon.
- **Don't** usar `pencil` ou `ink-blue` como cor decorativa, de marca, de botão ou de fundo de seção.
- **Don't** usar `manila` para texto; ele não passa de 2,8:1 sobre o vidro.
- **Don't** dar sombra a controles; só a placa e o aviso sobre ela se erguem.
- **Don't** trocar o círculo à mão por um círculo geométrico perfeito de CSS.
- **Don't** introduzir uma segunda família tipográfica.
