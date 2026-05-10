import pandas as pd
import numpy as np
import scipy.stats as st

df = pd.read_csv('data/results/google_form_cleaned.csv')

def get_mean_ci(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    if n < 2:
        return np.mean(a), 0.0
    m, se = np.mean(a), st.sem(a)
    if se == 0:
        return m, 0.0
    h = se * st.t.ppf((1 + confidence) / 2., n-1)
    return m, h

cols = df.columns[2:10]
print(f"{'Task / Column':<40} | Mean | ±CI")
print('-' * 60)
for col in cols:
    ratings = df[col].dropna().values
    m, ci = get_mean_ci(ratings)
    print(f"{col[:38]:<40} | {m:4.2f} | ±{ci:4.2f}")
