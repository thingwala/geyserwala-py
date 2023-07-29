PYPI_USER=thingwala

.PHONY: test

check:
	flake8 ./thingwala/geyserwala --ignore E501
	find ./thingwala/geyserwala -name '*.py' \
	| xargs pylint -d invalid-name \
	               -d missing-docstring \
	               -d line-too-long \

test:
	pytest ./test/ -vvv --junitxml=./reports/unittest-results.xml

to_pypi:
	pip install build twine

to_pypi_test: test
	python -m build
	TWINE_USERNAME=${PYPI_USER} twine upload -r testpypi dist/thingwala_geyserwala-$(shell cat ./version)*

to_pypi_live: test
	python -m build
	TWINE_USERNAME=${PYPI_USER} twine upload -r pypi dist/thingwala_geyserwala-$(shell cat ./version)*
