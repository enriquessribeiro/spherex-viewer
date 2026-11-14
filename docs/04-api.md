# API do backend

Especificação da API HTTP do backend (FastAPI, hospedado no Render) e do formato dos dados estáticos (GitHub Pages). **Status: rascunho v0**; ajustar durante a implementação e manter este documento como fonte da verdade.

Contexto: [03-arquitetura.md](03-arquitetura.md) (fluxo), [02-dados-spherex.md](02-dados-spherex.md) (dados), [05-hospedagem.md](05-hospedagem.md) (infraestrutura).

## 1. Princípios

1. **Um único formato de dados para os dois caminhos.** O backend ao vivo e os alvos pré-processados no GitHub Pages produzem **os mesmos arquivos JSON e binários**. O frontend não precisa saber de onde vieram.
2. **Processamento demorado é assíncrono.** O primeiro pedido de um campo novo leva de segundos a ~2 min (download do IRSA). A API responde na hora com o progresso, e o frontend consulta até ficar pronto.
3. **O pesado fica no servidor; o interativo fica no navegador.** O backend baixa, alinha e soma. Ele entrega as imagens como **matrizes de números (float32)**, que são pequenas (um campo de 6′ tem ~60×60 pixels ≈ 14 KB). O navegador faz contraste, blink, soma e subtração na hora, sem nova requisição.
4. **PNG também existe**, para miniaturas, embed simples e quem não quer lidar com binário.
5. **Tudo é cacheável.** Os recursos de um campo pronto são imutáveis (o identificador muda se os dados mudarem).

## 2. Conceitos

| Termo | Definição |
|---|---|
| **Campo** (*field*) | Região quadrada do céu definida por centro (RA, Dec) e lado (`fov`, em minutos de arco) |
| **Exposição** (*exposure*) | Uma imagem de um detector do SPHEREx que cobre o campo, já recortada e reprojetada para a grade do campo |
| **Época** (*epoch*) | Grupo de exposições próximas no tempo (intervalo > `EPOCH_GAP_DAYS`, padrão 10 dias, inicia nova época) |
| **Quadro** (*frame*) | Soma (coadd) ponderada das exposições de uma época em um detector. É o que a animação mostra |
| **Grade do campo** | Projeção tangente (TAN) centrada no campo, norte para cima, pixel de 6,15″, `N × N` pixels com `N = ceil(fov·60 / 6,15)` |

### 2.1 Identificador do campo

```
field_id = "{ra:.4f}{dec:+.4f}_{fov}"      ex.: "133.7951-7.2451_6"
```

Arredondar em 0,0001° (0,36″, bem menor que um pixel) faz pedidos quase iguais reaproveitarem o cache.

### 2.2 Versão dos dados

`data_version` é um hash curto das exposições usadas (URIs + versões dos arquivos). Quando chega dado novo do IRSA, ele muda. As URLs dos recursos incluem `data_version`, então podem ser cacheadas para sempre.

## 3. Convenções gerais

- **Base:** `https://<servico>.onrender.com/api/v1`
- **Coordenadas:** graus decimais, ICRS (J2000). Aceita-se também sexagesimal em `/resolve`.
- **Tempos:** MJD (número) + ISO 8601 UTC (texto), sempre os dois.
- **Comprimentos de onda:** micrômetros (µm).
- **Brilho:** MJy/sr, com luz zodiacal já subtraída.
- **CORS:** `Access-Control-Allow-Origin: *` em todas as rotas, para permitir embed e uso por outros sites.
- **Cache HTTP:**
  - recursos com `data_version` na URL: `Cache-Control: public, max-age=31536000, immutable`;
  - `/field` (status): `no-store` enquanto processa; `max-age=3600` quando pronto.
- **Erros:** sempre JSON no formato:

```json
{ "error": { "code": "FOV_TOO_LARGE", "message": "fov máximo é 30 arcmin" } }
```

