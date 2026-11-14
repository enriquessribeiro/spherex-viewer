# Resultados

Resultados obtidos com **dados reais** do SPHEREx durante o desenvolvimento. Serve de registro científico do projeto e de material para a apresentação.

## Marco 1 — WISE 0855 real andando (14/11/2026)

### Configuração

| Item | Valor |
|---|---|
| Campo | RA 133,79513°, Dec −7,24515° (coordenada do desafio), 6′ × 6′ (59 × 59 px) |
| Dados | `spherex_dr1`, 258 exposições, nenhuma falhou |
| Processamento | ~5 min com 4 downloads simultâneos (o IRSA respondeu `503` várias vezes; resolvido com novas tentativas) |
| Posição prevista | SIMBAD (J2000) propagada pelo movimento próprio: μα* = −8123,7 mas/ano, μδ = +673,2 mas/ano |

Épocas encontradas (exposições por detector):

| Época | Início | D1 | D2 | D3 | D4 | D5 | D6 |
|---|---|---|---|---|---|---|---|
| 1 | 05/05/2025 | 4 | 8 | 3 | 4 | 8 | 3 |
| 2 | 31/10/2025 | 18 | 19 | 18 | 18 | 19 | 18 |
| 3 | 11/12/2025 | — | 6 | 3 | — | 6 | 3 |
| 4 | 21/04/2026 | 14 | 15 | 21 | 14 | 15 | 21 |

### Astrometria em D6 (4,4–5,0 µm)

Centroide medido no quadro × posição prevista pelo movimento próprio:

| Época | MJD médio | Erro | Erro (px) | Sinal/ruído do pico |
|---|---|---|---|---|
| 1 | 60800,7 | 1,7″ | 0,28 | 2,4 |
| 2 | 60991,5 | 0,8″ | 0,13 | 9,6 |
| 3 | 61021,6 | 0,8″ | 0,13 | 6,1 |
| 4 | 61157,9 | 1,8″ | 0,29 | 18,9 |

- Deslocamento entre as épocas 1 e 4: **1,07 px medido × 1,29 px previsto** (~8″ em ~1 ano).
- Nos detectores D1–D4 o WISE 0855 **não aparece**, como esperado para um objeto a ~285 K, que só emite no infravermelho mais longo.
- Uma **estrela de fundo** a ~1,8 px do WISE 0855 aparece em D1–D4 e fica **parada** entre as épocas (variação ≤ 0,3 px). É a prova do alinhamento com dados reais.

![Zoom no WISE 0855: D6 épocas 2 e 4 (anã marrom se move para a direita/oeste), D1 épocas 2 e 4 (só a estrela de fundo, parada). A mira vermelha é fixa.](img/marco1-wise0855-zoom.png)

*Zoom 17 × 17 px. Da esquerda para a direita: D6 época 2, D6 época 4, D1 época 2, D1 época 4. Mira vermelha fixa no mesmo pixel.*

![Painel: linha de cima D1 (épocas 1, 2 e 4 + diferença), linha de baixo D6 (épocas 1–4 + diferença). Círculo = posição prevista do WISE 0855.](img/marco1-wise0855-painel.png)

Animação em D6: [`img/marco1-wise0855-D6.gif`](img/marco1-wise0855-D6.gif).

### Lições para o produto

| Observação | Consequência |
|---|---|
| O movimento é sutil (~1,3 px/ano) | Zoom, blink e mira fixa são essenciais no frontend |
| A diferença D1 (última − primeira) fica dominada por um desnível de fundo entre épocas (resíduo da luz zodiacal) | Subtrair o **fundo local** de cada quadro antes de exibir/diferenciar |
| A época 1 tem só 3 exposições em D6 (S/R 2,4); a diferença com ela vira ruído | A diferença padrão deve usar as **épocas com mais sinal**, não necessariamente a primeira e a última |
| Anãs marrons frias só aparecem em D5–D6 | Abrir em **D6** por padrão; explicar no site por que o objeto "some" nos outros detectores |
| O IRSA fica ocupado (`503`) por dezenas de segundos | Novas tentativas com espera de até ~1 min; exposição que falha é pulada e registrada |
