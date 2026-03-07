FROM rocker/r2u:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV MAKEFLAGS=-j1
ARG QUARTO_VERSION=1.8.26

RUN mkdir -p /root/.R && printf '%s\n' \
    'CFLAGS=-O1 -g0' \
    'CXXFLAGS=-O1 -g0' \
    'CXX11FLAGS=-O1 -g0' \
    'CXX14FLAGS=-O1 -g0' \
    'CXX17FLAGS=-O1 -g0' \
    'FFLAGS=-O1 -g0' \
    'FCFLAGS=-O1 -g0' \
    > /root/.R/Makevars

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    cmake \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    pandoc \
    pkg-config \
    wkhtmltopdf \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)" && \
    case "$arch" in \
      arm64|amd64) deb_arch="$arch" ;; \
      *) echo "Unsupported architecture for Quarto CLI: $arch" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /tmp/quarto.deb "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-${deb_arch}.deb" && \
    apt-get update && \
    apt-get install -y /tmp/quarto.deb && \
    rm -f /tmp/quarto.deb && \
    rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages(c('plumber','jsonlite','dplyr','broom','survival','meta','metafor','quarto','knitr','rmarkdown','base64enc','ggplot2'), Ncpus = 1); stopifnot(!is.null(quarto::quarto_path()))"

WORKDIR /srv
COPY plumber.R /srv/plumber.R
COPY templates /srv/templates

EXPOSE 8010
CMD ["R", "-e", "pr <- plumber::plumb('/srv/plumber.R'); pr$run(host='0.0.0.0', port=8010)"]
