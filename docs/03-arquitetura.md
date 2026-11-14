# Arquitetura técnica

Este documento explica, passo a passo, o que acontece desde que o usuário digita uma coordenada até a animação aparecer na tela. Para a visão geral do desafio, ver [01-projeto.md](01-projeto.md).

## 1. Visão geral

```
 Usuário  →  Site (frontend)  →  Nosso servidor (backend)  →  Arquivo da NASA (IRSA)
                     ↑                        │
                     └──── imagens prontas ───┘
```

São três peças:

1. **IRSA**: arquivo público da NASA/Caltech onde ficam as imagens do SPHEREx. Não é nosso; apenas consumimos.
2. **Backend**: programa em Python que roda num servidor. Busca as imagens, processa e entrega prontas.
3. **Frontend**: o site no navegador. Mostra a animação, os controles e os gráficos.

## 2. Fluxo passo a passo

### Passo 1 — Usuário informa a posição

Exemplo, WISE 0855: `RA 08h55m10.8s, Dec -07°14'42"`.

- O frontend converte para graus decimais (`133.795, -7.245`).
- O estado vai para a URL (`?ra=133.795&dec=-7.245&fov=6&det=6`), o que torna o link compartilhável e incorporável.
- O frontend chama o backend pedindo as épocas daquela posição.

### Passo 2 — Backend consulta quais imagens existem

O IRSA oferece um serviço **TAP** que aceita consultas em **ADQL** (parecido com SQL):

```sql
SELECT p.energy_bandpassname, p.time_bounds_lower, a.uri
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', 133.79513, -7.24515), p.poly)
```

Endpoint: `https://irsa.ipac.caltech.edu/TAP/sync` (`LANG=ADQL`, `FORMAT=csv`).

Cada linha do resultado traz:

- **data** da exposição, em MJD (Modified Julian Date; ex.: `60801.51` = 14/05/2025);
- **detector**, de `SPHEREx-D1` a `SPHEREx-D6`;
- **caminho** do arquivo FITS.

Teste em WISE 0855: **258 imagens** entre mai/2025 e mai/2026.

### Passo 3 — Baixar só o recorte (cutout)

Cada imagem original tem 2040×2040 pixels (~3,5° × 3,5° de céu). Pedimos ao IRSA só um recorte em volta do alvo, anexando parâmetros ao caminho:

```
https://irsa.ipac.caltech.edu/<uri>?center=133.79513,-7.24515d&size=0.1
```

**Problema medido:** cada recorte de 0,1° leva **~6 s** e pesa **~4 MB**, porque vem com todas as extensões. São 258 × 4 MB ≈ 1 GB, ou ~25 min se fosse sequencial.

**Soluções no backend:**

- **Download paralelo** (ex.: 16–32 conexões simultâneas).
- **Cache em disco**: a mesma posição e o mesmo campo de visão nunca são baixados duas vezes.
- **Carregamento progressivo**: o frontend mostra as épocas à medida que ficam prontas.
- **Pré-carga dos 5 alvos de teste** antes da apresentação; também funciona como modo offline se o IRSA cair.

### Passo 4 — Processar as imagens

Cada arquivo é um **FITS** multiextensão (formato padrão da astronomia: matrizes de números + cabeçalhos):

| Extensão | Conteúdo | Uso |
|---|---|---|
| `IMAGE` | Brilho de cada pixel (MJy/sr) | A imagem em si |
| `ZODI` | Modelo do brilho de fundo da poeira do Sistema Solar (luz zodiacal) | Subtraído da imagem |
| `FLAGS` | Bitmap de defeitos por pixel (pixel quente, fantasma de estrela brilhante, etc.) | Máscara / overlay |
| `VARIANCE` | Ruído de cada pixel | Peso na soma e barras de erro |
| `WCS-WAVE` | Comprimento de onda de cada pixel | Espectro |
| `PSF` | Forma de uma estrela pontual no detector | Uso futuro (fotometria) |

O processamento usa **Astropy**:

**4a. Agrupar em épocas.** As exposições vêm em rajadas: várias imagens do mesmo lugar em poucos dias, e a próxima visita só ~6 meses depois. Agrupamos exposições próximas no tempo (ex.: separação < 10 dias) em uma **época**, por detector.

