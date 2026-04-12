# plumber API for PaperFlow AI vNext analysis orchestration

library(plumber)
library(jsonlite)

`%||%` <- function(a, b) {
  if (is.null(a)) b else a
}

.as_num <- function(x) {
  suppressWarnings(as.numeric(x))
}

.num_or_null <- function(x) {
  if (is.null(x) || length(x) == 0) {
    return(NULL)
  }
  y <- suppressWarnings(as.numeric(x[1]))
  if (is.na(y)) {
    return(NULL)
  }
  y
}

.pick_meta <- function(obj, fields) {
  for (name in fields) {
    if (!is.null(obj[[name]])) {
      value <- .num_or_null(obj[[name]])
      if (!is.null(value)) {
        return(value)
      }
    }
  }
  NULL
}

.coerce_df <- function(rows) {
  if (is.null(rows) || length(rows) == 0) {
    return(data.frame())
  }
  jsonlite::fromJSON(
    jsonlite::toJSON(rows, auto_unbox = TRUE, null = "null", na = "null"),
    simplifyDataFrame = TRUE
  )
}

.studlab <- function(df) {
  if ("study_id" %in% names(df)) {
    return(as.character(df$study_id))
  }
  if ("row_key" %in% names(df)) {
    return(as.character(df$row_key))
  }
  as.character(seq_len(nrow(df)))
}

.extract_meta_summary <- function(meta_obj, model = "random", transform = "none") {
  if (identical(model, "fixed")) {
    te <- .pick_meta(meta_obj, c("TE.common", "TE.fixed"))
    lower <- .pick_meta(meta_obj, c("lower.common", "lower.fixed"))
    upper <- .pick_meta(meta_obj, c("upper.common", "upper.fixed"))
    p_value <- .pick_meta(meta_obj, c("pval.common", "pval.fixed"))
  } else {
    te <- .pick_meta(meta_obj, c("TE.random", "TE.random.w"))
    lower <- .pick_meta(meta_obj, c("lower.random", "lower.random.w"))
    upper <- .pick_meta(meta_obj, c("upper.random", "upper.random.w"))
    p_value <- .pick_meta(meta_obj, c("pval.random", "pval.random.w"))
  }

  effect <- te
  effect_lower <- lower
  effect_upper <- upper

  if (identical(transform, "exp")) {
    if (!is.null(te)) effect <- exp(te)
    if (!is.null(lower)) effect_lower <- exp(lower)
    if (!is.null(upper)) effect_upper <- exp(upper)
  } else if (identical(transform, "plogis")) {
    if (!is.null(te)) effect <- stats::plogis(te)
    if (!is.null(lower)) effect_lower <- stats::plogis(lower)
    if (!is.null(upper)) effect_upper <- stats::plogis(upper)
  }

  k <- .pick_meta(meta_obj, c("k", "k.all"))
  if (is.null(k) && !is.null(meta_obj$TE)) {
    k <- length(meta_obj$TE)
  }

  list(
    model = model,
    k = k,
    pooled = list(
      effect = effect,
      lower = effect_lower,
      upper = effect_upper,
      log_effect = te,
      p_value = p_value
    ),
    heterogeneity = list(
      i2 = .pick_meta(meta_obj, c("I2")),
      tau2 = .pick_meta(meta_obj, c("tau2"))
    )
  )
}

.as_char_vec <- function(value) {
  if (is.null(value)) {
    return(character(0))
  }
  if (is.character(value)) {
    return(value)
  }
  if (is.list(value)) {
    return(unlist(lapply(value, as.character), use.names = FALSE))
  }
  as.character(value)
}

.safe_weighted_lm <- function(te, se, data_df, formula_text) {
  w <- 1 / (se^2)
  data_df$.te <- te
  data_df$.w <- w
  stats::lm(stats::as.formula(paste(".te ~", formula_text)), data = data_df, weights = .w)
}

