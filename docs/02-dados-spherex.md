# Dados do SPHEREx

Referência sobre os dados da missão SPHEREx: o que existe, como está organizado, como acessar e o que isso implica para o projeto. Informações conferidas na documentação oficial do IRSA e em consultas reais ao arquivo em **14/11/2026**.

## 1. A missão em números

| Item | Valor |
|---|---|
| Lançamento | Março de 2025 |
| Início das observações científicas | Maio de 2025 |
| Duração nominal | 25 meses |
| Cobertura | Céu inteiro, **um levantamento (*survey*) a cada ~6 meses** |
| Faixa espectral | 0,75 – 5,0 µm (infravermelho próximo) |
| Canais espectrais | 102 |
| Detectores | 6 (2040 × 2040 pixels cada) |
| Tamanho do pixel | **6,15″** |
| Tempo de exposição | ~113,6 s |
| Regiões profundas | *Deep Fields* perto dos polos eclípticos, observados muito mais vezes |

**Levantamentos:** Surveys 1 e 2 no primeiro ano (mai/2025 – mai/2026) e Surveys 3 e 4 no segundo ano (a partir de 16/05/2026).

### 1.1 Detectores e faixas

Cada detector tem um filtro de variação linear (LVF): o comprimento de onda muda ao longo da imagem (mais curto no topo, mais longo embaixo). Uma única exposição de um detector registra, ao mesmo tempo, várias "cores" em posições diferentes do campo.

| Detector | Faixa (µm) | Resolução R | Bom para |
|---|---|---|---|
| D1 | 0,75 – 1,09 | 39 | Estrelas comuns |
| D2 | 1,10 – 1,62 | 41 | Estrelas, banda de água |
| D3 | 1,63 – 2,41 | 41 | Anãs frias (metano em ~2,2 µm) |
| D4 | 2,42 – 3,82 | 35 | Gelo de água (~3 µm), metano (~3,3 µm) |
| D5 | 3,83 – 4,41 | 112 | CO₂ (~4,27 µm) |
| D6 | 4,42 – 5,00 | 128 | CO (~4,67 µm); **anãs marrons frias brilham aqui** |

Como o céu cai em posições diferentes do filtro a cada apontamento, o mesmo ponto acaba medido nas 102 bandas depois de várias exposições. É isso que permite montar o espectro.

## 2. Releases

| Release | Conteúdo | Disponível | Situação |
|---|---|---|---|
| QR1 | Spectral Images (Quick Release) | jul/2025 | **Removido** em fev/2026 |
| QR2 | QR1 reprocessado + novos dados | out/2025 | **Substituído**; só download direto até fev/2027; não aparece em buscas |
| **QR3** | Surveys 3 e 4 (ano 2), semanal | desde set/2026 | **Atual** |
| **DR1** | Surveys 1 e 2 (ano 1) reprocessados + All-Sky Cube | nov/2026 | **Atual** |
| HRSC V1 | Catálogo de fontes de alta confiabilidade | ago/2027 (previsto) | — |
| DR2 + HRSC V2 | — | dez/2027 (previsto) | — |

**Regra:** usar **DR1 + QR3**. Não misturar com QR2 (a calibração mudou).

### 2.1 Coleções (nomes usados nas consultas)

Contagem de observações no TAP em 14/11/2026:

| Coleção | Conteúdo | Observações |
|---|---|---|
| `spherex_dr1` | DR1, levantamento amplo (Wide) | 158.884 |
| `spherex_dr1_deep` | DR1, Deep Fields | 39.401 |
| `spherex_dr1_cube` | DR1, All-Sky Cube (via SIA) | — |
| `spherex_dr1_cal` | Arquivos de calibração DR1 | 20 |
| `spherex_qr3` | QR3, levantamento amplo | 60.574 |
| `spherex_qr3_deep` | QR3, Deep Fields | 14.508 |

## 3. Produtos de dados

### 3.1 Spectral Image (Level 2): o produto principal

Uma exposição gera **6 arquivos**, um por detector (às vezes faltam alguns). Cada arquivo é um FITS multiextensão (MEF) de **~65–70 MB**.

