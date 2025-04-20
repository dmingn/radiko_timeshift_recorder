.PHONY: test
test:
	pipenv run mypy .
	pipenv run python -m pytest -svx -m "not radiko"
	pipenv run python -m pytest -svx -m "radiko"

.PHONY: up-server
up-server:
	docker compose up --build --remove-orphans

.PHONY: put-jobs-from-schedule
put-jobs-from-schedule:
	docker compose exec app python -m radiko_timeshift_recorder put-jobs-from-schedule --rules rules
