# SPHEREx Viewer — Visão geral do projeto

> NASA Space Apps Challenge 2026 (14–15 de novembro de 2026)
> Desafio: **Planet X and SPHEREx**

## 1. Resumo

O **SPHEREx Viewer** é uma ferramenta web pública que mostra imagens reais do telescópio espacial **SPHEREx** da NASA para qualquer região do céu e as anima no tempo, como um pequeno vídeo. Assim qualquer pessoa, cientista ou curiosa, consegue ver o que **se move ou muda de brilho** entre uma observação e outra: asteroides, cometas, estrelas próximas, anãs marrons e, quem sabe, um planeta ainda desconhecido.

O usuário digita uma coordenada (Ascensão Reta e Declinação) ou escolhe um alvo pronto. A ferramenta busca as imagens no arquivo público da NASA (IRSA/Caltech), processa tudo e mostra:

- uma **animação** das épocas disponíveis daquele trecho do céu;
- modos de **piscar** (blink) e **subtrair** imagens de datas diferentes, para destacar o que mudou;
- o **espectro infravermelho** (0,75–5,0 µm) de qualquer ponto clicado;
- **sobreposições** de catálogos de outros telescópios (Gaia, WISE);
- **links compartilháveis** com as coordenadas na URL.

## 2. Contexto científico

### 2.1 Por que comparar imagens no tempo?

Objetos próximos mudam de posição aparente no céu:

- **Asteroides e cometas** orbitam o Sol e se deslocam rápido entre imagens tiradas com horas ou dias de diferença.
- **Estrelas e anãs marrons próximas** têm *movimento próprio*: se deslocam devagar (segundos de arco por ano) enquanto orbitam a Galáxia.
- **Paralaxe**: como a Terra (e o SPHEREx) orbita o Sol, objetos próximos parecem oscilar ao longo do ano. Medir essa oscilação dá a distância.
- **Estrelas variáveis** não se movem, mas mudam de brilho.