| HDU | Nome | Conteúdo | Unidade |
|---|---|---|---|
| 1 | `IMAGE` | Brilho superficial calibrado. **Luz zodiacal não subtraída** | MJy/sr |
| 2 | `FLAGS` | Bitmap de flags por pixel | — |
| 3 | `VARIANCE` | Variância por pixel | (MJy/sr)² |
| 4 | `ZODI` | Modelo da luz zodiacal (para subtrair) | MJy/sr |
| 5 | `EPSF` (DR1/QR3) / `PSF` (QR2) | PSFs efetivas por zona do detector (21×21 zonas; D3 usa 11×41), 33×33 px, superamostradas 5× | — |
| 6 | `WCS-WAVE` | Tabela pixel → comprimento de onda central e largura de banda | µm |

O cabeçalho de `IMAGE` contém três WCS:

- **Principal**: pixel ↔ RA/Dec, com distorção SIP, pixels contados a partir de 1.
- **`A`**: o mesmo, com pixels contados a partir de 0.
- **`W`**: pixel ↔ comprimento de onda, via tabela `WCS-WAVE`. Desligar SIP ao usar (`spectral_wcs.sip = None`).

> ⚠️ A documentação diz que `WCS-WAVE` é **para visualização**. Para ciência, o recomendado são as camadas `CWAVE`/`CBAND` do produto de calibração *Spectral WCS*. Para o nosso espectro sob demanda, `WCS-WAVE` basta; citar isso como limitação.

#### Convenção de nome do arquivo

`level2_2025W19_1B_0241_1D1_spx_l2b-v27-2026-197.fits`

| Trecho | Significado |
|---|---|
| `level2` | Nível do produto |
| `2025W19_1B` | Período de planejamento (~3,5 dias de levantamento); semana 19 de 2025 |
| `0241` | Contador de *large slew* (grande reapontamento) |
| `1` | Contador de *small slew* (1–4 por large slew) |
| `D1` | Detector |
| `v27` | Versão do arquivo |
| `2026-197` | Data de processamento (ano-dia do ano) |

Exposições com o mesmo `large slew` e `small slew` diferentes são tiradas em sequência de minutos, uma ao lado da outra.

#### Flags (bits do `FLAGS`)

Lista **conferida no cabeçalho de recortes reais do DR1** (`MSKNnnnn` = nome, `MSKDnnnn` = descrição). Definição completa na Tabela 16 do *Explanatory Supplement*.

| Bit | Nome | Significado | Tratamento no projeto |
|---|---|---|---|
| 0 | TRANSIENT | Transiente detectado durante a leitura | Mascarar |
| 1 | OVERFLOW | Estouro na leitura | Mascarar |
| 2 | SUR_ERROR | Erro no processamento a bordo | Mascarar |
| 6 | NONFUNC | Pixel permanentemente inutilizável | Mascarar |
| 7 | DICHROIC | Baixa eficiência por causa do dicroico | Manter (calibrado) |
| 9 | MISSING_DATA | Dado perdido a bordo | Mascarar |
| 10 | HOT | Pixel quente | Mascarar |
| 11 | COLD | Sinal anormalmente baixo | Mascarar |
| 12 | FULLSAMPLE | Histórico completo de amostras disponível | Informativo |
| 14 | PHANMISS | Correção de "phantom" não aplicada | Manter |
| 15 | NONLINEAR | Correção de não linearidade não confiável (saturação) | Mascarar |
| 17 | PERSIST | Carga residual de exposição anterior | **Overlay**: pode simular um objeto que "apareceu" |
| 19 | OUTLIER | Pixel atípico | Mascarar |
| 20 | CROSSTALK | Afetado por crosstalk | Overlay |
| 21 | SOURCE | Pixel sobre uma fonte conhecida (~37% dos pixels) | **Não** mascarar (marca estrelas) |
| 22 | GHOST | Fantasma de fonte brilhante na exposição | Overlay |
| 23 | GHOST_FPA | Fantasma de fonte brilhante em outro detector | Overlay |
| 24 | GHOST_EXT | Fantasma de fonte brilhante fora do campo | Overlay |
| 25 | STREAK | Rastro | Overlay |
| 26 | BLOOM | Artefato de "bloom" | Overlay |
| 27 | SNOWBALL | Artefato "snowball" (raio cósmico) | Overlay |
| 28 | HALO | Halo transiente | Overlay |

