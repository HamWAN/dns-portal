IMAGE := hamwan-portal
PYTHON_VERSION ?= 3.9
DOCKER_RUNNER := docker run --rm $(IMAGE)

docker:
	docker build --build-arg PYTHON_VERSION=$(PYTHON_VERSION) -t $(IMAGE) .

test:
	$(DOCKER_RUNNER) manage.py test -v3
