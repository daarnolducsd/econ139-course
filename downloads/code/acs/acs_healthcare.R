# Load libraries
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


# Set file path
data_path <- file.path(topic_dir, "data", "acs_clean_healthcare.csv")

# Read CSV dataset
acs <- read_csv(data_path)

# Add observation count
acs <- acs %>% 
  mutate(obs_count = 1)

# Collapse data by age
acs_summary <- acs %>%
  group_by(age) %>%
  summarise(
    incwage = mean(incwage, na.rm = TRUE),
    in_labor_force = mean(in_labor_force, na.rm = TRUE),
    has_health_insurance = mean(has_health_insurance, na.rm = TRUE),
    has_medicare = mean(has_medicare, na.rm = TRUE),
    obs_count = sum(obs_count)
  ) 


# Plot: Has Health Insurance
insurance_plot <- ggplot(acs_summary, aes(x = age, y = has_health_insurance, size = obs_count)) +
  geom_point(color = "steelblue", alpha = 0.6) +
  labs(x = "Age", y = "Has Health Insurance") +
  theme_minimal() +
  scale_size_continuous(range = c(1, 6))

# Plot: Has Medicare
medicare_plot <- ggplot(acs_summary, aes(x = age, y = has_medicare, size = obs_count)) +
  geom_point(color = "steelblue", alpha = 0.6) +
  labs(x = "Age", y = "Has Medicare") +
  theme_minimal() +
  scale_size_continuous(range = c(1, 6))

# Plot: In Labor Force with reference lines and labels
labor_force_plot <- ggplot(acs_summary, aes(x = age, y = in_labor_force, size = obs_count)) +
  geom_point(color = "steelblue", alpha = 0.6) +
  geom_vline(xintercept = c(61.5, 64.5, 66.5), linetype = "dashed") +
  annotate("text", x = 61.5, y = 0.78, label = "Early Retirement", hjust = -0.1) +
  annotate("text", x = 64.5, y = 0.65, label = "Medicare", hjust = -0.1) +
  annotate("text", x = 66.5, y = 0.55, label = "Late Retirement", hjust = -0.1) +
  labs(x = "Age", y = "In Labor Force") +
  theme_minimal() +
  scale_size_continuous(range = c(1, 6))

ggsave(file.path(output_dir, "has_insurance.png"), insurance_plot, width = 8, height = 5)
ggsave(file.path(output_dir, "has_medicare.png"), medicare_plot, width = 8, height = 5)
ggsave(file.path(output_dir, "in_labor_force.png"), labor_force_plot, width = 8, height = 5)
