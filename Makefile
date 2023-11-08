.PHONY: help
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

install: ## install dependencies
	poetry install

download_ne_data: ## Download data from natural earth
	curl -o data/ne_110m_land.zip https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_land.zip
	unzip -o -d data/ne_110m_land data/ne_110m_land.zip
	curl -o data/ne_110m_lakes.zip https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_lakes.zip
	unzip -o -d data/ne_110m_lakes data/ne_110m_lakes.zip
	curl -o data/ne_50m_land.zip https://naturalearth.s3.amazonaws.com/50m_physical/ne_50m_land.zip
	unzip -o -d data/ne_50m_land data/ne_50m_land.zip
	curl -o data/ne_50m_lakes.zip https://naturalearth.s3.amazonaws.com/50m_physical/ne_50m_lakes.zip
	unzip -o -d data/ne_50m_lakes data/ne_50m_lakes.zip

proj_vis_background: ## Generates the background image for proj-vis
	poetry run python scripts/proj_vis_background.py

proj_vis_wgs84: ## Generates the WGS 84 map for proj-vis
	poetry run python scripts/proj_vis_wgs84.py

social_preview: ## Generates the social_preview image for this repository
	poetry run python scripts/social_preview.py

lint: ## Checks for linting errors
	poetry run flake8

update-engraver: ## upgrades map-engraver to latest version of master
	poetry remove map-engraver || true
	poetry add git+https://github.com/leifgehrmann/map-engraver.git
	poetry install
