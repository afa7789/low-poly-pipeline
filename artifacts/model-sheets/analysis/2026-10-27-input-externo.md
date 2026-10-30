# Input externo recebido pelo usuário (2026-10-27) — análise de outro assistente sobre o pipeline

O problema principal não parece ser falta de um gerador de modelos 3D. O sistema consegue medir e otimizar a semelhança de silhueta, mas ainda não consegue construir uma representação 3D estruturalmente equivalente ao conceito.

Na aranha: front/back volume central próximo mas pernas/pontas/proporções locais diferem; left: corpo é caixa com pernas anexadas, não abdômen orgânico coberto por carapaça; top/bottom: maiores falhas, conceito tem corpo oval, carapaça e oito pernas radiais, modelo parece bloco quadrado com membros; RTS: objeto mecânico de quatro apoios.

Não começaria adicionando mais regras ao preflight ou mais chamadas ao LLM. Primeiro mudaria a representação geométrica que o autor pode produzir e a maneira como ela é avaliada.

## 1. Alternativas open-source para testar (como propostas de geometria, não substituto dos gates)
- TRELLIS (Microsoft): image-to-3D, malha; não restrito às 6 silhuetas. Alta prioridade.
- Hunyuan3D 2.1 (Tencent): shape e textura separados; ~10 GB VRAM shape, 29 GB com textura. Alta prioridade.
- TripoSR (MIT): feed-forward leve; proporções de top/bottom/side não preservadas.
- TRELLIS.2: 4B params, PBR; pesado; detalhe ≠ low-poly.
Verificar licenças. Tratar como geradores experimentais de geometria, não substitutos dos gates de silhueta.

## 2. O que mudar no pipeline existente (preservar medição, preflight, 6 vistas, fit, histórico)
### A. Parar de tratar o modelo como coleção de caixas
Para a aranha: volumes orgânicos (elipsoides, volumes afunilados, perfis de seção custom para abdômen e carapaça); membros articulados (8 pernas parametrizadas independentemente com juntas, segmentos afunilados, perfis curvos); cascas em camadas (carapaça separada com espessura, curvatura, overhang); geometria de planta (perfil do corpo e arranjo das pernas restritos pelas silhuetas top/bottom). Primitiva de membro por perfil varrido ou sequência de segmentos afunilados com juntas, largura, curvatura, seção. Corpo: superelipsoide, lathe, ou loft por seções. O LLM escolhe e configura formas, não aproxima tudo com caixas.

### B. Reconstruir das 6 vistas simultaneamente
Render 6 vistas de cada candidato, comparar silhueta, loss por vista (IoU + contorno + landmarks), ajustar parâmetros, repetir. L_shape = Σ_v w_v (λ1 L_IoU + λ2 L_contour + λ3 L_landmarks). O que falta é otimizar os parâmetros da malha contra o objetivo completo, não só reparar dims de um spec autorado. O r≈0.998 do proxy só mostra que o proxy reproduz o render, não que a geometria bate com a referência.

### C. Consertar top e bottom da aranha primeiro
Restrições explícitas: contorno do corpo em top (razão comprimento/largura); contorno e overhang da carapaça; 8 raízes de perna e distribuição radial; direção, curvatura e ponta de cada perna; comprimentos relativos dos pares; silhueta de baixo (juntas visíveis, profundidade do corpo); silhueta da câmera RTS. Otimizador muda corpo e membros independentemente.

### D. Melhor estratégia de otimização
Powell sofre com parâmetros interagindo e objetivo descontínuo (IoU por pixel). Comparar: busca coarse-to-fine; CMA-ES ou outro derivative-free; rendering diferenciável. Benchmark em poucos assets difíceis. Otimização em estágios: proporções do corpo → posição dos membros → curvatura/espessura local → detalhes finos. Congelar só quando não impedir melhora global.

