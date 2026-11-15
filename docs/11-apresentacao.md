# Roteiro da apresentação — 3 minutos

> Formato recomendado pelo mentor: **o primeiro minuto é o problema**, os dois seguintes são **como o SPHEREx Viewer resolve**, com o site aberto.
> Ritmo de referência: ~130 palavras por minuto falando com calma. O texto de cada bloco cabe no tempo com folga para as pausas da demonstração.

## 0. Slides da demonstração (envio)

Os 7 slides em inglês exigidos pelo campo *Project Demonstration* do Space Apps estão em [`apresentacao/slides.pdf`](apresentacao/slides.pdf) (prévia de cada slide em [`apresentacao/previa/`](apresentacao/previa/)). A fonte é `apresentacao/slides.html`, com capturas do site publicado em `apresentacao/img/`; para gerar de novo: `node docs/apresentacao/gerar-pdf.mjs`.

| Slide | Conteúdo |
|---|---|
| 1 | Título: *SPHEREx Viewer — a movie of the changing infrared sky* |
| 2 | O problema: os dados são públicos, compará-los não é (Tombaugh, 258 exposições) |
| 3 | A solução: tela principal e os três passos |
| 4 | WISE 0855 andando: D6 em duas épocas, D1 e Diferença |
| 5 | Espectro e mapa do céu com Gaia DR3 |
| 6 | Validação científica dos 5 alvos e o portão de publicação |
| 7 | Link, QR code, custo zero e próximos passos |

### Slides do pitch (português) e vídeo de reserva

