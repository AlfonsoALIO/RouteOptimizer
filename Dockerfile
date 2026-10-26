# RouteOptimizer CLI image: A* dispatch + PuLP/CBC shift-plan (no SQL, no network).
# Build (version tag matches pyproject): ./scripts/build_docker.sh

FROM python:3.12-slim

ARG PACKAGE_VERSION=0.1.0
LABEL org.opencontainers.image.title="route-optimizer"
LABEL org.opencontainers.image.description="Mine fleet dispatch (A*) and shift plan (MILP/CBC)"
LABEL org.opencontainers.image.version="${PACKAGE_VERSION}"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /src

COPY pyproject.toml README.md LICENSE ./
COPY DEPENDENCY_LICENSES.md ./
COPY core/ core/
COPY core_search/ core_search/
COPY route_optimizer/ route_optimizer/
COPY samples/ samples/
COPY docs/ docs/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Default workdir for host mounts: -v "$PWD/data:/data"
WORKDIR /data
ENTRYPOINT ["route-optimizer"]
CMD ["--help"]