## 3. Papel da IA
Não pedir modelo completo do zero e reparar indefinidamente. Divisão: (1) análise de imagem (silhuetas, partes semânticas, landmarks, simetria, correspondências entre vistas); (2) proposta estrutural: LLM produz scene graph semântico (abdômen, carapaça, cabeça, raízes, juntas, perfis de segmento); malhas geradas por IA como proposta opcional; (3) fitting determinístico contra todas as vistas com simetria, conectividade, chão, orçamento; (4) validação independente (silhuetas, integridade, rig, câmera do jogo).

## 4. Melhorias adicionais priorizadas
1. Scoring de landmarks semânticos (perna presa na junta certa, carapaça espessa demais, feature no bodypart certo).
2. Câmera RTS como restrição de primeira classe (ângulo real, tamanho projetado, visibilidade de features).
3. Separar qualidade de geometria da apresentação: estágio de aceite de geometria antes de textura/rig/anim.
4. Melhorar o test set: um mecânico boxy, um orgânico, um humanoide, um prop assimétrico.
5. Medir custo por modelo aceito: tempo, passes, iterações, tris, componentes soltos, intervenção manual.

## 5. Experimento seguinte
Implementar uma família de geometria nova antes de adotar qualquer modelo de IA: criatura orgânica paramétrica com volumes elipsoidais e membros articulados por spline. Rodar a mesma aranha por 3 caminhos: baseline (DSL atual + fit + gates); upgrade procedural (primitivas orgânicas, landmarks de junta explícitos, fitting em 6 vistas); proposta IA (um image-to-3D open-weight + mesma avaliação + limpeza comum). Mesmas referências, câmeras, limiares. Resultado útil: malha com top/bottom melhores, topologia aceitável, menos correção manual.

Recomendação: consertar a representação geométrica e o fitting multi-vista antes de investir em textura ou repair LLM mais elaborado.

---

# Parte 2 — com a informação de que há 27 famílias de esqueleto (rig_families.py)

Precisa de um sistema de reconstrução geométrica condicionado pela família do esqueleto, reutilizando componentes sem obrigar todos os modelos a serem montados do mesmo jeito. Equilibrar consistência dentro da família e flexibilidade entre criaturas.

## Três camadas
1. Esqueleto e semântica: hierarquia de ossos, articulações, simetria, pontos de ancoragem, pose neutra, proporções medidas nas referências.
2. Representação geométrica por família: superfícies orgânicas, segmentos articulados, placas de armadura, formas rígidas, roupas, carapaças.
3. Fitting e validação universais (compartilhada pelos 27): 6 vistas, silhuetas, landmarks, sobreposições, orçamento, compatibilidade com o jogo.

## Famílias geométricas (exemplificativas, não 27 geradores)
- Bípedes humanoides: volumes conectados, perfis de seção, membros segmentados, placas sobrepostas; proporções do sheet, não de humanoide padrão.
- Artrópodes/múltiplos membros: corpo segmentado, carapaças, membros articulados, distribuição radial; número de membros e ancoragens vêm do esqueleto.
- Quadrúpedes: tronco longitudinal, ombros/quadris, 4 membros, cabeça; diferença dianteira/traseira.
- Golems/construtos/rígidos: blocos, prismas, placas, rochas; o DSL atual já serve melhor aqui.

## Quatro mudanças
1. Representação intermediária comum: o LLM produz descrição semântica de partes, perfis, articulações e relações; geradores por família convertem em malha.
2. Seleção de representação por parte: comparar caixa chanfrada / elipsoide / perfil extrudado / loft / membro segmentado; fitting ajusta depois da escolha.
3. Esqueleto como restrição, não gerador: rig define articulações; cabeça/torso/armadura vêm do sheet.
4. Parâmetros compartilhados × específicos: gerador humanoide comum, dimensões e formas por unidade.

## IA aberta
Testar TRELLIS/Hunyuan como geradores alternativos, não universais; avaliar se respeitam simultaneamente as ortográficas, a anatomia e o orçamento. Arquitetura híbrida provável: procedural condicionado pelo esqueleto + otimização multi-vista + IA para partes que o procedural não reconstrói.