- [`apresentacao/pitch-pt.pdf`](apresentacao/pitch-pt.pdf): 4 slides para o palco. Slides 1 e 2 no primeiro minuto (abertura e problema); depois troca para o site ao vivo; slide 3 em "por que dá para confiar" e slide 4 no fechamento. Fonte: `apresentacao/pitch-pt.html`; gerar de novo com `node docs/apresentacao/gerar-pdf.mjs pitch-pt`.
- [`apresentacao/demo-pitch.webm`](apresentacao/demo-pitch.webm): vídeo de 60 s, sem som, da demonstração na ordem do roteiro (WISE 0855 animando → D1 → Diferença → espectro → Barnard's Star), com legenda em cada passo. É o **plano B** se a internet cair: abrir no Chrome em tela cheia e narrar por cima. Gravado no site publicado com `node docs/apresentacao/gravar-video.mjs`.

## 1. Visão geral

| Tempo | Bloco | Na tela |
|---|---|---|
| 0:00–1:00 | **O problema** | Slide único (ou o topo do site, parado) |
| 1:00–1:15 | A solução em uma frase | Site aberto no WISE 0855 |
| 1:15–2:20 | Demonstração | WISE 0855: animar → D1 → Diferença → espectro |
| 2:20–2:50 | Por que dá para confiar | Pode ficar no site; números falados |
| 2:50–3:00 | Fechamento | Site |

A ideia que amarra tudo: **Plutão foi achado comparando duas fotos. O SPHEREx tira essas fotos do céu inteiro, mas ninguém de fora da astronomia consegue compará-las. Nós fizemos isso virar um filme.**

## 2. O texto

### 0:00–1:00 — O problema (~120 palavras)

> Em 1930, Clyde Tombaugh descobriu Plutão de um jeito simples: comparou duas fotos do mesmo pedaço do céu e viu um ponto que tinha mudado de lugar.
>
> Quase cem anos depois, a gente ainda procura coisas assim: anãs marrons frias perto do Sol e, quem sabe, um "Planeta X".
>
> O telescópio SPHEREx, da NASA, é perfeito para isso. Ele fotografa o céu inteiro em infravermelho a cada seis meses, e os dados são públicos.
>
> Mas público não quer dizer acessível. Só para um ponto do céu, o da anã marrom WISE 0855, são **258 imagens**, cada uma numa cor diferente, giradas, com pixels com defeito. Para ver se algo se moveu, é preciso alinhar tudo pixel a pixel.
>
> Hoje, só um astrônomo consegue fazer essa comparação. E é dado demais para os astrônomos olharem sozinhos.

**Se tiver slide**: à esquerda, as duas placas de Tombaugh com Plutão marcado; à direita, uma grade de miniaturas das 258 exposições cruas do WISE 0855 (tortas, de cores diferentes). Uma frase só: *"Os dados existem. Comparar, não."*

### 1:00–1:15 — A solução em uma frase (~35 palavras)

> O SPHEREx Viewer transforma esse arquivo num filme do céu. Você escolhe um alvo ou digita uma coordenada, e vê as épocas passando, como as placas de Tombaugh, direto no navegador.

**Ação**: mostrar o site já aberto no WISE 0855 (a página abre animando, em D6).

### 1:15–2:20 — Demonstração (~110 palavras + pausas)

| Fala | Ação |
|---|---|
| "Este é o WISE 0855, a anã marrom mais fria que se conhece. Olhem o centro: o ponto anda dentro do círculo vermelho, que é onde o catálogo diz que ele deveria estar." | Deixar animar duas ou três épocas. Apontar o círculo. |
| "No infravermelho curto ela some: é fria demais. Só a estrela de fundo aparece, parada. Por isso precisamos do SPHEREx." | Clicar em **D1**. Depois voltar para **D6**. |
| "O modo Diferença subtrai uma época da outra: o céu parado some e sobra só o que mudou. Vermelho onde ela chegou, azul onde estava." | Clicar em **Diferença**. |
| "Como cada foto mede uma cor diferente, juntamos todas no espectro dela. O brilho sobe no fim, em 4 a 5 micrômetros: é onde um objeto frio brilha." | Rolar até o **Espectro**. |
| "Funciona nos cinco alvos do desafio e em qualquer coordenada." | (Opcional, só se sobrar tempo) clicar em **Barnard's Star** e mostrar o ponto subindo. |

### 2:20–2:50 — Por que dá para confiar (~55 palavras)

> E não é só bonito: os cinco alvos passam numa validação científica automática, com erro de décimos a centésimos de pixel na posição. O site se atualiza sozinho a cada três dias com os dados novos da NASA e só publica se a validação passar. De graça, em português e inglês.

### 2:50–3:00 — Fechamento (~30 palavras)

> Tombaugh passou meses olhando placas de vidro. Com o SPHEREx Viewer, qualquer pessoa faz a mesma comparação em segundos e pode ser a próxima a ver um ponto que se move.

## 3. Antes de subir no palco

- **Abrir as abas antes**, já carregadas (os dados vêm do cache do navegador):
  - <https://enriquessribeiro.github.io/spherex-viewer/?target=wise0855> (aba principal)
  - <https://enriquessribeiro.github.io/spherex-viewer/?target=barnard&mode=blink> (reserva)
- Clicar uma vez em D1, Diferença e Animar em cada aba, para os quadros já estarem baixados.
- **Não usar busca por nome nem coordenada nova ao vivo**: isso passa pela API no Render, que dorme no plano gratuito e leva minutos para processar um campo novo.
- Zoom do navegador em 110–125% se o projetor for pequeno. O círculo vermelho precisa ser visível do fundo da sala.
- **Plano B sem internet**: o vídeo `apresentacao/demo-pitch.webm` (seção 0), salvo no computador da apresentação antes de subir. Se a rede cair, troca para o vídeo sem comentar.
- Cronometrar dois ensaios completos. Se passar de 3:00, cortar primeiro a linha opcional (Barnard's Star) e depois a frase do D1. O aviso de estrela vizinha no espectro fica para as perguntas (seção 5).

## 4. Números para ter na ponta da língua

| Número | O que é |
|---|---|
| 258 | Exposições do WISE 0855 entre mai/2025 e mai/2026, em 4 épocas |
| 102 | Bandas do SPHEREx, de 0,75 a 5 µm, em 6 detectores |
| 6 meses | Intervalo entre dois mapeamentos do céu inteiro |
| 6,15″ | Tamanho de um pixel do SPHEREx |
| ~285 K | Temperatura do WISE 0855 (~12 °C) |
| 0,02 px | Erro na medida do movimento da Barnard's Star (~11″ para o norte em um ano) |
| 1,35× e 0,46× | Variação de brilho de RW Aurigae (12σ) e R Draconis (15σ) |
| 16 | Testes da validação científica com dados reais, que bloqueiam a publicação se falharem |
| a cada 3 dias | Atualização automática dos dados |
| R$ 0 | Custo de hospedagem (GitHub Pages + Render grátis) |

## 5. Perguntas prováveis

**Por que não usar o visualizador do IRSA ou o Aladin?**
Eles mostram uma imagem ou o mosaico do ano inteiro somado, em que nada se move. O SPHEREx Viewer alinha exposições de datas diferentes na mesma grade e as compara: é a comparação que revela movimento e variação. O mapa do céu do próprio site usa o Aladin para navegar.

**Como vocês sabem que o resultado está certo?**
Comparamos com valores independentes: posições e movimentos do SIMBAD e do Gaia DR3. A posição prevista bate com a medida em décimos ou centésimos de pixel, e as estrelas de campo ficam paradas entre épocas (0,02–0,04 px). Esses 16 testes rodam toda vez que os dados são atualizados.

**Dá para achar o Planeta X com isso?**
A ferramenta faz exatamente a comparação que acharia: um ponto que muda de lugar entre épocas. Se um objeto desconhecido for brilhante o bastante para o SPHEREx no infravermelho, ele aparece andando. O que não prometemos é que ele esteja nos dados. O que o projeto entrega é a forma de procurar.

**Por que o espectro do WISE 0855 é alto no começo?**
Uma estrela a ~7,6″ cai dentro da abertura de medida em D1, D2 e D4. O pixel do SPHEREx tem 6,15″ e não separa as duas, então ali o fluxo é principalmente dela. O site mostra esse aviso acima do gráfico e marca esses detectores com asterisco. A parte que é do WISE 0855 é a de 4–5 µm, onde a estrela vizinha é fraca e a anã marrom brilha.

**E asteroides?**
Asteroides cruzam o campo em horas. Hoje as exposições são agrupadas em épocas de semanas, então um asteroide aparece em uma época e some na outra. Mostrar exposição por exposição é o próximo passo natural.

**Funciona para qualquer ponto do céu?**
Sim. Os alvos do desafio são pré-processados e abrem na hora; qualquer outra coordenada é processada sob demanda pela API (alguns minutos na primeira vez).

**Quanto custa manter?**
Nada. Site no GitHub Pages, API no plano gratuito do Render, atualização pelo GitHub Actions. Não há banco de dados: os dados são arquivos e o índice é o próprio arquivo da NASA.

**O que vem depois?**
Espectro para qualquer ponto (hoje só para os alvos), exposições individuais para asteroides e uma forma de o público marcar candidatos, como faz o projeto Backyard Worlds.
