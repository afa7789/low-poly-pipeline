# 03 — Balanço dos papers aplicados ao pipeline de modelos (2026-10-31)

Fonte: `castle_fight/docs/references.md` (tabela "Modelos 3D por IA", linhas 190–303, **97 linhas** (a 97.ª é a OKLab do `eye_fuse`, Leva 18), uma por paper × módulo), `papers/README.md`
(os 22 PDFs lidos) e as fichas `melhorias/01–14`. Contagem = `grep -c` do nome na tabela; "default" = o módulo corre sem flag no `main 9a5a83fd`.

## Grupo A — ficaram no default e resolveram algo

| paper | linhas | onde ficou | o que resolveu (evidência) |
|---|---|---|---|
| Ottosson — Oklab (2020) | 2 | `silhouette.zone_feature_oklab`, `luma_l1` (§19.C2); `merge_materials` por ΔE (§27.T5); `--zone-contrast` (L15-3); `eye_fuse` (L18-1, opt-in) | zonas de cor do sheet medidas, contraste por zona, fusão de materiais; sem resultado negativo em nenhuma leva |
| Garland–Heckbert — QEM (1997) | 3 | `cull.decimate_union` (§20.M12); `retopo.Reducer` (§28.L10-3, **default** `BODY=sdf`, ficha 09); `eye_union` QEM com `max_dev` (L17-2) | slivers 9–32 % → 0–5 % em 10/10 (L10-8); lint limpo 3/5 vs 0/5 (L10-9) |
| Quilez smin + Museth VDB | 2 + 1 | `sdf_body.py`, `sdf_extract.py` (§28.L10-1/2, default) | corpo fechado em 1–3.6 s contra 25–35 s da união booleana; IoU ≥ união −.01 em 5/5 (ficha 09) |
| Halladay (2016) + Pöyry (2018) — atlas e mips | 2 + 1 | `shared_atlas` (`COL = 2`), `surfaces.pack_cells` (`align`, `pad`), `mesh_lint.mip_bleed` (§27.T1/T2/T6) | bleed de mip medido e padding por célula no atlas; default desde a Leva 9 (ficha 08) |
| SoftRas (2019) + GenDR (2022) + PyTorch3D (padrão) | 3 + 3 + 1 | `soft_sil.py`, `optimize_verts` `GRAD="soft"` (§26.L8-1/2, default) | gradiente 0.46 s vs 1.52 s; soft-120 ≥ fd-120 em 13/15 vistas; slivers caem 5/5 (ficha 07). **Único paper de reconstrução que virou default** — e como optimizador, não como reconstrução |
| Le — gradient texturing (2026) | 1 | `surfaces.ramp_slot`, `paint_cel`, atlas partilhado (§19.C1/C2, L6-11) | rampa cel por célula é a textura default; rampa fixa foi negativa e saiu (papers/README) |
| Chen et al. 2023 — Robust Low-Poly Meshing | 6 | `mesh_lint` (manifold, watertight, `normal_diff`, `components`), `form_cost`, `--budgets` (§19.A1, §24.L6-6/10) | a régua de malha de todas as levas; gate `components` apanhou n00U com 2 corpos (ficha 09) |
| Wiersma — ALPS (2026) | 6 | `mesh_lint.fairness/sliver_pct`, `preflight.symmetry`, guarda entre fases do deform | métricas default; `optimize_verts` (L6-7) ficou opt-in |

## Grupo B — muito código, pouco resultado no juiz