.advanced_meta <- function(meta_obj, df, params, transform = "none") {
  warnings <- list()
  advanced <- list()

  # Subgroup analysis
  subgroup_var <- params$subgroup_variable %||% params$subgroup_column %||% params$subgroup
  if (!is.null(subgroup_var) && subgroup_var %in% names(df)) {
    grp <- as.character(df[[subgroup_var]])
    grp[is.na(grp) | !nzchar(grp)] <- "unspecified"
    keep <- is.finite(meta_obj$TE) & is.finite(meta_obj$seTE)
    subgroup_rows <- list()
    for (level in unique(grp[keep])) {
      idx <- keep & grp == level
      if (sum(idx) < 2) {
        next
      }
      subgroup_model <- tryCatch(
        meta::metagen(
          TE = meta_obj$TE[idx],
          seTE = meta_obj$seTE[idx],
          studlab = (.studlab(df))[idx],
          sm = meta_obj$sm %||% "GEN",
          common = FALSE,
          random = TRUE,
          hakn = TRUE
        ),
        error = function(e) NULL
      )
      if (!is.null(subgroup_model)) {
        subgroup_rows[[length(subgroup_rows) + 1]] <- c(
          list(level = level, studies = sum(idx)),
          .extract_meta_summary(subgroup_model, model = "random", transform = transform)$pooled
        )
      }
    }
    if (length(subgroup_rows) > 0) {
      advanced$subgroup <- list(variable = subgroup_var, groups = subgroup_rows)
    } else {
      warnings <- append(warnings, sprintf("Subgroup analysis skipped: `%s` has insufficient complete rows.", subgroup_var))
    }
  }

  # Sensitivity analysis (exclude flagged rows + leave-one-out)
  sensitivity <- list()
  if ("sensitivity_flag" %in% names(df)) {
    sensitivity_flag <- as.logical(df$sensitivity_flag)
    keep <- is.finite(meta_obj$TE) & is.finite(meta_obj$seTE)
    keep_main <- keep & !sensitivity_flag
    if (sum(keep_main) >= 2) {
      m_main <- tryCatch(
        meta::metagen(
          TE = meta_obj$TE[keep_main],
          seTE = meta_obj$seTE[keep_main],
          studlab = (.studlab(df))[keep_main],
          sm = meta_obj$sm %||% "GEN",
          common = FALSE,
          random = TRUE,
          hakn = TRUE
        ),
        error = function(e) NULL
      )
      if (!is.null(m_main)) {
        sensitivity$exclude_flagged <- .extract_meta_summary(m_main, model = "random", transform = transform)$pooled
      }
    }
  }

  inf_obj <- tryCatch(meta::metainf(meta_obj), error = function(e) NULL)
  if (!is.null(inf_obj)) {
    te_vals <- inf_obj$TE.random %||% inf_obj$TE.fixed %||% numeric(0)
    labels <- inf_obj$studlab %||% character(0)
    if (length(te_vals) > 0 && length(labels) > 0) {
      pooled <- .pick_meta(meta_obj, c("TE.random", "TE.common", "TE.fixed")) %||% 0
      deltas <- abs(te_vals - pooled)
      ord <- order(deltas, decreasing = TRUE)
      top_n <- min(5, length(ord))
      influence_rows <- list()
      for (i in seq_len(top_n)) {
        j <- ord[i]
        influence_rows[[i]] <- list(
          study = labels[j],
          delta = deltas[j],
          pooled_without_study = te_vals[j]
        )
      }
      sensitivity$leave_one_out <- influence_rows
    }
  }

  if (length(sensitivity) > 0) {
    advanced$sensitivity <- sensitivity
  }

  # Meta-regression
  covariates <- .as_char_vec(params$meta_regression_covariates %||% params$covariates %||% params$moderators)
  covariates <- covariates[covariates %in% names(df)]
  if (length(covariates) > 0) {
    keep <- is.finite(meta_obj$TE) & is.finite(meta_obj$seTE)
    reg_df <- data.frame(df[keep, covariates, drop = FALSE])
    reg_df <- data.frame(lapply(reg_df, function(col) suppressWarnings(as.numeric(col))))
    complete <- stats::complete.cases(reg_df)
    if (sum(complete) >= 4) {
      te <- meta_obj$TE[keep][complete]
      se <- meta_obj$seTE[keep][complete]
      reg_df <- reg_df[complete, , drop = FALSE]
      formula_text <- paste(covariates, collapse = " + ")

      fit <- NULL
      if (requireNamespace("metafor", quietly = TRUE)) {
        fit <- tryCatch(
          metafor::rma.uni(
            yi = te,
            sei = se,
            mods = stats::as.formula(paste("~", formula_text)),
            method = "REML",
            data = reg_df
          ),
          error = function(e) NULL
        )
      }
      if (is.null(fit)) {
        fit <- tryCatch(.safe_weighted_lm(te, se, reg_df, formula_text), error = function(e) NULL)
      }

      if (!is.null(fit)) {
        coef_tbl <- tryCatch(
          {
            sm <- summary(fit)
            cf <- as.data.frame(sm$coefficients)
            cf$term <- rownames(cf)
            rownames(cf) <- NULL
            cf
          },
          error = function(e) NULL
        )
        advanced$meta_regression <- list(
          covariates = covariates,
          rows = length(te),
          coefficients = coef_tbl %||% list()
        )
      } else {
        warnings <- append(warnings, "Meta-regression failed for requested covariates.")
      }
    } else {
      warnings <- append(warnings, "Meta-regression skipped: not enough complete rows for moderators.")
    }
  }

  list(advanced = advanced, warnings = warnings)
}

