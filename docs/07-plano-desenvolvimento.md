# Plano de desenvolvimento

Como o projeto será construído: fases, ordem das tarefas, marcos de entrega e fluxo de trabalho com git. Baseado em [06-testes.md](06-testes.md) (TDD) e [04-api.md](04-api.md) (contratos).

## 1. Método

- **Fatias verticais com TDD**: um teste falhando → código mínimo para passar → commit → próxima fatia. Detalhes em [06-testes.md](06-testes.md).
- **Prioridade por risco**: primeiro o que pode inviabilizar o projeto (pipeline científico com dados reais), depois a interface, depois os extras.
- **Docs sempre em dia**: se a implementação mudar algo de API, arquitetura ou dados, o documento correspondente muda no mesmo PR.

## 2. Fases

### Fase 0 — Preparação (~30 min)

Branch: `fase-0/preparacao`

- [x] Estrutura do repositório: `backend/`, `frontend/`, `schemas/`
- [x] Backend: `pyproject.toml` (astropy, numpy, reproject, fastapi, httpx, pytest)
- [x] pytest com marcadores `live` e `science` desligados por padrão
- [x] Workflow `test.yml`: testes rápidos em todo push e PR
- [x] Confirmar no SIMBAD coordenadas, movimento próprio e época de referência dos 5 alvos (movido para a fase 2)
- [x] Criar `targets.yaml` (movido para a fase 2)

> A fase 0 foi feita no início do branch `fase-1/pipeline`.

### Fase 1 — Pipeline científico (dados sintéticos)

Branch: `fase-1/pipeline`. É a parte de maior risco, por isso vem primeiro.

- [x] `SyntheticArchive` + estrela parada em 2 épocas → estrela no pixel central do quadro
- [x] Apontamentos com rotação/deslocamento diferentes → estrela no mesmo pixel (alinhamento)
- [x] Estrela que anda 2 px → deslocamento detectado
- [x] Agrupamento de épocas; épocas sem algum detector
- [x] Subtração da luz zodiacal, máscara de flags, soma ponderada por variância, contraste comum entre épocas
- [x] Erro `NoCoverage` e grade no tamanho do contrato da API

> O cenário de espectro sintético de [06-testes.md](06-testes.md) fica para a fase 6 (extra *espectro sob demanda*).

### Fase 2 — Dados reais

Branch: `fase-2/dados-reais`

- [x] `IrsaArchive` com respostas reais gravadas do WISE 0855 (258 exposições, 4 grupos)
- [x] Download paralelo + cache em disco
- [x] **🎯 Marco 1:** WISE 0855 real processado de ponta a ponta, com a anã marrom andando entre épocas
- [x] Calibrar e registrar as tolerâncias da validação científica em [06-testes.md](06-testes.md)
- [x] Validação científica dos 5 alvos (`pytest -m science`)
- [x] Extras forçados pelos dados reais: flags em dois níveis e núcleo saturado, interpolação normalizada, fundo residual, exposição indisponível pulada, novas tentativas em `503`

### Fase 3 — Saídas e API

Branch: `fase-3/api`

- [x] Gerar `field.json` + `.f32` / `.png`, validados pelos JSON Schemas
- [x] `build_static`: gera `data/` dos alvos. **A partir daqui o frontend pode ser feito sem backend no ar**
- [x] API FastAPI: `/field` assíncrono (202 → 200), `/resolve`, `/config`, `/health`, erros, CORS
- [x] Extras: `default_detector` por alvo, miniatura na época mais recente com ≥ 3 exposições, máscara (saturado/baixa qualidade) no lugar de `flags.u32`

### Fase 4 — Frontend

Branch: `fase-4/frontend`

- [x] `viewer-core` com TDD: decodificar `.f32`, esticamento, diferença, soma, estado na URL
- [x] Interface: entrada de coordenadas, botões dos alvos, player, blink, diferença, seletor de detector
- [x] **🎯 Marco 2:** site funcionando com os dados estáticos, ou seja, **MVP entregável**
- [x] Extras: direção visual "Placas do comparador" (PRODUCT.md, `.impeccable/surfaces/`), zoom 1×/2×/4×, contraste, negativo/positivo, régua do tempo proporcional às datas, busca por nome/RA-Dec via API opcional, copiar link, embed

