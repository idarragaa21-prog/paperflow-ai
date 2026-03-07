FROM rocker/r-ver:4.4.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    pandoc \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages(c('plumber','jsonlite','dplyr','broom','survival','meta','metafor','quarto','knitr','rmarkdown','base64enc','ggplot2'), repos='https://cloud.r-project.org'); quarto::quarto_install(force = TRUE, quiet = TRUE)"

WORKDIR /srv
COPY plumber.R /srv/plumber.R
COPY templates /srv/templates

EXPOSE 8010
CMD ["R", "-e", "pr <- plumber::plumb('/srv/plumber.R'); pr$run(host='0.0.0.0', port=8010)"]
