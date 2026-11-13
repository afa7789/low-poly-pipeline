# IA_gen_paper — PDF do paper inteiro (ordem do README): pandoc + tectonic (XeTeX), fontes DejaVu.
PANDOC   ?= pandoc
ENGINE   ?= tectonic
FICHAS    = $(sort $(wildcard melhorias/[0-9][0-9]-*.md))
SRC       = 01-tese.md 00-baseline.md TIMELINE.md 02-evolucao.md 04-resultados-e-descobertas.md 05-avaliacao-humana-vs-juiz.md $(FICHAS) 03-balanco-papers.md
HEADER    = ferramentas/pandoc-header.tex
TITLE     = Geração de modelos 3D low-poly por IA — Castle Fight (registo das melhorias do pipeline)

.PHONY: pdf build run clean lint test

pdf: paper.pdf
build: pdf
run: pdf
	open paper.pdf

paper.pdf: $(SRC) $(HEADER) Makefile
	$(PANDOC) $(SRC) -o $@ \
	  --from markdown+pipe_tables+raw_tex --pdf-engine=$(ENGINE) \
	  --toc --toc-depth=2 --resource-path=. \
	  -H $(HEADER) \
	  --metadata title="$(TITLE)" --metadata date="$$(date +%Y-%m-%d)" --metadata lang=pt-BR \
	  -V papersize=a4 -V fontsize=9pt -V geometry:margin=1.6cm \
	  -V mainfont="DejaVu Sans" -V monofont="DejaVu Sans Mono" -V monofontoptions=Scale=0.85 \
	  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue
	@mdls -name kMDItemNumberOfPages -raw paper.pdf 2>/dev/null | xargs -I{} echo "paper.pdf: {} páginas" || true

lint:
	@for f in $(SRC); do test -f $$f || { echo "falta $$f"; exit 1; }; done; echo "fontes ok: $(words $(SRC)) ficheiros"

test: lint
	$(PANDOC) $(SRC) -t plain -o /dev/null && echo "pandoc parse ok"

clean:
	rm -f paper.pdf