### Fase 5 — Publicação

Branch: `fase-5/deploy`

- [ ] Workflow `update-data.yml`: pipeline → validação científica → GitHub Pages
- [ ] Deploy da API no Render
- [ ] Frontend usando a API para coordenadas fora da lista

### Fase 6 — Extras

Branch: `fase-6/<extra>` (um branch por extra, pois são independentes). Em ordem de valor para os jurados:

1. [ ] Espectro sob demanda
2. [ ] Aladin Lite com Gaia/WISE + marcador de posição prevista
3. [ ] Overlay de flags de contaminação
4. [ ] Falsa cor (3 detectores)
5. [ ] Campo de visão variável
6. [ ] Modo embed
7. [ ] Roteiro do pitch (`docs/11-apresentacao.md`) com os resultados da validação científica

## 3. Prioridade se o tempo apertar

Os dois marcos garantem a entrega:

| Marco | Garante |
|---|---|
| 🎯 1 — WISE 0855 real andando | O núcleo científico funciona com dados reais |
| 🎯 2 — Site com dados estáticos | O objetivo obrigatório do desafio está cumprido |

Ordem de corte se faltar tempo: extras da fase 6 (de baixo para cima) → backend ao vivo no Render → atualização automática. Um site no GitHub Pages com os 5 alvos já atende ao desafio.

## 4. Divisão em equipe

As fases 1–3 (backend) e 4 (frontend) podem andar **em paralelo** a partir do início da fase 1: um `field.json` de exemplo, válido pelo JSON Schema, é gerado logo cedo e serve de dado falso para o frontend até a fase 3 entregar os dados reais. O contrato entre os dois lados é o [04-api.md](04-api.md) + `schemas/`.

## 5. Fluxo de git

### 5.1 Branches

- `main` sempre estável: só recebe código por **Pull Request**.
- **Um branch por fase**, criado a partir da `main` atualizada:

```
fase-0/preparacao
fase-1/pipeline
fase-2/dados-reais
fase-3/api
fase-4/frontend
fase-5/deploy
fase-6/espectro, fase-6/aladin, ...
```

- Mudanças só de documentação fora de uma fase: `docs/<assunto>`.
- Correções urgentes: `fix/<assunto>`.

### 5.2 Commits

- Pequenos, um por fatia de TDD (teste + código mínimo).
- Mensagem em português, no formato `tipo: descrição`:

| Tipo | Uso |
|---|---|
| `feat` | Funcionalidade nova |
| `test` | Só testes |
| `fix` | Correção |
| `docs` | Documentação |
| `refactor` | Reorganização sem mudar comportamento |
| `chore` | Configuração, dependências, CI |

- **Sem linha de coautoria do Claude** (`Co-Authored-By`).

### 5.3 Pull Requests

- Um PR por fase (ou por extra na fase 6), aberto contra a `main`.
- Pode ser aberto cedo como **rascunho (draft)** para acompanhar o andamento.
- Descrição do PR:
  - o que a fase entrega (checklist da seção 2);
  - como testar (comandos);
  - resultados relevantes (ex.: imagens do Marco 1, números da validação científica);
  - docs atualizados.
- **Critérios para merge:**
  - testes rápidos passando no `test.yml`;
  - docs atualizados se algum contrato mudou;
  - revisão de outra pessoa da equipe quando houver.
- **Merge com "Create a merge commit"**, preservando os commits de cada fatia (o histórico de TDD). Depois do merge, apagar o branch.
- Sem linha de geração/coautoria do Claude na descrição.

### 5.4 Ciclo de uma fase

```bash
git switch main && git pull
git switch -c fase-1/pipeline
# ciclos de TDD: teste falha → código → teste passa → commit
git push -u origin fase-1/pipeline
gh pr create --base main --title "Fase 1: pipeline científico" --body "..."
# revisão → merge → apagar branch
```
