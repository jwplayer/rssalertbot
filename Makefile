VERSION		:= $(shell head CHANGELOG.rst | grep -e '^[0-9]' | head -n 1 | cut -f 1 -d ' ')
DHREPO		:= jwplayer/rssalertbot
DOCKERIMG	= $(DHREPO):$(VERSION)
PYTEST          := ${VIRTUAL_ENV}/bin/pytest

# default is to build and publish the docker image
all: build push

build:
	docker build --build-arg PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL} -t $(DOCKERIMG) .

push:
	docker push $(DOCKERIMG)

.PHONY: build push

venv_test:
ifndef VIRTUAL_ENV
	$(error Please activate a virtualenv)
endif

$(PYTEST): | venv_test
	@pip install mock pytest

test: $(PYTEST)
	pip install '.[dynamo,slack]'
	$(PYTEST) -v

clean:
	@rm -rf build rssalertbot.egg-info .pytest_cache

.PHONY: clean test
