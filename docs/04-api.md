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
field_id = "{ra:.4f}{dec:+.4f}_{fov}"      ex.: "133.7951-7.2452_6"
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
  "field_id": "133.7951-7.2452_6",
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

Também `.../frames/{epoch}/{det}.flags.u32`: bitmap uint32 com a **união** (OR) dos flags das exposições, para o overlay de contaminação.

### 4.6 `GET /api/v1/fields/{field_id}/{data_version}/frames/{epoch}/{det}.png`

O mesmo quadro já renderizado em PNG, em escala de cinza, com o esticamento padrão do campo (comum a todas as épocas daquele detector).

| Parâmetro | Padrão | Opções |
|---|---|---|
| `stretch` | `asinh` | `linear`, `log`, `asinh`, `sqrt` |
| `vmin`, `vmax` | do manifesto | MJy/sr |
| `scale` | 1 | Fator de ampliação inteiro (vizinho mais próximo), 1–8 |

Uso: miniaturas, embed simples, compartilhamento em redes sociais.

### 4.7 `GET /api/v1/fields/{field_id}/{data_version}/exposures/{exposure_id}.f32`

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

### 4.9 `GET /api/v1/fields/{field_id}/{data_version}/frames/{epoch}/{det}.fits`

Download do quadro como FITS, com cabeçalho WCS completo e extensões `IMAGE`, `VARIANCE`, `FLAGS`. Para quem quiser analisar em outro programa (DS9, Astropy, Aladin Desktop).

## 5. Manifesto do campo (`field.json`)

Resposta de `GET /field` quando pronto, e **também o arquivo `field.json` dos alvos estáticos**.

```json
{
  "schema_version": 1,
  "field_id": "133.7951-7.2452_6",
  "data_version": "a3f9c2",
  "status": "ready",
  "generated_at": "2026-11-14T21:03:11Z",
  "center": { "ra": 133.79513, "dec": -7.24515 },
  "fov_arcmin": 6,
  "grid": {
    "n": 59,
    "pixel_scale_arcsec": 6.15,
    "wcs": { "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
             "CRVAL1": 133.79513, "CRVAL2": -7.24515,
             "CRPIX1": 30.0, "CRPIX2": 30.0,
             "CDELT1": -0.001708, "CDELT2": 0.001708 }
  },
  "collections": ["spherex_dr1", "spherex_qr3"],
  "latest_exposure_mjd": 61174.287,
  "base_url": "fields/133.7951-7.2452_6/a3f9c2/",
  "epochs": [
    {
      "index": 1,
      "mjd_start": 60800.700, "mjd_end": 60801.515, "mjd_mid": 60801.108,
      "date_start": "2025-05-05", "date_end": "2025-05-06",
      "frames": {
        "D1": { "n_exposures": 4, "lambda_min_um": 0.75, "lambda_max_um": 1.09,
                "frame": "frames/1/D1.f32", "variance": "frames/1/D1.var.f32",
                "flags": "frames/1/D1.flags.u32", "png": "frames/1/D1.png",
                "flag_summary": { "GHOST": 0, "NONLINEAR": 3 } },
        "D6": { "...": "..." }
      },
      "exposures": [
        { "id": "2025W19_1B_0241_1D1", "det": "D1", "mjd": 60801.514,
          "collection": "spherex_dr1", "file": "exposures/2025W19_1B_0241_1D1.f32" }
      ]
    }
  ],
  "display": {
    "D1": { "stretch": "asinh", "vmin": -0.05, "vmax": 2.3 },
    "D6": { "stretch": "asinh", "vmin": -0.02, "vmax": 0.9 }
  },
  "target": {
    "name": "WISE 0855-0714",
    "pm_ra_masyr": -8118.0, "pm_dec_masyr": 673.0, "ref_epoch_mjd": 57000.0,
    "predicted_positions": [ { "epoch": 1, "ra": 133.7925, "dec": -7.2440 } ]
  }
}
```

Notas:

- Caminhos de arquivos são **relativos a `base_url`**, que por sua vez é relativo à raiz da API (`/api/v1/`) ou à pasta de dados estáticos (`data/`). O frontend só concatena.
- Uma época pode não ter todos os detectores: `frames` contém apenas os que existem.
- `display` traz os limites de contraste **comuns a todas as épocas** de cada detector, calculados por percentis (ex.: 1% e 99,5%) do conjunto.
- `target` só existe quando o campo veio de um nome resolvido ou de um alvo da lista; contém as posições previstas por época (movimento próprio + paralaxe quando disponível).

## 6. Dados estáticos (GitHub Pages)

Gerados pelo `pipeline.build_static` e publicados pelo Action ([05-hospedagem.md](05-hospedagem.md)). Mesmo formato da API:

```
data/
├── manifest.json                      ← índice de alvos pré-processados
└── fields/
    └── 133.7951-7.2452_6/
        └── a3f9c2/
            ├── field.json             ← igual à seção 5
            ├── frames/1/D1.f32
            ├── frames/1/D1.png
            ├── ...
            └── exposures/...
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
      "field": "fields/133.7951-7.2452_6/a3f9c2/field.json",
      "latest_exposure_mjd": 61174.287,
      "thumbnail": "fields/133.7951-7.2452_6/a3f9c2/frames/4/D6.png"
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
| `det` | `det=D6` ou `det=D1,D3,D6` | Detector, ou três para falsa cor (R,G,B) |
| `mode` | `play`, `blink`, `diff`, `sum` | Modo de visualização |
| `a`, `b` | `a=1&b=4` | Épocas usadas em blink/diff |
| `fps` | `fps=2` | Velocidade da animação |
| `stretch` | `asinh` | Esticamento |
| `overlay` | `gaia,wise,flags,pm` | Camadas ligadas |
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
| Overlay de flags | Bits escolhidos de `.flags.u32` desenhados em cor semitransparente |
| Marcador de posição prevista | `target.predicted_positions` convertidas para pixel com `grid.wcs` |

## 9. Limites operacionais (Render free)

| Limite | Valor inicial |
|---|---|
| `fov` máximo | 30 arcmin |
| Downloads simultâneos do IRSA | 12 |
| Trabalhos de campo simultâneos | 2 (excedente → `429 BUSY`) |
| Validade do cache de consulta TAP | 24 h |
| Tempo máximo por campo | 5 min (depois, `502 UPSTREAM_ERROR` com o que já ficou pronto em `partial`) |

Valores ficam em variáveis de ambiente para ajuste sem mudar código.

## 10. Versionamento

- Prefixo `/api/v1`. Mudanças incompatíveis → `/api/v2`.
- `schema_version` no `field.json` e no `manifest.json`. O frontend recusa versões que não conhece com mensagem clara.
- Documentação interativa automática do FastAPI em `/docs` (Swagger) e `/openapi.json`.
