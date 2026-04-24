.PHONY: install refresh serve clean

PYTHON ?= .venv/bin/python
PORT ?= 8000

install:
	python3.13 -m venv .venv
	.venv/bin/pip install -e .

refresh:
	$(PYTHON) -m pipeline.build
	cp games.json web/games.json

serve:
	@test -f web/games.json || (echo "web/games.json missing — run 'make refresh' first" && exit 1)
	cd web && $(PYTHON) -m http.server $(PORT)

clean:
	rm -rf cache games.json web/games.json review.tsv
