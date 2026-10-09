lint:

	find . -name "*.py" -not -path "*venv/*" -not -path "*virtualenv*" | xargs black --line-length 79

clean:

	find . | grep -E "(__pycache__|\.pyc|\.pyo|\.pytest_cache|\.egg-info|\.zip)" | grep -v ".venv" | grep -v "build.sh" | xargs rm -rf

prepare-functions:

	./functions/prepare-functions.sh

cleanup-functions:

	rm -rf functions/lib/
	rm -rf functions/packages/*/*/build.sh
	rm -rf functions/packages/*/*/.ignore
	rm -rf functions/packages/*/*/virtualenv
	rm -rf functions/packages/*/*/__deployer__.zip

deploy-functions:

	make cleanup-functions
	make prepare-functions
	doctl serverless deploy functions --env ./.env --verbose --trace
	make cleanup-functions

run-daily:

	cd functions/packages/cron/daily && python __main__.py false

run-hourly:

	cd functions/packages/cron/hourly && python __main__.py false
