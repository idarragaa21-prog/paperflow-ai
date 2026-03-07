# plumber API for PaperFlow AI analysis orchestration

library(plumber)
library(jsonlite)
library(base64enc)
library(survival)
library(meta)
library(metafor)

`%||%` <- function(a, b) {
  if (is.null(a)) b else a
}

.supported_types <- c(
  "descriptives",
  "group_comparison",
  "linear_regression",
  "logistic_regression",
  "survival",
  "meta_analysis",
  "meta_regression",
  "sensitivity",
  "heterogeneity",
  "funnel_plot"
)

#* @get /health
function() {
  list(
    status = "ok",
    engine = "paperflow-r",
    version = R.version.string,
    quarto = tryCatch(as.character(quarto::quarto_path()), error = function(e) "missing")
  )
}

.coerce_df <- function(rows) {
  if (is.null(rows) || length(rows) == 0) {
    return(data.frame())
  }
  jsonlite::fromJSON(jsonlite::toJSON(rows, auto_unbox = TRUE), simplifyDataFrame = TRUE)
}

.numeric_column <- function(df, name) {
  if (is.null(name) || !(name %in% names(df))) {
    return(NULL)
  }
  suppressWarnings(as.numeric(df[[name]]))
}

.run_descriptives <- function(df) {
  columns <- lapply(names(df), function(name) {
    column <- df[[name]]
    out <- list(non_null = sum(!is.na(column)), unique = length(unique(column)))
    if (is.numeric(column)) {
      out$mean <- mean(column, na.rm = TRUE)
      out$sd <- stats::sd(column, na.rm = TRUE)
    }
    out
  })
  names(columns) <- names(df)
  list(
    summary = list(columns = columns),
    warnings = list(),
    script = "summary(df)"
  )
}

.run_group_comparison <- function(df, params) {
  group_col <- params$group_column
  value_col <- params$value_column
  if (is.null(group_col) || is.null(value_col) || !(group_col %in% names(df)) || !(value_col %in% names(df))) {
    stop("Missing group_column or value_column")
  }
  grouped <- aggregate(df[[value_col]], by = list(df[[group_col]]), FUN = mean, na.rm = TRUE)
  names(grouped) <- c("group", "mean")
  warnings <- list()
  inferential <- NULL
  if (length(unique(df[[group_col]])) == 2 && is.numeric(df[[value_col]])) {
    inferential <- broom::tidy(stats::t.test(df[[value_col]] ~ df[[group_col]]))
  } else {
    warnings <- append(warnings, "Two-group t-test skipped; requires exactly two groups and numeric value column")
  }
  list(
    summary = list(groups = grouped, inferential = inferential),
    warnings = warnings,
    script = paste0("aggregate(", value_col, " ~ ", group_col, ", data = df, FUN = mean)")
  )
}

.run_regression <- function(df, analysis_type, params) {
  target <- params$target_column
  features <- params$feature_columns %||% list()
  usable <- features[features %in% names(df)]
  if (is.null(target) || !(target %in% names(df)) || length(usable) == 0) {
    stop("Missing target_column or feature_columns")
  }

  formula_text <- paste(target, "~", paste(usable, collapse = " + "))
  if (analysis_type == "linear_regression") {
    model <- lm(stats::as.formula(formula_text), data = df)
  } else {
    model <- glm(stats::as.formula(formula_text), data = df, family = binomial())
  }
  tidy <- broom::tidy(model)
  glance <- broom::glance(model)
  list(
    summary = list(formula = formula_text, coefficients = tidy, diagnostics = glance),
    warnings = list(),
    script = paste(c(
      "df <- read.csv('dataset.csv')",
      sprintf("model <- %s(%s, data = df%s)", ifelse(analysis_type == "linear_regression", "lm", "glm"), formula_text, ifelse(analysis_type == "linear_regression", "", ", family = binomial()")),
      "summary(model)"
    ), collapse = "\n")
  )
}