Bits mascarados no pipeline: `0, 1, 2, 6, 9, 10, 11, 15, 19`.

### 3.2 All-Sky Cube (só DR1)

Um cubo do céu inteiro combinando todas as exposições do ano 1:

- 12.288 blocos HEALPix (ordem 5, NESTED), ~1,8° × 1,8° cada;
- 512 × 512 pixels de **12,9″**, **102 canais**;
- **luz zodiacal já subtraída**;
- extensões `IMAGE`, `NHITS`, `FLAGS`, `SPECTRAL_CHANNELS`, `WCS-WAVE`;
- versão HiPS em PNG para visualização (esticamento fixo 0–40 MJy/sr), que pode ser carregada direto no **Aladin Lite**.

Problemas conhecidos: canais 51 e 52 vazios; listras por linhas atmosféricas (He em 1,083 µm).

**Uso no projeto:** não serve para ver movimento (combina o ano inteiro num único quadro), mas é ótimo como **imagem de referência/contexto** e como camada colorida no Aladin.

### 3.3 Produtos de calibração úteis

| Produto | Uso potencial |
|---|---|
| Spectral WCS (`CWAVE`, `CBAND`) | Comprimento de onda preciso por pixel |
| Nonfunctional Pixels | Máscara de pixels mortos |
| Solid Angle Pixel Map | Converter MJy/sr → fluxo por pixel (fotometria) |
| Flux Corrections | Combinar QR2 com QR3 (evitamos) |

## 4. Como acessar

> **Importante:** o TAP do IRSA **não envia cabeçalhos CORS** (testado). O navegador não consegue consultar o IRSA diretamente, o que confirma a necessidade do backend.

### 4.1 TAP (ADQL): usado pelo projeto

- Endpoint: `https://irsa.ipac.caltech.edu/TAP/sync`
- Parâmetros: `QUERY=<adql>`, `LANG=ADQL`, `FORMAT=csv` (ou `votable`, `json`)
- Tabelas (modelo CAOM): `spherex.observation` → `spherex.plane` → `spherex.artifact` (também `spherex.obscore`)

| Tabela | Colunas úteis |
|---|---|
| `spherex.observation` | `obsid`, `collection`, `observationid` |
| `spherex.plane` | `planeid`, `obsid`, `energy_bandpassname` (`SPHEREx-D1`…`D6`), `time_bounds_lower`/`upper` (MJD), `time_exposure` (s), `energy_bounds_lower`/`upper` (m), `position_samplesize` (″), `poly` (contorno no céu), `quality_flag`, `metrics_maglimit` |
| `spherex.artifact` | `planeid`, `uri` (caminho do arquivo), `producttype`, `contentlength` (bytes) |

Consulta de referência (todas as exposições sobre uma posição, com coleção e detector):

```sql
SELECT o.collection, p.energy_bandpassname AS detector,
       p.time_bounds_lower AS mjd, a.uri
FROM spherex.plane p
JOIN spherex.observation o ON p.obsid = o.obsid
JOIN spherex.artifact a    ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', 133.79513, -7.24515), p.poly)
  AND o.collection IN ('spherex_dr1', 'spherex_qr3')
  AND a.producttype = 'science'
ORDER BY p.time_bounds_lower
```

A lista de coleções deve vir da **configuração** do projeto, não do código.

### 4.2 Cutouts (recortes): usado pelo projeto

Anexar ao endereço do arquivo:

```
https://irsa.ipac.caltech.edu/<uri>?center=<ra>,<dec>&size=<tamanho>
```

- `size` em graus (no tutorial, `size=0.1` → ~58 × 58 pixels).
- Recortados: `IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`. `WCS-WAVE` é remapeado para o recorte.
- **A extensão PSF vem inteira, sem recorte.** É por isso que um recorte minúsculo pesa ~4 MB e leva ~6 s. A imagem útil tem poucas dezenas de KB.
- Detalhes: <https://irsa.ipac.caltech.edu/ibe/cutouts.html>