| paper | linhas | onde entrou | resultado medido |
|---|---|---|---|
| Sano, Date, Kanai (2026) — low-poly por projecções | **17** | `silhouette.outline/douglas_peucker/snap_axes`, `cut_hull`, `massing` (box_rings, lathe, hull_profile), `segment_sheet`, `depth_rule`, `inscribe.carve/pull_red` (levas 1, 5–7, 12–13) | contorno no brief e massing por partes são a base do spec; mas spill ≤ .03 em **0/36 vistas** (L12-10b, ficha 11), inscribe fecha só n01X (L13-5, ficha 12) |
| Guillard et al. — Sketch2Mesh (2021) | **13** | `fit_spec` (D1, +.10–.15 IoU, ficha 01), `parts_fit`, `deform_to_sheet`, `align_features`, `optimize_verts`, `joint_term`, `leg_spill` (levas 1, 4–7) | o primeiro `fit_spec` deu o 1.º PASS do n005 (ficha 01); as camadas seguintes (deform, fit-parts, fit-joints) deslocam o spill em centésimos e o juiz de forma não muda (fichas 11–12); PASS honesto 0/6 na Leva 12 |
| Gao, Wu, Pan (2022) — edifícios | 2 | `building_hull`, `massing_spec` | sem bateria de edifícios medida com juiz — a preencher |
| Laurentini — visual hull (1994) | 1 | `inscribe.hull_grid/carve` (L13-5) | inscribe-by-construction: fecha o gate só em n01X (ficha 12) |
| Chatterjee et al. (CVT por curvatura) + Valette–Chassery ×2 | 1 + 2 | `retopo.cvt/lloyd/dual_faces` (L11-6, opt-in `--sdf-retopo cvt`) | malha mais bonita (slivers < 5 % 5/5, fairness 24–27 → 17–19) mas IoU pior vista −.012…−.028 em 5 unidades (ficha 10); forma não moveu |
| Cohen-Steiner — VSA (2004) | 1 | `look.regions` (L12-9) | métricas default, `--look-*` opt-in; crease recall +.08 (alvo +.15), wire entropy não mexe (ficha 11) |
| Botsch–Kobbelt — remalhagem (2004) | 1 | `retopo.remesh` (L10-4) | negativa: fairness pior, juiz forma contra; opt-in (ficha 09) |
| Kato — N3MR (2018) · Niemeyer — DVR (2020) · DIB-R++ (2021) | 1 + 1 + 1 | `dihedral_term` (L8-4), `soft_asym` (L8-5), `fit_luma` (L8-8) | opt-in: diedro custa IoU −.01/−.02; assimétrica neutra; luma piora n01X (ficha 07) |
| Depth Anything V2 (2024) | 2 | `depth_map`, `fit_spec --depth` (L5-4b), `landmark_calibration` (L12-8) | `z_err ≤ .05 H` em 2/6; `--depth` no-op por dados (fichas 11–12); opt-in |
| Lewis 1995 — NCC | 1 | `side_iou`, `--flip-side` (L11-0) | hfoo left não sobe (ficha 10); opt-in |

## Grupo C — só ideia, sem modelo (ou juiz negativo)

| paper | linhas | o que entrou | estado |
|---|---|---|---|
| MeshGPT (2024) | 1 | métricas de malha, `render_wire`, eixos do `review.md` | gerador vetado; só régua |
| EdgeRunner (2024) | 4 | `BACK_PROP_DEPTH`, `MIN_TRIS`, `balance`, `sides` por membro | ideias de orçamento; nenhuma linha gera malha |
| MeshAnything (2024) · Meshy T2 (2026) | 1 + 1 | docstring do `retopo.py`; grade 96³ e "peças = componentes" no `sdf_body` | só a ideia; geradores imagem→3D vetados por regra do projecto |
| ULIP (2023) | 1 | `clip_score.py` (§19.E2) | **negativo**: CLIP não separa forma (ficha 01) |
| Begemann–Hutson (2026) · Zhao et al. (2026) | 1 + 1 | bloco Readiness, `best_of_n`, score tempo/qualidade | contexto; sem efeito medido no juiz |

Fora dos três grupos, os papers de agente (Self-Refine, Idea2Img → `eye_stage`, L15-5; Reflexion, CRITIC → `eye_critic`, L16-2; Zheng et al. →
`review_pair --votes`, L17-1): 1 linha cada. L15-5 é o item que moveu semelhança ao concept (sheet/artista/wc3 4-0 em 18/18 pares, ficha 12);
L16-2 foi negativo (ficha 13); L17-1 parcial (ficha 14).

## Tese do balanço

1. **Os papers de reconstrução assumem input coerente** (scan, nuvem de pontos, foto, esboço único). O input aqui é um desenho cartoon com 3 vistas
   que não batem entre si (ficha 10: pique vertical no front, diagonal no left; ficha 11: rts incoerente do n017). Os termos de custo por vista
   competem, e o gate honesto não fecha: 0/36 vistas com spill ≤ .03 depois de 30 linhas de Sano + Sketch2Mesh (fichas 11–12).
2. **O que moveu semelhança ao concept foi o laço VLM que vê** (L15-5, fichas 12–13): 4-0 em 18/18 pares contra o baseline e 18/18 contra o
   controlo justo — sem paper de geometria por trás, só Self-Refine/Idea2Img como forma do laço.
3. **O que moveu forma foi a união** (L17-2, ficha 14): forma ≥ 3-1 em 5/6 a 8 votos, com smin + surface nets + QEM — papers do grupo A reaproveitados,
   não papers novos.
4. Os papers do grupo A são todos de **medida ou de malha** (cor, decimação, atlas, lint, gradiente): resolvem o que é determinístico e mensurável.
   Os do grupo B tentam resolver **forma a partir de vistas** e param no mesmo tecto que o modelo de forma permite (ficha 11, conclusão).

