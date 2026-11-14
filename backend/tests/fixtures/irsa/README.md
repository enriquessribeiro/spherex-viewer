# Fixtures reais do IRSA

Gravadas em 14/11/2026 para o WISE 0855 (RA 133.79513, Dec -7.24515).

| Arquivo | Origem |
|---|---|
| `wise0855_tap.csv` | Resposta do TAP (`spherex_dr1` + `spherex_qr3`, `producttype = 'science'`): 258 exposições |
| `wise0855_D1_epoca1.fits` | Recorte `size=0.15` de `level2_2025W19_1B_0241_1D1_spx_l2b-v27-2026-197` (06/05/2025) |
| `wise0855_D6_epoca4.fits` | Recorte `size=0.15` de `level2_2026W20_1A_0033_1D6_spx_l2b-v27-2026-246` (mai/2026) |

Os recortes tiveram a extensão `EPSF` removida (~4 MB, não usada) para não pesar no repositório.
Os números destas fixtures não mudam; testes `live` devem usar `>=` porque o arquivo real recebe dados novos.
