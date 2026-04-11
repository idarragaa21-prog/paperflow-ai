FROM rocker/r-ver:4.4.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    gfortran \
    pkg-config \
    libcairo2-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libnlopt-dev \
    libpng-dev \
    libtiff5-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libsodium-dev \
    libxml2-dev \
    pandoc \
    r-cran-plumber \
    r-cran-jsonlite \
    r-cran-dplyr \
    r-cran-survival \
    r-cran-metafor \
    r-cran-metadat \
    r-cran-lme4 \
    r-cran-rcppeigen \
    r-cran-cpp11 \
    r-cran-readr \
    r-cran-ggplot2 \
    r-cran-vroom \
    r-cran-tzdb \
    r-cran-isoband \
    r-cran-purrr \
    r-cran-stringr \
    r-cran-rlang \
    r-cran-tibble \
    r-cran-scales \
    r-cran-magrittr \
    r-cran-xml2 \
    && rm -rf /var/lib/apt/lists/*

ENV R_LIBS_SITE=/usr/lib/R/site-library:/usr/local/lib/R/site-library:/usr/local/lib/R/library

RUN R -e ".libPaths(c('/usr/lib/R/site-library', .libPaths())); install.packages(c('CompQuadForm','metabook','meta'), repos='https://cloud.r-project.org', dependencies=FALSE); stopifnot(requireNamespace('plumber', quietly=TRUE), requireNamespace('meta', quietly=TRUE), requireNamespace('metafor', quietly=TRUE), requireNamespace('jsonlite', quietly=TRUE), requireNamespace('ggplot2', quietly=TRUE), requireNamespace('lme4', quietly=TRUE))"

WORKDIR /srv
COPY plumber.R /srv/plumber.R

EXPOSE 8010
CMD ["R", "-e", "pr <- plumber::plumb('/srv/plumber.R'); pr$run(host='0.0.0.0', port=8010)"]
