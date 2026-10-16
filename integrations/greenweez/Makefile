export DBT_PROFILES_DIR ?= .github/dbt-profiles
DBT = dbt

.PHONY: setup seed build test lint docs demo clean build-gsheet demo-gsheet load-gsheet-real build-gsheet-real demo-gsheet-real

setup:            ## install Python deps and dbt packages
	pip install -r requirements.txt
	$(DBT) deps

seed:             ## regenerate and load the synthetic raw data (DuckDB)
	python scripts/generate_seed_data.py
	$(DBT) seed

build:            ## load seeds, then build + test every model on the DuckDB demo target
	$(DBT) seed --target demo
	$(DBT) build --target demo --exclude resource_type:seed

test:             ## run only the tests (after `make build`)
	$(DBT) test --target demo

lint:             ## sqlfluff + yamllint
	sqlfluff lint models tests
	yamllint .

docs:             ## generate and serve dbt docs
	$(DBT) docs generate --target demo
	$(DBT) docs serve --target demo

demo: build       ## build, then open the Streamlit dashboard
	pip install -r demo/requirements.txt
	streamlit run demo/app.py

clean:
	rm -rf target dbt_packages logs

build-gsheet:     ## same pipeline fed by the order-level Google Sheets export (synthetic seeds on DuckDB)
	$(DBT) seed --target gsheet
	$(DBT) build --target gsheet --vars '{source_system: fvt_gsheet}' --selector fvt_gsheet --indirect-selection cautious --exclude resource_type:seed

demo-gsheet: build-gsheet   ## dashboard on the Google Sheets export shape (synthetic seeds)
	pip install -r demo/requirements.txt
	DEMO_DB=target/gsheet.duckdb DEMO_DATA_LABEL="Synthetic copy of the Google Sheets export" streamlit run demo/app.py

load-gsheet-real:  ## copy the real fvt_gsheet tables from BigQuery (read-only) into target/gsheet_real.duckdb
	pip install -r scripts/requirements-bq.txt
	python scripts/load_gsheet_from_bigquery.py

build-gsheet-real: load-gsheet-real  ## build the marts on the real Google Sheets data
	$(DBT) build --target gsheet_real --vars '{source_system: fvt_gsheet}' --selector fvt_gsheet --indirect-selection cautious --exclude resource_type:seed

demo-gsheet-real: build-gsheet-real  ## dashboard on the real Google Sheets data (needs GOOGLE_APPLICATION_CREDENTIALS)
	pip install -r demo/requirements.txt
	DEMO_DB=target/gsheet_real.duckdb DEMO_DATA_LABEL="Google Sheets export (real data, 2021-10-01 to 2021-10-15)" streamlit run demo/app.py
