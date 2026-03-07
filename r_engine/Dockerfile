FROM rocker/r-ver:4.4.2

ENV MAKEFLAGS=-j1

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
    cmake \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    pandoc \
    pkg-config \
    wkhtmltopdf \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages(c('plumber','jsonlite','dplyr','broom','survival','meta','metafor','quarto','knitr','rmarkdown','base64enc','ggplot2'), repos='https://cloud.r-project.org', Ncpus = 1); quarto::quarto_install(force = TRUE, quiet = TRUE)"

WORKDIR /srv
COPY plumber.R /srv/plumber.R
COPY templates /srv/templates

EXPOSE 8010
CMD ["R", "-e", "pr <- plumber::plumb('/srv/plumber.R'); pr$run(host='0.0.0.0', port=8010)"]