.build_meta_model <- function(df, params, allow_mods = FALSE) {
  yi_col <- params$effect_column %||% params$yi_column
  sei_col <- params$se_column %||% params$sei_column
  if (is.null(yi_col) || is.null(sei_col) || !(yi_col %in% names(df)) || !(sei_col %in% names(df))) {
    stop("Meta analyses require effect_column/yi_column and se_column/sei_column")
  }
  yi <- suppressWarnings(as.numeric(df[[yi_col]]))
  sei <- suppressWarnings(as.numeric(df[[sei_col]]))
  ok <- !is.na(yi) & !is.na(sei) & sei > 0
  if (sum(ok) < 2) {
    stop("Meta analyses require at least two valid rows")
  }
  model <- NULL
  if (allow_mods) {
    moderators <- params$moderator_columns %||% list()
    usable_mods <- moderators[moderators %in% names(df)]
    if (length(usable_mods) == 0) {
      stop("Meta regression requires moderator_columns")
    }
    mods_formula <- stats::as.formula(paste("~", paste(usable_mods, collapse = " + ")))
    model <- metafor::rma.uni(yi = yi[ok], sei = sei[ok], mods = mods_formula, data = df[ok, , drop = FALSE], method = "REML")
  } else {
    model <- metafor::rma.uni(yi = yi[ok], sei = sei[ok], method = "REML")
  }
  list(model = model, yi_col = yi_col, sei_col = sei_col, rows = sum(ok))
}

.run_meta_like <- function(df, params, analysis_type) {
  meta_fit <- .build_meta_model(df, params, allow_mods = identical(analysis_type, "meta_regression"))
  model <- meta_fit$model
  summary_payload <- list(
    estimate = unname(model$b[1, 1]),
    ci_lb = model$ci.lb[1],
    ci_ub = model$ci.ub[1],
    tau2 = model$tau2,
    i2 = model$I2,
    k = model$k
  )

  if (analysis_type == "sensitivity") {
    summary_payload$leave_one_out <- metafor::leave1out(model)
  }
  if (analysis_type == "heterogeneity") {
    summary_payload$heterogeneity <- list(qe = model$QE, qep = model$QEp, i2 = model$I2, h2 = model$H2)
  }
  if (analysis_type == "funnel_plot") {
    summary_payload$funnel_points <- data.frame(effect = model$yi, se = sqrt(model$vi))
  }
  if (analysis_type == "meta_regression") {
    summary_payload$coefficients <- broom::tidy(model)
  }

  list(
    summary = summary_payload,
    warnings = list(),
    script = paste(
      sprintf("meta_df <- read.csv('dataset.csv')"),
      sprintf("fit <- metafor::rma.uni(yi = %s, sei = %s, method = 'REML')", meta_fit$yi_col, meta_fit$sei_col),
      "summary(fit)",
      sep = "\n"
    )
  )
}

.run_survival <- function(df, params) {
  time_col <- params$time_column
  event_col <- params$event_column
  covariates <- params$covariate_columns %||% list()
  usable_covariates <- covariates[covariates %in% names(df)]
  if (is.null(time_col) || is.null(event_col) || !(time_col %in% names(df)) || !(event_col %in% names(df))) {
    stop("Survival analysis requires time_column and event_column")
  }
  formula_rhs <- if (length(usable_covariates) > 0) paste(usable_covariates, collapse = " + ") else "1"
  formula_text <- paste0("survival::Surv(", time_col, ", ", event_col, ") ~ ", formula_rhs)
  model <- survival::coxph(stats::as.formula(formula_text), data = df)
  list(
    summary = list(formula = formula_text, coefficients = broom::tidy(model), diagnostics = broom::glance(model)),
    warnings = list(),
    script = paste("survival::coxph(", formula_text, ", data = df)", sep = "")
  )
}

.run_analysis <- function(df, analysis_type, params) {
  if (!(analysis_type %in% .supported_types)) {
    stop(sprintf("Unsupported analysis_type=%s", analysis_type))
  }
  switch(
    analysis_type,
    descriptives = .run_descriptives(df),
    group_comparison = .run_group_comparison(df, params),
    linear_regression = .run_regression(df, analysis_type, params),
    logistic_regression = .run_regression(df, analysis_type, params),
    survival = .run_survival(df, params),
    meta_analysis = .run_meta_like(df, params, analysis_type),
    meta_regression = .run_meta_like(df, params, analysis_type),
    sensitivity = .run_meta_like(df, params, analysis_type),
    heterogeneity = .run_meta_like(df, params, analysis_type),
    funnel_plot = .run_meta_like(df, params, analysis_type)
  )
}

