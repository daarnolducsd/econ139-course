#####################################
# Exploration of CPS
#####################################

library(tidyverse)

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
topic_dir <- if (length(script_arg)) {
  script_path <- sub("^--file=", "", script_arg[1])
  # R encodes spaces in its --file argument as ~+~.
  script_path <- gsub("~+~", " ", script_path, fixed = TRUE)
  dirname(dirname(normalizePath(script_path, mustWork = TRUE)))
} else {
  normalizePath(getwd())
}
output_dir <- file.path(topic_dir, "outputs")
dir.create(output_dir, showWarnings = FALSE)


data <- read_csv(file.path(topic_dir, "data", "cps_aug_25.csv"))

# Restrict to individuals >=16 with non-missing labor force values
data <- data %>% filter(LABFORCE != 0 & AGE>=16)

# table of labforce
table(data$LABFORCE)

# table of employment status 
table(data$EMPSTAT)

# table of occupations 
occ_counts <- data %>%
  filter(EMPSTAT == 10 | EMPSTAT == 12) %>%
  count(OCC)


# Earnings analysis 
summary(data$EARNWEEK2)
data <- data %>% mutate(EARNWEEK2 = ifelse(EARNWEEK2 == 999999.99, NA, EARNWEEK2))
summary(data$EARNWEEK2)

png(file.path(output_dir, "weekly_earnings.png"), width = 1000, height = 700)
hist(data$EARNWEEK2,
     main = "Histogram of Weekly Earnings",
     xlab = "Weekly Earnings Rounded",
     col = "skyblue",
     border = "white",
     breaks=40)

dev.off()
