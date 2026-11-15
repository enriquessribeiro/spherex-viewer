# Hospedagem, armazenamento e atualização de dados

Decisões de infraestrutura do projeto. Restrição principal: **tudo deve ser 100% gratuito**.

## 1. Resumo das decisões

| Peça | Decisão | Motivo |
|---|---|---|
| Frontend + alvos pré-processados | **GitHub Pages** | Grátis, publicação nativa pelo GitHub Actions, tudo no mesmo lugar |
| Backend ao vivo (coordenadas quaisquer) | **Render (plano free)** | Único plano gratuito viável para Python + Astropy |
| Atualização dos alvos pré-processados | **GitHub Actions agendado** (a cada 3 dias) | Grátis em repositório público; atende ao item "fácil de atualizar" do desafio |
| Armazenamento de imagens | **Arquivos (cache), sem banco de dados** | Imagens são arquivos; a busca de "quais imagens existem" é feita pelo próprio IRSA |
| Repositório | **Público** | Exigência usual do Space Apps e condição para Pages e Actions gratuitos |

## 2. Visão geral

```
                     ┌─────────────────────────────────────────────┐
                     │ GitHub Pages                                │
 Usuário ──────────▶ │  frontend + /data/<alvo>/… (pré-processado) │ ← sempre funciona, abre na hora
                     └───────────────┬─────────────────────────────┘
                                     │ coordenada fora da lista?
                                     ▼
                     ┌───────────────────────────────┐      ┌──────┐
                     │ Backend FastAPI (Render free) │ ───▶ │ IRSA │
                     │  cache temporário em disco    │      └──────┘
                     └───────────────────────────────┘
   GitHub Actions (a cada 3 dias) ── roda o mesmo pipeline ──▶ republica o GitHub Pages
```

Há dois caminhos de dados:

| | Backend ao vivo (Render) | Alvos pré-processados (Pages) |
|---|---|---|
| Atende | Qualquer coordenada digitada | 5 alvos de teste + alvos de vitrine |
| Origem do dado | IRSA, no momento da consulta | Processamento feito antes e salvo como arquivo |
| Atualização | **Automática**: toda consulta lê o estado atual do IRSA (respeitando a validade do cache de consultas, ~1 dia) | **Não automática**: é uma "foto" do momento da geração. Quem refaz é o GitHub Actions |
| Por que existe | Cumprir o objetivo do desafio | Abrir instantaneamente e **nunca falhar na demo**: o servidor grátis dorme, o IRSA pode cair e a primeira consulta leva 1–2 min |

O **pipeline Python é um só** (consulta → recorte → alinhamento → soma → PNG/espectro), usado tanto pela API quanto pelo script estático.

## 3. Armazenamento (cache em 3 camadas)

Não usamos banco de dados. Tudo é arquivo:

| Camada | Conteúdo | Tamanho | Validade |
|---|---|---|---|
| `cache/queries/` | Resultado da consulta TAP para uma posição (datas, detectores, URIs), em JSON | poucos KB | ~1 dia (dados novos chegam semanalmente) |
| `cache/exposures/` | Recorte de cada exposição em FITS, sem a extensão PSF: `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI` e a tabela `WCS-WAVE` (comprimento de onda, usada pelo espectro) | ~60 KB cada → ~15 MB por alvo | Permanente (exposições não mudam dentro de um release) |
| `cache/renders/` | PNG por época/detector, diferenças, espectros | poucos KB cada | Até mudar o conjunto de exposições |

O FITS bruto baixado (~4 MB) **é descartado** após a extração. Quase todo o seu tamanho vem da extensão PSF, que não usamos; a imagem útil em 0,1° tem só ~60×60 pixels (pixel de ~6″).

Se no futuro forem necessários metadados consultáveis (ex.: regiões já processadas, favoritos), usar **SQLite**. Fora do MVP.

## 4. Backend ao vivo — Render (free)

Limites do plano gratuito (conferidos em nov/2026):

- **Dorme após 15 min** sem tráfego e leva **~1 min para acordar**.
- **Disco temporário**: perdido ao dormir, reiniciar ou republicar. O cache é só um ganho de desempenho, nunca uma dependência.
- **Pouca memória** (~512 MB).
- 750 horas de instância grátis por mês.

Cuidados:

- Processar exposição por exposição e liberar memória logo.
- Limitar o paralelismo de downloads (~8–16 conexões) e o campo de visão máximo.
- O frontend mostra o progresso com honestidade (*"acordando o servidor / baixando dados da NASA, ~1–2 min na primeira vez"*) e exibe as épocas à medida que ficam prontas.
- Evolução futura: abrir com os dados estáticos e consultar o backend em segundo plano para acrescentar épocas novas.

### 4.1 Como publicar a API

O repositório traz um *blueprint* do Render em [`render.yaml`](../render.yaml):

