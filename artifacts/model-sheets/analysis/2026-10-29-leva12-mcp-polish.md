# Leva 12 — polimento final por Blender MCP, alguns minutos por modelo (2026-10-29) — PLANEJAMENTO (nada implementado)

Decisão do usuário (2026-10-29): "pelo menos alguns minutos de melhorias grossas com isso do MCP no final deveria ser feito, em cada
modelo". Referência: workflow público Opus + Blender MCP (modelar peça a peça, rig, clipes, cena de revisão fixa, listar o que está
errado antes de mexer) e Pokorný, *Using AI in Blender* (WSCG 2026, DOI 10.24132/CSRN.2026-D37): entre os add-ons de IA do Blender,
os "universais" (Blender GPT, Blender MCP) geram e executam Python na cena; os de modelagem/textura são geradores treinados (vetados
aqui); a lição prática do paper é que sem prompt preciso o resultado desvia — logo o passo precisa de brief fixo e gates.

## 1. O que o passo é (e não é)
- É: um estágio `polish` depois do clay final (pós-laço L11-2, pré-cor), em que um agente Claude, ligado ao Blender via MCP, vê a cena
  de revisão (clay + sheet + overlays + números das 6 vistas + diagnose) e faz **melhorias grossas** por Python na cena: mover/escalar/
  rodar peças, suavizar junta, fechar buraco, endireitar prop, alinhar pés ao chão, com orçamento de tempo fixo (3–5 min) e no máximo
  N operações. Cada operação fica gravada como script Python reproduzível (`polish.py` no run) e o clay só é substituído se os gates
  passarem (nenhuma vista cai > 0.01, `mesh_lint` limpo, tris ≤ orçamento, rig/clipes importam).
- Não é: esculpir à mão por horas, gerar malha/textura por IA (regra), texturizar (textura é procedural), nem substituir a rodada 0.

## 2. Pré-requisitos (L12-0)
- Instalar `blender-mcp` (addon no Blender 5.2 + servidor `uvx blender-mcp`), registar no Claude Code (`claude mcp add blender -- uvx
  blender-mcp`); hoje não está instalado (verificado: `uvx` existe, addon não). Smoke: abrir `clay.glb`, ler bbox, mover uma peça, exportar.
- Cena de revisão (`review_scene.py`): chão neutro, 6 câmeras fixas = as do `silhouette.json`, sheet pinado, overlays vermelho/verde, texto
  com IoU por vista e nome do run. Mesma cena para antes/depois.
- `polish` headless: o agente trabalha via MCP (Blender com UI aberta) **ou** via `blender -b` com o mesmo script; os dois caminhos
  produzem `polish.py` idêntico, para a bateria correr sem UI.

## 3. Itens
| # | item | aceite |
|---|---|---|
| L12-0 | instalar/ligar Blender MCP + cena de revisão + smoke | mover peça por MCP, exportar, `silhouette` igual ao headless |
| L12-1 | contrato do estágio `polish`: brief fixo, orçamento (tempo/N ops), `polish.py` gravado, gates depois, `review.md` ganha secção "Polimento" | 10 ops sintéticas aplicam e revertem; gate rejeita queda > 0.01 |
| L12-2 | prova em 3 unidades v14 (hfoo, n00U, n017: as CHECK e a quadrúpede), 5 min cada, antes/depois com juiz pareado | nenhuma vista cai; forma ≥ 3-1 em ≥ 2/3; custo ≤ 6 min/unidade |
| L12-3 | bateria v15 (5 unidades, autor + laço + polish) pareada com v14; ficha 11; matriz L11-7 reexecutada com o default novo | PASS ≥ 4/5; forma ≥ 3-1 em ≥ 3/5; default só se passar |

## 4. Riscos
- Reprodutibilidade: o agente decide diferente a cada corrida → o que fica é o `polish.py` e as medidas; a bateria repete o script, não o agente.
- Custo: 5 min × 233 edifícios + unidades = ~20 h de agente; aceitável em lote noturno, 2 Blenders em paralelo.
- Sheet incoerente (pique vertical vs diagonal): o polish não "corrige" o sheet; mexe só no modelo.
- Fora: geradores (3D Modeling Agent, AutoDepth, StableGen, Auto Painter, Meshy): vetados.