.run_metagen <- function(df, sm = "GEN", model = "random", transform = "none", effect_col = "log_effect") {
  if (!requireNamespace("meta", quietly = TRUE)) {
    stop("R package 'meta' is required")
  }

  te <- .as_num(df[[effect_col]])
  se <- .as_num(df$se)
  keep <- is.finite(te) & is.finite(se) & (se > 0)
  if (sum(keep) < 2) {
    return(list(
      summary = list(note = "Not enough rows with finite effect + SE"),
      warnings = list("Need at least 2 complete rows for metagen."),
      script = "# Insufficient complete rows for metagen."
    ))
  }

  m <- meta::metagen(
    TE = te[keep],
    seTE = se[keep],
    studlab = .studlab(df)[keep],
    sm = sm,
    common = identical(model, "fixed"),
    random = identical(model, "random"),
    hakn = identical(model, "random")
  )

  list(
    summary = .extract_meta_summary(m, model = model, transform = transform),
    warnings = list(),
    script = paste(
      c(
        "library(meta)",
        "df <- read.csv('dataset.csv')",
        sprintf("m <- metagen(TE=df$%s, seTE=df$se, sm='%s', common=%s, random=%s)", effect_col, sm, tolower(identical(model, "fixed")), tolower(identical(model, "random"))),
        "summary(m)"
      ),
      collapse = "\n"
    ),
    meta_obj = m
  )
}

