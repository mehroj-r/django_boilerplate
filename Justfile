set dotenv-load := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default:
    @just --list

help:
    @just --list

# Sync template dependencies to root for IDE support
sync:
    python scripts/sync-deps.py

# Generate a test project
test-gen:
    python scripts/generate-project.py ./build --no-input --force

# Run tests in a newly generated test project
test: test-gen
    cd ./build && uv sync && uv run src/manage.py test

# Clean up generated test projects
clean:
    rm -rf ./build

# Run the template's own test suite (generation matrix + patch engine)
test-template:
    uv run pytest tests -q

# Lint the code using ruff and ty
lint:
    ruff check .
    ty check .

# Format the code using ruff
format:
    ruff format .