Foi assim que Clyde Tombaugh descobriu **Plutão** em 1930: comparando duas chapas fotográficas e notando um ponto que tinha se deslocado. Hoje projetos de ciência cidadã como o [Backyard Worlds](https://backyardworlds.org) usam a mesma técnica, e voluntários já descobriram a maior parte dos cometas e anãs marrons conhecidos.

### 2.2 A missão SPHEREx

- Lançada em **março de 2025**, observando desde **maio de 2025**.
- Mapeia o **céu inteiro a cada ~6 meses**.
- Faz imagens em **102 bandas** do infravermelho próximo, de **0,75 a 5,0 µm**: cada imagem é, na prática, um espectro de baixa resolução de tudo no campo.
- É muito sensível a moléculas como **água, CO₂, CO e hidrocarbonetos**, e a objetos frios como anãs marrons, que são brilhantes em ~4–5 µm e quase invisíveis no óptico.
- Mais de **1 bilhão de objetos** registrados. É dado demais para uma pessoa (ou um algoritmo sozinho) analisar, daí a necessidade de ferramentas que coloquem o público para ajudar.

**Os 6 detectores.** O SPHEREx tem 6 detectores, cada um coberto por um filtro de variação linear (LVF): o comprimento de onda varia ao longo da imagem. Cada exposição de cada detector cobre uma faixa:

| Detector / Banda | Faixa (µm) | Resolução espectral R |
|---|---|---|
| D1 | 0,75 – 1,09 | 39 |
| D2 | 1,10 – 1,62 | 41 |
| D3 | 1,63 – 2,41 | 41 |
| D4 | 2,42 – 3,82 | 35 |
| D5 | 3,83 – 4,41 | 112 |
| D6 | 4,42 – 5,00 | 128 |

Como o céu "anda" pelo filtro a cada apontamento, um mesmo ponto do céu acaba medido em todos os comprimentos de onda depois de várias exposições, e é assim que se monta o espectro.

## 3. O desafio

### 3.1 Objetivo obrigatório

> Criar uma ferramenta web pública que mostre imagens do céu da missão SPHEREx e torne fácil para qualquer pessoa ver rapidamente como elas mudam ao longo do tempo. O usuário digita as coordenadas (RA e Dec) de um trecho do céu; a ferramenta mostra uma série de imagens desse trecho como um pequeno vídeo, facilitando ver objetos em movimento.

### 3.2 Alvos de teste exigidos

| Alvo | O que é | O que esperamos ver | RA, Dec (J2000, época 2000) | Movimento próprio (mas/ano, α*, δ) |
|---|---|---|---|---|
| **Barnard's Star** | Anã vermelha a 6 anos-luz, o maior movimento próprio conhecido (~10,4″/ano) | Deslocamento de ~1,7 px/ano para o norte | 269,45208°, +4,69336° | −801,6, +10362,4 |
| **Epsilon Indi B** | Par de anãs marrons (Ba/Bb) orbitando ε Indi A (a 6,7′), a ~12 anos-luz | Ponto frio movendo-se ~4,7″/ano para sudeste, como ε Indi A | 331,04415°, −56,78284° | +3982,0, −2466,8 |
| **WISE 0855** | A anã marrom mais fria conhecida (~285 K), a 7,4 anos-luz | Quase invisível no curto IR, aparece em ~4–5 µm; move ~8,1″/ano para oeste | 133,81891°, −7,24705° | −8123,7, +673,2 |
| **RW Aurigae** | Estrela jovem variável (T Tauri) | Variação de brilho entre épocas | 76,95653°, +30,40144° | +7,2, −20,3 |
| **R Draconis** | Variável de longo período (tipo Mira), ~245 dias | Grande variação de brilho entre épocas | 248,16761°, +66,75498° | −20,6, +6,1 |

Fonte: SIMBAD (espelho de Harvard), consultado em 14/11/2026; mesmos valores em [`targets.yaml`](../targets.yaml). As posições são para a época J2000 e precisam ser **propagadas pelo movimento próprio** até a data da observação: em 2025 o WISE 0855 está ~3,4′ a oeste da coordenada da sua designação (que é de 2010, usada no texto do desafio).

### 3.3 Considerações opcionais (diferenciais)

Itens que o desafio sugere e que pretendemos atender, em ordem de prioridade:

1. **Fácil atualização com novos releases**: coleções de dados configuráveis, sem nada fixo no código.
2. **Uso criativo das 102 bandas**: somar todas as exposições de cada detector numa época para aumentar o sinal/ruído; composição colorida (falsa cor) combinando detectores.
3. **Espectro sob demanda** ("extra kudos"): clicar num ponto e ver o espectro 0,75–5 µm.
4. **Somar e subtrair épocas**: imagem de diferença para destacar o que se moveu ou variou.
5. **Campo de visão escolhível**: maior permite rastrear objetos rápidos, ao custo de mais transferência.
6. **Sobreposição de outros telescópios**: Gaia e WISE, via Aladin Lite.
7. **Coordenadas na URL**: links compartilháveis e incorporáveis (iframe).
8. **Metadados e flags de contaminação**: mostrar pixels com problemas (fantasmas, pixels quentes, etc.).
9. **Usar ferramentas existentes**: Astropy (processamento) e Aladin Lite / CDS (visualização).

## 4. Dados

### 4.1 Fonte

Os dados ficam no **IRSA** (NASA/IPAC Infrared Science Archive, Caltech): <https://irsa.ipac.caltech.edu/Missions/spherex.html>

| Release | Data | Situação |
|---|---|---|
| QR2 (Quick Release 2) | out/2025 | Substituído por QR3/DR1 |
| QR3 | set/2026 | Disponível (`spherex_qr3`, `spherex_qr3_deep`) |
| **DR1** (Data Release 1) | nov/2026 | **Disponível** (`spherex_dr1`, `spherex_dr1_deep`) |

### 4.2 Produto usado: Spectral Image (Level 2)

Cada arquivo é um FITS multiextensão de **2040 × 2040 pixels** (~6″/pixel) com:

| Extensão | Conteúdo | Uso no projeto |
|---|---|---|
| `IMAGE` | Fluxo calibrado (MJy/sr), luz zodiacal **não** subtraída | Imagem principal |
| `FLAGS` | Bitmap de flags por pixel | Máscara e overlay de contaminação |
| `VARIANCE` | Variância por pixel | Pesos na soma (coadd) e barras de erro do espectro |
| `ZODI` | Modelo da luz zodiacal | Subtraído da imagem |
| `PSF` | PSFs efetivas (grade 21×21) | Futuro: fotometria por ajuste de PSF |
| `WCS-WAVE` | Tabela pixel → comprimento de onda | Espectro sob demanda |

Flags relevantes: `TRANSIENT` (bit 0), `HOT` (10), `COLD` (11), `NONLINEAR` (15), `OUTLIER` (19), `SOURCE` (21), `GHOST*` (22–24), `BLOOM`/`SNOWBALL`/`HALO` (26–28).

### 4.3 Como acessar (já testado)

**Consulta (TAP/ADQL)**: lista todas as imagens que cobrem uma posição:

```sql
SELECT p.energy_bandpassname, p.time_bounds_lower, a.uri
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', <ra_deg>, <dec_deg>), p.poly)
```

Endpoint: `https://irsa.ipac.caltech.edu/TAP/sync` (parâmetros `QUERY`, `LANG=ADQL`, `FORMAT=csv`).

**Recorte (cutout)**: em vez de baixar 2040×2040, pede só o pedaço de interesse:

```
https://irsa.ipac.caltech.edu/<uri>?center=<ra>,<dec>d&size=<graus>
```

**Resultados do teste em WISE 0855 (14/11/2026):**

- **258 imagens** entre MJD 60800 (mai/2025) e 61174 (mai/2026), ou seja, cerca de 2 mapeamentos completos, em todos os detectores.
- Um recorte de 0,1° pesa **~4 MB** e levou **~6 s** (o arquivo vem com todas as extensões, incluindo PSF).
- **Consequência:** baixar e processar no navegador é inviável. Precisamos de um **backend com download paralelo e cache**.

Também há acesso via SIA (`Irsa.query_sia(..., collection=['spherex_dr1','spherex_qr3'])`) e cópia na AWS S3. Ver os [tutoriais do IRSA](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/).

## 5. Solução proposta

### 5.1 Fluxo do usuário

1. Abre o site e digita RA/Dec (sexagesimal ou graus), um nome de objeto, ou clica num alvo pronto.
2. Escolhe o campo de visão (ex.: 3′, 6′, 12′) e o detector / modo de cor.
3. Vê a **animação** das épocas, com play/pause, velocidade e barra de tempo com datas.
4. Alterna para **blink** (duas épocas) ou **diferença** (época B − época A).
5. Clica num objeto e vê seu **espectro** e os flags daquele pixel.
6. Liga overlays do **Gaia/WISE** para ver se o objeto já é conhecido e onde ele "deveria" estar.
7. Copia o **link** da visualização para compartilhar.

### 5.2 Arquitetura

```
┌──────────────────────────┐        ┌─────────────────────────────┐        ┌──────────────┐
│ Frontend (navegador)     │  HTTP  │ Backend Python (FastAPI)    │  HTTP  │ IRSA / NASA  │
│ - player de épocas       │ ─────▶ │ - consulta TAP              │ ─────▶ │ TAP + cutout │
│ - blink / diferença      │        │ - download paralelo + cache │        └──────────────┘
│ - gráfico de espectro    │ ◀───── │ - coadd por época/detector  │
│ - Aladin Lite (Gaia/WISE)│  PNG/  │ - reprojeção, PNG, espectro │
│ - estado na URL          │  JSON  │ - cache em disco            │
└──────────────────────────┘        └─────────────────────────────┘
```

**Backend (Python + FastAPI + Astropy):**

- Consulta o IRSA e **agrupa** as imagens em *épocas* (visitas próximas no tempo) por detector.
- Baixa os recortes **em paralelo** e guarda em **cache** (mesma região não é baixada duas vezes).
- Para cada época e detector: subtrai a luz zodiacal, mascara pixels com flags ruins, **reprojeta** para uma grade comum (centrada na coordenada pedida) e faz a **soma ponderada** pela variância.
- Gera PNGs com esticamento (*stretch*) consistente entre épocas, para que a animação não "pisque" por diferença de contraste.
- Calcula imagens de diferença e espectros.
- Coleções de dados (`spherex_dr1`, `spherex_qr3`, ...) definidas em configuração, então um novo release é só configuração.

**Frontend:**

- Player de épocas (canvas), blink, diferença, seletor de detector e de campo de visão.
- Gráfico de espectro (fluxo × comprimento de onda, com erro).
- Aladin Lite v3 (CDS) para contexto e overlays de catálogos (Gaia DR3, AllWISE/CatWISE).
- Estado completo na URL: `?ra=133.795&dec=-7.245&fov=6&det=6&mode=blink`.
- Página "embed" mínima para uso em iframe.

### 5.3 Endpoints previstos (rascunho)

| Endpoint | Função |
|---|---|
| `GET /api/epochs?ra&dec&fov` | Lista épocas disponíveis (datas, detectores, nº de exposições) |
| `GET /api/image?ra&dec&fov&epoch&det&stretch` | PNG da soma de uma época/detector |
| `GET /api/diff?ra&dec&fov&a&b&det` | PNG da diferença entre duas épocas |
| `GET /api/spectrum?ra&dec&epoch` | Espectro (λ, fluxo, erro, flags) no ponto |
| `GET /api/flags?ra&dec&fov&epoch&det` | Máscara de flags para overlay |
| `GET /api/resolve?name` | Nome do objeto → coordenadas (via CDS Sesame) |

Detalhes finais vão para `docs/04-api.md`.

## 6. Escopo e prioridades

O hackathon dura ~48 h. Priorizamos entregar o obrigatório funcionando com dados reais e só depois os diferenciais.

**MVP (obrigatório):**

- [ ] Entrada de RA/Dec + alvos de teste prontos
- [ ] Backend: consulta TAP + download paralelo de cutouts + cache
- [ ] Coadd por época de um detector (começar por D6 em 4,4–5 µm, ótimo para anãs marrons)
- [ ] Player de animação das épocas
- [ ] Validação nos 5 alvos de teste

**Diferenciais (em ordem):**

- [ ] Coordenadas na URL + link de compartilhamento
- [ ] Blink e diferença entre épocas
- [ ] Seletor de detector e de campo de visão
- [ ] Espectro sob demanda
- [ ] Overlay de flags de contaminação
- [ ] Aladin Lite com Gaia/WISE + marcador de posição prevista por movimento próprio
- [ ] Composição em falsa cor (ex.: D1/D3/D6)
- [ ] Modo embed (iframe)

**Fora do escopo:** detecção automática de objetos em movimento por IA, contas de usuário, processamento do céu inteiro.

## 7. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Cutouts lentos (~6 s, ~4 MB cada; centenas por alvo) | Download paralelo, cache em disco, carregar épocas progressivamente, pré-carregar os 5 alvos de teste antes da demo |
| IRSA fora do ar durante a demo | Cache dos alvos de teste guardado localmente; modo offline com esses dados |
| Alinhamento entre épocas imperfeito (distorção SIP) | Reprojetar com WCS completo (Astropy / `reproject`) para grade comum |
| Contraste diferente entre quadros "pisca" na animação | Esticamento (stretch) calculado uma vez para todas as épocas |
| Objetos de alto movimento próprio fora do centro | Propagar a posição pela época usando o movimento próprio do Gaia |
| Pixel do SPHEREx grande (~6″) | Escolher bem os alvos de demo; explicar a limitação; destacar o diferencial espectral |

## 8. Referências

- Desafio: <https://www.spaceappschallenge.org/2026/challenges/>
- SPHEREx no IRSA: <https://irsa.ipac.caltech.edu/Missions/spherex.html>
- Documentação do arquivo SPHEREx: <https://caltech-ipac.github.io/spherex-archive-documentation>
- Tutoriais IRSA: [introdução](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/), [cutouts](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/), [mosaicos](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic/), [HiPS](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/)
- Missão SPHEREx (JPL): <https://www.jpl.nasa.gov/missions/spherex/>
- Aladin Lite (CDS): <https://aladin.cds.unistra.fr/AladinLite/>
- Astropy: <https://www.astropy.org/>
- Backyard Worlds: <https://backyardworlds.org>
