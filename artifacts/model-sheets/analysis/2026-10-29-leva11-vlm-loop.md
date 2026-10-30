# Leva 11 — DFS: VLM no loop sobre o modelo (2026-10-29) — PLANEJAMENTO (nada implementado)

Reservada pelo usuário em 2026-10-29 ("fase D" da proposta CSG→SDF): só depois de a Leva 10 fechar a forma one-shot. A Leva 10
fechou com `BODY = "sdf"` default (PIPELINE §28.L10-9). Geradores (Meshy T2 e cia) continuam só como ideias. Regras: textura
procedural, sem image-to-3D, BFS primeiro — por isso a leva é um laço **guardado**: cada rodada só é aceite se nenhuma vista cair.

## 1. O que já existe (reaproveitar, não reescrever)

| peça | onde | estado |
|---|---|---|
| Diagnóstico VLM por vista/peça (vermelho/verde → causa → correção, "três mudanças em ordem", dono fit/autor/sheet) | `diagnose.py`, `spec_pipeline.run_diagnose` (§22.L4-8) | saída só; 45 s, ~4 k tokens; não volta ao modelo |
| Repair com peças congeladas (preflight → patch parcial) | `spec_pipeline.repair` (§20.S1) | só erros de preflight; não lê imagens |
| Passes por vista (`--passes left,rts`) | `spec_pipeline` | LLM reescreve o spec vista a vista; sem gate de "não piorar" |
| Fit numérico (Powell) e por gradiente (Adam, raster suave) | `fit_spec.py`, `fit_grad.py` (§26.L8-7) | parâmetros por peça já existem: é onde "restrições de volume" entram |
| Juiz pareado 4 votos A/B trocados | `review_pair` | mede rodada N × rodada 0 |
| Corpo SDF em 1–4 s + silhouette 6 vistas | `build_unit --body sdf`, `silhouette.py --tilts` | uma rodada custa ~2 min sem LLM; câmeras fixas comparam rodadas |

Diagnóstico de v13 já diz o que o laço faria: hfoo left (.415) = sheet lateral espelhado (figura olha para a direita da imagem) +
pique vertical vs diagonal no sheet; n02X left = ombros; n00U rts = pernas; n017 rts/left = juntas engordadas pelo `smin`.

## 2. Desenho

```
rodada 0 = pipeline atual (spec autor → fit → sdf → deform → verts → silhouette, câmeras fixadas)
repetir até N (default 2):
  diagnose(rodada k)  → deltas estruturados por peça (schema fechado, limites)
  aplicar deltas      → spec k+1 (parse_spec + preflight; peças não citadas congeladas)
  rebuild (sdf, mesmas câmeras) → silhouette k+1
  aceitar k+1  sse  nenhuma vista cai > 0.01  e  (média sobe ≥ 0.005  ou  um gate que falhava passa)
  senão       → descartar, tentar o delta seguinte da lista (até 3 por rodada), depois parar
juiz pareado: melhor rodada × rodada 0 (forma, sheet)
```

Schema dos deltas (saída do VLM, validada antes de aplicar; qualquer campo fora do schema descarta o delta inteiro):

```json
{"deltas": [{"part": "spine", "action": "scale", "axis": "x", "value": 0.8, "why": "pack too wide in top/rts"},
            {"part": "forearm.L", "action": "radius", "value": 1.3},
            {"part": "head", "action": "move", "axis": "y", "value": 0.02},
            {"part": "spine.pack", "action": "add", "kind": "lathe", "dims": [0.2, 0.08, 0.08], "at": [0, 1.35, -0.3]}],
 "expected": {"left": 0.05, "top": 0.03}}
```

Limites: `scale`/`radius` em [0.7, 1.4]; `move` ≤ 0.08 H por eixo; `rotate` ≤ 25°; `add` ≤ 2 peças por rodada, cada ≤ 10 % do
volume; `remove` só peças < 2 % da figura. Tudo o que o preflight já proíbe continua proibido (o delta é um spec novo).

## 3. Itens

| # | item | módulo | aceite | tempo |
|---|---|---|---|---|
| L11-0 | **flip lateral medido** (BFS, pré-requisito): `silhouette.py` testa o espelho horizontal nas vistas left/right/rts e guarda `flipped`; `fit`/`deform` usam a mesma escolha | `silhouette.py`, `fit_spec`, `deform_to_sheet`, relatório `sheet` | hfoo left .415 → ≥ .60 sem mudar o spec; as outras 4 unidades não mudam > 0.005; teste com sheet sintético espelhado | 60 min |
| L11-1 | schema de deltas + aplicação ao spec com peças congeladas + limites | `diagnose.py` (prompt pede `deltas`), novo `apply_deltas.py`, `preflight` | 10 deltas sintéticos aplicam e reconstroem; fora de limite → rejeitado com motivo; `parse_spec` passa | 60 min |
| L11-2 | laço guardado (`--loop N`): rebuild sdf com câmeras fixas, aceite por rodada, log por delta (aceite/rejeitado/Δ por vista) | `spec_pipeline` (`loop_stage`), `history` por rodada | 5 unidades v13: nenhuma vista cai > 0.01 na rodada aceite (por construção); custo ≤ 3 min/rodada; log legível | 90 min |
| L11-3 | deltas como restrições do fit em vez de edição do spec (ablação): o delta vira limite/alvo por peça no `fit_grad` | `fit_grad.py` (bounds por peça), `apply_deltas` | mesma entrada, 2 vias; vence a que sobe mais a média sem queda; relatório | 60 min |
| L11-4 | bateria **v14** (5 unidades, `--loop 2`, autor session:opus, pareada contra v13) + ficha | `v14.sh`, `history/…-v14/`, `melhorias/10-…` | PASS ≥ 4/5; média das 6 vistas ≥ v13 em 5/5 (rodada 0 = v13 por construção); juiz forma ≥ 3-1 em ≥ 3/5; custo ≤ +4 min e ≤ +15 k tokens por unidade; default `--loop` só se tudo passar | bateria |
| L11-5 | `k` do `smin` por junta (custo real do SDF na v13: rts −.03): k = 0 nas pernas/braços, 1 no tronco, medido no controle `v13-r1-union` | `sdf_body.pair_k`, `build_unit sdf_k=` | n017/hfoo rts ≥ união −0.01; slivers e nd não pioram | 45 min |

Ordem: L11-0 → L11-1 → L11-2 → {L11-3 ∥ L11-5} → L11-4. Tudo atrás de flag até a v14.

## 4. Riscos e respostas
- VLM inventa: schema fechado, limites, aceite por medida (uma rodada que piora é descartada, nunca "confiada").
- Sheet incoerente (pique vertical vs diagonal, lateral espelhada): L11-0 resolve o espelho; incoerência já é marcada em
  `sheet.coherence` e a vista incoerente não gera delta.
- Custo: 1 chamada VLM por rodada (não por vista); rebuild sdf 1–4 s; silhouette ~60 s; teto N = 2.
- Overfit às 5 unidades: v14 nas mesmas 5 + `sdf_batch.py` nas 10 (sem LLM) continua a regressão de forma.
- DFS versus BFS: o laço nunca substitui a rodada 0; se `--loop` não virar default, a saída one-shot é a mesma de hoje.

## 5. Fora
- Gerar malha com Meshy/TRELLIS/etc. (vetado). Pintar/texturizar pelo VLM (textura procedural). Loop sobre o estágio de cor
  (só forma). Mais de 2 rodadas por default (custo).