| HTTP | `code` | Quando |
|---|---|---|
| 400 | `INVALID_COORDS` | RA fora de [0, 360) ou Dec fora de [−90, 90] |
| 400 | `FOV_TOO_LARGE` / `FOV_TOO_SMALL` | `fov` fora de [1, 30] arcmin |
| 400 | `INVALID_PARAM` | Parâmetro ausente ou mal formatado |
| 404 | `NO_COVERAGE` | Nenhuma exposição SPHEREx cobre a posição |
| 404 | `NOT_FOUND` | Campo, época, detector ou objeto inexistente |
| 429 | `BUSY` | Servidor processando trabalhos demais; tentar depois (`Retry-After`) |
| 502 | `UPSTREAM_ERROR` | IRSA ou CDS falhou ou excedeu o tempo |
| 500 | `INTERNAL` | Erro inesperado |

## 4. Endpoints

**Estado da implementação** (fase 3, código em `backend/api/`):

| Endpoint | Estado |
|---|---|
| `GET /api/v1/health` | ✅ |
| `GET /api/v1/config` | ✅ conteúdo reduzido: limites de `fov`, downloads paralelos e `poll_after_ms` (detectores e bits ficam no frontend/contrato) |
| `GET /api/v1/resolve` | ✅ coordenadas (graus ou sexagesimal) sem rede; nomes via SIMBAD (espelho de Harvard, depois CDS). Sem movimento próprio para coordenadas digitadas |
| `GET /api/v1/field` | ✅ 202 com progresso → 200 com `field.json`; erros 400/404/429/502 |
| `GET /api/v1/fields/{field_id}/{data_version}/...` | ✅ `field.json`, `.f32`, `.var.f32`, `.mask.u8`, `.png` (PNG com o esticamento padrão; parâmetros `stretch`/`vmin`/`vmax`/`scale` ainda não implementados) |
| `spectrum.json` dos alvos | ✅ nos dados estáticos (`build_static`); pela API, planejado |
| `.../exposures/{id}.f32` | Planejado — fase 6 |
| `.../frames/{epoch}/{det}.fits` | Planejado |

Diferenças em relação ao rascunho: o `partial` (épocas já prontas durante o processamento) e o `eta_s` ainda não são enviados no `202`; erros transitórios (`UPSTREAM_ERROR`) são esquecidos depois de reportados, para o próximo pedido tentar de novo.

### 4.1 `GET /api/v1/health`

Verifica se o servidor está de pé. Usado pelo frontend para mostrar "acordando o servidor…".

```json
{ "status": "ok", "version": "0.1.0", "uptime_s": 42 }
```

### 4.2 `GET /api/v1/config`

Parâmetros e limites atuais, para o frontend não ter nada fixo no código.

```json
{
  "collections": ["spherex_dr1", "spherex_qr3"],
  "fov_arcmin": { "min": 1, "max": 30, "default": 6 },
  "pixel_scale_arcsec": 6.15,
  "epoch_gap_days": 10,
  "detectors": [
    { "id": "D1", "lambda_min_um": 0.75, "lambda_max_um": 1.09, "R": 39 },
    { "id": "D2", "lambda_min_um": 1.10, "lambda_max_um": 1.62, "R": 41 },
    { "id": "D3", "lambda_min_um": 1.63, "lambda_max_um": 2.41, "R": 41 },
    { "id": "D4", "lambda_min_um": 2.42, "lambda_max_um": 3.82, "R": 35 },
    { "id": "D5", "lambda_min_um": 3.83, "lambda_max_um": 4.41, "R": 112 },
    { "id": "D6", "lambda_min_um": 4.42, "lambda_max_um": 5.00, "R": 128 }
  ],
  "flag_bits": { "TRANSIENT": 0, "HOT": 10, "COLD": 11, "NONLINEAR": 15, "OUTLIER": 19,
                 "SOURCE": 21, "GHOST": [22, 23, 24], "BLOOM": 26, "SNOWBALL": 27, "HALO": 28 }
}
```

### 4.3 `GET /api/v1/resolve?name=<texto>`

Converte nome de objeto ou coordenada em texto para graus. Usa o CDS Sesame (SIMBAD/NED/VizieR) e devolve o movimento próprio quando existe, para o marcador de posição prevista.

