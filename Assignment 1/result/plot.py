import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

# Load your merged dataset
df = pd.read_csv('tfidf_with_excess_returns.csv')

# Create quintiles for Fin-Neg and H4N
df['finneg_quintile'] = pd.qcut(df['avg_tfidf_finneg'], 5, labels=False) + 1
df['h4n_quintile'] = pd.qcut(df['avg_tfidf_h4n'], 5, labels=False) + 1

# Group by quintile and get median excess returns
finneg_medians = df.groupby('finneg_quintile')['excess_return_3d'].median()
h4n_medians = df.groupby('h4n_quintile')['excess_return_3d'].median()

# Plot with custom styling
plt.figure(figsize=(8, 6))
plt.plot(
    finneg_medians.index, finneg_medians.values * 100,
    label='Fin-Neg', marker='o', linestyle='-', color='black', linewidth=2
)
plt.plot(
    h4n_medians.index, h4n_medians.values * 100,
    label='H4N-Inf', marker='D', linestyle='--', color='gray', linewidth=2
)

# X-axis settings
plt.xticks([1, 2, 3, 4, 5], ['Low', '2', '3', '4', 'High'], fontsize=12)
plt.xlabel('Quintile (based on average TF-IDF of negative words)', fontsize=12)

# Y-axis settings
plt.ylabel('Median Filing Period Excess Return(T to T+2)', fontsize=12)
plt.gca().yaxis.set_major_formatter(mtick.PercentFormatter(decimals=2))
# Add horizontal dotted lines at each y-tick except 0
y_ticks = plt.yticks()[0]
for y in y_ticks:
    if abs(y) < 1e-5:
        plt.axhline(y, color='black', linewidth=1)  # bold line at y=0
    else:
        plt.axhline(y, color='gray', linestyle=':', linewidth=1)

# Legend
plt.legend(frameon=True, fontsize=11)

plt.title('Median 3-Day Excess Return by TF-IDF Quintile')

# Grid and layout
plt.grid(False)
plt.tight_layout()

# Save or show
plt.show()