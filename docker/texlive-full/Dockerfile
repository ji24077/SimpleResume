# Overleaf-like: TeX Live in image + latexmk (MVP = reproducible full environment).
#
# Build:  docker compose build texlive
#         # or: docker build -t simpleresume-texlive:full -f docker/texlive-full/Dockerfile .
#
# API:    export LATEX_DOCKER_IMAGE=simpleresume-texlive:full

FROM texlive/texlive:latest

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends latexmk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

CMD ["latexmk", "-version"]
