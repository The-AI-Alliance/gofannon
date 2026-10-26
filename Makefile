# Makefile — image build targets used by the production puppet deploy.

.PHONY: build-api build-webui build-all clean-images

build-api:
	docker build -f webapp/infra/docker/Dockerfile.api \
	  -t gofannon-api:latest \
	  webapp/packages/api/user-service

build-webui:
	docker build -f webapp/infra/docker/Dockerfile.webui \
	  --build-arg VITE_APP_ENV=local \
	  -t gofannon-webui:latest \
	  webapp

build-all: build-api build-webui

clean-images:
	docker rmi -f gofannon-api:latest gofannon-webui:latest 2>/dev/null || true