| grupo | papers | linhas em `references.md` | que viraram default |
|---|---|---|---|
| A — default e resolveu | 12 | 30 (a linha "Quilez; Garland" conta uma vez) | 12 |
| B — código sem juiz | 14 | 44 | 0 (só métricas) |
| C — ideia / negativo | 7 | 10 | 0 |
| agente (laço, crítico, juiz) | 5 | 5 | L15-5 sim; L16-2, L17-1 não |

(As 97 linhas incluem ainda Knodt–Gao 1, Saved Pixel 2, Android docs 1, Pokorný 1, Lorensen 1, Hertzmann/Northrup 1, Zhukov 1: 8 linhas de
textura/contorno/contexto, não classificadas.)

## O que isto muda para a Leva 18+

- Parar de gastar levas em **geometria por silhueta**: três levas (12–14) de papers de reconstrução não moveram o juiz; a lacuna que restava (forma
  contínua) fechou com a união (L17-2), que já é código nosso.
- O eixo aberto é **textura e leitura do concept**: a pintura procedural (L17-3) atingiu as estatísticas do WC3 e perdeu 8-0 por falta de área de atlas;
  a ordem certa é fundir cores em ≤ 12 materiais → unir → pintar ilhas grandes (ficha 14). Nenhum dos 22 PDFs trata disto; os que entram agora são de
  pintura/NPR (Hertzmann–Zorin, Zhukov) e de atlas (Halladay, Pöyry), já no grupo A.
- Erros que nenhum gate vê (ficha 15: olhos que o concept não tem) vêm de **defaults no prompt e no brief**, não de geometria: a próxima régua é texto
  (lista de identidade) contra o modelo, não IoU.
- O custo que escala era a chamada ao VLM no `v18-r0` (92 % do tempo, só olho); no roster-v6 o artista é 26 % do estágio de modelo e ≈ 65 % é pré-olho (massing, fit, SAM2, TripoSplat) — ver `04-resultados-e-descobertas.md`. Novos papers só entram se reduzirem rondas, chamadas **ou** o tempo do pré-olho.

## Adenda 2026-11-07 — modelos neurais como molde, não como gerador (fichas 18–19)

Entre 2026-11-04 e 11-07 entraram dois modelos neurais no default do estágio de modelo, com uma regra nova que não cabe nos grupos A–C:
são **moldes invisíveis para a malha** (`neural_molds.py`, venv próprio, nunca importado pelo pipeline; a malha continua a ser as primitivas
do artista + a nossa união). Ainda não têm linha em `castle_fight/docs/references.md` (a registar; Hunyuan3D-2.1 já tem, linha 304, pelo `eye_project`).

| paper / modelo | onde ficou | efeito medido (n = 2, replay, 1 trajectória; ruído declarado .12) | default? |
|---|---|---|---|
| SAM 2 (Ravi et al., 2024; `facebook/sam2.1-hiera-large`) | `--part-masks sam2` (máscara por peça com o `box2d` do `parts.json` como prompt), `--eye-mold masks` (casco front + left das máscaras do corpo) | molde de massa: n02S front/left +.041/+.037 só com o molde (replay, sem LLM), +.047/+.050 com juntas; n01G +.012/−.022, rts +.067 (ficha 18); correu nas 165 unidades do roster-v6 (ficha 19) **sem braço off**: efeito em largura não medido | sim (2026-11-04/05) |
| TripoSplat (VAST, 2026) | `--depth-model triposplat` (um splat do painel front, z-buffer ortográfico front + left; substitui Depth Anything V2 como fonte de `--depth`), `--eye-mold splat` | molde de profundidade; perfil fino (não sabe do pescoço/corcunda): n02S +.026/+.011, menos que `masks`; ≈ 350 s por unidade (≈ 16 h de máquina nas 165) por um ganho medido só numa unidade | `--depth-model` sim; `--eye-mold splat` não |

O que isto muda na tese do balanço: o ponto 1 ("papers de reconstrução assumem input coerente") continua — o TripoSplat só vê o painel front e dá um
perfil errado onde o concept tem 3 vistas incoerentes; o que serve é o **segmentador** (SAM2), porque mede o desenho por peça, que é a unidade do nosso
pipeline, e não tenta reconstruir. A regra do projecto (sem geradores imagem→3D) mantém-se: o splat nunca vira malha.

## Conclusão (1 frase para o paper)

Dos papers na tabela, viraram default os que medem ou simplificam malha e cor (12 papers, 30 linhas) e nenhum dos que reconstroem forma a partir de vistas
(14 papers, 44 linhas), porque o input é um cartoon com vistas incoerentes e não um scan — o que fechou semelhança foi um laço VLM que vê, e o que fechou
forma foi uma união com ferramentas que já estavam no default.
