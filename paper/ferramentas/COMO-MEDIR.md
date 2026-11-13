# Como medir uma etapa nova

Usado para as 24 etapas de `02-evolucao.md` (n01X ×13, hfoo ×11). Mesmo procedimento para as próximas.

## Requisitos

| o quê | onde | para quê |
|---|---|---|
| repo `castle_fight` | `../castle_fight` (ou `--castle <path>`) | `check_gates.py`, `silhouette.py`, `render_unit.py` |
| Blender 5.2.x | `blender` no PATH | renders de silhueta e das vistas |
| ImageMagick | `magick` no PATH | tiras e montagens com legenda |
| Python 3 + numpy | — | `silhouette.py` |
| fonte Arial | `/System/Library/Fonts/Supplemental/Arial.ttf` | legenda (sem `-font` o magick falha) |
| sheet aprovado | `castle_fight/artifacts/model-sheets/refs/<unit>/sheet.jpg` | o juiz; o mesmo em todas as etapas |

Não usa API nem rede. Custa só tempo: ~10 s por etapa nova (2 chamadas de Blender), quase zero com cache.

## Passos

1. Gere o run no pipeline normalmente (fica em `castle_fight/artifacts/model-sheets/runs/draft/<unit>/<run>/model.glb`).
2. Adicione uma linha em `ferramentas/etapas.csv`:
   ```
   unit,order,stage,commit,glb,change
   n01X,14,v-nova,<hash>,artifacts/model-sheets/runs/draft/n01X/<run>/model.glb,<o que mudou em 1 frase>
   ```
   - `order` = posição cronológica (continua a numeração da unidade).
   - `glb` relativo à raiz do `castle_fight`.
   - `commit` = commit do pipeline que gerou o GLB.
3. Rode:
   ```bash
   cd /Users/afa/Developer/arthur/IA_gen_paper
   python3 ferramentas/medir_etapas.py --only n01X     # ou sem --only para todas
   ```
4. Saem:
   - `evolution-metrics.csv`: uma linha por etapa (tris, materiais, skins, clips, IoU f/l/b/top, IoU 32 px, gate);
   - `figuras/<unit>-<NN>-<stage>.png`: tira front | left | wc3 (câmera do jogo) com legenda;
   - `figuras/<unit>-evolucao.png`: sheet aprovado no topo e todas as etapas embaixo.
5. Confira a montagem com os olhos antes de citar o número.

## O que a ferramenta faz (em ordem)

1. `check_gates.stats(glb)`: lê o JSON do GLB e conta tris, materiais, skins e animações.
2. `silhouette.py <sheet> <glb> <cache>/sil`: renderiza máscaras ortográficas, normaliza pela altura,
   compara com os painéis do sheet e grava `silhouette.json`. Gate: front ≥ 0.75 e left ≥ 0.65.
3. `blender -b -P render_unit.py -- <glb> <cache>/views`: Eevee, mundo cinza, vistas front, left e wc3.
4. `magick`: legenda (`label:`) em cima de front+left+wc3 lado a lado, 960 px de largura.

Cache em `ferramentas/.cache/<unit>-<NN>-<stage>/`. `--force` refaz tudo. Apague o cache se mudar
`silhouette.py` ou `render_unit.py`, senão os números antigos voltam.

## Cuidados

- **Régua fixa.** Os números só se comparam se `silhouette.py` não mudou. Se mudar, rode `--force` em
  todas as etapas e anote o commit da régua em `02-evolucao.md`.
- **Mesmo juiz.** Se `refs/<unit>/sheet.jpg` for regenerado, as etapas antigas ficam incomparáveis.
- GLBs antigos podem ter nome diferente (`v3/n01X-argon.glb`, `v9/n01X-v9.glb`): confira o caminho no CSV.
- Ruído: duas runs iguais diferem até 0.12 de IoU. Etapa nova com 1 run só não prova ganho.
- Bug que já aconteceu: `-annotate` com `+append` cortava a legenda (offset de canvas). Por isso usamos
  `label:` + `+repage`.
