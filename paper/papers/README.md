# Papers lidos pelo pipeline de modelos (cópia dos PDFs do Desktop, 2026-10-29)

Fontes: `~/Desktop/genAI/` (10 PDFs, baixados 2026-10-20; `MANIFEST.md`, `readme.txt`, `references.bib`) e
`~/Desktop/Differentiable_Rendering_DOIs_20261021/` (12 PDFs; `DOI_manifest.json`, `DOIs_list.md`). O que foi aplicado está em
`castle_fight/docs/references.md` (uma linha por paper usado, com módulo e seção do PIPELINE) e nas fichas `melhorias/0N-*.md`.

## genai/ — levas 1–7 (fichas 01–06)

| PDF | Uso no pipeline | Estado |
|---|---|---|
| Sano_2025_LowPoly_Mesh_from_Point_Clouds | silhuetas por vista, `cut: sheet` (casco), massing por partes, acoplamento vermelho/verde | aplicado (levas 1, 5, 6) |
| Sketch2Mesh_2021 | deformação do contorno para o sheet (`deform_to_sheet`), corpo vs prop, 6 vistas | aplicado (levas 6, 7) |
| Wiersma_2026_Gradient_Descent_ALPS | `optimize_verts` (IoU + chamfer + Laplaciano, line search, recusa de sliver), guarda entre fases | aplicado (leva 6; gradiente analítico na leva 8) |
| Chen_2023_Robust_Low-Poly_Meshing | união booleana do corpo, `clean_mesh`, decimação por tolerância, gates de `mesh_lint` | aplicado (leva 6) |
| EdgeRunner_2024 / MeshGPT_2024 | só métricas de malha (orçamento, arestas vivas); geradores autoregressivos vetados | parcial (métricas) |
| ULIP_2023 | CLIP/ULIP como juiz | negativo (E2: CLIP não separa forma) |
| Le_2026_Optimising_3D_Textures | rampa cel por célula, atlas compartilhado | aplicado (C1/C2, L6-11; rampa fixa negativa) |
| Begemann_Hutson_2026 / Zhao_2026 | contexto (pipelines humanos vs IA; Meshy/Hunyuan/Tripo) | referência; geradores image-to-3D vetados |

## diffrender/ — leva 8 (ficha 07; análise em `castle_fight/artifacts/model-sheets/analysis/2026-10-29-papers-diffrender.md`)

| # | PDF | Uso | Estado |
|---|---|---|---|
| 01 | SoftRas (ICCV 2019) | `soft_sil.py` raster suave; gradiente de `optimize_verts` e `fit_grad` | aplicado (L8-1, L8-2, L8-7) |
| 02 | Neural 3D Mesh Renderer (CVPR 2018) | regularizador de diedro | aplicado, negativo (L8-4, opt-in) |
| 03 | PyTorch3D (2020) | padrão de desenho do raster (não é dependência) | aplicado (L8-1) |
| 04 | DVR (CVPR 2020) | perda assimétrica vermelho/verde | aplicado, neutro (L8-5, opt-in) |
| 05 | MCViNE (NIMA 2016) | — (nêutrons; DOI fora de domínio) | n/a |
| 06 | DiffusionAvatars (CVPR 2024) | — (difusão; loop modelo→sheet viola BFS) | vetado |
| 07 | AvatarStudio (2023) | — (SDS/nvdiffrast) | vetado |
| 08 | Inverse rendering translúcido (CVPR 2023) | — (fotorealismo) | n/a |
| 09 | Polarimetric inverse rendering (TMM 2024) | — | n/a |
| 10 | DIB-R++ (NeurIPS 2021) | luma por shading diferido (`fit_luma`) | aplicado, negativo (L8-8, opt-in) |
| 11 | DIB-R (NeurIPS 2019) | alpha de fundo = variante de distribuição; câmera por gradiente | não usado em código (grade de câmera já exata) |
| 12 | GenDR (CVPR 2022) | distribuições (uniforme, logística, gamma_inv), Yager(2), anelamento de τ | aplicado, neutro (L8-3, opt-in) |
