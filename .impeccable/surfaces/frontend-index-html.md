---
version: 1
slug: "frontend-index-html"
primary_target: "frontend/index.html"
related_targets: ["frontend/src/main.ts"]
---

# Visualizador (tela principal)

Modo: Operate. Público: geral + jurados primeiro; amadores em seguida. Tarefa: escolher um alvo (ou RA/Dec/nome) e ver o que se move ou muda de brilho entre épocas. Prova: dados reais do SPHEREx dos 5 alvos do desafio. Restrições: estático no GitHub Pages; API opcional; português; celular na demonstração.

## Direction contract

THESIS: As épocas do SPHEREx como placas fotográficas de vidro comparadas no blink comparator, o método que achou Plutão. Recusa o padrão da categoria: tela azul-marinho de "espaço" com brilhos e acento neon.

OWN-WORLD: Fundo de vidro claro levemente quente (#f2efe7), tinta preta de negativo (#141414), lápis de cera vermelho (#c4302b) só para marcas de descoberta (círculo e seta no objeto, época selecionada), manila (#9c8f74) para etiquetas e réguas. Céu em negativo por padrão (estrelas pretas). Diferença: vermelho = apareceu, azul-tinta (#2b4c9c) = sumiu, com legenda. Algarismos tabulares, rótulos pequenos em caixa alta, etiqueta de placa como componente.

STORY: O visitante abre, vê a placa piscando e o objeto circulado mudando de lugar; entende "isso se moveu no céu"; troca de alvo, de detector ou de modo; copia o link.

FIRST VIEWPORT: Topo: nome, busca (alvo, RA/Dec ou nome) e botão copiar link. Esquerda (dominante, ~60%): a placa quadrada grande com o quadro atual, mira fixa e círculo vermelho na posição prevista; etiqueta da placa (época, data, exposições, detector). Direita: os 5 alvos com miniaturas; modo Animar/Piscar/Diferença; detector D1–D6 com faixa em µm em escala; contraste e negativo/positivo. Embaixo: régua do tempo com as épocas em escala de datas reais. Ação principal: escolher alvo / tocar Animar.

FORM: Placas do comparador, escolha do Impeccable (posição 1 da lista ordenada), assigned era 4. seed:d361871885b5d68c
Assinatura: círculo e seta em lápis vermelho desenhados à mão sobre a placa, que acompanham a posição prevista do objeto época a época; régua do tempo proporcional às datas; uma cor só para mudança.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
