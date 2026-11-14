# Estratégia de testes

Testes projetados **antes** do desenvolvimento para guiar a implementação. Este documento define **onde** testar (as fronteiras) e **o que** conta como correto (critérios de aceitação). Os testes em si são escritos durante o desenvolvimento.

## 1. Princípios

1. **Testar pelas interfaces públicas, nunca pela implementação.** Um teste só deve quebrar quando o comportamento muda, não quando o código é reorganizado.
2. **Valores esperados vêm de fontes independentes**: dados sintéticos em que *nós* plantamos a resposta, ou valores da literatura (SIMBAD, artigos). Nunca recalcular o esperado do mesmo jeito que o código calcula.
3. **Fatias verticais (TDD):** um teste falhando → código mínimo para passar → próximo teste. **Não** escrever todos os testes de uma vez antes do código.
4. **Rápido por padrão, lento quando marcado.** A suíte padrão roda em segundos e sem internet. Testes com rede ficam marcados (`@pytest.mark.live`, `@pytest.mark.science`) e rodam sob demanda e no Action.

## 2. Fronteiras de teste

Só escrevemos testes nestas 7 fronteiras.

| # | Fronteira | Interface | Ferramenta | Rede | Roda em |
|---|---|---|---|---|---|
| 1 | Pipeline científico | `build_field(ra, dec, fov, archive)` | pytest | Não | Sempre |
| 2 | Adaptador do IRSA | `IrsaArchive.query()`, `.fetch_cutout()` | pytest | Gravado / `live` | Sempre / sob demanda |
| 3 | API HTTP | Endpoints de [04-api.md](04-api.md) | pytest + `TestClient` do FastAPI | Não | Sempre |
| 4 | Contrato de dados | JSON Schema de `field.json` e `manifest.json` | pytest + Vitest | Não | Sempre |
| 5 | Núcleo do frontend | Módulo `viewer-core` (lógica pura) | Vitest | Não | Sempre |
| 6 | Validação científica | Pipeline completo com dados reais dos 5 alvos | pytest (`science`) | Sim | Manual + **Action (bloqueia publicação)** |
| 7 | Ponta a ponta | Site no navegador | Playwright | Não (dados estáticos) | Opcional |

**Fora dos testes:** funcionamento interno do Aladin Lite, aparência visual, desempenho do Render.

### 2.1 Fronteira 1: pipeline científico (com arquivo sintético)