## Informação que falta
Quanto os 27 compartilham estruturalmente? Variações de uma hierarquia comum, ou famílias muito diferentes (humanoide, aranha, quadrúpede, serpente, sem membros)? Isso decide: sistema genérico de superfícies condicionado pela hierarquia óssea, ou vários geradores especializados sob interface comum.

---

# Parte 3 — mantendo as ferramentas atuais (Claude, Gemini, Nano Banana, Python/numpy, Blender)

Melhoria deve vir da arquitetura, da representação geométrica e do ciclo de otimização, não de outro gerador de IA. Gargalo: passagem de referências 2D para uma especificação geométrica suficientemente expressiva; nenhum componente recupera uma forma que a representação inicial não permite expressar.

## Cinco mudanças priorizadas
1. Representação geométrica (máxima): volumes por perfis, superfícies extrudadas, membros curvos, volumes orgânicos, placas sobrepostas; serve bípedes, artrópodes, quadrúpedes e rígidos.
2. Interpretação do sheet: landmarks e máscaras por parte (torso, cabeça, membros, armadura, acessórios) relacionadas entre as 6 vistas; código transforma referência em restrições mensuráveis.
3. Fitting sobre todas as vistas: não só soma de margens; perdas por vista e por região, mínimos individuais, pesos por família; uma melhora no front não pode esconder regressão no top.
4. Claude/Gemini como especialistas delimitados: análise semântica → proposta de geometria → diagnóstico de falhas → reparo localizado; caminho rápido de 1 chamada continua; casos difíceis recebem análise extra.
5. Cada falha vira experimento reproduzível: spec inicial, parâmetros ajustados, margens por vista, regras violadas, resultado de cada reparo.

## DSL
| tipo | uso |
|---|---|
| ellipsoid / superellipsoid | cabeça, abdômen, músculos |
| loft | torso, cauda, pescoço, membros de espessura variável |
| sweep | braços, pernas, tentáculos, antenas, caudas curvas |
| extruded_profile | silhuetas extrudadas, asas, placas |
| shell | carapaças, capacetes, armaduras, cascos |
| beveled_primitive | armas, armaduras rígidas, mecânico |
Começar por ellipsoid, loft e sweep, mantendo as primitivas. Separar geometria de articulação (perna = perfil + curvatura; ancoragem e hierarquia = rig).

## Contratos para Claude/Gemini
Análise (partes, relações, materiais, incertezas; não inventa medidas que o código calcula) → Autoria (análise estruturada + DSL + exemplos aprovados → spec compatível com o esqueleto) → Diagnóstico (renders, 6 métricas, overlays → quais partes causam cada falha, mudanças localizadas) → Reparo (só parâmetros editáveis; não mexe no rig nem em peças congeladas). Não usar os dois como juízes redundantes em toda etapa; gates determinísticos primeiro; modelo extra só quando o diagnóstico automático não basta.

## Fitting: não regressão
- Nenhuma vista já aprovada cai abaixo do gate sem exceção explícita.
- Vistas críticas que falham têm prioridade até o mínimo.
- Entre viáveis, o que reduz a perda global e respeita o orçamento.
Comparar Powell com busca hierárquica por grupos (volumes principais → membros → perfis/detalhes) antes de trocar de otimizador.

## Checklist
0. Baseline reproduzível: 6-10 modelos representativos dos 27 esqueletos, métricas, imagens, tempo.
1. Diagnóstico por região: landmarks, máscaras por parte, perdas por vista, não regressão.
2. Novas primitivas: ellipsoid, loft, sweep com ancoragem, simetria, orçamento.
3. Fitting hierárquico vs Powell.
4. Diagnóstico com Claude/Gemini só para falhas difíceis; reparos localizados.
5. Avaliação cruzada nos tipos de esqueleto: qualidade, custo, estabilidade.
Começar por 0 e 1 antes de alterar o autor LLM.