### 4.3 Outros acessos

| Método | Endereço | Observação |
|---|---|---|
| SIA2 | `https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+<ra>+<dec>+<raio>` | Pode atrasar ~1 dia em relação ao TAP; não inclui calibração |
| Diretórios (IBE) | `https://irsa.ipac.caltech.edu/ibe/data/spherex/{dr1,qr3,qr2}/` | Padrão `level2/<período>/l2b-v<versão>-<data>/<detector>/` |
| AWS S3 | <https://irsa.ipac.caltech.edu/cloud_access/#spherex> | Espelho na nuvem (coluna `cloud_access` no SIA) |
| Data Explorer (GUI) | <https://irsa.ipac.caltech.edu/applications/spherex> | Bom para conferir manualmente o que o nosso pipeline gera |
| Python | `astroquery.ipac.irsa` (`Irsa.query_tap`, `Irsa.query_sia`), `pyvo` | Alternativa às requisições HTTP diretas |

## 5. Exemplo real: WISE 0855

Consulta em 14/11/2026, posição RA 133,79513°, Dec −7,24515°.

**Por detector (só `spherex_dr1`; ainda não há dados QR3 nessa posição):**

| Detector | Exposições |
|---|---|
| D1 | 36 |
| D2 | 48 |
| D3 | 45 |
| D4 | 36 |
| D5 | 48 |
| D6 | 45 |
| **Total** | **258** |

**Agrupando por tempo (intervalo > 10 dias = nova época):**

| Época | Período | Exposições |
|---|---|---|
| 1 | 05/05/2025 – 06/05/2025 | 30 |
| 2 | 31/10/2025 – 14/11/2025 | 110 |
| 3 | 11/12/2025 – 13/12/2025 | 18 |
| 4 | 21/04/2026 – 14/05/2026 | 100 |

Observações:

- Não são exatamente 2 épocas a cada 6 meses: a cobertura real tem **4 grupos** em ~1 ano. O agrupamento precisa ser feito pelos dados, não assumido.
- Algumas épocas duram semanas. Para objetos rápidos (asteroides), dá para animar **dentro** de uma época; para objetos lentos (anãs marrons), compara-se **entre** épocas.
- Nem todo detector aparece em toda época. O player precisa lidar com épocas faltando.
- WISE 0855 se move ~8″/ano, ou seja, ~1,3 pixel entre a primeira e a última época.

## 6. Implicações para o projeto

| Fato | Consequência |
|---|---|
| Sem CORS no IRSA | Toda consulta passa pelo nosso backend |
| Recorte carrega o PSF inteiro (~4 MB) | Download paralelo, cache, descartar o bruto após extrair as camadas úteis |
| `IMAGE` inclui luz zodiacal | Subtrair `ZODI` antes de exibir |
| Épocas irregulares e detectores faltando | Agrupar por tempo dinamicamente; UI tolerante a lacunas |
| Pixel de 6,15″ | Movimentos de poucos ″/ano são sutis; imagem de diferença e marcador de posição prevista são essenciais |
| DR1 + QR3 atuais, QR2 obsoleto | Coleções configuráveis; nunca misturar QR2 |
| Novos dados QR3 semanais | Backend ao vivo sempre atualizado; Action semanal para os estáticos |
| All-Sky Cube com HiPS | Camada de contexto colorida no Aladin Lite, sem custo de processamento |

## 7. Referências

- Arquivo SPHEREx no IRSA: <https://irsa.ipac.caltech.edu/Missions/spherex.html>
- Documentação do arquivo: [visão geral](https://caltech-ipac.github.io/spherex-archive-documentation), [releases](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-releases), [produtos](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products), [acesso](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access)
- Explanatory Supplement (PDF): <https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf>
- Serviço de cutouts: <https://irsa.ipac.caltech.edu/ibe/cutouts.html>
- Tutoriais Python: [introdução](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/), [cutouts](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/), [PSF](https://caltech-ipac.github.io/irsa-tutorials/spherex-psf/), [HiPS cube](https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/)
- Site da missão: <https://spherex.caltech.edu/>
