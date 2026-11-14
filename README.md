# low-poly-pipeline

Ferramenta para gerar modelos 3D low-poly (unidades e prédios) e animações para o jogo **Castle Fight**, feita com
Blender + Python e agentes de IA. Em andamento: funciona para o alpha, ainda em melhorias.

## O que tem aqui

| pasta | o quê |
|---|---|
| `tools/blender/` | o pipeline: construção dos modelos (`units/<id>.py`, `buildings_<raça>.py`), rigs/clipes, juízes de silhueta, gates |
| `tools/` | scripts auxiliares (instalar no jogo, lotes) |
| `tests/` | testes (`make test`) |
| `artifacts/model-sheets/` | `PIPELINE.md` (documentação longa), análises, viewer; saídas pesadas ficam fora do git |
| `paper/` | o paper (pt-BR): tese, baseline, evolução em 24 etapas, resultados de 165 modelos, avaliação humano vs juiz LLM, fichas de cada melhoria. `make -C paper pdf` gera o PDF |
| `docs/references.md` | papers usados e onde cada um entrou no pipeline |
| `AGENTS.md` | instruções para agentes de código (Claude Code, Codex...) |

## Rodar

Requisitos: `blender` 4.x e `python3.14` no PATH; `uvx` para o lint; `pandoc` + `tectonic` para o PDF do paper.

```bash
make link CF_GAME=/caminho/para/castle_fight   # liga dados/assets do jogo + pasta de saída ./output
make test                                      # testes
make lint                                      # ruff, complexidade <= 10
tools/blender/hand_review.sh hfoo biped        # gera e revisa uma unidade -> artifacts/model-sheets/hand/hfoo/
```

Sem o checkout do jogo dá para ler o código e o paper, mas as unidades não resolvem os dados (`data/*.tsv`,
`assets/`, sheets de concept).

## Fora do git

- `output/` (runs, renders, sheets): `CF_PIPELINE_OUT` muda o lugar.
- PDFs dos papers e baseline TRELLIS (~30 GB): numa pasta à parte, `CF_PAPER=<pasta>` com `papers/` e `baseline/`;
  `make link` liga em `paper/`. Veja `paper/papers/README.md` para a lista de papers.
