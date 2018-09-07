# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://bitbucket.org/ned/coveragepy/src/default/NOTICE.txt

# Makefile for utility work on coverage.py.

default:
	@echo "* No default action *"

clean:
	-pip uninstall -y coverage
	-rm -f *.pyd */*.pyd
	-rm -f *.so */*.so
	-PYTHONPATH=. python tests/test_farm.py clean
	-rm -rf tests/farm/*/out
	-rm -rf build coverage.egg-info dist htmlcov
	-rm -f *.pyc */*.pyc */*/*.pyc */*/*/*.pyc */*/*/*/*.pyc */*/*/*/*/*.pyc
	-rm -f *.pyo */*.pyo */*/*.pyo */*/*/*.pyo */*/*/*/*.pyo */*/*/*/*/*.pyo
	-rm -f *.bak */*.bak */*/*.bak */*/*/*.bak */*/*/*/*.bak */*/*/*/*/*.bak
	-rm -f *$$py.class */*$$py.class */*/*$$py.class */*/*/*$$py.class */*/*/*/*$$py.class */*/*/*/*/*$$py.class
	-rm -rf __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__ */*/*/*/__pycache__ */*/*/*/*/__pycache__
	-rm -f coverage/*,cover
	-rm -f MANIFEST
	-rm -f .coverage .coverage.* coverage.xml .metacov*
	-rm -f tests/zipmods.zip
	-rm -rf tests/eggsrc/build tests/eggsrc/dist tests/eggsrc/*.egg-info
	-rm -f setuptools-*.egg distribute-*.egg distribute-*.tar.gz
	-rm -rf doc/_build doc/_spell
	-rm -rf .tox_kits

sterile: clean
	-rm -rf .tox*

LINTABLE = coverage tests igor.py setup.py __main__.py

lint:
	tox -e lint

todo:
	-grep -R --include=*.py TODO $(LINTABLE)

spell:
	-pylint --disable=all --enable=spelling $(LINTABLE)

pep8:
	pycodestyle --filename=*.py --repeat $(LINTABLE)

test:
	tox -e py27,py35 $(ARGS)

TOX_SMOKE_ARGS = -n 6 -m "not expensive" --maxfail=3 $(ARGS)

smoke:
	COVERAGE_NO_PYTRACER=1 tox -e py26,py33 -- $(TOX_SMOKE_ARGS)

pysmoke:
	COVERAGE_NO_CTRACER=1 tox -e py26,py33 -- $(TOX_SMOKE_ARGS)

metacov:
	COVERAGE_COVERAGE=yes tox $(ARGS)

metahtml:
	python igor.py combine_html

# Kitting

kit:
	python setup.py sdist --formats=gztar

wheel:
	tox -c tox_wheels.ini $(ARGS)

manylinux:
	docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /io/ci/manylinux.sh build
	docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_i686 /io/ci/manylinux.sh build

kit_upload:
	twine upload dist/*

kit_local:
	# pip.conf looks like this:
	#   [global]
	#   find-links = file:///Users/ned/Downloads/local_pypi
	cp -v dist/* `awk -F "//" '/find-links/ {print $$2}' ~/.pip/pip.conf`
	# pip caches wheels of things it has installed. Clean them out so we
	# don't go crazy trying to figure out why our new code isn't installing.
	find ~/Library/Caches/pip/wheels -name 'coverage-*' -delete

download_appveyor:
	python ci/download_appveyor.py nedbat/coveragepy

build_ext:
	python setup.py build_ext

install:
	python setup.py install

uninstall:
	-rm -rf $(PYHOME)/lib/site-packages/coverage*
	-rm -rf $(PYHOME)/scripts/coverage*

# Documentation

SPHINXBUILD = sphinx-build
SPHINXOPTS = -a -E doc
WEBHOME = ~/web/stellated/
WEBSAMPLE = $(WEBHOME)/files/sample_coverage_html
WEBSAMPLEBETA = $(WEBHOME)/files/sample_coverage_html_beta

docreqs:
	pip install -r doc/requirements.pip

dochtml:
	PYTHONPATH=$(CURDIR) $(SPHINXBUILD) -b html $(SPHINXOPTS) doc/_build/html
	@echo
	@echo "Build finished. The HTML pages are in doc/_build/html."

docspell:
	$(SPHINXBUILD) -b spelling $(SPHINXOPTS) doc/_spell

publish:
	rm -f $(WEBSAMPLE)/*.*
	mkdir -p $(WEBSAMPLE)
	cp doc/sample_html/*.* $(WEBSAMPLE)

publishbeta:
	rm -f $(WEBSAMPLEBETA)/*.*
	mkdir -p $(WEBSAMPLEBETA)
	cp doc/sample_html_beta/*.* $(WEBSAMPLEBETA)
