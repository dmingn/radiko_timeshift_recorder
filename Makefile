.PHONY: test
test:
	pipenv run mypy .
	pipenv run python -m pytest -svx
