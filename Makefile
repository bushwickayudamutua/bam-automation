lint:

	find . -name "*.py" -not -path "*venv/*" -not -path "*virtualenv*" | xargs black --line-length 79

clean:

	find . | grep -E "(__pycache__|\.pyc|\.pyo|\.pytest_cache|\.egg-info|\.zip)" | grep -v ".venv" | grep -v "build.sh" | xargs rm -rf

prepare-functions:

	./functions/prepare-functions.sh

cleanup-functions:

	rm -rf functions/packages/*/*/virtualenv
	rm -rf functions/packages/*/*/__deployer__.zip

remove-core-from-functions:

	rm -rf functions/packages/*/*/core

deploy-functions:

	make remove-core-from-functions
	make prepare-functions
	doctl serverless deploy functions --env ./.env --verbose --trace
	make remove-core-from-functions

run-daily:

	cd functions/packages/cron/daily && python __main__.py false

run-hourly:

	cd functions/packages/cron/hourly && python __main__.py false

test-core:

	cd core && pytest -vv .

test-app:

	cd app && pytest -vv .
