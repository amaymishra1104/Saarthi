.PHONY: dev test build run reset

dev:
	@echo "Starting SAARTHI Backend and Frontend..."
	@powershell -ExecutionPolicy Bypass -File ./run_saarthi.ps1

test:
	@.\.venv\Scripts\pytest -v

build:
	@cd frontend && npm run build

reset:
	@curl -X POST http://localhost:8000/api/admin/reset

