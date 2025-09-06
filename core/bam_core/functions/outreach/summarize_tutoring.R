library(dplyr)
library(data.table)
library(ggplot2)
library(assertthat)

df <- fread("~/Downloads/Imported table-Interested.csv")

assert_that(all(df$`Still interested in tutoring` == "Yes"))
assert_that(!any(duplicated(df$`Phone Number`)))

TUTORING_COLS <- c(`Subjects needed` = "subjects", Grade = "grade", `Preferred Language` = "language", Modality = "modality")
df <- df %>%
  select(`Oldest request`, `Most recent request`, !!!syms(names(TUTORING_COLS))) %>%
  mutate(across(
    all_of(names(TUTORING_COLS)),
    ~ strsplit(.x, split = ",")
  ))

tutoring_tb <- lapply(names(TUTORING_COLS), function(col) {
  x <- df %>% pull(!!sym(col))
  xu <- unique(unlist(x))
  x_count_mtx <- lapply(x, function(curr_x) { xu %in% curr_x }) %>%
    do.call(what = rbind) %>%
    data.frame(check.names = F)
  colnames(x_count_mtx) <- paste(TUTORING_COLS[col], xu, sep = ":")
  return(x_count_mtx)
}) %>% do.call(what = cbind)

dummy <- lapply(names(TUTORING_COLS), function(col_name) {
  message(col_name)
  
  col <- paste(unname(TUTORING_COLS[col_name]))
  pref <- paste0(col, ":")
  curr_tutoring_tb <- tutoring_tb %>% select(starts_with(pref))
  curr_tutoring_tb[[paste0(pref, "NA")]] <- rowSums(curr_tutoring_tb) == 0
  assert_that(all((curr_tutoring_tb[[paste0(pref, "NA")]]) == (sapply(df[[col_name]], length) == 0)))
  
  counts <- curr_tutoring_tb %>% colSums()
  unique_vals <- gsub(pref, "", names(counts)) %>% setNames(names(counts))
  n_cols <- length(unique_vals)
  
  plot_data <- data.table(field_value = unname(unique_vals), field_counts = unname(counts)) %>%
    arrange(field_counts) %>%
    mutate(field_value = factor(field_value, levels = unique(field_value)))
  
  pal_names <- c(setdiff(plot_data$field_value, "NA"), "NA")
  pal <- RColorBrewer::brewer.pal(n = 12, name = "Paired")
  pal <- c(pal[seq(2, 12, 2)], pal[seq(1, 11, 2)])
  pal <- c(rev(pal[1:(n_cols-1)]), "#999999") %>% setNames(pal_names)
  
  gp <- ggplot(plot_data, aes(x = field_value, y = field_counts)) +
    geom_col(aes(fill = field_value)) +
    geom_label(aes(label = field_counts, color = field_value), position = position_nudge(y = 0.1)) +
    labs(x = col_name, y = "# interested") +
    scale_color_manual(values = pal) + scale_fill_manual(values = pal) +
    theme_classic() + theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = 0.5), legend.position = "none")
  ggsave(gp, filename = paste0("plots/", col, ".png"), height = 4, width = n_cols / 2 + 1)
  
  pair_counts <- lapply(names(unique_vals), function(val1) {
    lapply(names(unique_vals), function(val2) {
      if(val1 != val2) {
        pair <- sort(c(unique_vals[val1], unique_vals[val2]))
        data.table(
          val1 = pair[1],
          val2 = pair[2],
          n = sum(curr_tutoring_tb[[val1]] & curr_tutoring_tb[[val2]])
        ) %>% mutate(subjects = paste(val1, val2, sep = ", "), .before = n)
      }
    }) %>% do.call(what = rbind)
  }) %>% do.call(what = rbind) %>%
    dplyr::filter(val1 != "NA", val2 != "NA", n > 0, !duplicated(subjects)) %>%
    arrange(-n)
  fwrite(pair_counts, file = paste0("plots/", col, "-pairs.csv"))
})

dummy <- lapply(names(TUTORING_COLS), function(col_name1) {
  dummy <- lapply(names(TUTORING_COLS), function(col_name2) {
    if(col_name1 == col_name2) return(NULL)
    message(col_name1, " and ", col_name2)
    
    col1 <- paste(unname(TUTORING_COLS[col_name1]))
    pref1 <- paste0(col1, ":")
    curr_tutoring_tb1 <- tutoring_tb %>% select(starts_with(pref1))
    curr_tutoring_tb1[[paste0(pref1, "NA")]] <- rowSums(curr_tutoring_tb1) == 0
    
    counts1 <- curr_tutoring_tb1 %>% colSums()
    unique_vals1 <- gsub(pref1, "", names(counts1)) %>% setNames(names(counts1))
    n_cols1 <- length(unique_vals1)
    
    col2 <- paste(unname(TUTORING_COLS[col_name2]))
    pref2 <- paste0(col2, ":")
    curr_tutoring_tb2 <- tutoring_tb %>% select(starts_with(pref2))
    curr_tutoring_tb2[[paste0(pref2, "NA")]] <- rowSums(curr_tutoring_tb2) == 0
    
    counts2 <- curr_tutoring_tb2 %>% colSums()
    unique_vals2 <- gsub(pref2, "", names(counts2)) %>% setNames(names(counts2))
    n_cols2 <- length(unique_vals2)
    
    pair_counts <- lapply(names(unique_vals1), function(val1) {
      lapply(names(unique_vals2), function(val2) {
        pair <- c(unique_vals1[val1], unique_vals2[val2])
        data.table(
          val1 = pair[1],
          val2 = pair[2],
          n = sum(curr_tutoring_tb1[[val1]] & curr_tutoring_tb2[[val2]])
        ) %>% mutate(pair = paste(val1, val2, sep = ", "), .before = n)
      }) %>% do.call(what = rbind)
    }) %>% do.call(what = rbind) %>%
      dplyr::filter(val1 != "NA", val2 != "NA", n > 0) %>%
      arrange(-n)
    fwrite(pair_counts, file = paste0("plots/", col1, "__", col2, "-pairs.csv"))
  })
})

