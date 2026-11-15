# Relatório de progresso — fases 0 a 6

> Situação em **14/11/2026**, primeiro dia do NASA Space Apps Challenge 2026.
> Site publicado: <https://enriquessribeiro.github.io/spherex-viewer/>
> Desafio: **Planet X and SPHEREx**. Repositório: `enriquessribeiro/spherex-viewer`.

Este relatório consolida o que foi construído até agora, como foi construído e por quê. Os detalhes de cada assunto estão nos documentos de referência ([índice](README.md)); aqui o foco é a história completa e as decisões.

## 1. Resumo executivo

- **O núcleo científico está pronto e validado com dados reais.** O pipeline busca as imagens do SPHEREx no arquivo da NASA (IRSA), alinha todas as exposições numa grade comum, agrupa em épocas e soma, produzindo os quadros que o site vai animar.
- **Os 5 alvos do desafio passam numa validação científica automática** (16 testes) comparando o que o pipeline produz com valores independentes da literatura (SIMBAD, Gaia):

| Alvo | O que a ferramenta mostra |
|---|---|
| WISE 0855 | Anã marrom a 285 K: só aparece em 4–5 µm; move-se ~8″/ano; posição prevista × medida com erro de 0,12–0,19 px |
| Barnard's Star | Move-se **~11″ para o norte em um ano**, medido com erro de ~0,02 px, apesar de saturar o detector |
| Epsilon Indi B | Detectado com folga (S/R 250–640); movimento confere |
| RW Aurigae | Brilho sobe 1,35× entre épocas (12σ) |
| R Draconis | Brilho cai para 0,46× entre épocas (15σ) |
| Estrelas de campo | Ficam paradas entre épocas com variação de 0,02–0,04 px (alinhamento ~25× melhor que um pixel) |

