# Técnicas dos geradores 3D aproveitáveis na pipeline (2026-10-31)

Pesquisa web por leitura de papers, READMEs e issues. Nada foi instalado nem corrido. Máquina alvo: M4 Pro, 24 GB, torch com MPS.
Estado da pipeline: nota 4/10 pelo autor; textura é o pior eixo; receita v18-cvt é default (L19-0).

## Conclusão

1. Tripo não publica o pós-processamento. TRELLIS e Hunyuan publicam, e é aí que está o que serve.
2. Os três relatórios convergem no mesmo item: projectar o concept sheet de 5 vistas no atlas. É o único item que muda o visual de imediato.
3. Para o baseline do paper, `trellis-mac` é o único gerador completo confirmado em M4 Pro 24 GB. Nenhum aceita as 5 vistas de forma confirmada.

## Top 5 para a pipeline (ganho ÷ esforço)

| # | técnica | origem | etapa | esforço | Mac |
|---|---|---|---|---|---|
| 1 | Projecção das 5 vistas no atlas | Hunyuan3D-Paint | textura | ~200 linhas | NumPy + OpenCV |
| 2 | "Delight" discreto por material | adaptação do Hunyuan | textura, pré-passo do 1 | ~50 linhas | NumPy |
| 3 | CVT com densidade por curvatura + arestas vivas | Fuhrmann 2010, Dora SES | retopo | ~1 dia | NumPy |
| 4 | Pesos por Bone Heat | Pinocchio, Blender | rig | ~1 h | bpy |
| 5 | Limpeza de faces interiores por visibilidade | TRELLIS `_fill_holes` | antes da redução | ~1 dia | CPU |

### 1. Projecção das 5 vistas

Por texel UV: posição 3D e normal, projecção em cada vista, teste de profundidade.
Peso = `w_vista · cos(n·v)^k`, k = 4 a 6, zero abaixo de cos 75°.
Pesos de vista no Hunyuan: frente 1, trás .5, lados .1, topo e baixo .05. Os nossos têm de ser medidos.
Máscara de bordo: erosão da máscara visível + Canny na profundidade. Evita esticar a silhueta.
Média ponderada. Texels sem cobertura ficam com a pintura procedural actual ou inpaint por vértices 1/d².
Fontes: `hy3dpaint/DifferentiableRenderer/MeshRender.py`, `pipeline_utils.py`.

Risco próprio: as vistas do nosso sheet são incoerentes entre si (Levas 12–13). Projectá-las pode dar costuras onde as vistas discordam.
Isto não está medido. O piloto deve ser 1 unidade antes de qualquer bateria.

### 2. Delight discreto

Hunyuan usa difusão. O nosso sheet é cel, por isso o problema é discreto: por cluster OKLab, tom de maior L = albedo, sombras do mesmo cluster remapeadas, linhas preservadas.
Hipótese ainda não testada.

### 3. CVT por curvatura

`ρ(x) = clamp((|κ1|+|κ2|)^α + β·máscara_parte)`, com cabeça e mãos a 2×. Sementes em arestas com diedro > 30° fixas ou restritas à aresta (SES do Dora).
Responde à queixa "não optimizou como o paper de low poly": hoje os triângulos são uniformes.

### 4. Bone Heat

`ARMATURE_AUTO` com o esqueleto fixo, depois normalizar e limitar a 4 influências. Alternativa robusta a peças que se tocam: geodésica voxel (Dionne 2013) a 64³.

### 5. Limpeza interior

Câmaras Hammersley, faces nunca vistas = interiores, remover e fechar furos pequenos. Evitar `pymeshfix`, que é GPL.

## Outros itens

- FlexiCubes em CPU na extracção a 96³: arestas mais nítidas. `flexicubes.py` é torch puro.
- QEM em 2 passos à CuMesh: 3× alvo, limpeza, alvo; penalização skinny 1e-3; flip com custo infinito.
- xatlas: `padding` 3, `resolution` 256, `bruteForce`, `maxCost` 4–8 para menos ilhas.
- Segmentação SDF (CGAL) cruzada com osso: ilhas de atlas por parte.
- Bake high→low com cage em Cycles CPU.
- Juiz automático: CLIP, CMMD, LPIPS em normais; opção "Não sei" no juiz.

## Baseline de geradores no Mac (para o paper)

Bloqueado pela regra `no-image-to-3d-generators` até decisão do autor.

| ferramenta | entrada | saída | prova em Mac | RAM e tempo | licença |
|---|---|---|---|---|---|
| trellis-mac | 1 imagem | forma + PBR | autor, M4 Pro 24 GB | pico ~18 GB, ~5 min a frio; throttling levou um run a ~36 min | MIT; RMBG-2.0 CC BY-NC; DINOv3 gated |
| trellis.cpp | 1 imagem | forma + PBR | M5 24 GB, M4 Pro por testar | 5,6 GB RSS (a conferir), 9:21 a 512³ | MIT |
| hunyuan3d-2.1-mac-rocm | 1 imagem | forma + PBR | M4 Pro 24 GB | ~14 min, ~8 GB de swap | wrapper MIT; pesos Tencent, exclui UE, UK, Coreia |
| Hunyuan3D-2mv | multi-vista | só forma | sem prova em MPS | desconhecido | Tencent |

Limites: imagem única recebe uma vista recortada, o que penaliza o baseline face à pipeline. Malhas de 200K a 4,8M faces até 700 tris exigem rebake.

## Ferramentas de malha no Mac

| ferramenta | função | estado | nota |
|---|---|---|---|
| Blender 5.2.3 | base | sim | Metal em Cycles |
| QuadWild-BiMDF | quad remesh | sim por README | GPL-3 |
| TreeMeshGPT | retopo nuvem → malha | parcial, melhor candidato | MIT; falta procurar `.cuda()` |
| PartField | partes | parcial | `cuda` por default; licença NVIDIA por ler |
| MeshAnything V2 | retopo ≤ 1600 faces | parcial | não comercial; flash-attn hardcoded |
| UniRig | rig | não sem porte | não preciso: esqueleto fixo |
| Instant Meshes | remesh | parcial | GUI quebrada em Mac; perde UV |

## Próximo passo proposto

L20-0: projecção + delight numa unidade (hfoo), comparação visual pelo autor, sem chamadas VLM (replay do v18-r0).
