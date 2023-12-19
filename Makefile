lint:

	find . -name "*.py" -not -path "*venv/*" -not -path "*virtualenv*" | xargs black --line-length 79

clean:

	find . | grep -E "(__pycache__|\.pyc|\.pyo|\.pytest_cache|\.egg-info|\.zip)" | grep -v ".venv" | grep -v "build.sh" | xargs rm -rf

copy-core-to-functions:

	cp -R core functions/packages/cron/hourly/
	cp -R core functions/packages/cron/daily/
	cp -R core functions/packages/airtable/dedupe_views/
	cp -R core functions/packages/airtable/consolidate_eg_requests/
	cp -R core functions/packages/airtable/timeout_eg_requests/
	cp -R core functions/packages/airtable/update_field_value/
	cp -R core functions/packages/mailjet/update_lists/
	cp -R core functions/packages/website/update_request_data/

remove-core-from-functions:

	rm -rf functions/packages/*/*/core

deploy-functions:

	make remove-core-from-functions
	make copy-core-to-functions
	doctl serverless deploy functions --env ./.env --verbose --trace
	make remove-core-from-functions

run-daily:

	cd functions/packages/cron/daily && python __main__.py

run-hourly:

	cd functions/packages/cron/hourly && python __main__.py

test-core:

	cd core && pytest -vv . --ignore=tests/test_security.py

test-app:

	cd app && pytest -vv .
