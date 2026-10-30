# Papers de atlas / paleta / packing × estágio de textura (2026-10-29) — PLANEJAMENTO (nada implementado)

Fonte: lista do usuário (`~/Desktop/Papers_MrBang_Texture_Atlas/referencias_atlas.md`; referência visual: Mr. Bang, atlas 32×64 +
260 tris). Papers lidos por abstract/página (a pasta de PDFs estava vazia). Estado lido de `surfaces.py`, `shared_atlas.py`,
`build_unit.py`, `colour_stage.py`, `mesh_lint.py`, `src/render/ModelCook.cpp`, `src/render/UnitBatch.cpp`, PIPELINE §19 C1/C2,
§24.L6-11, §26.L8-8. Regras: textura sempre procedural (nunca recortar o sheet), forma > textura, alpha = placeholders, BFS, sem IA.

## 1. Footprint medido hoje

| unidade (run) | atlas | KB img | GLB KB | mats/prims | tris | verts | sampler |
|---|---|---|---|---|---|---|---|
| n005 v12-r1 | 768×768 (3×3 blocos de 256, 7 usados) | 83.9 | 281 | 7 / 7 | 630 | 1558 | NEAREST |
| n017 v12-r1 | 512×512 (2×2, 4 usados) | 55.5 | 235 | 4 / 4 | 626 | 1584 | NEAREST |
| n017 v11-r1 | 768×512 | 63.4 | 243 | 5 / 5 | 610 | 1553 | NEAREST |
| n01X v12 (painted) | 4 imagens 256² | ~150 | 251 | 4 | 652 | — | LINEAR (viola `images == 1`) |
| `--atlas shared` (24.L6-11) | 64×64 | 0.7–1.1 | — | iguais | 630 | 932–1024 | NEAREST |

- GLB n005: imagem 84 KB; animação 62 KB; POSITION 18.7 + NORMAL 18.7 + UV 12.5 + JOINTS 6.2 + **WEIGHTS 24.9 KB (float32;
  UNSIGNED_BYTE normalizado daria 6 KB)**; índices 3.8 KB; JSON 67 KB (272 bufferViews).
- Informação útil do cel plano (`RAMP_SLOPE = 0`): 3 tons × material + ink + decais ≈ 40 cores; `paint_cel` repete 8 slots de rampa
  iguais em células de 256 px. O 768² é overhead de ink e de slots repetidos.
- Engine: `ModelCook.BuildMaterial` carrega `mipmaps=1`, filtro default rlgl GL_NEAREST → sem mips em jogo hoje; `UnitBatch` faz 1
  draw instanciado por mesh/material → draws por tipo de unidade = nº de materiais (7 no n005).
- Gates (`mesh_lint`): `images == 1`, `uv_out_of_range == 0`; relatório `atlas_kb`, `uv_overlap_pct`, `atlas_used_pct`.
- Raças: 14; Human com 2 unidades já usa 12 das 64 colunas do atlas partilhado (~10 unidades/raça antes de estourar).

## 2. Paper → técnica → aplicável?

| paper | técnica | aplicável? | onde | ganho | custo | conflito |
|---|---|---|---|---|---|---|
| Pöyry 2018 | packing irregular, rotações, orçamento de tempo; revisão MaxRects/skyline/NFP | parcial: "MaxRects/shelf basta" | `surfaces.atlas_layout` → `pack_cells` | 768² → 128²/unidade (−80 KB); mistura células 64 (decal) e 2 px (rampa) | 30 min | nenhum |
| Knodt & Gao TOG 2025 (overlap + carving) | sobrepor charts espelhados (OT), cortar texels vazios | ideia sim, método não: L/R já mapeiam na mesma célula (`TEX_SLOTS`); carving = "1 texel por tom" | `atlas_uvs` (já) | já colhido; carving via T1 | OT: horas, sem ganho | nenhum |
| Knodt TOG 2023 (joint UV + baking) | UV + bake por render diferenciável high→low | **não**: sem high-poly nem textura fonte | — | 0 | alto | bakear do sheet = recorte disfarçado |
| Nöll & Stricker 2011 | modulo-valid packing (chart dá a volta) | não: exige REPEAT; nossas células são retângulos | — | 0 | — | — |
| Yang TOG 2023 (learning packing) | política neural vs xatlas | **não**: retângulos fixos empacotam a 100 % com shelf | — | 0 | treino | "sem IA" |
| TABI 2026 | packing GPU interativo | não (offline, poucos charts); heurística "linhas por altura" = shelf | `pack_cells` | = T1 | — | — |
| Lodi / Sander UVAtlas | bin packing clássico | shelf FFD para células de 2 alturas | `pack_cells` | 1 imagem por raça com decais | 30 min | — |
| Palette workflow (Saved Pixel, Polylusion) | texels sólidos reutilizados; cor = 1 texel | **sim, já é o `shared_atlas`**; falta dedup por ΔE e caber mais unidades | `shared_atlas.key/extend` + `silhouette.oklab` | ≥ 20 unidades por 64²; 1 textura/raça | 45 min | nenhum |
| Halladay 2016 (mips) | padding ≥ 2^níveis, células POT, clamp | sim se ligarmos mips: colunas de 1 px não são mip-safe | `shared_atlas.image` (coluna 2–4 px), `mesh_lint` mip-sim | mips sem sangue até 1/4; em jogo hoje 0 | 30 min | nenhum |
| Gradient Texturing (Le; itch.io) | rampa vertical por slot | já feito (`ramp_column`); rampa medida negativa (19.C1, 24.L6-11) | — | — | — | — |
| Android docs | POT, menor resolução aceitável, 1 material partilhado | sim: 64²/128² POT; `merge_materials` | 7 → 1 draws | 45 min | — |