1. Em <https://dashboard.render.com>: **New → Blueprint** → conectar o repositório `spherex-viewer`.
2. Confirmar o serviço `spherex-viewer-api` (plano *Free*). O Render instala com `uv sync` e inicia com `uvicorn`.
3. Copiar a URL do serviço (ex.: `https://spherex-viewer-api.onrender.com`) e gravá-la na variável `API_BASE` do repositório no GitHub (ver §6.3).
4. Rodar o workflow *Atualizar dados e publicar* (ou esperar o próximo push): o site passa a consultar a API para coordenadas e nomes fora da lista.

Configuração do blueprint, pensada para os 512 MB do plano gratuito:

| Variável | Valor | Motivo |
|---|---|---|
| `SPHEREX_FOV_MAX` | `10` | O pipeline guarda as exposições do campo em memória, e o consumo cresce com o quadrado do campo: ~75 MB em 6′ com 537 exposições, mais de 1 GB em 30′ |
| `SPHEREX_MAX_JOBS` | `1` | Um campo por vez; o segundo pedido recebe `429 BUSY` |
| `SPHEREX_CACHE_DIR` | `/tmp/spherex-cache` | Disco temporário |

O comando de início foi testado localmente num ambiente isolado (`uv run --frozen --no-dev uvicorn api.main:app`). **O deploy no Render em si depende da conta de quem publica.**

## 5. Frontend + dados estáticos — GitHub Pages

### 5.1 Por que GitHub Pages (e não Vercel)

| Critério | GitHub Pages | Vercel (Hobby) |
|---|---|---|
| Custo | Grátis (repo público) | Grátis |
| Integração com o Action | **Nativa**, sem token | Exige Vercel CLI + token como secret |
| Equipe | Todos com acesso ao repo publicam | Hobby é pessoal (membros só no plano pago) |
| Uso | Livre | Somente não comercial |
| Prévia por PR | Não | Sim |
| Redirects/headers | Não | Sim |
| CORS | Liberado por padrão | Configurável |

Os itens em que a Vercel ganha (prévias, redirects, funções) não são necessários: o site é estático, as URLs com coordenadas usam parâmetros de busca (`?ra=…&dec=…`), que funcionam sem rotas especiais, e o backend fica no Render.

### 5.2 Cuidados

- O site fica em subcaminho: `https://<usuario>.github.io/spherex-viewer/`. **Usar caminhos relativos** para assets e dados (ou configurar o `base` do bundler).
- Limites suaves: site ≤ 1 GB, ~100 GB de tráfego/mês. Folgado para nosso volume.
- Os dados gerados **não são commitados**: o Action os gera e publica direto no Pages, sem inchar o histórico do git.

## 6. Atualização automática — GitHub Actions

### 6.1 Funcionamento

A cada 3 dias (o SPHEREx recebe dados semanalmente; o intervalo menor mantém o cache do Actions vivo), o Action:

1. Sobe uma máquina Linux temporária.
2. Faz checkout do código.
3. Instala Python e dependências.
4. Restaura o cache de exposições já baixadas (`actions/cache`).
5. Roda o pipeline para os alvos de `targets.yaml`.
6. Publica frontend + dados no GitHub Pages.
7. Descarta a máquina.

### 6.2 Estrutura no repositório

```
spherex-viewer/
├── targets.yaml                  ← lista de alvos pré-processados
├── pipeline/
│   └── build_static.py           ← processa todos os alvos
├── frontend/                     ← o site (dados gerados vão em frontend/public/data/, fora do git)
└── .github/workflows/
    └── update-data.yml           ← agendamento e deploy
```

`targets.yaml` (coordenadas a confirmar no SIMBAD, exceto WISE 0855):

```yaml
targets:
  - id: wise0855
    name: WISE 0855
    ra: 133.79513
    dec: -7.24515
    fov_arcmin: 6
  - id: barnard
    name: Barnard's Star
    ra: 269.4521
    dec: 4.6934
    fov_arcmin: 6
  # epsindib, rwaur, rdra...
```

### 6.3 Workflow

O workflow real é [`.github/workflows/update-data.yml`](../.github/workflows/update-data.yml). Passos, em ordem:

| Passo | O que faz |
|---|---|
| Restaurar recortes | `actions/cache/restore` em `backend/cache` (recortes do IRSA de execuções anteriores) |
| Processar os alvos | `pipeline.build_static` → `frontend/public/data` (manifesto + campos dos alvos) |
| Guardar recortes | `actions/cache/save` com `if: always()`: os downloads não se perdem se um passo seguinte falhar |
| Validação científica | `pytest -m science`. **Se falhar, o job para aqui e nada é publicado** |
| Relatório | `science-report.xml` salvo como artefato da execução, mesmo em caso de falha |
| Construir o site | `npm ci && npm run build` (o Vite copia `public/data` para `dist/data`), com `VITE_API_BASE` vindo da variável `API_BASE` do repositório |
| Publicar | `upload-pages-artifact` de `frontend/dist` + job `deploy` (só na `main`) |

Gatilhos: a cada 3 dias (`cron: "0 6 */3 * *"`), botão *Run workflow* e push na `main` que altere `backend/`, `frontend/`, `schemas/`, `targets.yaml` ou o próprio workflow (mudanças só de documentação não republicam).

