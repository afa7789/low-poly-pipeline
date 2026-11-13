# 20 — Texturas pós-GLB: pesquisa (trabalho futuro, sem medição)

- Data: 2026-11-07
- Commit(s): nenhum (relatório `texture-research.md`, scratchpad da sessão). Nada foi implementado nem medido: esta ficha regista o estado da arte avaliado e a ordem de pilotos proposta.
- Problema do baseline atacado (§7): textura. A pintura procedural (L17-3, ficha 14) perdeu 8-0 para o cel plano; a projecção do sheet (L20, ficha 16/§39) vaza cor e fica borrada; o `roster-v6` (ficha 19) entrega 165 modelos com cor chapada + AO em 12 cores, 1 atlas por modelo, e o jogo renderiza em pixel art a ≈ 450 px (feat/pixel-art, `bf6906f6`).
- Alvo (regra do autor): o Bob-omb da nupsume — 202 tris, textura 64 × 64 = blocos de cor + poucos detalhes pintados.

## Hipótese de trabalho (nada medido)

1. A 450 px verticais uma unidade ocupa ≈ 40–80 px de ecrã: textura de 64–128 px por modelo já satura; textura 2K de IA é desperdício e vira ruído depois do pixel shader.
2. Caminho barato e seguro: **(1) atlas de paleta/gradiente** + **(3) bakes estilizados sem IA**. Determinístico, headless, segundos por modelo, custo 0.
3. IA só para o "detalhe pintado" (olhos, rebites, emblema): **(4) inpaint de render + reprojecção mascarada** (nano-banana ou SD), restrito por máscara de ilha. Os métodos multi-view (TEXTure, SyncMVD, Hunyuan-Paint) não correm no Mac e exageram detalhe para 700 tris.

## Opções avaliadas

| # | método | corre onde | custo | o que dá em 700 tris | risco |
|---|---|---|---|---|---|
| 1 | atlas de paleta: faixas de gradiente (sombra → luz) por material, cada ilha UV vira ponto/segmento na faixa (Synty/Kenney); script bpy headless, UV por projecção Z local | Mac, < 1 s/modelo | 0 | exactamente o look Bob-omb/WC3-lite; sem detalhe pintado | bleed se swatch < 4 px com mip: nearest, sem mip, swatch ≥ 4×4 |
| 2a | Meshy Retexture API (`enable_original_uv=true`, text/image style, multiview) | API | ≈ US$ 0,20/modelo (2K) → ≈ US$ 80 nos 393 | "painted character", low-poly "ainda a amadurecer" | costura entre ilhas, estilo não controlado, 2K → downscale + quantizar |
| 2b | Tripo `/v3/models/texture` | API | ≈ US$ 0,01/crédito, não publicado | "mais limpo, engine-ready" | não documenta se preserva UV |
| 2c | Hunyuan3D-2.1 Paint | CUDA 21 GB (`device="cuda"` fixo) → não corre no Mac; fal.ai/Replicate ≈ US$ 0,10–0,30 | — | PBR realista; estilizado só com concept muito limpo | re-unwrap interno (perde o atlas), licença exclui UE/UK/KR |
| 2d | SyncMVD, MVPaint, TEXTure/Text2Tex/Paint3D, TEXGen/UniTEX, StableGen | CUDA (SD1.5 + ControlNet); MPS teórico | 5–10 min GPU | consistência boa (SyncMVD), FID mau em UV puro (TEXGen) | fragmentação em ilhas pequenas; costuras view-by-view |
| 2e | Dream Textures (Blender, Apple Silicon ok) | Mac, ≈ 30 s/vista | 0 | projecção 1 vista de cada vez | faces grandes deformam; sem headless |
| 3 | bakes estilizados sem IA: AO (já existe), curvatura por vértice em numpy (diedro), thickness, Z local, normal·up; composição PIL: cor base × ramp(AO) + edge-wear + rim + ruído ordenado → quantizar ≤ 16 cores; dilatação 4–8 px por ilha | Mac, < 2 s/modelo | 0 | "Synty + sujidade"; sem olhos/emblemas | Pointiness do Cycles não é curvatura em 700 tris: calcular por vértice |
| 4 | inpaint de 4–6 renders ortográficos (cor, depth, normal, id de peça, máscara de ilha) com nano-banana (US$ 0,02–0,04/img) ou SD inpaint + ControlNet depth em MPS; reprojecção com peso cos(n·v) e depth test, só dentro da máscara de ilha; quantizar e dilatar no fim | Mac + API | ≈ US$ 0,15–0,25/modelo → US$ 60–100 nos 393; ≈ 1 min | olhos, rebites, emblema, costuras; evolução directa do `eye_project` | IA muda proporção e inventa (TexEditor: Nano Banana Pro quebra geometria fina): reprojectar só o delta de cor com máscara "detalhe" |

## Regras de pixel art que a textura tem de respeitar

1. Densidade: 1 texel ≈ 1 px de ecrã à distância padrão; unidade de 2 m a ≈ 60 px → 32–64 texels por lado da peça maior; atlas 64–128 px por modelo, 256 só para edifícios grandes.
2. Filtro nearest, sem mipmap (ou mip só do atlas quantizado); bilinear mata o look.
3. Paleta 16–32 cores por raça; AO em 3–4 degraus (hoje 12 → reduzir).
4. Dither ordenado 2×2/4×4 só em gradientes grandes; nunca em peças < 8 texels; a 450 px o 4×4 vira ruído → preferir bandas.
5. O que lê: silhueta, 2–3 tons por peça, olhos/visor, 1 emblema, borda escura (o contorno por profundidade do shader já existe). Rebite isolado não lê; fileira de rebites lê como lista.

## Ordem de piloto proposta

1. **Atlas de paleta + AO em 3 degraus** (opção 1), 1 dia: `scripts/palette_atlas.py` headless; A/B contra o actual em hfoo, n005 e 1 edifício, renderizado pelo pixel shader.
2. **Bakes estilizados** (opção 3) em cima do 1, 1–2 dias; gate: nenhuma cor fora da paleta, zero spill.
3. **Inpaint nano-banana + reprojecção mascarada** (opção 4) só para detalhes, 2–3 dias; 5 modelos, < US$ 2; se vazar, cair para decalques procedurais do `parts.json` (a cara já tem `face_kind`, ficha 15).

Meshy/Tripo: 1 teste de US$ 0,20 no hfoo com `enable_original_uv=true` só para calibrar; não entra no pipeline (2K realista, costura, dependência externa).

## O que piorou / limitações

- Nada medido. As afirmações sobre Meshy/Tripo/Hunyuan vêm da documentação e de um benchmark de terceiros, não de um teste nosso.
- Papers/ferramentas a registar em `docs/references.md` quando um piloto correr: MVPaint (arXiv 2411.02336), Im2SurfTex (arXiv 2502.14006), TexEditor (arXiv 2603.18488), texel splatting (arXiv 2603.14587), Hunyuan3D-2.1 (já na linha 304 como fonte do `eye_project`), SyncMVD, TEXTure/Text2Tex/Paint3D, TEXGen; blog Ready Player Me (ControlNet em UV + inpaint).

## Conclusão (1 frase para o paper)

Para 700 tris vistos a 450 px em pixel art, a hipótese é que a textura certa é pequena e determinística (atlas de paleta + bakes estilizados, custo 0) e que a IA só entra como inpaint mascarado de detalhes sobre renders, nunca como re-texturização 2K — é o próximo piloto, não um resultado; nada nesta ficha foi medido.
