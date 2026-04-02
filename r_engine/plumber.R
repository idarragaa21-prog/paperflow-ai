# plumber API for PaperFlow AI analysis orchestration

library(plumber)
library(jsonlite)

`%||%` <- function(a, b) {
  if (is.null(a)) b else a
}

#* @get /health
function() {
  list(status = "ok", engine = "paperflow-r", version = R.version.string)
}

.coerce_df <- function(rows) {
  if (is.null(rows) || length(rows) == 0) {
    return(data.frame())
  }
  jsonlite::fromJSON(jsonlite::toJSON(rows, auto_unbox = TRUE), simplifyDataFrame = TRUE)
}

.run_regression <- function(df, analysis_type, params) {
  target <- params$target_column
  features <- params$feature_columns
  if (is.null(target) || is.null(features) || length(features) == 0 || !(target %in% names(df))) {
    return(list(
      summary = list(note = "Missing target_column or feature_columns"),
      warnings = list("Incomplete regression parameters"),
      script = paste("#", analysis_type, "params incomplete")
    ))
  }

  usable_features <- features[features %in% names(df)]
  if (length(usable_features) == 0) {
    return(list(
      summary = list(note = "No valid feature columns found"),
      warnings = list("Feature columns not found in dataset"),
      script = paste("#", analysis_type, "no valid feature columns")
    ))
  }

  target_sym <- as.name(target)
  rhs <- as.name(usable_features[[1]])
  if (length(usable_features) > 1) {
    for (i in 2:length(usable_features)) {
      rhs <- call("+", rhs, as.name(usable_features[[i]]))
    }
  }
  safe_formula <- as.formula(call("~", target_sym, rhs), env = parent.frame())

  # For logging and summary
  formula_text <- paste(deparse(safe_formula), collapse = " ")

  warnings <- list()
  model <- NULL
  if (analysis_type == "linear_regression") {
    model <- lm(safe_formula, data = df)
  } else {
    model <- glm(safe_formula, data = df, family = binomial())
  }

  model_summary <- summary(model)
  coeff_df <- as.data.frame(model_summary$coefficients)
  coeff_df$term <- rownames(coeff_df)
  rownames(coeff_df) <- NULL

  list(
    summary = list(
      formula = formula_text,
      coefficients = coeff_df
    ),
    warnings = warnings,
    script = paste(c(
      sprintf("df <- read.csv('dataset.csv')"),
      sprintf("model <- %s(%s, data = df%s)", ifelse(analysis_type == "linear_regression", "lm", "glm"), formula_text, ifelse(analysis_type == "linear_regression", "", ", family = binomial()")),
      "summary(model)"
    ), collapse = "\n")
  )
}

#* @post /run-analysis
function(req, res) {
  payload <- req$postBody
  parsed <- jsonlite::fromJSON(payload, simplifyVector = FALSE)
  analysis_type <- tolower(parsed$analysis_type %||% "descriptives")
  params <- parsed$input_params %||% list()
  rows <- parsed$rows %||% list()
  df <- .coerce_df(rows)

  warnings <- list()
  summary_payload <- list(
    analysis_type = analysis_type,
    row_count = nrow(df),
    column_count = ncol(df)
  )
  script <- sprintf("# PaperFlow AI r-engine\n# analysis_type: %s", analysis_type)
  figure <- list(title = "Analysis summary", caption = paste("Generated for", analysis_type))

  if (analysis_type == "descriptives") {
    column_profiles <- lapply(names(df), function(name) {
      column <- df[[name]]
      out <- list(non_null = sum(!is.na(column)), unique = length(unique(column)))
      if (is.numeric(column)) {
        out$mean <- mean(column, na.rm = TRUE)
      }
      out
    })
    names(column_profiles) <- names(df)
    summary_payload$columns <- column_profiles
  } else if (analysis_type == "group_comparison") {
    group_col <- params$group_column
    value_col <- params$value_column
    if (!is.null(group_col) && !is.null(value_col) && group_col %in% names(df) && value_col %in% names(df)) {
      means <- aggregate(df[[value_col]], by = list(df[[group_col]]), FUN = mean, na.rm = TRUE)
      names(means) <- c("group", "mean")
      summary_payload$groups <- means
    } else {
      warnings <- append(warnings, "Missing group_column or value_column for group comparison")
    }
  } else if (analysis_type %in% c("linear_regression", "logistic_regression")) {
    result <- .run_regression(df, analysis_type, params)
    summary_payload <- c(summary_payload, result$summary)
    warnings <- append(warnings, result$warnings)
    script <- result$script
  } else {
    warnings <- append(warnings, sprintf("Advanced analysis '%s' is not fully modelled in this r-engine; returning a degraded summary only", analysis_type))
    summary_payload$note <- "Advanced analysis returned a degraded summary only. Extend plumber.R for full domain-specific modelling."
    figure$title <- sprintf("Analysis summary (%s, degraded)", analysis_type)
    figure$caption <- sprintf("Degraded summary fallback for unsupported advanced analysis '%s'.", analysis_type)
  }

  list(
    summary = summary_payload,
    warnings = warnings,
    script = script,
    engine_version = R.version.string,
    figure = figure
  )
}