| Parâmetro | Exemplo |
|---|---|
| `name` | `Barnard's star`, `WISE 0855-0714`, `08h55m10.831s -07d14m42.53s`, `133.795 -7.245` |

```json
{
  "query": "Barnard's star",
  "ra": 269.452076, "dec": 4.693364,
  "epoch": "J2000",
  "pm_ra_masyr": -801.551, "pm_dec_masyr": 10362.394,
  "parallax_mas": 546.976,
  "source": "SIMBAD"
}
```

Coordenadas numéricas são convertidas localmente, sem chamada externa. Erro `404 NOT_FOUND` se o nome não for resolvido.

O site propaga a posição J2000 pelo movimento próprio até a época dos campos (MJD 61000, a mesma de `targets.py`) antes de pedir o campo: sem isso o WISE 0855 cairia ~3,5′ fora do centro, fora de um campo de 6′. Assim, um alvo da lista buscado pelo nome abre o campo pré-processado.

### 4.4 `GET /api/v1/field?ra=&dec=&fov=` — endpoint principal

Pede um campo. **Inicia o processamento se necessário** e devolve o status e, quando pronto, o manifesto completo.

| Parâmetro | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `ra` | sim | — | Graus |
| `dec` | sim | — | Graus |
| `fov` | não | 6 | Lado do campo em arcmin (1–30) |
| `refresh` | não | `false` | Ignora o cache de consulta ao IRSA (força buscar exposições novas) |

**Processando → `202 Accepted`:**

```json
{
  "field_id": "133.7951-7.2451_6",
  "status": "processing",
  "stage": "downloading",
  "progress": { "done": 87, "total": 258 },
  "eta_s": 45,
  "poll_after_ms": 2000,
  "partial": { "...": "manifesto com as épocas já prontas (mesmo formato do ready)" }
}
```

`stage`: `querying` → `downloading` → `processing` → `ready`. O campo `partial` permite mostrar as épocas à medida que ficam prontas.

**Pronto → `200 OK`:** manifesto do campo (seção 5).

**Fluxo esperado do frontend:**

```
GET /field?ra&dec&fov ──▶ 202 (progresso) ──▶ espera poll_after_ms ──▶ GET /field ... ──▶ 200 (manifesto)
```

Dois pedidos simultâneos do mesmo campo compartilham o mesmo trabalho; não há download duplicado.

### 4.5 `GET /api/v1/fields/{field_id}/{data_version}/frames/{epoch}/{det}.f32`

Matriz float32 do quadro (coadd) de uma época/detector. É o recurso usado pela animação.

- Corpo: `N × N` valores float32 **little-endian**, linha a linha, primeira linha = **norte** (topo da imagem). `NaN` = sem dado.
- `Content-Type: application/octet-stream`
- Tamanho: `N² × 4` bytes (6′ → ~59×59 → ~14 KB; 30′ → ~293×293 → ~343 KB).
- Variante `{det}.var.f32`: variância do quadro, no mesmo formato.

Também `.../frames/{epoch}/{det}.mask.u8`: 1 byte por pixel, bit 0 = saturado, bit 1 = baixa qualidade (ver §5). Um bitmap com a união dos flags de contaminação (fantasmas, persistência) fica para a fase 6.

### 4.6 `GET /api/v1/fields/{field_id}/{data_version}/frames/{epoch}/{det}.png`

O mesmo quadro já renderizado em PNG, em escala de cinza, com o esticamento padrão do campo (comum a todas as épocas daquele detector).

| Parâmetro | Padrão | Opções |
|---|---|---|
| `stretch` | `asinh` | `linear`, `log`, `asinh`, `sqrt` |
| `vmin`, `vmax` | do manifesto | MJy/sr |
| `scale` | 1 | Fator de ampliação inteiro (vizinho mais próximo), 1–8 |

Uso: miniaturas, embed simples, compartilhamento em redes sociais.

### 4.7 `GET /api/v1/fields/{field_id}/{data_version}/exposures/{exposure_id}.f32` *(planejado — fase 6)*

