# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primário: público geral e jurados do NASA Space Apps Challenge 2026.** Pessoas curiosas, sem formação em astronomia, que abrem o site e precisam ver em segundos um objeto se mover (ou mudar de brilho) no céu infravermelho do SPHEREx, e entender o que estão vendo.
- **Secundário: astrônomos amadores** que querem examinar uma coordenada própria, trocar de detector, ajustar contraste e comparar épocas. Os controles avançados existem, mas não competem com a primeira impressão.

## Product Purpose

Ferramenta web pública que mostra imagens do telescópio espacial SPHEREx (NASA) de qualquer trecho do céu, época por época, como uma pequena animação, para qualquer pessoa notar objetos que se movem (estrelas próximas, anãs marrons, possivelmente planetas desconhecidos) ou que mudam de brilho (estrelas variáveis). Responde ao desafio "Planet X and SPHEREx" do Space Apps 2026: o usuário informa RA/Dec e vê a série de imagens; os alvos de teste são Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae e R Draconis.

Sucesso: um jurado abre o link, escolhe um alvo e vê, sem instrução, o objeto andar ou piscar; um amador digita uma coordenada e chega à mesma visualização.

## Positioning

Usa dados **reais** do SPHEREx (DR1 + QR3), processados por um pipeline próprio validado cientificamente: a ferramenta reproduz o movimento próprio conhecido de WISE 0855, Barnard's Star e Epsilon Indi B com erro de centésimos a décimos de pixel, e detecta a variação de RW Aurigae e R Draconis. Os 102 canais infravermelhos são agrupados nos 6 detectores (0,75–5,0 µm): uma anã marrom fria como WISE 0855 só aparece nos comprimentos de onda longos, algo que câmeras comuns não mostram.

## Operating Context

- Site estático no GitHub Pages (alvos pré-processados, abre instantaneamente) + API opcional no Render (gratuito, "dorme" após 15 min; primeira consulta a uma coordenada nova leva de segundos a minutos).
- Dados por campo: `field.json` + quadros float32 por época e detector, máscara de saturação/baixa qualidade; o navegador aplica contraste, piscar, diferença e soma.
- Estado completo na URL (links compartilháveis) e modo `embed` para iframe.
- Apresentação do hackathon: demonstração ao vivo para jurados.

## Capabilities and Constraints

- Movimento sutil: pixel de 6,15″; WISE 0855 move ~1,3 px/ano, Barnard's Star ~1,7 px/ano. Zoom, piscar e mira fixa são necessários para perceber.
- Épocas irregulares (2 a 8 por campo), algumas com poucas exposições; nem todo detector existe em toda época.
- Núcleo de estrelas muito brilhantes vem sem dado (saturado) e deve aparecer com o brilho máximo, não como buraco.
- Cada alvo tem um detector padrão (D6 para anãs frias; D2 para os demais).
- 100% gratuito (sem serviços pagos).
- Interface em **português (Brasil)**.

## Brand Commitments

- Nome: **SPHEREx Viewer**.
- Créditos de dados: NASA/JPL-Caltech/IPAC (SPHEREx, via IRSA). Não usar logotipos da NASA como marca própria do projeto.

## Evidence on Hand

- Resultados científicos reais e imagens: `docs/08-resultados.md`, `docs/img/`.
- Dados dos 5 alvos gerados por `backend/pipeline/build_static` (~5 MB).
- Não há depoimentos, usuários ou métricas de uso: não inventar.

## Product Principles

1. **Ver antes de ler**: o objeto se movendo aparece na primeira tela, explicações vêm depois e são curtas.
2. **Honestidade científica**: mostrar datas, número de exposições e limitações (saturação, épocas ruidosas) em vez de esconder.
3. **Um link conta a história**: toda visualização é reproduzível pela URL.
4. **Profundidade sob demanda**: controles avançados recolhidos até serem pedidos.

## Accessibility & Inclusion

Uso por público geral, inclusive no celular durante a apresentação; legível em telas pequenas; controles operáveis por teclado; cores da diferença (vermelho/azul) acompanhadas de legenda textual.
