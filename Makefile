.PHONY: help install install-dev data train samples dashboard test lint format clean

help:
	@echo "install      install runtime dependencies"
	@echo "install-dev  install all dependencies"
	@echo "data         download the PTB-XL dataset"
	@echo "train        run the full training pipeline"
	@echo "samples      write demo ECGs for the dashboard"
	@echo "dashboard    launch the Streamlit app"
	@echo "test         run the test suite"
	@echo "lint         check style"
	@echo "format       apply formatting"

install:
	poetry install --only main

install-dev:
	poetry install

data:
	bash scripts/download_data.sh

train:
	poetry run python -m ecg_afib.main

samples:
	poetry run python scripts/make_samples.py

dashboard:
	poetry run streamlit run src/ecg_afib/streamlit_app.py

test:
	poetry run pytest

lint:
	poetry run ruff check src tests scripts

format:
	poetry run ruff format src tests scripts

clean:
	rm -rf .pytest_cache .ruff_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
