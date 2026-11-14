# Hospedagem, armazenamento e atualização de dados

Decisões de infraestrutura do projeto. Restrição principal: **tudo deve ser 100% gratuito**.

## 1. Resumo das decisões

| Peça | Decisão | Motivo |
|---|---|---|
| Frontend + alvos pré-processados | **GitHub Pages** | Grátis, publicação nativa pelo GitHub Actions, tudo no mesmo lugar |
| Backend ao vivo (coordenadas quaisquer) | **Render (plano free)** | Único plano gratuito viável para Python + Astropy |
| Atualização dos alvos pré-processados | **GitHub Actions agendado** (semanal) | Grátis em repositório público; atende ao item "fácil de atualizar" do desafio |
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
   GitHub Actions (semanal) ── roda o mesmo pipeline ──▶ republica o GitHub Pages
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
| `cache/exposures/` | Recorte já reduzido de cada exposição: só `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI` + cabeçalho WCS, em `.npz` | ~60 KB cada → ~15 MB por alvo | Permanente (exposições não mudam dentro de um release) |
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

Toda semana (o SPHEREx recebe dados semanalmente), o Action:

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
├── frontend/                     ← o site (dados gerados vão em frontend/data/)
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

### 6.3 Workflow (rascunho)

```yaml
name: Atualizar dados SPHEREx

on:
  schedule:
    - cron: "0 6 * * 1"     # segundas, 06:00 UTC
  workflow_dispatch:         # botão "Run workflow"
  push:
    branches: [main]         # republica quando o código muda

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - uses: actions/cache@v4
        with:
          path: cache/
          key: spherex-cache-${{ github.run_id }}
          restore-keys: spherex-cache-
      - name: Processar alvos
        run: python -m pipeline.build_static --targets targets.yaml --out frontend/data
      - name: Validação científica (bloqueia publicação, ver 06-testes.md)
        run: pytest -m science --data frontend/data --report science-report.json
      - uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Configuração única no GitHub: **Settings → Pages → Source: GitHub Actions**.

### 6.4 Atualização incremental

- O script grava `frontend/data/manifest.json` com, por alvo, a data da exposição mais recente e o horário de geração.
- A cada execução, consulta o IRSA. Se não houver exposição nova, reaproveita o resultado anterior. Se houver, baixa **só as novas** (as antigas estão no `actions/cache`) e recalcula as épocas.
- O frontend exibe: *"Dados atualizados em DD/MM/AAAA — inclui imagens até DD/MM/AAAA"*.

### 6.5 Limites

- Repositório público: minutos de Actions ilimitados. Cada execução deve levar ~5–15 min; o limite por job é 6 h.
- O `cron` é em UTC e pode atrasar em horários de pico.
- **Em repositórios públicos, agendamentos são desativados após 60 dias sem commits.** Reativar na aba *Actions* quando necessário.

### 6.6 Como responde ao desafio

> *"New SPHEREx data is arriving fast! Make sure to design a tool that's easy to update with the latest data releases."*

- Backend ao vivo: sempre consulta o estado atual do arquivo.
- Alvos pré-processados: atualização automática semanal, sem intervenção.
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
