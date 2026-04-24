.PHONY: install refresh serve clean

PYTHON ?= .venv/bin/python
PORT ?= 8000

install:
	python3.13 -m venv .venv
	.venv/bin/pip install -e .

refresh:
	$(PYTHON) -m pipeline.build
	cp games.json docs/games.json

serve:
	@test -f docs/games.json || (echo "docs/games.json missing — run 'make refresh' first" && exit 1)
	cd docs && $(PYTHON) -m http.server $(PORT)

clean:
	rm -rf cache games.json docs/games.json review.tsv