**4b. Alinhar (reprojetar).** Cada exposição foi feita com apontamento e rotação ligeiramente diferentes. Usando o **WCS** de cada arquivo (o mapeamento pixel ↔ coordenada do céu, com distorção SIP), reprojetamos todas para uma **grade comum** centrada na posição pedida (`reproject`). Assim a mesma estrela cai no mesmo pixel em todos os quadros; sem isso a animação "treme".

**4c. Somar (coadd).** Dentro de cada época e detector, fazemos a média ponderada pelo inverso da variância, ignorando pixels com flags ruins. Isso reduz o ruído e revela objetos fracos.

**4d. Contraste consistente.** Aplicamos um esticamento não linear (ex.: `asinh` ou log) com **os mesmos limites para todas as épocas**. Caso contrário a animação pisca por mudança de contraste e não por mudança real no céu.

**4e. Gerar PNG** e enviar ao navegador.

### Passo 5 — Visualização no frontend

- **Animação:** as épocas em loop, com play/pause, velocidade e datas.
- **Blink:** alterna entre duas épocas escolhidas, a técnica clássica que levou à descoberta de Plutão.
- **Diferença:** o backend calcula `época B − época A`. O que ficou parado se cancela (fundo cinza); o que se moveu aparece como um par escuro/claro (posição antiga/nova); o que variou de brilho fica todo claro ou todo escuro.
- **Seleção de detector:** de D1 (0,75 µm) a D6 (5 µm). Anãs marrons frias como a WISE 0855 quase não aparecem em D1 e brilham em D6.
- **Campo de visão:** o usuário escolhe o tamanho do recorte. Um campo maior pega objetos rápidos, mas o download é mais lento.

### Passo 6 — Recursos extras

**Espectro sob demanda.** O SPHEREx usa filtros de variação linear (LVF): cada linha do detector mede um comprimento de onda diferente. Como o céu passa por posições diferentes do filtro a cada exposição, o mesmo ponto acaba medido nas **102 bandas**. Para um ponto clicado:

1. Em cada exposição, converte-se RA/Dec → pixel (WCS principal).
2. Lê-se o brilho naquele pixel (fotometria de abertura, descontando o fundo) e sua variância.
3. Lê-se o comprimento de onda daquele pixel (WCS espectral, chave `W`, tabela `WCS-WAVE`).
4. Plota-se **fluxo × comprimento de onda** com barras de erro.

O resultado é a "impressão digital" do objeto, com bandas de água, metano, CO₂, CO etc.

**Aladin Lite.** É um painel com a mesma região sobreposta aos catálogos do **Gaia DR3** e do **AllWISE/CatWISE**. Responde à pergunta "esse ponto já é conhecido?".

