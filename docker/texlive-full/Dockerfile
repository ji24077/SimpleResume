# Overleaf-like: TeX Live + latexmk. Build: docker compose build texlive
FROM texlive/texlive:latest

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends latexmk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

CMD ["latexmk", "-version"]