.run_meta_binary <- function(df, preset) {
  if (!requireNamespace("meta", quietly = TRUE)) {
    stop("R package 'meta' is required")
  }

  a <- .as_num(df$a_events)
  b <- .as_num(df$b_non_events)
  c <- .as_num(df$c_events)
  d <- .as_num(df$d_non_events)
  n_e <- a + b
  n_c <- c + d
  keep <- is.finite(a) & is.finite(b) & is.finite(c) & is.finite(d) & n_e > 0 & n_c > 0
  model <- if (identical(preset, "meta_binary_fixed")) "fixed" else "random"

  if (sum(keep) >= 2) {
    m <- meta::metabin(
      event.e = a[keep],
      n.e = n_e[keep],
      event.c = c[keep],
      n.c = n_c[keep],
      studlab = .studlab(df)[keep],
      sm = "OR",
      method = "Inverse",
      common = identical(model, "fixed"),
      random = identical(model, "random")
    )
    return(list(
      summary = .extract_meta_summary(m, model = model, transform = "exp"),
      warnings = list(),
      meta_obj = m,
      script = paste(
        c(
          "library(meta)",
          "df <- read.csv('dataset.csv')",
          "m <- metabin(event.e=df$a_events, n.e=df$a_events+df$b_non_events, event.c=df$c_events, n.c=df$c_events+df$d_non_events, sm='OR')",
          "summary(m)"
        ),
        collapse = "\n"
      )
    ))
  }

  # Fallback to generic inverse-variance if effect+SE are available.
  out <- .run_metagen(df, sm = "OR", model = model, transform = "exp", effect_col = "log_effect")
  if (length(out$warnings) == 0) {
    out$warnings <- list("2x2 counts were incomplete; used generic log-effect model.")
  } else {
    out$warnings <- append(list("2x2 counts were incomplete; used generic log-effect model."), out$warnings)
  }
  out
}

.run_meta_continuous <- function(df, preset) {
  if (!requireNamespace("meta", quietly = TRUE)) {
    stop("R package 'meta' is required")
  }
  sm <- if (identical(preset, "meta_continuous_smd")) "SMD" else "MD"

  te <- .as_num(df$effect_value)
  if (all(!is.finite(te)) && ("log_effect" %in% names(df))) {
    te <- .as_num(df$log_effect)
  }
  df$effect_value <- te
  out <- .run_metagen(df, sm = sm, model = "random", transform = "none", effect_col = "effect_value")
  out$script <- paste(
    c(
      "library(meta)",
      "df <- read.csv('dataset.csv')",
      sprintf("m <- metagen(TE=df$effect_value, seTE=df$se, sm='%s', random=TRUE)", sm),
      "summary(m)"
    ),
    collapse = "\n"
  )
  out
}

.run_meta_survival_hr <- function(df) {
  if (!("log_effect" %in% names(df))) {
    df$log_effect <- NA_real_
  }
  log_effect <- .as_num(df$log_effect)
  if ("effect_value" %in% names(df)) {
    hr <- .as_num(df$effect_value)
    idx <- !is.finite(log_effect) & is.finite(hr) & hr > 0
    log_effect[idx] <- log(hr[idx])
  }
  df$log_effect <- log_effect
  out <- .run_metagen(df, sm = "HR", model = "random", transform = "exp", effect_col = "log_effect")
  out$script <- paste(
    c(
      "library(meta)",
      "df <- read.csv('dataset.csv')",
      "m <- metagen(TE=df$log_effect, seTE=df$se, sm='HR', random=TRUE)",
      "summary(m)"
    ),
    collapse = "\n"
  )
  out
}

.run_meta_proportion <- function(df) {
  if (!requireNamespace("meta", quietly = TRUE)) {
    stop("R package 'meta' is required")
  }

  event <- .as_num(df$events_total %||% df$a_events)
  n <- .as_num(df$total_n)
  if (all(!is.finite(n))) {
    n <- .as_num(df$a_events) + .as_num(df$b_non_events)
  }
  keep <- is.finite(event) & is.finite(n) & (n > 0)
  if (sum(keep) < 2) {
    return(list(
      summary = list(note = "Not enough rows with event / total for proportion meta-analysis."),
      warnings = list("Need at least 2 rows with finite events and totals."),
      script = "# Insufficient rows for metaprop."
    ))
  }

  m <- meta::metaprop(
    event = event[keep],
    n = n[keep],
    studlab = .studlab(df)[keep],
    sm = "PLOGIT",
    random = TRUE,
    common = FALSE
  )

  list(
    summary = .extract_meta_summary(m, model = "random", transform = "plogis"),
    warnings = list(),
    meta_obj = m,
    script = paste(
      c(
        "library(meta)",
        "df <- read.csv('dataset.csv')",
        "m <- metaprop(event=df$events_total, n=df$total_n, sm='PLOGIT', random=TRUE)",
        "summary(m)"
      ),
      collapse = "\n"
    )
  )
}

