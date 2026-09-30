from pathlib import Path

# Load libraries
import pandas as pd
import plotly.express as px

# Set file path
topic_dir = Path(__file__).resolve().parents[1]
data_path = topic_dir / "data" / "acs_clean_healthcare.csv"
output_dir = topic_dir / "outputs"
output_dir.mkdir(exist_ok=True)

# Read CSV dataset
acs = pd.read_csv(data_path)

# Add observation count
acs['obs_count'] = 1

# Collapse data by age
acs_summary = (
    acs.groupby('age', as_index=False)
    .agg(
        incwage=('incwage', 'mean'),
        in_labor_force=('in_labor_force', 'mean'),
        has_health_insurance=('has_health_insurance', 'mean'),
        has_medicare=('has_medicare', 'mean'),
        obs_count=('obs_count', 'sum')
    )
)

# --- Plot: Has Health Insurance ---
fig1 = px.scatter(
    acs_summary,
    x='age',
    y='has_health_insurance',
    size='obs_count',
    size_max=10,
    color_discrete_sequence=['steelblue'],
    labels={'has_health_insurance': 'Has Health Insurance', 'age': 'Age'}
)
fig1.write_html(output_dir / "has_insurance.html")

# --- Plot: Has Medicare ---
fig2 = px.scatter(
    acs_summary,
    x='age',
    y='has_medicare',
    size='obs_count',
    size_max=10,
    color_discrete_sequence=['steelblue'],
    labels={'has_medicare': 'Has Medicare', 'age': 'Age'}
)
fig2.write_html(output_dir / "has_medicare.html")

# --- Plot: In Labor Force with reference lines and labels ---
fig3 = px.scatter(
    acs_summary,
    x='age',
    y='in_labor_force',
    size='obs_count',
    size_max=10,
    color_discrete_sequence=['steelblue'],
    labels={'in_labor_force': 'In Labor Force', 'age': 'Age'}
)

# Add vertical lines and annotations
for x_val, text, y_pos in zip([61.5, 64.5, 66.5],
                              ['Early Retirement', 'Medicare', 'Late Retirement'],
                              [0.78, 0.65, 0.55]):
    fig3.add_vline(x=x_val, line=dict(dash='dash'))
    fig3.add_annotation(x=x_val, y=y_pos, text=text, showarrow=False, xanchor='left')

fig3.write_html(output_dir / "in_labor_force.html")

print(f"Saved interactive figures in {output_dir}")