Uma exposição individual, reprojetada para a grade do campo e com a luz zodiacal subtraída, no mesmo formato de `.f32`. Permite animar **dentro** de uma época, útil para objetos rápidos como asteroides, que andam de um minuto para o outro.

### 4.8 `GET /api/v1/fields/{field_id}/{data_version}/spectrum?ra=&dec=`

Espectro de um ponto do campo, medido em **todas** as exposições.

| Parâmetro | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `ra`, `dec` | sim | — | Ponto clicado (deve estar dentro do campo) |
| `aperture_arcsec` | não | 9 | Raio da abertura de fotometria |
| `epoch` | não | todas | Restringir a uma época (para comparar espectros entre épocas) |

```json
{
  "ra": 133.79513, "dec": -7.24515,
  "aperture_arcsec": 9,
  "units": { "wavelength": "um", "flux": "uJy" },
  "points": [
    { "wavelength": 4.612, "bandwidth": 0.036, "flux": 152.3, "flux_err": 8.1,
      "det": "D6", "epoch": 2, "mjd": 60980.43, "exposure_id": "2025W44_2A_0112_3D6",
      "flags": ["SOURCE"] }
  ]
}
```

Método: fotometria de abertura na posição, em cada exposição, com fundo local em anel. Comprimento de onda lido do WCS espectral (`WCS-WAVE`, ver limitação em [02-dados-spherex.md](02-dados-spherex.md)). Pontos com flags graves (HOT, NONLINEAR, GHOST…) vêm marcados, e o frontend pode escondê-los.

**Implementado (fase 6) para os alvos pré-processados**, em `pipeline/spectrum.py`, gravado como `spectrum.json` na pasta do campo (`field.json` → `"spectrum": "spectrum.json"`; formato em [`schemas/spectrum.schema.json`](../schemas/spectrum.schema.json)):

- Posição do alvo **na data de cada exposição** (movimento próprio), abertura de **2 px (12″)**, fundo pela mediana com corte sigma no anel de 5–8 px, sobre `IMAGE − ZODI`. Unidade: µJy (MJy/sr × ângulo sólido do pixel). Sem correção pela PSF: a forma do espectro é confiável, o valor absoluto fica ~10% abaixo do total.
- Exposição descartada se a abertura tem pixel sem dado (núcleo saturado: R Draconis não tem espectro) ou com flag grave; com flag suspeito (TRANSIENT, NONLINEAR…) entra marcada (`flagged`).
- **Vizinhas na abertura** (`neighbors`): fontes com S/R > 5, a mais de 1 px e até 3 px do alvo, por detector, na época mais profunda. No WISE 0855 há uma estrela a ~9″: em D1–D3 o fluxo medido é dela, e o site avisa.
- No site: uma bolinha por exposição, a época que está na placa em lápis, a mediana por caixas de λ/40 em tinta, faixa de cada detector sob o eixo, tooltip e tabela.

### 4.9 `GET /api/v1/fields/{field_id}/{data_version}/frames/{epoch}/{det}.fits`

Download do quadro como FITS, com cabeçalho WCS completo e extensões `IMAGE`, `VARIANCE`, `FLAGS`. Para quem quiser analisar em outro programa (DS9, Astropy, Aladin Desktop).

## 5. Manifesto do campo (`field.json`)

Resposta de `GET /field` quando pronto, e **também o arquivo `field.json` dos alvos estáticos**.