A peça mais importante. O pipeline recebe um **adaptador de arquivo** (`archive`) injetável. Nos testes, usamos um `SyntheticArchive` que gera FITS falsos no mesmo formato do SPHEREx (extensões `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `WCS-WAVE`, cabeçalho WCS com rotação/deslocamento), contendo coisas que nós plantamos.

| Cenário plantado | Comportamento esperado |
|---|---|
| Estrela parada, 2 épocas, apontamentos com rotação e deslocamento diferentes | Nos quadros das duas épocas, a estrela cai no **mesmo pixel** (±0,1 px) |
| Estrela que anda 2 px entre épocas | Centroide do quadro da época 2 deslocado 2 px (±0,2 px) na direção plantada |
| Exposições em t = 0, 1, 2 dias e 180, 181 dias | **2 épocas** com 3 e 2 exposições |
| Gap exatamente no limite (`EPOCH_GAP_DAYS`) | Regra de borda documentada e respeitada |
| Época sem o detector D4 | `frames` da época não contém D4; nenhuma falha |
| Luz zodiacal constante de 5 MJy/sr | Fundo do quadro ≈ 0 (±ruído) |
| Pixel marcado HOT com valor absurdo | Ignorado na soma (não aparece no quadro) |
| Pixel marcado SOURCE | **Não** é mascarado |
| N exposições com ruído σ | Ruído do quadro ≈ σ/√N |
| Duas exposições com variâncias diferentes | Soma pondera por 1/variância |
| Fonte com brilho diferente por época | `display.vmin/vmax` iguais para todas as épocas do detector |
| Fonte com espectro plantado (ex.: pico em 4,6 µm) | `spectrum` recupera o pico no comprimento de onda certo (± 1 canal) |
| `fov` = 6′ | Grade de 59 × 59 pixels, norte para cima |
| Nenhuma exposição | Erro de domínio `NoCoverage` |

### 2.2 Fronteira 2: adaptador do IRSA

- **Fixtures gravadas** (em `tests/fixtures/irsa/`), capturadas uma vez do IRSA real:
  - resposta TAP (CSV) para WISE 0855;
  - 2–3 recortes FITS reais de WISE 0855 (um de D1 e um de D6, de épocas diferentes), **sem** a extensão PSF para não pesar no repositório.
- Testes com fixtures:
  - interpreta a consulta → **258 exposições**, contagens por detector D1–D6 = 36/48/45/36/48/45, **4 grupos de tempo** (05/2025, 10–11/2025, 12/2025, 04–05/2026);
  - lê um recorte real → extensões esperadas presentes, WCS válido, unidades MJy/sr;
  - monta a URL de recorte corretamente (`?center=ra,dec&size=graus`).
- Teste `@live` (rede): uma consulta real responde, as colunas esperadas existem e um recorte baixa. Serve para detectar mudança de formato no IRSA.

> Os números do WISE 0855 foram obtidos em 14/11/2026 e valem para as fixtures gravadas. No teste `live`, verificar apenas `≥ 258` exposições, pois chegam dados novos.

### 2.3 Fronteira 3: API HTTP

Com `TestClient` e o pipeline usando o `SyntheticArchive`:

- `GET /field` em campo novo → `202` com `status: processing` e `progress`; depois → `200` com manifesto válido.
- Dois `GET /field` simultâneos do mesmo campo → **um único** processamento (o arquivo falso conta as chamadas).
- Coordenadas quase iguais (diferença < 0,0001°) → mesmo `field_id`.
- Erros: `INVALID_COORDS` (dec = 95), `FOV_TOO_LARGE` (fov = 60), `NO_COVERAGE`, `UPSTREAM_ERROR` (arquivo falso lança erro), `BUSY` (limite de trabalhos).
- Recursos binários: `.f32` com `N² × 4` bytes, `Content-Type` correto.
- Cabeçalhos: `Access-Control-Allow-Origin: *`; `immutable` em recursos versionados; `no-store` enquanto processa.
- `/resolve` com coordenadas numéricas não faz chamada externa; com nome, usa um adaptador do CDS injetável (falso nos testes).

### 2.4 Fronteira 4: contrato de dados

- Esquemas em `schemas/field.schema.json` e `schemas/manifest.schema.json` (fonte única da verdade, ao lado de [04-api.md](04-api.md)).
- Backend: toda saída de `build_field` e do `build_static` é validada contra o esquema.
- Frontend: os exemplos usados nos testes do `viewer-core` também são validados contra o mesmo esquema.
- Assim, API, arquivos estáticos e frontend não podem divergir sem quebrar um teste.

### 2.5 Fronteira 5: núcleo do frontend (`viewer-core`)

Lógica pura em JavaScript, sem DOM, testada com Vitest e valores literais:

| Função | Exemplo de teste |
|---|---|
| Decodificar `.f32` | Buffer de 4 floats conhecidos → matriz 2×2 com esses valores; `NaN` preservado |
| Esticamento | `linear` com vmin = 0, vmax = 10: 5 → 0,5; valores fora do intervalo → 0 e 1 |
| Diferença | `[1,2] − [1,5]` → `[0,3]`; `NaN` em qualquer lado → `NaN` |
| Soma ponderada | Valores 2 e 4 com variâncias 1 e 1 → 3; com variâncias 1 e 3 → 2,5 |
| Coordenada ↔ pixel | Centro do campo → pixel central; 1 pixel a leste → coluna −1 (leste à esquerda) |
| Estado na URL | `parse(serialize(estado)) == estado`; parâmetros inválidos → padrões + aviso |
| Escolha da fonte | Alvo presente no `manifest.json` → estático; senão → API |

### 2.6 Fronteira 6: validação científica (aceitação)

Roda o pipeline completo com **dados reais** do IRSA nos 5 alvos do desafio. Os valores esperados vêm da literatura (SIMBAD/Gaia), não do nosso código.

| Alvo | Critério | Fonte da verdade |
|---|---|---|
| Barnard's Star | Deslocamento do centroide entre a primeira e a última época compatível com o movimento próprio (~10,4″/ano) em módulo e direção (norte), dentro de tolerância T₁ | SIMBAD / Gaia DR3 |
| WISE 0855 | Deslocamento compatível com ~8″/ano (direção oeste); fluxo em D6 ≫ fluxo em D1 (razão > R₁) | Luhman (2014); SIMBAD |
| Epsilon Indi B | Deslocamento compatível com ~4,7″/ano; direção igual à de ε Indi A | SIMBAD / Gaia DR3 |
| R Draconis | Variação de brilho entre épocas > K₁ × incerteza | Variável Mira (AAVSO) |
| RW Aurigae | Variação de brilho entre épocas > K₂ × incerteza | T Tauri variável (AAVSO) |
| Estrelas de campo (todos os alvos) | Na diferença entre épocas, resíduo RMS das estrelas paradas < K₃ × ruído (prova de alinhamento) | Estrelas paradas do Gaia |

**Tolerâncias** (T₁, R₁, K₁, K₂, K₃) a calibrar na primeira execução real e registrar aqui com justificativa. Ponto de partida: T₁ = 0,5 px (~3″), K = 3σ.

> ⚠️ Antes da primeira execução, confirmar no SIMBAD as coordenadas, o movimento próprio e a época de referência de cada alvo (ver [01-projeto.md](01-projeto.md)).

**Bloqueia a publicação:** no GitHub Action, a validação roda depois do pipeline e **antes** do deploy. Se falhar:

- o job de deploy não roda (`needs`), o que funciona no plano gratuito por ser o comportamento padrão do Actions;
- o site continua com a **última versão válida** (o Pages mantém o deploy anterior);
- o GitHub envia e-mail de falha;
- o relatório (valores medidos × esperados) fica salvo como artefato da execução.

Os resultados também servem de material para o pitch: *"a ferramenta reproduz o movimento próprio conhecido da Barnard's Star com erro de X″"*.

### 2.7 Fronteira 7: ponta a ponta (opcional)

Playwright, servindo o frontend com dados estáticos de teste (sem backend):

- abrir `?target=wise0855` → 4 épocas listadas, animação rodando;
- clicar em *Blink* → o quadro exibido alterna;
- alterar o detector → URL atualizada.

## 3. Estrutura de pastas

```
backend/
  tests/
    fixtures/irsa/            ← respostas reais gravadas (TAP CSV, recortes sem PSF)
    synthetic.py              ← SyntheticArchive (gerador de FITS falsos)
    test_pipeline.py          ← fronteira 1
    test_irsa_archive.py      ← fronteira 2
    test_api.py               ← fronteira 3
    test_schemas.py           ← fronteira 4 (backend)
    science/
      test_targets.py         ← fronteira 6 (@pytest.mark.science)
frontend/
  tests/
    viewer-core.test.js       ← fronteira 5
    schemas.test.js           ← fronteira 4 (frontend)
    e2e/                      ← fronteira 7
schemas/
  field.schema.json
  manifest.schema.json
```

## 4. Como rodar

```bash
# rápido, sem rede (padrão)
pytest
npm test

# com rede
pytest -m live          # adaptador IRSA real
pytest -m science       # validação científica dos 5 alvos
```

Em `pytest.ini`/`pyproject.toml`, `live` e `science` ficam excluídos por padrão (`-m "not live and not science"`).

## 5. No GitHub Actions

| Workflow | Quando | O que roda |
|---|---|---|
| `test.yml` | Todo push e PR | pytest rápido + Vitest |
| `update-data.yml` | Semanal, manual e push na `main` | pipeline dos alvos → `pytest -m science` → **deploy só se passar** |

Trecho de `update-data.yml` (complementa [05-hospedagem.md](05-hospedagem.md)):

```yaml
      - name: Processar alvos
        run: python -m pipeline.build_static --targets targets.yaml --out frontend/data
      - name: Validação científica (bloqueia publicação)
        run: pytest -m science --data frontend/data --report science-report.json
      - name: Guardar relatório
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: science-report
          path: science-report.json
      - uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/
```

## 6. Ordem das primeiras fatias (TDD)

1. **F1**: estrela sintética parada, 2 épocas → quadro com a estrela no pixel central.
2. **F1**: estrela que anda 2 px → deslocamento detectado no quadro da época 2.
3. **F1**: agrupamento de épocas (3 + 2 exposições).
4. **F2**: interpretar a consulta gravada do WISE 0855 → 258 exposições, 4 grupos.
5. **F6**: WISE 0855 real → primeiro resultado científico (deslocamento + D6 ≫ D1).
6. **F3/F4**: API `/field` com 202 → 200 e manifesto válido pelo esquema.
7. **F5**: `viewer-core` (decodificar, esticar, blink/diferença, URL).