.run_meta_diag_accuracy <- function(df) {
  tp <- .as_num(df$tp %||% df$a_events)
  fn <- .as_num(df$fn %||% df$b_non_events)
  fp <- .as_num(df$fp %||% df$c_events)
  tn <- .as_num(df$tn %||% df$d_non_events)

  sens <- tp / (tp + fn)
  spec <- tn / (tn + fp)
  sens_w <- tp + fn
  spec_w <- tn + fp

  sens_keep <- is.finite(sens) & is.finite(sens_w) & sens_w > 0
  spec_keep <- is.finite(spec) & is.finite(spec_w) & spec_w > 0

  pooled_sens <- NULL
  pooled_spec <- NULL
  if (sum(sens_keep) > 0) {
    pooled_sens <- stats::weighted.mean(sens[sens_keep], sens_w[sens_keep], na.rm = TRUE)
  }
  if (sum(spec_keep) > 0) {
    pooled_spec <- stats::weighted.mean(spec[spec_keep], spec_w[spec_keep], na.rm = TRUE)
  }

  warnings <- list()
  if (is.null(pooled_sens) || is.null(pooled_spec)) {
    warnings <- append(warnings, "Insufficient 2x2 data for pooled sensitivity/specificity.")
  }

  list(
    summary = list(
      model = "diagnostic_weighted_pool",
      k = nrow(df),
      pooled = list(
        sensitivity = pooled_sens,
        specificity = pooled_spec
      )
    ),
    warnings = warnings,
    script = paste(
      c(
        "df <- read.csv('dataset.csv')",
        "sens <- df$a_events / (df$a_events + df$b_non_events)",
        "spec <- df$d_non_events / (df$c_events + df$d_non_events)",
        "weighted.mean(sens, df$a_events + df$b_non_events, na.rm = TRUE)",
        "weighted.mean(spec, df$c_events + df$d_non_events, na.rm = TRUE)"
      ),
      collapse = "\n"
    )
  )
}

.run_rob_summary <- function(df) {
  if (!("risk_of_bias_overall" %in% names(df))) {
    return(list(
      summary = list(note = "risk_of_bias_overall column is missing."),
      warnings = list("No RoB labels available in dataset."),
      script = "# No risk_of_bias_overall column in dataset."
    ))
  }

  rob <- tolower(trimws(as.character(df$risk_of_bias_overall)))
  rob <- rob[!is.na(rob) & nzchar(rob)]
  if (length(rob) == 0) {
    return(list(
      summary = list(note = "No non-empty RoB labels found."),
      warnings = list("risk_of_bias_overall values are empty."),
      script = "# Empty risk_of_bias_overall values."
    ))
  }

  tab <- table(rob)
  counts <- as.list(as.integer(tab))
  names(counts) <- names(tab)
  pct <- round(100 * as.numeric(tab) / sum(tab), 2)
  percentages <- as.list(pct)
  names(percentages) <- names(tab)

  list(
    summary = list(
      model = "risk_of_bias_summary",
      total = sum(tab),
      counts = counts,
      percentages = percentages
    ),
    warnings = list(),
    script = "table(tolower(trimws(df$risk_of_bias_overall)))"
  )
}