```json
{
  "schema_version": 1,
  "field_id": "133.7951-7.2451_6",
  "data_version": "a3f9c2",
  "status": "ready",
  "generated_at": "2026-11-14T21:03:11Z",
  "center": { "ra": 133.79513, "dec": -7.24515 },
  "fov_arcmin": 6,
  "grid": {
    "n": 59,
    "pixel_scale_arcsec": 6.15,
    "row_order": "north_first",
    "wcs": { "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
             "CRVAL1": 133.79513, "CRVAL2": -7.24515,
             "CRPIX1": 30.0, "CRPIX2": 30.0,
             "CDELT1": -0.001708, "CDELT2": 0.001708 }
  },
  "collections": ["spherex_dr1", "spherex_qr3"],
  "latest_exposure_mjd": 61174.287,
  "base_url": "fields/133.7951-7.2451_6/a3f9c2/",
  "epochs": [
    {
      "index": 1,
      "mjd_start": 60800.700, "mjd_end": 60801.515, "mjd_mid": 60801.108,
      "date_start": "2025-05-05", "date_end": "2025-05-06",
      "frames": {
        "D1": { "n_exposures": 4, "mjd_mean": 60801.51,
                "lambda_min_um": 0.75, "lambda_max_um": 1.09, "background": 0.031,
                "frame": "frames/1/D1.f32", "variance": "frames/1/D1.var.f32",
                "mask": "frames/1/D1.mask.u8", "png": "frames/1/D1.png" },
        "D6": { "...": "..." }
      },
      "exposures": [
        { "id": "2025W19_1B_0241_1D1", "det": "D1", "mjd": 60801.514,
          "collection": "spherex_dr1" }
      ]
    }
  ],
  "display": {
    "D1": { "stretch": "asinh", "vmin": -0.05, "vmax": 2.3 },
    "D6": { "stretch": "asinh", "vmin": -0.02, "vmax": 0.9 }
  },
  "failed_exposures": ["2025W45_2A_0308_4D5"],
  "target": {
    "id": "wise0855", "name": "WISE 0855-0714",
    "description": "A anã marrom mais fria conhecida",
    "pm_ra_masyr": -8123.7, "pm_dec_masyr": 673.2, "ref_mjd": 51544.5,
    "predicted_positions": [ { "epoch": 1, "ra": 133.7925, "dec": -7.2440 } ]
  }
}
```

Notas:

- Caminhos de arquivos são **relativos a `base_url`**, que por sua vez é relativo à raiz da API (`/api/v1/`) ou à pasta de dados estáticos (`data/`). O frontend só concatena.
- Uma época pode não ter todos os detectores: `frames` contém apenas os que existem.
- `display` traz os limites de contraste **comuns a todas as épocas** de cada detector: `vmin` = percentil 1 e `vmax` = **máximo** (para variáveis brilhantes não saturarem).
- **Esquema formal:** [`schemas/field.schema.json`](../schemas/field.schema.json) (JSON Schema 2020-12), validado nos testes do backend e do frontend.
- **Máscara** (`.mask.u8`, 1 byte por pixel, norte na 1ª linha): bit 0 = **saturado** (núcleo de estrela brilhante sem dado; pintar com o brilho máximo), bit 1 = **baixa qualidade** (só havia dados com flag suspeito). O overlay de fantasmas/artefatos (flags 17, 20, 22–28) fica para a fase 6.
- `exposures` lista as exposições usadas (sem arquivo individual por enquanto). `failed_exposures` lista as que o IRSA não entregou.
- O PNG já aplica o esticamento `asinh` com os limites de `display` e pinta o núcleo saturado de branco.
- `target` só existe quando o campo veio de um nome resolvido ou de um alvo da lista; contém as posições previstas por época, só pelo movimento próprio: a paralaxe (até ~0,55″ na Barnard's Star, < 0,1 px) não é aplicada.

## 6. Dados estáticos (GitHub Pages)

Gerados pelo `pipeline.build_static` e publicados pelo Action ([05-hospedagem.md](05-hospedagem.md)). Mesmo formato da API:

```
data/
├── manifest.json                      ← índice de alvos pré-processados
└── fields/
    └── 133.7951-7.2451_6/
        └── a3f9c2/
            ├── field.json             ← igual à seção 5
            ├── frames/1/D1.f32
            ├── frames/1/D1.png
            ├── ...
```

`data/manifest.json`:

```json
{
  "schema_version": 1,
  "generated_at": "2026-11-17T06:12:40Z",
  "targets": [
    {
      "id": "wise0855",
      "name": "WISE 0855",
      "description": "A anã marrom mais fria conhecida; move-se ~8″/ano",
      "ra": 133.79513, "dec": -7.24515, "fov_arcmin": 6,
      "field": "fields/133.7951-7.2451_6/a3f9c2/field.json",
      "latest_exposure_mjd": 61174.287,
      "thumbnail": "fields/133.7951-7.2451_6/a3f9c2/frames/4/D6.png"
    }
  ]
}
```

**Regra do frontend:** se o campo pedido corresponde a um alvo de `data/manifest.json`, carrega o estático (instantâneo). Senão, usa `GET /api/v1/field`.

## 7. URL do site (estado compartilhável)

Não é API do backend, mas é o "contrato público" para links e embed. Todo o estado da visualização fica na query string:

| Parâmetro | Exemplo | Descrição |
|---|---|---|
| `ra`, `dec` | `ra=133.79513&dec=-7.24515` | Centro (graus) |
| `target` | `target=wise0855` | Alternativa a ra/dec: alvo da lista |
| `name` | `name=Barnard's%20star` | Alternativa: resolve via `/resolve` |
| `fov` | `fov=6` | Campo em arcmin |
| `det` | `det=D6` | Detector |
| `color` | `color=1` | Falsa cor: D6, D3 e D1 nos canais R, G e B |
| `mode` | `play`, `blink`, `diff`, `sum` | Modo: animar, piscar, diferença em σ ou soma de todas as épocas |
| `a`, `b` | `a=1&b=4` | Épocas usadas em blink/diff |
| `fps` | `fps=2` | Velocidade da animação |
| `stretch` | `asinh` | Esticamento |
| `overlay` | `gaia,wise,flags,pm` | Camadas ligadas (planejado) |
| `embed` | `embed=1` | Interface mínima para iframe |

Exemplo:

```
https://<usuario>.github.io/spherex-viewer/?target=wise0855&det=D6&mode=blink&a=1&b=4
```

Embed:

```html
<iframe src="https://<usuario>.github.io/spherex-viewer/?ra=269.452&dec=4.693&det=D6&embed=1"
        width="480" height="480" style="border:0"></iframe>
```

## 8. Operações feitas no navegador (sem endpoint)

Com os quadros em float32, o frontend calcula na hora:

| Operação | Como |
|---|---|
| Contraste / esticamento | Aplica `stretch` com `vmin`/`vmax` (do manifesto ou ajustados pelo usuário) |
| Blink | Alterna quadros `a` e `b` |
| Diferença | `b − a`, mapa de cores divergente (azul = sumiu, vermelho = apareceu) |
| Soma de épocas | Média ponderada por `1/variância` das épocas escolhidas |
| Falsa cor | Três detectores nos canais R, G e B |
| Overlay de qualidade | Bits de `.mask.u8` (saturado, baixa qualidade) desenhados em cor semitransparente; contaminação (fantasmas etc.) na fase 6 |
| Marcador de posição prevista | `target.predicted_positions` convertidas para pixel com `grid.wcs` |

## 9. Limites operacionais (Render free)

| Limite | Valor inicial |
|---|---|
| `fov` máximo | 30 arcmin por padrão; configurável por `SPHEREX_FOV_MAX` (10 no Render grátis, por causa da memória) |
| Downloads simultâneos do IRSA | 4 (o IRSA respondeu `503 Server busy` com apenas 2; o adaptador repete com espera exponencial) |
| Trabalhos de campo simultâneos | 2 (excedente → `429 BUSY`) |
| Validade do cache de consulta TAP | 24 h |
| Tempo máximo por campo | 30 min, configurável por `SPHEREX_JOB_TIMEOUT_S` (depois, `502 UPSTREAM_ERROR` e a vaga é liberada; `partial` ainda não existe). Um campo novo leva 5–20 min com o IRSA saudável |

Valores ficam em variáveis de ambiente para ajuste sem mudar código.

## 10. Versionamento

- Prefixo `/api/v1`. Mudanças incompatíveis → `/api/v2`.
- `schema_version` no `field.json` e no `manifest.json`. O frontend recusa versões que não conhece com mensagem clara.
- Documentação interativa automática do FastAPI em `/docs` (Swagger) e `/openapi.json`.
