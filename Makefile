lint:

	find . -name "*.py" -not -path "*venv/*" -not -path "*virtualenv*" | xargs black --line-length 79

clean:

	find . | grep -E "(__pycache__|\.pyc|\.pyo|\.pytest_cache|\.egg-info|\.zip)" | grep -v ".venv" | grep -v "build.sh" | xargs rm -rf

prepare-functions:

	./functions/prepare-functions.sh

cleanup-functions:

	rm -rf functions/lib/core/
	rm -f functions/packages/*/*/.ignore
	rm -f functions/packages/*/*/build.sh

deploy-functions:

	make prepare-functions
	doctl serverless deploy functions --env ./.env --remote-build --verbose --verbose-build --trace
	make cleanup-functions

run-daily:

	cd functions/packages/cron/daily && python __main__.py false

run-hourly:

	cd functions/packages/cron/hourly && python __main__.py false

test-core:

	cd core && pytest -vv .

test-app:

	cd app && pytest -vv .