.render_artifacts <- function(title, analysis_type, summary_payload, warnings, script_text, figure_payload) {
  template_path <- "/srv/templates/analysis_report.qmd"
  if (!file.exists(template_path)) {
    stop("Missing Quarto template")
  }

  workdir <- tempfile(pattern = "paperflow-report-")
  dir.create(workdir, recursive = TRUE, showWarnings = FALSE)
  template_copy <- file.path(workdir, "analysis_report.qmd")
  file.copy(template_path, template_copy, overwrite = TRUE)

  params <- list(
    title = title,
    analysis_type = analysis_type,
    summary_json = jsonlite::toJSON(summary_payload, auto_unbox = TRUE, pretty = TRUE, null = "null"),
    warnings_json = jsonlite::toJSON(warnings, auto_unbox = TRUE, pretty = TRUE, null = "null"),
    script_text = script_text,
    figure_json = jsonlite::toJSON(figure_payload, auto_unbox = TRUE, pretty = TRUE, null = "null")
  )

  outputs <- list(
    html = list(ext = "html", mime = "text/html"),
    docx = list(ext = "docx", mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
  )

  rendered <- list()
  oldwd <- getwd()
  on.exit(setwd(oldwd), add = TRUE)
  setwd(workdir)

  for (fmt in names(outputs)) {
    output_file <- file.path(workdir, sprintf("analysis_report.%s", outputs[[fmt]]$ext))
    quarto::quarto_render(
      input = template_copy,
      execute_params = params,
      output_format = fmt,
      output_file = basename(output_file),
      quiet = TRUE
    )
    rendered[[length(rendered) + 1]] <- list(
      artifact_type = paste0("report_", fmt),
      filename = basename(output_file),
      mime_type = outputs[[fmt]]$mime,
      metadata_json = list(format = fmt, template_version = "analysis_report_v2"),
      content_base64 = base64enc::base64encode(output_file)
    )
  }

  html_output <- file.path(workdir, "analysis_report.html")
  pdf_output <- file.path(workdir, "analysis_report.pdf")
  wkhtmltopdf <- Sys.which("wkhtmltopdf")
  if (wkhtmltopdf == "") {
    stop("wkhtmltopdf is required for PDF exports")
  }
  conversion <- system2(
    wkhtmltopdf,
    c("--enable-local-file-access", normalizePath(html_output, mustWork = TRUE), normalizePath(pdf_output, mustWork = FALSE)),
    stdout = TRUE,
    stderr = TRUE
  )
  status <- attr(conversion, "status") %||% 0
  if (status != 0 || !file.exists(pdf_output)) {
    stop(paste(c("wkhtmltopdf failed", conversion), collapse = "\n"))
  }
  rendered[[length(rendered) + 1]] <- list(
    artifact_type = "report_pdf",
    filename = basename(pdf_output),
    mime_type = "application/pdf",
    metadata_json = list(format = "pdf", template_version = "analysis_report_v2"),
    content_base64 = base64enc::base64encode(pdf_output)
  )
  rendered
}

#* @post /run-analysis
function(req, res) {
  payload <- jsonlite::fromJSON(req$postBody, simplifyVector = FALSE)
  analysis_type <- tolower(payload$analysis_type %||% "descriptives")
  params <- payload$input_params %||% list()
  rows <- payload$rows %||% list()
  title <- payload$title %||% "PaperFlow Analysis"
  df <- .coerce_df(rows)

  result <- .run_analysis(df, analysis_type, params)
  summary_payload <- c(
    list(
      analysis_type = analysis_type,
      row_count = nrow(df),
      column_count = ncol(df)
    ),
    result$summary
  )
  figure <- list(
    title = paste("Analysis figure:", analysis_type),
    caption = paste("Generated from", analysis_type, "analysis."),
    analysis_type = analysis_type
  )

  artifacts <- .render_artifacts(
    title = title,
    analysis_type = analysis_type,
    summary_payload = summary_payload,
    warnings = result$warnings,
    script_text = result$script,
    figure_payload = figure
  )

  list(
    summary = summary_payload,
    warnings = result$warnings,
    script = result$script,
    engine_version = R.version.string,
    template_version = "analysis_report_v2",
    figure = figure,
    artifacts = artifacts
  )
}