**Movimento próprio.** Para estrelas de alto movimento próprio (Barnard's Star ≈ 10″/ano), propagamos a posição do Gaia até a data de cada época e desenhamos um marcador da posição prevista.

## 3. Endpoints do backend

A especificação completa está em [04-api.md](04-api.md). Resumo: o backend processa um **campo** de forma assíncrona (`GET /api/v1/field`, com progresso) e entrega os quadros de cada época/detector como matrizes float32. Contraste, blink, diferença e soma são feitos **no navegador**, sem novas requisições. Também há endpoints de espectro, PNG, FITS e resolução de nomes.

## 4. Tecnologias

| Parte | Tecnologia | Motivo |
|---|---|---|
| Backend | **Python + FastAPI** | Ecossistema astronômico é Python; FastAPI é simples e assíncrono |
| Processamento | **Astropy, reproject, numpy** | Padrão para FITS, WCS, coordenadas e tempo |
| Acesso a dados | **TAP/ADQL + cutouts do IRSA** (opcional: `astroquery`) | Já testado e funcionando |
| Download | `httpx` assíncrono | Paralelismo de cutouts |
| Cache | Disco local (chave = URI + centro + tamanho) | Simples, suficiente para o hackathon |
| Frontend | HTML/JS (eventualmente React) | Player, blink, diferença, gráficos |
| Mapa do céu | **Aladin Lite v3** (CDS) | Contexto e overlays Gaia/WISE |
| Gráfico de espectro | Biblioteca JS de gráficos (a definir) | Fluxo × λ com erro |

## 5. Atualização com novos releases

As coleções/releases do SPHEREx (`spherex_dr1`, `spherex_qr3`, ...) ficam em **configuração**, não fixas no código. Como a consulta TAP sempre lê o estado atual do arquivo, novas semanas de dados aparecem automaticamente no backend ao vivo; um novo release é só uma linha de configuração.

Hospedagem, cache e a atualização semanal dos alvos pré-processados (GitHub Pages + Render + GitHub Actions) estão em [05-hospedagem.md](05-hospedagem.md).

## 6. Pontos críticos

1. **Velocidade de download**: paralelismo, cache e pré-carga.
2. **Alinhamento**: se falhar, a animação perde sentido. Validar com estrelas de campo, que devem ficar perfeitamente paradas.
3. **Pixel grande (~6″)**: Barnard's Star anda ~1,5–2 pixels por semestre. É visível, mas sutil; a imagem de diferença e o marcador de posição prevista ajudam muito.
4. **Fontes brilhantes**: geram fantasmas e saturação. Usar as FLAGS para avisar o usuário.

## 7. Decisões de implementação do pipeline

Decisões tomadas durante a implementação (fases 1 e 2), várias forçadas pelos dados reais. Código em `backend/pipeline/`.

| Decisão | Motivo | Onde |
|---|---|---|
| O pipeline recebe um **adaptador de arquivo** (`Archive`: `query` + `fetch_cutout`) | Testar a ciência com dados sintéticos; trocar IRSA por cache/arquivo gravado sem mudar o pipeline | `archive.py` |
| Recorte pedido com **1,5 × o campo** | Com o detector girado, o recorte precisa cobrir a diagonal do campo (√2 ≈ 1,41) | `field.py` |
| **Interpolação normalizada** na reprojeção (imagem e mapa de pixels válidos reprojetados e divididos) | A bilinear comum espalhava cada pixel mascarado para ~4 vizinhos: com dados reais só 91,6% do quadro ficava válido | `field.py` |
| Flags em **dois níveis**: graves (`1, 6, 9, 10, 11`) sempre excluídos; suspeitos (`0, 2, 15, 19`) excluídos só se outra exposição tiver o ponto limpo, senão usados e marcados em `Frame.low_quality` | Na Barnard's Star real, TODAS as exposições marcam o anel da estrela com TRANSIENT/SUR_ERROR, mas os valores são bons. Mascarar deixava um buraco 3×3 e erro de posição de 1–3 px; com dois níveis o erro cai para 0,11–0,18 px | `field.py` |
| Valor "limpo" de uma exposição só onde **nenhum** pixel suspeito entra na interpolação | Senão o pixel de borda usaria só os vizinhos limpos, mais fracos (asa da estrela), e subestimaria o brilho | `field.py` |
| Núcleo sem dado (`IMAGE` = NaN com OVERFLOW) marcado em `Frame.saturated` | O SPHEREx não entrega o núcleo de estrelas muito brilhantes; o frontend deve pintá-lo com o brilho máximo, não como buraco | `field.py` |
| Soma ponderada por **1/variância**, com variância propagada | Exposições mais ruidosas pesam menos; a variância do quadro alimenta o espectro e o S/R | `field.py` |
| **Fundo residual removido** de cada quadro (mediana com corte sigma 3σ), valor guardado em `Frame.background` | No WISE 0855 real, um desnível de fundo entre épocas (resíduo da luz zodiacal) dominava a imagem de diferença em D1 | `field.py` |
| Contraste: `vmin` = percentil 1, `vmax` = **máximo**, comum a todas as épocas | Variáveis brilhantes (R Dra) não podem saturar, senão a variação some | `field.py` |
| **4 downloads simultâneos**, 6 tentativas com espera exponencial (2–32 s) | O IRSA responde `503 Server busy` mesmo com 2 pedidos simultâneos | `field.py`, `irsa.py` |
| **Exposição indisponível é pulada** e listada em `Field.failed_exposures`; o campo só falha se nenhuma exposição vier | Um único `503` persistente derrubou um campo de 258 exposições | `field.py` |
| Extensão **EPSF descartada** ao ler o recorte | ~4 MB por recorte, não usada | `irsa.py` |
| Cache em disco: recortes permanentes, consultas por 24 h, escrita atômica | Reprocessar sem baixar de novo; dados novos chegam semanalmente | `cache.py` |
| Centro dos alvos = posição **propagada pelo movimento próprio** | O WISE 0855 está ~3,4′ a oeste da coordenada da designação (2010) | `targets.py`, `targets.yaml` |