.run_publication_bias <- function(df) {
  base <- .run_metagen(df, sm = "OR", model = "random", transform = "exp", effect_col = "log_effect")
  if (length(base$warnings) > 0) {
    return(base)
  }

  warnings <- list()
  bias <- list(egger_p = NULL, rank_p = NULL, k_for_bias = NULL)
  meta_obj <- base$meta_obj
  k <- .pick_meta(meta_obj, c("k", "k.all")) %||% length(meta_obj$TE)
  bias$k_for_bias <- k

  if (!is.null(k) && k >= 10) {
    if (requireNamespace("meta", quietly = TRUE)) {
      egger <- tryCatch(meta::metabias(meta_obj, method.bias = "linreg"), error = function(e) NULL)
      rank <- tryCatch(meta::metabias(meta_obj, method.bias = "rank"), error = function(e) NULL)
      if (!is.null(egger)) {
        bias$egger_p <- .pick_meta(egger, c("p.value", "pval"))
      }
      if (!is.null(rank)) {
        bias$rank_p <- .pick_meta(rank, c("p.value", "pval"))
      }
    } else {
      warnings <- append(warnings, "Package 'meta' unavailable for bias tests.")
    }
  } else {
    warnings <- append(warnings, "At least 10 studies are recommended for publication-bias tests.")
  }

  base$summary$publication_bias <- bias
  base$warnings <- append(base$warnings, warnings)
  base$script <- paste(
    c(
      "library(meta)",
      "df <- read.csv('dataset.csv')",
      "m <- metagen(TE=df$log_effect, seTE=df$se, sm='OR', random=TRUE)",
      "metabias(m, method.bias='linreg')",
      "metabias(m, method.bias='rank')"
    ),
    collapse = "\n"
  )
  base
}

