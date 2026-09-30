#################

# Analyze CPS 

################

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

topic_dir = Path(__file__).resolve().parents[1]
output_dir = topic_dir / "outputs"
output_dir.mkdir(exist_ok=True)

# Read in data
cps = pd.read_csv(topic_dir / 'data' / 'cps_aug_25.csv')

# Filter data: restrict to LABFORCE!=0 & AGE>=16
cps = cps[(cps['LABFORCE'] != 0) & (cps['AGE'] >= 16)]

# frequency table of LABFORCE
labforce_freq = cps['LABFORCE'].value_counts()
print(labforce_freq)

# frequency table of EMPSTAT 
empstat_freq = cps['EMPSTAT'].value_counts()
print(empstat_freq)

# frequency table of OCC conditional on employment 
emp_cps = cps[cps['EMPSTAT'].isin([10,12])]
occ_freq = emp_cps['OCC'].value_counts().sort_values(ascending=False)
print(occ_freq)

# removing missing values from earnweewk
earn_cps = emp_cps[emp_cps['EARNWEEK2'] != 999999.99]

# histogram of EARNWEEK2
plt.figure(figsize=(10, 6))
plt.hist(earn_cps['EARNWEEK2'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')
plt.title('Distribution of Weekly Earnings (EARNWEEK2)', fontsize=16, fontweight='bold')
plt.xlabel('Weekly Earnings ($)', fontsize=12)
plt.ylabel('Frequency', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_dir / "weekly_earnings.png", dpi=150)
plt.show()
