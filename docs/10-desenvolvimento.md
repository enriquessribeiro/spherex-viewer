# Como rodar localmente

Guia prático para desenvolver e testar o SPHEREx Viewer. Visão geral em [01-projeto.md](01-projeto.md); decisões em [03-arquitetura.md](03-arquitetura.md).

## 1. Requisitos

- [uv](https://docs.astral.sh/uv/) (gerencia o Python 3.12 e as dependências)
- Acesso à internet para os dados reais (IRSA e SIMBAD). Os testes rápidos não precisam de rede.

## 2. Instalação

```bash
cd backend
uv sync
```

## 3. Testes

```bash
cd backend
uv run pytest                # rápidos, sem rede (~8 s): pipeline sintético, IRSA gravado, cache, contrato, API
uv run pytest -m live        # serviços reais: IRSA e SIMBAD
uv run pytest -m science     # validação científica dos 5 alvos com dados reais
```

| Marcador | O que testa | Tempo |
|---|---|---|
| (padrão) | Fronteiras 1–4 com dados sintéticos e respostas gravadas | ~8 s |
| `live` | Resolvedor SIMBAD e acesso ao IRSA | segundos |
| `science` | Os 5 alvos do desafio contra SIMBAD/Gaia | ~60 min na 1ª vez (download), ~2,5 min com cache |

Estratégia completa em [06-testes.md](06-testes.md).

## 4. Gerar os dados estáticos dos alvos

```bash
cd backend
uv run python -m pipeline.build_static --targets ../targets.yaml --out ../frontend/data
# só alguns alvos:
uv run python -m pipeline.build_static --only wise0855 barnard --out ../frontend/data
```

- Recortes e consultas ficam em `backend/cache/` (ignorado pelo git). Com o cache cheio, os 5 alvos levam ~2,5 min.
- Saída: `manifest.json` + `fields/<field_id>/<data_version>/...` (~5 MB no total). Formato em [04-api.md](04-api.md) §5–6.

## 5. Rodar a API

```bash
cd backend
uv run uvicorn api.main:app --reload --port 8000
```

- Documentação interativa: <http://127.0.0.1:8000/docs>
- Exemplo:

```bash
curl "http://127.0.0.1:8000/api/v1/resolve?name=Barnard's%20star"
curl "http://127.0.0.1:8000/api/v1/field?ra=133.76002&dec=-7.24221&fov=6"   # 202 até ficar pronto, depois 200
```

| Variável de ambiente | Padrão | Uso |
|---|---|---|
| `SPHEREX_CACHE_DIR` | `cache` | Cache de recortes e consultas |
| `SPHEREX_DATA_DIR` | `<cache>/fields-data` | Campos gerados pela API |
| `SPHEREX_MAX_JOBS` | `2` | Campos processados ao mesmo tempo |

Medido localmente: WISE 0855 com o cache cheio fica pronto em ~22 s (reprojeção de 258 exposições); um campo novo depende do IRSA (~5–20 min para 250–550 exposições).

## 6. Estrutura do backend

| Pasta | Conteúdo |
|---|---|
| `pipeline/` | Ciência: `archive` (interface), `irsa` (adaptador), `cache`, `field` (`build_field`), `output` (`write_field`), `targets`, `build_static` |
| `api/` | HTTP: `app` (`create_app`), `jobs` (processamento assíncrono), `coords`, `simbad`, `main` (produção) |
| `tests/` | Testes por fronteira; `fixtures/irsa/` com respostas reais gravadas; `science/` com a validação científica |
| `../schemas/` | JSON Schema de `field.json` e `manifest.json` (contrato com o frontend) |

## 7. Fluxo de trabalho

Branch por fase, PR para a `main`, commits por fatia de TDD. Detalhes em [07-plano-desenvolvimento.md](07-plano-desenvolvimento.md) §5.