.capture_plot_triplet <- function(plot_fun) {
  root <- tempfile("paperflow_plot_")
  svg_path <- paste0(root, ".svg")
  png_path <- paste0(root, ".png")
  pdf_path <- paste0(root, ".pdf")
  warnings <- character(0)

  run_device <- function(open_fn) {
    tryCatch(
      {
        open_fn()
        plot_fun()
      },
      error = function(err) {
        warnings <<- c(warnings, as.character(err))
      }
    )
    if (grDevices::dev.cur() > 1) {
      try(grDevices::dev.off(), silent = TRUE)
    }
  }

  run_device(function() grDevices::svg(svg_path, width = 11, height = 8))
  run_device(function() grDevices::png(png_path, width = 1600, height = 1100, res = 180))
  run_device(function() grDevices::pdf(pdf_path, width = 11, height = 8, onefile = FALSE))

  out <- list()
  if (file.exists(svg_path)) {
    out$svg <- paste(readLines(svg_path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  }
  if (file.exists(png_path)) {
    out$png_base64 <- jsonlite::base64_enc(png_path)
  }
  if (file.exists(pdf_path)) {
    out$pdf_base64 <- jsonlite::base64_enc(pdf_path)
  }
  if (length(warnings) > 0) {
    out$warnings <- as.list(unique(warnings))
  }
  out
}

.build_figure_artifacts <- function(result, analysis_type, df) {
  artifacts <- list()
  warnings <- list()

  m <- result$meta_obj %||% NULL
  if (!is.null(m) && requireNamespace("meta", quietly = TRUE)) {
    forest <- .capture_plot_triplet(function() {
      meta::forest(m)
    })
    if (!is.null(forest$svg) || !is.null(forest$png_base64) || !is.null(forest$pdf_base64)) {
      artifacts$forest <- forest[setdiff(names(forest), "warnings")]
    }
    if (!is.null(forest$warnings)) {
      warnings <- append(warnings, forest$warnings)
    }

    te_length <- length(m$TE %||% numeric(0))
    if (te_length >= 3) {
      funnel <- .capture_plot_triplet(function() {
        meta::funnel(m)
      })
      if (!is.null(funnel$svg) || !is.null(funnel$png_base64) || !is.null(funnel$pdf_base64)) {
        artifacts$funnel <- funnel[setdiff(names(funnel), "warnings")]
      }
      if (!is.null(funnel$warnings)) {
        warnings <- append(warnings, funnel$warnings)
      }
    } else {
      warnings <- append(warnings, "Funnel plot skipped: requires at least 3 studies.")
    }

    inf_obj <- tryCatch(meta::metainf(m), error = function(err) NULL)
    if (!is.null(inf_obj)) {
      influence <- .capture_plot_triplet(function() {
        meta::forest(inf_obj)
      })
      if (!is.null(influence$svg) || !is.null(influence$png_base64) || !is.null(influence$pdf_base64)) {
        artifacts$influence <- influence[setdiff(names(influence), "warnings")]
      }
      if (!is.null(influence$warnings)) {
        warnings <- append(warnings, influence$warnings)
      }
    } else {
      warnings <- append(warnings, "Influence plot skipped: metainf could not be computed.")
    }
  }

  if ("risk_of_bias_overall" %in% names(df)) {
    rob_values <- tolower(trimws(as.character(df$risk_of_bias_overall)))
    rob_values <- rob_values[!is.na(rob_values) & nzchar(rob_values)]
    if (length(rob_values) > 0) {
      rob_table <- sort(table(rob_values), decreasing = TRUE)
      rob <- .capture_plot_triplet(function() {
        palette <- c("#16a34a", "#f59e0b", "#ef4444", "#6b7280", "#0ea5e9")
        col <- palette[seq_len(min(length(palette), length(rob_table)))]
        if (length(col) < length(rob_table)) {
          col <- rep(col, length.out = length(rob_table))
        }
        old_par <- par(no.readonly = TRUE)
        on.exit(par(old_par), add = TRUE)
        barplot(
          rob_table,
          col = col,
          ylab = "Count",
          main = "Risk of Bias Summary",
          las = 2
        )
      })
      if (!is.null(rob$svg) || !is.null(rob$png_base64) || !is.null(rob$pdf_base64)) {
        artifacts$rob <- rob[setdiff(names(rob), "warnings")]
      }
      if (!is.null(rob$warnings)) {
        warnings <- append(warnings, rob$warnings)
      }
    } else if (analysis_type == "risk_of_bias_summary") {
      warnings <- append(warnings, "RoB plot skipped: no risk_of_bias_overall labels available.")
    }
  } else if (analysis_type == "risk_of_bias_summary") {
    warnings <- append(warnings, "RoB plot skipped: risk_of_bias_overall column missing.")
  }

  list(artifacts = artifacts, warnings = warnings)
}

.run_meta_preset <- function(df, analysis_type, params) {
  warnings <- list()
  script <- sprintf("# PaperFlow vNext R preset\n# preset: %s", analysis_type)

  # normalize expected numeric columns when present
  numeric_candidates <- c(
    "log_effect", "se", "effect_value", "a_events", "b_non_events", "c_events", "d_non_events", "proportion"
  )
  for (name in intersect(numeric_candidates, names(df))) {
    df[[name]] <- .as_num(df[[name]])
  }

  out <- switch(
    analysis_type,
    meta_binary_random = .run_meta_binary(df, "meta_binary_random"),
    meta_binary_fixed = .run_meta_binary(df, "meta_binary_fixed"),
    meta_continuous_md = .run_meta_continuous(df, "meta_continuous_md"),
    meta_continuous_smd = .run_meta_continuous(df, "meta_continuous_smd"),
    meta_generic_iv = .run_metagen(df, sm = "GEN", model = "random", transform = "none", effect_col = "log_effect"),
    meta_survival_hr = .run_meta_survival_hr(df),
    meta_proportion = .run_meta_proportion(df),
    meta_diag_accuracy = .run_meta_diag_accuracy(df),
    risk_of_bias_summary = .run_rob_summary(df),
    publication_bias_suite = .run_publication_bias(df),
    NULL
  )

  if (is.null(out)) {
    return(list(
      summary = list(
        analysis_type = analysis_type,
        row_count = nrow(df),
        column_count = ncol(df),
        note = "Unsupported preset"
      ),
      warnings = list(sprintf("Unsupported preset: %s", analysis_type)),
      script = script
    ))
  }

  transform <- "none"
  if (analysis_type %in% c("meta_binary_random", "meta_binary_fixed", "meta_survival_hr", "publication_bias_suite")) {
    transform <- "exp"
  } else if (analysis_type %in% c("meta_proportion")) {
    transform <- "plogis"
  }

  if (!is.null(out$meta_obj)) {
    adv <- .advanced_meta(out$meta_obj, df, params, transform = transform)
    if (length(adv$advanced %||% list()) > 0) {
      out$summary$advanced <- adv$advanced
    }
    if (length(adv$warnings %||% list()) > 0) {
      out$warnings <- append(out$warnings %||% list(), adv$warnings)
    }
  }

  # Attach common envelope fields.
  out$summary$analysis_type <- analysis_type
  out$summary$row_count <- nrow(df)
  out$summary$column_count <- ncol(df)
  out
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

  formula_text <- paste(target, "~", paste(usable_features, collapse = " + "))
  model <- NULL
  if (analysis_type == "linear_regression") {
    model <- lm(stats::as.formula(formula_text), data = df)
  } else {
    model <- glm(stats::as.formula(formula_text), data = df, family = binomial())
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
    warnings = list(),
    script = paste(c(
      "df <- read.csv('dataset.csv')",
      sprintf("model <- %s(%s, data = df%s)", ifelse(analysis_type == "linear_regression", "lm", "glm"), formula_text, ifelse(analysis_type == "linear_regression", "", ", family = binomial()")),
      "summary(model)"
    ), collapse = "\n")
  )
}

#* @get /health
#* @serializer unboxedJSON
function() {
  list(status = "ok", engine = "paperflow-r", version = R.version.string)
}

#* @post /run-analysis
#* @serializer unboxedJSON
function(req, res) {
  payload <- req$postBody %||% "{}"
  # Defensive fix for non-standard JSON values emitted by upstream clients.
  payload <- gsub("-Infinity", "null", payload, fixed = TRUE)
  payload <- gsub("Infinity", "null", payload, fixed = TRUE)
  payload <- gsub("NaN", "null", payload, fixed = TRUE)

  parsed <- tryCatch(
    jsonlite::fromJSON(payload, simplifyVector = FALSE),
    error = function(err) {
      res$status <- 422
      return(list(
        summary = list(note = "Invalid JSON payload"),
        warnings = list(as.character(err)),
        script = "# invalid input payload",
        engine_version = R.version.string
      ))
    }
  )
  if (!is.null(res$status) && res$status == 422) {
    return(parsed)
  }

  analysis_type <- tolower(parsed$analysis_type %||% "descriptives")
  params <- parsed$input_params %||% list()
  rows <- parsed$rows %||% list()
  df <- .coerce_df(rows)

  preset_types <- c(
    "meta_binary_random",
    "meta_binary_fixed",
    "meta_continuous_md",
    "meta_continuous_smd",
    "meta_generic_iv",
    "meta_survival_hr",
    "meta_proportion",
    "meta_diag_accuracy",
    "risk_of_bias_summary",
    "publication_bias_suite"
  )

  if (analysis_type %in% preset_types) {
    result <- .run_meta_preset(df, analysis_type, params)
    figures <- .build_figure_artifacts(result, analysis_type, df)
    result_warnings <- result$warnings %||% list()
    if (length(figures$warnings %||% list()) > 0) {
      result_warnings <- append(result_warnings, figures$warnings)
    }
    return(list(
      summary = result$summary,
      warnings = result_warnings,
      script = result$script %||% sprintf("# preset: %s", analysis_type),
      engine_version = R.version.string,
      figure_artifacts = figures$artifacts %||% list()
    ))
  }

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
    warnings <- append(warnings, sprintf("Unsupported analysis '%s'.", analysis_type))
    summary_payload$note <- "Unsupported analysis type for current engine."
  }

  list(
    summary = summary_payload,
    warnings = warnings,
    script = script,
    engine_version = R.version.string,
    figure = figure
  )
}