- **O backend está completo para o MVP.** Os dados de cada campo são gravados num formato formal (JSON Schema), os 5 alvos são gerados como dados estáticos (5 MB no total) e há uma API que processa qualquer coordenada sob demanda.
- **O site está no ar** em <https://enriquessribeiro.github.io/spherex-viewer/>, com os 5 alvos do desafio: Animar, Piscar e Diferença, detectores D1–D6, régua do tempo, link compartilhável. A API está no Render.
- **A publicação está completa.** O IRSA ficou fora do ar durante a primeira publicação (o site foi ao ar com um *snapshot* validado localmente); quando voltou, o workflow *Atualizar dados e publicar* passou a rodar com sucesso a cada merge, com a validação científica como portão.
- **Fase 6 (extras) entregue**: espectro de 0,75 a 5 µm dos alvos, medido exposição por exposição; mapa do céu inteiro com catálogos Gaia DR3 e AllWISE; falsa cor; soma de épocas; flags de contaminação na placa; campo de 6′ ou 10′, os dois publicados e abrindo na hora; coordenadas do desafio em sexagesimal e de outra época abrindo o alvo certo.
- **Uma revisão de código independente foi feita** depois da fase 6 começar; os achados válidos foram corrigidos (PRs #16 e #17) e um achado foi refutado com observação no navegador.
- Números: 22 PRs mergeados, 93 commits, 179 testes (88 rápidos do backend + 16 científicos + 8 de serviços reais + 67 do frontend), 11 documentos e 4 diagramas.

## 2. Linha do tempo

| Etapa | O que aconteceu | Resultado |
|---|---|---|
| Pesquisa | Leitura do desafio oficial; teste de acesso aos dados do IRSA (TAP + recortes) | Dados do DR1 públicos e acessíveis; recorte lento (~4 MB, ~6 s) |
| Documentação inicial | 01 (projeto), 02 (dados), 03 (arquitetura), 04 (API), 05 (hospedagem), 06 (testes), 07 (plano) | **PR #1** (docs + plano) |
| Fase 0 + Fase 1 | Estrutura do backend, CI e pipeline com dados sintéticos, em 9 fatias de TDD | **PR #2**: 16 testes |
| Fase 2 | Adaptador do IRSA, cache, paralelismo, alvos, Marco 1 e validação científica | **PR #3**: 42 + 16 testes |
| Relatório | Este documento (versão das fases 0 a 2) | **PR #4** |
| Fase 3 | Contrato de dados (JSON Schema), gravação dos campos, dados estáticos dos alvos e API | **PR #5**: 67 + 16 + 8 testes |
| Fase 4 | Núcleo do site com TDD, interface "Placas do comparador", revisão de design em duas rodadas, `PRODUCT.md` e `DESIGN.md` | **PR #7**: + 32 testes do frontend; **Marco 2** |
| Diagramas e README | Fluxo do sistema em diagramas de raia; README na raiz do repositório | **PRs #8, #9, #10** |
| Fase 5 | Workflow de publicação, blueprint do Render, limite de campo configurável | **PR #11** |
| Queda do IRSA | Primeira publicação falhou (TAP com 502). Fallback de consulta para o SIA e publicação de snapshot | **PRs #12, #13**; site no ar |
| Relatório | Este documento (versão até a fase 5) | **PR #14** |
| Fase 6 — mapa | Mapa do céu inteiro com Aladin Lite e o HiPS do SPHEREx | **PR #15** |
| Revisão de código | Correções da revisão independente: zoom fixo no céu, corrida ao trocar de campo, busca por nome com movimento próprio, limite de tempo dos trabalhos, erros do IRSA | **PRs #16, #17** |
| Fase 6 — desafio | Coordenada do desafio (sexagesimal, outra época) abre o WISE 0855 | **PR #18** |
| Fase 6 — visualização | Somar épocas, falsa cor, flags na placa, escolha do campo | **PR #19** |
| Fase 6 — catálogos | Gaia DR3 e AllWISE no mapa | **PR #20** |
| Fase 6 — contraste | Contraste inicial ajustado no alvo, para o WISE 0855 aparecer | **PR #21** |
| Fase 6 — espectro | Espectro dos alvos, medido em cada exposição | **PR #22**; IRSA de volta, publicação automática com sucesso |
| API ocupada | `429` vira espera com aviso, não erro; busca nova volta ao campo padrão | **PR #23** |

## 3. O que foi construído

### 3.1 Estrutura do repositório

```
spherex-viewer/
├── docs/                    ← documentação (este relatório incluso)
│   └── img/                 ← imagens dos resultados (Marco 1)
├── targets.yaml             ← os 5 alvos do desafio (SIMBAD) e o detector padrão de cada um
├── schemas/                 ← contrato de dados: field.schema.json, manifest.schema.json
├── .github/workflows/
│   └── test.yml             ← CI: testes rápidos em todo PR
└── backend/                 ← Python 3.12, gerenciado com uv
    ├── pipeline/
    │   ├── archive.py       ← interface do arquivo de dados (Exposure, Archive, ArchiveUnavailable)
    │   ├── irsa.py          ← adaptador do IRSA (TAP + recortes + novas tentativas)
    │   ├── cache.py         ← cache em disco de consultas e recortes
    │   ├── field.py         ← o pipeline: build_field (épocas, alinhamento, soma)
    │   ├── targets.py       ← alvos e propagação por movimento próprio
    │   ├── output.py        ← write_field: field.json + quadros binários + PNG + espectro
│   ├── spectrum.py      ← espectro: fotometria por exposição e estrelas vizinhas
    │   └── build_static.py  ← dados estáticos dos alvos (manifest.json + campos)
    ├── api/
    │   ├── app.py           ← create_app: rotas, erros, CORS
    │   ├── jobs.py          ← processamento assíncrono de campos, com progresso
    │   ├── coords.py        ← coordenadas digitadas (graus ou sexagesimal)
    │   ├── simbad.py        ← nomes de objetos → posição e movimento próprio
    │   └── main.py          ← instância de produção (IRSA real + cache)
    └── tests/
        ├── synthetic.py     ← céu sintético no formato do SPHEREx
        ├── test_pipeline.py, test_irsa_archive.py, test_cache.py, test_targets.py
        ├── test_output.py, test_build_static.py, test_api.py, test_simbad_live.py
        ├── fixtures/irsa/   ← respostas reais gravadas do IRSA (WISE 0855)
        └── science/         ← validação científica com dados reais

frontend/                    ← o site (Vite + TypeScript, sem framework)
├── src/core/                ← lógica pura e testada: quadros, contraste, diferença em σ,
│                               renderização, WCS, épocas, estado na URL, fonte dos dados
├── src/main.ts, data.ts     ← controlador da tela e carregamento (estático ou API)
├── src/ui/marks.ts          ← marcas de lápis (círculo e seta)
├── src/ui/skymap.ts         ← mapa do céu inteiro (Aladin Lite) e catálogos Gaia/AllWISE
├── src/ui/spectrum.ts       ← gráfico do espectro (SVG) e tabela
└── tests/                   ← Vitest; fixture de contrato gravada pelo backend

.github/workflows/
├── test.yml                 ← testes do backend e do frontend em todo PR
├── update-data.yml          ← alvos → validação científica → GitHub Pages (a cada 3 dias)
└── publish-snapshot.yml     ← publica os dados do branch data-snapshot (manual)
render.yaml                  ← blueprint da API no Render
PRODUCT.md, DESIGN.md        ← registro do produto e do sistema visual
```

### 3.2 O pipeline, passo a passo

`build_field(ra, dec, fov_arcmin, archive)` é a peça central:

```
consulta ao arquivo ──▶ agrupamento em épocas ──▶ download paralelo dos recortes
        │                                                  │
        ▼                                                  ▼
   NoCoverage se vazio                para cada exposição: subtrai luz zodiacal,
                                      classifica pixels por flags, reprojeta
                                      para a grade do campo (interpolação normalizada)
                                                           │
                                                           ▼
                                      por época e detector: soma ponderada por
                                      1/variância, remove fundo residual, marca
                                      pixels saturados e de baixa qualidade
                                                           │
                                                           ▼
                                      Field: épocas × detectores × quadros,
                                      limites de contraste comuns, exposições que falharam
```

Saída (`Field`):

| Campo | Conteúdo |
|---|---|
| `epochs[i].frames[det]` | `Frame` com `data`, `variance`, `n_exposures`, `background`, `low_quality`, `saturated` |
| `display[det]` | Limites de contraste comuns a todas as épocas do detector |
| `failed_exposures` | Exposições que o IRSA não entregou (puladas) |
| `wcs`, `n` | Grade do campo (TAN, norte para cima, 6,15″/pixel) |

### 3.3 Adaptador do IRSA e cache

- `IrsaArchive.query(ra, dec)`: consulta TAP/ADQL nas coleções `spherex_dr1` e `spherex_qr3`.
- `IrsaArchive.fetch_cutout(...)`: recorte via serviço de cutouts; descarta a extensão EPSF (~4 MB).
- Novas tentativas com espera exponencial (2, 4, 8, 16, 32 s) em `429/5xx`; depois `ArchiveUnavailable`.
- `CachedArchive`: recortes guardados para sempre, consultas por 24 h, escrita atômica.

### 3.4 Alvos

`targets.yaml` tem os 5 alvos com posição e movimento próprio do SIMBAD (época J2000). O centro de cada campo é a posição **propagada até nov/2025** (meio do primeiro ano de dados), para objetos rápidos ficarem perto do centro em todas as épocas.

### 3.5 Contrato de dados e dados estáticos (fase 3)

`write_field(field, raiz, target)` grava cada campo em `fields/<field_id>/<data_version>/`:

| Arquivo | Conteúdo |
|---|---|
| `field.json` | Manifesto do campo: grade, épocas, quadros por detector, limites de contraste, exposições, alvo e posições previstas |
| `frames/<época>/<det>.f32` | Quadro em float32 little-endian, N × N, **norte na primeira linha** |
| `.var.f32` | Variância |
| `.mask.u8` | Bit 0 = saturado (pintar com o brilho máximo); bit 1 = baixa qualidade |
| `.png` | Quadro renderizado (esticamento asinh, núcleo saturado em branco) |

- `field_id` = coordenadas arredondadas em 0,0001° + campo (ex.: `133.7600-7.2422_6`); `data_version` = hash das exposições usadas + versão do pipeline. URLs com `data_version` podem ser cacheadas para sempre.
- **JSON Schema** (`schemas/`) é a fonte da verdade do formato; os testes validam toda saída contra ele, e o frontend vai validar contra o mesmo.
- `build_static` gera `manifest.json` + os campos dos alvos. Com dados reais: 5 alvos em ~2,5 min (cache cheio), **5 MB** no total.

### 3.6 API (fase 3)

| Rota | Comportamento |
|---|---|
| `GET /api/v1/field?ra&dec&fov` | Primeiro pedido dispara o processamento: `202` com progresso (recortes baixados / total) até ficar pronto, então `200` com o `field.json`. Pedidos do mesmo campo compartilham o trabalho |
| `GET /api/v1/fields/...` | Arquivos do campo, com cache imutável e proteção contra *path traversal* |
| `GET /api/v1/resolve?name` | Coordenadas (graus ou sexagesimal) sem rede; nomes via SIMBAD |
| `GET /api/v1/health`, `/config` | Estado e limites |

Erros padronizados: `400` (parâmetros), `404 NO_COVERAGE`, `429 BUSY` (+ `Retry-After`), `502 UPSTREAM_ERROR` (o próximo pedido tenta de novo). CORS liberado para embed. Medido localmente: WISE 0855 pronto em ~22 s com o cache cheio.

### 3.7 O site (fase 4)

- **`viewer-core`** (TypeScript puro, 32 testes): decodifica os quadros float32 e a máscara; contraste linear/asinh/log/raiz; **diferença em unidades de ruído**, (b − a)/√(var_a + var_b); renderização nas cores da placa; projeção TAN para posicionar as marcas; par de épocas padrão pelo maior sinal; estado ⇄ URL; escolha entre dados estáticos e API. Um teste de contrato valida, com o mesmo JSON Schema, arquivos gravados pelo backend.
- **Interface**: placa em negativo com mira fixa e círculo/seta de lápis na posição prevista; Animar, Piscar e Diferença; detectores com a faixa em µm desenhada em escala; régua do tempo nas datas reais com o nº de exposições; contraste, negativo/positivo, zoom 1×/2×/4×; busca por nome ou RA/Dec; copiar link; `embed=1`.
- **Direção visual "Placas do comparador"**, escolhida numa página de decisão entre alternativas: as épocas como as placas de vidro com que Tombaugh achou Plutão. Vermelho reservado às marcas de descoberta. Registrada em `PRODUCT.md`, `DESIGN.md` e `.impeccable/surfaces/`.
- **Revisão de design independente em duas rodadas**. Pontos em aberto, por troca consciente: a placa ocupa ~55% da área de conteúdo a 1440×900 (o contrato pedia ~60%; maior empurraria a régua para baixo da dobra).

### 3.8 Publicação (fase 5)

| Peça | Estado |
|---|---|
| GitHub Pages (origem: GitHub Actions) | ✅ no ar |
| `publish-snapshot.yml` | ✅ publicou o site enquanto o IRSA estava fora; fica como reserva |
| `update-data.yml` (pipeline → validação científica → Pages) | ✅ falhou duas vezes com o IRSA fora do ar; desde que ele voltou, roda com sucesso a cada merge na `main` (~4–5 min com cache) e publica o espectro |
| API no Render (`render.yaml`, um campo por vez de até 10′) | ✅ processa campos sob demanda; com a fila cheia responde `429` e o site espera |
| Variável `API_BASE` no repositório | ✅ embutida no site publicado |

### 3.9 Extras (fase 6)

| Extra | Como funciona |
|---|---|
| **Espectro dos alvos** | Cada exposição do SPHEREx vê o alvo num comprimento de onda diferente (filtro de variação linear). O pipeline mede o fluxo numa abertura de 2 px (12″) com fundo num anel de 5–8 px, em µJy, e lê o comprimento de onda da tabela `WCS-WAVE`. O site desenha os pontos de 0,75 a 5 µm com a mediana por faixa e avisa quando uma estrela vizinha (S/R > 5) cai na abertura. WISE 0855: 241 de 258 exposições medidas, vizinha a ~8″ em D1, D2 e D4 |
| **Mapa do céu inteiro** | Aladin Lite com o HiPS do SPHEREx DR1, troca de detector, alvos marcados; clique abre o ponto na placa |
| **Catálogos** | Gaia DR3 e AllWISE pelo VizieR (espelho de Harvard primeiro), até 2.000 fontes num campo de até 1°, recarregados ao mover o mapa |
| **Falsa cor** | D6, D3 e D1 nos canais vermelho, verde e azul (`color=1`) |
| **Somar épocas** | Soma por 1/variância de todas as épocas: mais profundidade, sem movimento |
| **Flags na placa** | Opcional: pinta em tom de papel os pixels saturados ou de baixa qualidade (flags suspeitas usadas por falta de alternativa limpa) e conta quantos são |
| **Campo variável** | 6′ ou 10′, os dois publicados para os alvos (troca instantânea). O 3′ saiu por repetir o zoom 2×; coordenadas fora da lista vão pela API |
| **Coordenadas do desafio** | RA/Dec em graus ou sexagesimal; uma coordenada de outra época que cai a menos de 1′ do caminho de um alvo abre o alvo (a do WISE 0855 no texto do desafio abre o WISE 0855) |
| **Contraste no alvo** | O contraste inicial é ajustado no pico do alvo, não no pixel mais brilhante do campo |

As posições previstas foram conferidas contra o Gaia DR3 (≤ 0,13″) e, para o WISE 0855, que não está no Gaia, contra o AllWISE (1,3″ da posição de 2010, coerente com o movimento próprio).

## 4. Processo de trabalho

### 4.1 Documentação primeiro

Antes de qualquer código, o projeto foi especificado em documentos: objetivo, dados, arquitetura, contrato da API, hospedagem e estratégia de testes. Durante o desenvolvimento, **toda decisão que mudou algo foi registrada no documento correspondente no mesmo PR**.

### 4.2 Fluxo de git

- Um branch por fase (`fase-1/pipeline`, `fase-2/dados-reais`), um PR por fase, `main` só recebe por PR.
- Commits pequenos, um por fatia de TDD, no formato `tipo: descrição`, em português.
- CI (`test.yml`) roda os testes rápidos em todo PR.

### 4.3 TDD com fatias verticais

Cada funcionalidade nasceu de um teste: **teste falhando → código mínimo → teste passando → commit**. Regras que seguimos:

- **Testar pelas interfaces públicas** (`build_field`, `IrsaArchive`, `CachedArchive`, `Target`), nunca por detalhes internos.
- **Valores esperados vindos de fontes independentes**: o que plantamos no céu sintético, literais da especificação (ex.: média ponderada = 2,5) ou catálogos (SIMBAD, Gaia). Nunca recalculando do jeito que o código calcula.
- **Teste que nasce verde é verificado por sabotagem**: quebramos o código de propósito (sem alinhamento, épocas misturadas, `<=` trocado por `<`) e confirmamos que o teste falha.
- **Teste frágil é corrigido, não afrouxado**: ex.: o pico de uma estrela depende de onde a grade cai; passamos a medir o fluxo total, que se conserva.

### 4.4 Sete fronteiras de teste

Definidas antes do código ([06-testes.md](06-testes.md)); até agora implementadas:

| Fronteira | Situação |
|---|---|
| 1. Pipeline com céu sintético (+ recortes reais gravados), incluindo o espectro | ✅ 42 testes |
| 2. Adaptador do IRSA (respostas gravadas, fallback para o SIA) + cache | ✅ 15 testes |
| Alvos (propagação × Gaia DR3, `targets.yaml`) | ✅ 2 testes |
| 3. API HTTP | ✅ 18 testes (+ 8 `live` do SIMBAD) |
| 4. Contrato de dados (JSON Schema) | ✅ 11 testes (gravação + dados estáticos) |
| 5. Núcleo do frontend | ✅ 67 testes (Vitest) |
| 6. Validação científica (dados reais) | ✅ 16 testes |
| 7. Ponta a ponta no navegador | Não automatizado. O site local e o publicado foram abertos num navegador sem interface para capturas e checagem de erros |

## 5. Decisões técnicas

### 5.1 Arquitetura e infraestrutura

| Decisão | Alternativas consideradas | Motivo |
|---|---|---|
| Backend em **Python** (Astropy, reproject, numpy) | — | Ecossistema astronômico; leitura de FITS, WCS e reprojeção prontos |
| **Sem banco de dados**; cache em arquivos | Banco para imagens | Imagens são arquivos; o índice é o próprio IRSA |
| **GitHub Pages** para o site + alvos pré-processados | Vercel | Publicação nativa pelo Actions, sem token; grátis em repo público |
| **Render (free)** para o backend ao vivo | Hugging Face, Fly.io, Railway, Vercel Functions | Único gratuito viável para Python + Astropy (HF restringiu o grátis; Fly/Railway sem plano grátis) |
| **GitHub Actions a cada 3 dias** para atualizar os alvos | Semanal | O cache do Actions expira em 7 dias sem uso |
| Validação científica **bloqueia a publicação** | Só avisar | Site nunca publica dados que falham na ciência; a última versão boa continua no ar |
| Backend entrega **matrizes float32**; contraste, blink, diferença e soma no navegador | Só PNG | Interatividade sem novas requisições; quadros são pequenos (~14 KB) |

### 5.2 Pipeline (várias forçadas pelos dados reais)

| Decisão | Por quê | Como descobrimos |
|---|---|---|
| Pipeline recebe um **adaptador de arquivo** injetável | Testar a ciência com céu sintético; trocar IRSA por cache sem mudar o pipeline | Desenho inicial |
| Recorte de **1,5 × o campo** | Com o detector girado, o recorte precisa cobrir a diagonal (√2) | Teste de alinhamento com rotação |
| **Subtrair `ZODI`** antes de alinhar | `IMAGE` inclui a luz zodiacal | Documentação do produto |
| **Interpolação normalizada** | A bilinear espalhava cada pixel mascarado para ~4 vizinhos | Recorte real: só 91,6% do quadro válido |
| Lista de bits de flags **refeita a partir do cabeçalho real** | A documentação não listava OVERFLOW, SUR_ERROR, NONFUNC, MISSING_DATA | Inspeção de recorte real |
| Flags em **dois níveis** (graves sempre excluídos; suspeitos só se houver alternativa limpa) | Na Barnard's Star, todas as exposições marcam o anel da estrela como suspeito, mas os valores são bons | Barnard's Star aparecia como buraco 3×3, com erro de posição de 1–3 px |
| Valor "limpo" só onde **nenhum** pixel suspeito entra na interpolação | Senão a borda usaria só a asa da estrela e subestimaria o brilho | Teste sintético (fluxo 572 × 628 esperado) |
| Núcleo sem dado marcado como **`saturated`** | O SPHEREx não entrega o núcleo de estrelas muito brilhantes (`NaN` + OVERFLOW) | Barnard's Star |
| Soma ponderada por **1/variância**, com variância propagada | Exposições ruidosas pesam menos; variância alimenta S/R e espectro | Desenho inicial |
| **Fundo residual** removido de cada quadro (mediana com corte sigma) | Desnível de fundo entre épocas dominava a diferença | Marco 1 (diferença em D1 toda azul) |
| Contraste com `vmax` = **máximo**, comum a todas as épocas | Variáveis brilhantes não podem saturar, senão a variação some | Requisito dos alvos variáveis |
| Épocas = grupos com intervalo > **10 dias**, detectados pelos dados | A cobertura real é irregular (WISE 0855: 4 grupos em 1 ano) | Consulta real |
| **4 downloads simultâneos**, 6 tentativas | O IRSA respondeu `503` com só 2 pedidos simultâneos | Gravação das fixtures |
| Exposição indisponível é **pulada e registrada** | Um único `503` persistente derrubou um campo de 258 exposições | Primeira execução do Marco 1 |
| Centro dos alvos = posição **propagada** | O WISE 0855 está ~3,4′ a oeste da coordenada de 2010 do desafio | Comparação com SIMBAD |

### 5.3 Contrato, dados estáticos e API (fase 3)

| Decisão | Por quê |
|---|---|
| **JSON Schema** como fonte da verdade do formato | Backend, dados estáticos e frontend não podem divergir sem quebrar um teste |
| Quadros com o **norte na primeira linha** | Convenção de imagem (topo = norte); a grade interna do pipeline usa a convenção FITS (linha 0 = sul) e a conversão acontece só na gravação |
| **`mask.u8`** (saturado, baixa qualidade) no lugar de `flags.u32` | É o que o frontend precisa agora; o overlay de fantasmas/persistência fica para a fase 6 |
| `field_id` com arredondamento padrão de ponto flutuante | Igual ao `toFixed` do JavaScript: frontend e backend concordam (−7,24515 → −7,2451) |
| `data_version` = hash das exposições + versão do pipeline | Dado novo ou processamento novo → URL nova; o resto pode ficar em cache para sempre |
| `default_detector` por alvo (D6 para anãs frias) | Lição do Marco 1: o WISE 0855 só aparece em D5–D6 |
| Miniatura na época mais recente com **≥ 3 exposições** | Épocas de 1 exposição (Barnard's Star, set/2026) são ruidosas demais para a vitrine |
| API **assíncrona com progresso** (202 → 200) | Um campo novo leva minutos (IRSA); o servidor grátis não pode prender a conexão |
| Erros transitórios **esquecidos após reportados** | O próximo pedido tenta de novo em vez de ficar preso no erro |
| Arquivo e resolvedor **injetáveis** em `create_app` | API testada sem rede, com o céu sintético |
| SIMBAD pelo **espelho de Harvard** primeiro | O servidor principal do CDS esteve fora do ar |

### 5.4 Site e publicação (fases 4 e 5)

| Decisão | Por quê |
|---|---|
| **Vite + TypeScript sem framework** | Site pequeno e estático; Vitest integrado para o TDD do núcleo |
| Lógica em `core/` separada da interface | O que é testável (matemática, coordenadas, URL) fica sem DOM |
| **Diferença em unidades de ruído** (abaixo de 2σ some, a partir de 5σ cor cheia) | Escalada pelo brilho máximo saía em branco; por percentil virava "confete". Usa a variância das duas épocas |
| Miniaturas desenhadas no navegador, com contraste pelos percentis do próprio quadro | Os PNGs invertidos por CSS viravam quadrados brancos; fração fixa do intervalo estourava em D6 |
| Régua do tempo proporcional às datas, com rótulos que colidem escondidos | As épocas são irregulares; mostrar isso é parte da honestidade do dado |
| **Publicação bloqueada pela validação científica** | O site nunca publica dados que falham na ciência |
| `actions/cache` dividido em restaurar e salvar (`if: always()`) | Os downloads do IRSA não se perdem se um passo seguinte falhar |
| Workflow só dispara em push que mexe em código | Mudanças de documentação não republicam |
| **`SPHEREX_FOV_MAX`** (10′ no Render) | O pipeline guarda as exposições na memória: ~75 MB em 6′, mais de 1 GB em 30′; o Render grátis tem 512 MB |
| **Fallback de consulta TAP → SIA** | O TAP caiu sozinho; o SIA devolve as mesmas exposições |
| **Snapshot em branch separado** (`data-snapshot`) + workflow manual | Publicar com o IRSA fora do ar sem commitar dados gerados na `main` |

### 5.5 Validação científica

| Decisão | Por quê |
|---|---|
| Medidas por **ajuste gaussiano usando só pixels válidos** | O centroide simples tratava o núcleo saturado como zero e criava uma tendência falsa de 0,3 px/ano na Barnard's Star |
| Tolerâncias **calibradas com dados reais e justificadas** | Posição < 0,5 px; deslocamento < 0,25 px; estrelas paradas < 0,3 px (observado bem abaixo) |
| Astrometria só em épocas com **S/R ≥ 5** | Épocas com poucas exposições (WISE 0855 época 1, S/R 3) são marginais |
| Variáveis por **fotometria relativa** às estrelas de campo, com dispersão **robusta (MAD)** | Cancela diferenças de calibração entre épocas; uma estrela de campo variável não infla o critério |
| Estrelas de campo a **> 12 px** do alvo, com ajuste válido em todas as épocas | O halo do R Draconis estava sendo usado como "estrela de campo" |
| Controles negativos: **alvo é o objeto mais variável do campo**; **≤ 20%** das estrelas de campo parecem variáveis | Algumas estrelas de campo variam de verdade (4/36); o limite foi definido após a observação e está registrado como tal |

## 6. Problemas encontrados e como foram resolvidos

| # | Problema | Causa | Solução | Fase |
|---|---|---|---|---|
| 1 | Teste do pico de estrela falhava (77,9 × 100) | Recorte com nº par de pixels: centro entre 4 pixels | Medir fluxo total, não pico | 1 |
| 2 | `503 Server busy` do IRSA | Servidor ocupado | Novas tentativas com espera exponencial; paralelismo limitado | 2 |
| 3 | Bits de flag inesperados | Documentação incompleta | Lista refeita do cabeçalho real | 2 |
| 4 | Só 91,6% do quadro real válido | NaN espalhado pela interpolação | Interpolação normalizada | 2 |
| 5 | Campo inteiro falhou após 115 downloads | Um `503` persistente | Pular e registrar a exposição | 2 |
| 6 | Diferença entre épocas dominada pelo fundo | Resíduo da luz zodiacal | Remoção do fundo residual | 2 |
| 7 | Barnard's Star como buraco 3×3 | Anel suspeito + núcleo sem dado | Flags em dois níveis + `saturated` | 2 |
| 8 | Tendência falsa no movimento da Barnard | Centroide simples com núcleo NaN | Ajuste gaussiano (no teste) | 2 |
| 9 | Variáveis reprovadas | Halo do R Dra usado como comparação; desvio padrão inflado | Raio de exclusão + MAD (no teste) | 2 |
| 10 | Controle negativo reprovado | Estrelas de campo que variam de verdade | Controle reformulado | 2 |
| 11 | Separação ε Indi A–B escrita como 1,5′ | Erro de memória | Calculado: 6,7′; campo de 6′ centrado no B | 2 |
| 12 | `field_id` do exemplo do contrato não batia (−7,2452 × −7,2451) | −7,24515 não é exato em binário | Exemplo corrigido; arredondamento padrão, igual ao do JavaScript | 3 |
| 13 | Commit feito com um teste falhando | A cadeia de comandos usava `grep`, que devolve sucesso | Corrigido antes do push; commit só depois de `pytest` passar | 3 |
| 14 | Miniatura da Barnard's Star usava uma época de 1 exposição | Regra "última época" | Época mais recente com ≥ 3 exposições | 3 |
| 15 | Vermelho nos sliders, foco e detector, contra o próprio contrato de design | Cor de destaque aplicada por padrão | Vermelho só nas marcas de descoberta (apontado pelo revisor) | 4 |
| 16 | Diferença em branco, depois "confete" de ruído | Escala pelo brilho máximo, depois por percentil | Diferença em unidades de ruído | 4 |
| 17 | Régua do tempo abaixo da dobra a 1440×900 | Placa grande demais | Etiqueta compacta, zoom no canto da placa | 4 |
| 18 | `fov=nan` respondia 500 | Comparações com NaN passam direto | 400 `INVALID_PARAM` para números não finitos | 5 |
| 19 | `API_BASE` criado como *Secret* | O workflow lê uma *Variable* | Recriado como variável (a URL é pública de qualquer forma) | 5 |
| 20 | Primeira publicação falhou na primeira consulta | TAP do IRSA com 502 (sync, async e availability) | Fallback para o SIA + publicação de snapshot | 5 |
| 21 | Segunda execução falhou mesmo com o fallback | O SIA também passou a responder 502 | Sem solução do nosso lado; site segue no snapshot | 5 |
| 22 | Revisão de código adiada | Limite de uso de 5 horas atingido no início | Feita no começo da fase 6; achados válidos corrigidos | 6 |
| 23 | "Failed to fetch" no console do mapa | Telemetria do Aladin Lite | `log: false` | 6 |
| 24 | VizieR principal fora do ar; Gaia lento | Instabilidade do CDS; colunas demais | Espelho de Harvard primeiro; só as colunas usadas | 6 |
| 25 | Pontos vermelhos falsos na soma em falsa cor | Máscara de saturado juntada com OU entre épocas | Saturado só onde nenhuma época tem dado | 6 |
| 26 | WISE 0855 quase invisível ao abrir | Contraste pelo pixel mais brilhante do campo | Limites ajustados no pico do alvo (topo = pico / 0,8) | 6 |
| 27 | Espectro do WISE 0855 contaminado | Abertura de 3 px pegava uma estrela a ~8″ | Abertura de 2 px (12″) + aviso de vizinhas por detector | 6 |
| 28 | Erro "API ocupada" ao testar o site | `429` tratado como erro; teste no site publicado disparou um campo de 10′ | `429` vira espera com aviso; testes só no site local | 6 |


## 7. Resultados

Detalhes, tabelas e imagens em [08-resultados.md](08-resultados.md).

![WISE 0855 em D6 (épocas 2 e 4) e D1 (épocas 2 e 4), mira fixa](img/marco1-wise0855-zoom.png)

*WISE 0855: em D6 (dois primeiros painéis) a anã marrom se desloca ~1 px para a direita (oeste) entre nov/2025 e mai/2026; em D1 (dois últimos) ela não aparece e a estrela de fundo fica parada.*

Achados com valor para a apresentação:

- A ferramenta **reproduz o movimento próprio conhecido** de três objetos próximos (WISE 0855, Barnard's Star, ε Indi B) com erro de centésimos a décimos de pixel.
- **Detecta variabilidade** das duas estrelas variáveis do desafio com alta significância.
- **Revelou estrelas de campo que parecem variar e não estão catalogadas como variáveis**, incluindo uma provável estrela jovem associada a uma fonte de raios X em Taurus: exatamente o tipo de descoberta que o desafio quer viabilizar.

## 8. Limitações conhecidas

- **Variabilidade por quadro de detector é aproximada**: o quadro soma exposições em comprimentos de onda diferentes (filtro de variação linear). O espectro (fase 6) separa os comprimentos de onda, mas só para os 5 alvos; campos novos pela API ainda não têm espectro.
- **Espectro de fonte fraca**: R Draconis e Barnard's Star saturam e quase não têm pontos; vizinhas a menos de ~12″ entram na abertura (o site avisa por detector).
- **Pixel grande (6,15″)**: movimentos de alguns ″/ano são sutis (~1 px/ano); o site precisa de zoom, blink e mira fixa.
- **Épocas com poucas exposições** são ruidosas (ex.: WISE 0855 em mai/2025).
- **`WCS-WAVE` é "para visualização"** segundo a documentação do SPHEREx; suficiente para o espectro do site, não para ciência de precisão.
- **Primeiro download é lento** (~60 min para os 5 alvos), por causa da extensão PSF que o IRSA sempre envia. Execuções seguintes usam o cache.
- **SIMBAD principal (CDS) estava fora do ar**; usado o espelho de Harvard.
- **Dependência do IRSA no caminho ao vivo**: sem os serviços de consulta, a API não processa campos novos e o robô não atualiza os alvos. Os 5 alvos publicados não são afetados.
- **A API no Render processa um campo por vez**: com a fila cheia, o visitante espera (`Retry-After`). Um campo frio leva minutos.
- **Memória do pipeline cresce com (nº de exposições × área do campo)**: todas as exposições reprojetadas ficam na memória até a soma. Contornado com o limite de 10′ no Render; a solução é acumular as somas em fluxo.
- **O "σ" da diferença é aproximado**: a variância é interpolada junto com a imagem na reprojeção, o que tende a superestimá-la. A diferença fica conservadora (mostra menos pixels do que deveria), o que não foi medido.
- **A posição prevista não inclui paralaxe**: o efeito é menor que 0,1 px para os alvos.

## 9. Onde estamos e próximos passos

| Fase | Entrega | Estado |
|---|---|---|
| 0–3 | Pipeline, dados reais, validação científica, contrato e API | ✅ |
| 4 | Site (**Marco 2**) | ✅ |
| 5 | Publicação | ✅ site, API e atualização automática |
| 6 | Extras | ✅ espectro, mapa e catálogos, falsa cor, soma, flags, campo variável, embed |

Pendências, em ordem sugerida:

1. Roteiro do pitch (`docs/11-apresentacao.md`) com os resultados da validação científica e o diagrama de [visão geral](diagramas/atividade-visao-geral.png).
2. A página do projeto no site do evento. (Licença: GPL-3.0, compatível com o Aladin Lite.)
3. Espectro também para campos novos pela API.
