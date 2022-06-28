# Platform constants
ifeq ($(OS), Windows_NT)
	PY = python
	VENV_SUBDIR = Scripts
	DEL = rmdir /Q /S
else
	PY = python3
	VENV_SUBDIR = bin
	DEL = rm -rf
endif

# Virtual environment name and its paths
VENV_NAME = venv
export VENV_PATH := $(abspath ${VENV_NAME})
export PATH := ${VENV_PATH}/$(VENV_SUBDIR):${PATH}

.PHONY:  # Ensures this only runs if a virtual environment doesn't exist
${VENV_NAME}: requirements.txt requirements-dev.txt
	$(PY) -m venv $(VENV_NAME)
	pip install -r requirements.txt -r requirements-dev.txt

# Directory paths
BASE_DIR := $(VENV_PATH)/../game
WINDOW_PATH = $(BASE_DIR)/window.py
RESOURCES_PATH = $(BASE_DIR)/resources


# -------------------- Builds --------------------
prepare-venv: ${VENV_NAME}  # Creates a virtual environment if one doesn't exist

fresh-venv:  # Creates a fresh virtual environment
	$(DEL) "$(VENV_PATH)"
	make prepare-venv

pre-commit:  # Runs pre-commit
	pre-commit run --all-files

build:  # Builds the game with nuitka
	nuitka "$(BASE_DIR)"\
 	--standalone\
 	--follow-imports\
 	--include-data-dir="$(RESOURCES_PATH)"=resources\
 	--enable-plugin=numpy