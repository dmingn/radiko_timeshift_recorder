.PHONY: test
test:
	uv run mypy .
	uv run python -m pytest -svx -m "not radiko"
	uv run python -m pytest -svx -m "radiko"

.PHONY: up-server
up-server:
	docker compose up --build --remove-orphans

.PHONY: put-jobs-from-schedule-by-rules
put-jobs-from-schedule-by-rules:
	docker compose exec app sh -c "python -m radiko_timeshift_recorder put-jobs-from-schedule-by-rules /radiko_timeshift_recorder/rules/*.yaml"

.PHONY: clean
clean:
	@git clean -fdX out/