Configuração única no GitHub:

- **Settings → Pages → Source: GitHub Actions**.
- **Settings → Secrets and variables → Actions → Variables → `API_BASE`**: URL da API no Render, sem barra no fim (ex.: `https://spherex-viewer-api.onrender.com`). Opcional: sem ela o site funciona só com os alvos pré-processados.

Simulação local feita em 14/11/2026 com o cache cheio: alvos em 2 min 18 s, validação científica em 2 min 34 s (16 testes), site de 5,4 MB; o site construído abre num subcaminho (`/spherex-viewer/`) sem erros.

### 6.3.1 Quando o IRSA está fora do ar

Em 14/11/2026 a primeira publicação falhou: o serviço TAP do IRSA respondia `502` (sync, async e availability), embora o SIA e os recortes estivessem no ar. Duas defesas saíram disso:

- **Consulta com fallback**: depois de 2 tentativas no TAP, `IrsaArchive.query` refaz a consulta pelo **SIA2** (`/SIA?COLLECTION=…&POS=circle …`), que devolveu exatamente as mesmas exposições. Assim o workflow normal funciona com o TAP fora.
- **Publicação de snapshot** ([`publish-snapshot.yml`](../.github/workflows/publish-snapshot.yml), manual): constrói o site com os dados do branch `data-snapshot`, gerados localmente por `build_static` e validados por `pytest -m science`. Serve para ter o site no ar quando o IRSA inteiro estiver indisponível. A próxima execução bem-sucedida do workflow normal substitui essa publicação.

Para atualizar o snapshot: gerar os dados, rodar a validação científica e regravar o branch `data-snapshot` com o conteúdo de `frontend/public/data`.

### 6.4 Atualização incremental

- O script grava `frontend/public/data/manifest.json` com, por alvo, a data da exposição mais recente e o horário de geração.
- A cada execução, consulta o IRSA. Se não houver exposição nova, reaproveita o resultado anterior. Se houver, baixa **só as novas** (as antigas estão no `actions/cache`) e recalcula as épocas.
- O frontend exibe: *"Dados atualizados em DD/MM/AAAA — inclui imagens até DD/MM/AAAA"*.

### 6.5 Limites

- Repositório público: minutos de Actions ilimitados. Cada execução deve levar ~5–15 min; o limite por job é 6 h.
- O `cron` é em UTC e pode atrasar em horários de pico.
- **Em repositórios públicos, agendamentos são desativados após 60 dias sem commits.** Reativar na aba *Actions* quando necessário.
- **O GitHub apaga caches sem uso há 7 dias.** Com agendamento exatamente semanal o cache pode expirar e forçar o download completo. Por isso o agendamento será **a cada 3 dias** (`cron: "0 6 */3 * *"`).

### 6.6 Tempo de execução (medido)

| Execução | O que baixa | Tempo |
|---|---|---|
| Primeira (cache vazio) | ~1.950 recortes dos 5 alvos (~4 MB cada no download; ~190 KB cada no cache, ~370 MB no total) | ~60 min (medido localmente: 5 a 19 min por alvo) |
| Recorrente (cache cheio) | Consulta TAP + exposições novas | ~1–3 min |
| Validação científica | Nada (usa o cache) | ~2,5 min |

Cada alvo também é publicado num campo de 10′ (`EXTRA_FOVS` em `build_static.py`), para a troca de tamanho no site ser instantânea. O recorte maior tem outra chave no cache, então a primeira execução depois dessa mudança baixa de novo um recorte por exposição (mais ~1.950, ~60 min); depois disso volta ao tempo recorrente.

O download é lento porque o serviço de recortes do IRSA sempre inclui a extensão PSF (~4 MB), descartada depois. Rodar a primeira execução **cedo**, para o cache já estar cheio na avaliação.

### 6.7 Como responde ao desafio

> *"New SPHEREx data is arriving fast! Make sure to design a tool that's easy to update with the latest data releases."*

- Backend ao vivo: sempre consulta o estado atual do arquivo.
- Alvos pré-processados: atualização automática a cada 3 dias, sem intervenção.
- Adicionar alvo: uma linha em `targets.yaml` (qualquer pessoa pode sugerir por Pull Request).
- Novo release: alterar a configuração de coleções, sem mudar código.
- Histórico de cada atualização visível e auditável na aba *Actions*.

## 7. Alternativas descartadas

| Opção | Motivo do descarte |
|---|---|
| Banco de dados para imagens | Desnecessário: imagens são arquivos e o índice é o próprio IRSA |
| Hugging Face Spaces | Plano gratuito para Docker restrito desde ~jul/2026 (relatos no fórum) |
| Fly.io / Railway | Sem plano gratuito permanente |
| Backend em Vercel Functions | Disco temporário, limite de tempo por requisição, cold start com Astropy |
| Vercel para o frontend | Exige token no Action; plano Hobby é pessoal e não comercial |
| Rodar local + túnel | Depende de um computador ligado durante a avaliação |
| Commitar os dados gerados no git | Incharia o histórico a cada semana |
