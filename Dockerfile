# THE GRID — L4 exhibit. Static play surface on HF Docker Spaces (port 7860).
# Not a Vite kernel. play.html is the runtime.
#
# Base image pinned by OCI index digest (python:3.12-slim = 3.12.14-slim-trixie,
# resolved from registry-1.docker.io on 2026-09-29). Dependabot's docker
# ecosystem (.github/dependabot.yml) proposes digest bumps.
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
WORKDIR /app
# Every COPY source below is the Space deploy set: the reusable deployer
# (.github/workflows/hf-space.yml) derives the files it publishes from these lines.
COPY play.html index.html
COPY healthz ./healthz
COPY README.md ALIGN.md ./
ENV PORT=7860
EXPOSE 7860
# Liveness: the static server must answer /healthz with HTTP 200 and a body.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; r = urllib.request.urlopen('http://127.0.0.1:7860/healthz', timeout=4); sys.exit(0 if r.status == 200 and r.read() else 1)"]
CMD ["python", "-m", "http.server", "7860", "--bind", "0.0.0.0"]
