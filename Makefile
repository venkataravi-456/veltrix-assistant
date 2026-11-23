.PHONY: test run install lint

test:
	pytest -v tests/

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

install:
	pip install -r requirements.txt