## 3. Leva 9 — textura (proposta, ordem T1 → T6 → T2 → T3 → T5 → T4)

| # | item | módulo/função | aceite | tempo |
|---|---|---|---|---|
| T1 | atlas cel compacto: slot de rampa 2 px (ink 1 px) em vez de 8; decal 16 px; `pack_cells` shelf FFD | `surfaces.paint_cel/atlas_layout`, `build_unit.texturize/atlas_uvs/paint_decals` | n005 imagem ≤ 128², `atlas_kb` ≤ 8 (de 83.9); `luma_l1` ±0.003; `zones mean` não cai > 0.01; `uv_out_of_range 0`; decal legível (olhos n005) | 60 min |
| T6 | mip-safe medido: box-filter 1/2, 1/4, 1/8 em numpy; texels que misturam 2 células; células POT + padding 2 px | `mesh_lint` (`mip_bleed`), `shared_atlas.image` | 0 texels mistos até 1/4 nos atlas T1/T2; relatório só | 30 min |
| T2 | paleta mínima partilhada: `shared_atlas.key` quantiza em Oklab (ΔE < 0.02 funde colunas da mesma superfície); coluna 2 px | `shared_atlas.key/extend/image`, `silhouette.oklab` | Human 12 → ≤ 9 colunas; 64² cobre ≥ 16 unidades/raça (estimar com todos os specs v12); render texel-igual onde não houve fusão | 45 min |
| T3 | decais no atlas partilhado (1 imagem): faixa superior com células 16 px MaxRects, chaves append-only | `shared_atlas` (`decals`), `build_unit.texturize_shared/paint_decals`, `shared_uvs` | `images == 1`; pareado sheet não perde 4-0 como em 24.L6-11; atlas raça ≤ 128², ≤ 4 KB | 60 min |
| T5 | 1 material no export (`merge_materials`), default em cel | `build_unit.bind_atlas`, review (coluna materials) | n005 prims 7 → 1; engine importa; `UnitBatch` 1 draw/tipo; render pixel-igual | 45 min |
| T4 | espelho L/R: provar que `.L/.R` já partilham célula e tom; registrar `uv_overlap_pct` esperado > 0 | `mesh_lint.raster_uv` + nota | linha no PIPELINE + teste | 30 min |

Bateria: n005, n017, hfoo, n00U, n02X v12 (estágio 2 sobre o clay, câmeras do estágio 1); `review_pair` só em T3.

## 4. Não vale / não fazer
- Packing aprendido (Yang), joint UV baking (Knodt 2023), carving por OT (Knodt 2025), modulo-valid (Nöll), TABI GPU: resolvem charts irregulares ou high→low que não temos; células retangulares já empacotam a 100 %.
- Recortar o concept sheet como atlas (regra); religar rampa por face (negativo 2×); `cull=remove` (rasga clipes); segunda imagem para decais (gate `images == 1`); LINEAR/mips no cel (borra ink; engine sem mips).
- Quantizar WEIGHTS/anim: fora do escopo textura, mas é o maior bloco do GLB depois do T1 (25 KB) — candidato de outra leva.
