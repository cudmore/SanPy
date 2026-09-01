import pandas as pd
import numpy as np
from itertools import combinations
from statsmodels.stats.multitest import multipletests
from scipy.stats import ttest_ind, mannwhitneyu

def getGroups(df, value_col, groupby_cols, agg_list):
    """
    Group and aggregate a DataFrame, and return raw values for each group.
    """
    if value_col not in df.columns:
        raise ValueError(f"Column '{value_col}' not found in DataFrame.")
    
    grouped = df.groupby(groupby_cols)[value_col]
    agg_df = grouped.agg(agg_list).reset_index()

    # Add column to indicate which measurement this aggregation applies to
    agg_df.insert(0, 'Stat', value_col)

    raw_groups = {name: group[value_col].values
                  for name, group in df.groupby(groupby_cols)}
    
    return agg_df, raw_groups


def run_pairwise_tests(raw_groups, test_func, test_name="custom_test"):
    """
    Run pairwise statistical tests between all groups.

    Parameters:
        raw_groups (dict): Keys are group names, values are 1D arrays of data.
        test_func (callable): A function that accepts (array1, array2) and returns (stat, pval).
        test_name (str): Optional name for the test, for labeling.

    Returns:
        results_df (pd.DataFrame): Pairwise comparisons with raw and corrected p-values.
    """
    results = []

    for (g1, g2) in combinations(raw_groups.keys(), 2):
        data1, data2 = raw_groups[g1], raw_groups[g2]
        stat, pval = test_func(data1, data2)
        results.append({
            'group1': g1,
            'group2': g2,
            'statistic': stat,
            'pval': pval,
            'test': test_name
        })

    results_df = pd.DataFrame(results)

    # Correct for multiple comparisons
    _, corrected_pvals, _, _ = multipletests(results_df['pval'], method='fdr_bh')
    results_df['pval_corrected'] = corrected_pvals
    results_df['significant'] = results_df['pval_corrected'] < 0.05

    return results_df

# Define wrapper function for Mann–Whitney U test
def mannwhitney_u_test(x, y):
    # Remove NaNs
    x_clean = x[~np.isnan(x)]
    y_clean = y[~np.isnan(y)]
    stat, pval = mannwhitneyu(x_clean, y_clean, alternative='two-sided')
    return stat, pval

def run():

    """
    Cell ID
    Region
    Condition
    Repeat
    """
    path = '/Users/cudmore/Desktop/sanpy-data/analysis-20250618-RHC/tif_pool_main.csv'
    # path = '/Users/cudmore/Desktop/sanpy-data/analysis-20250618-RHC/tif_pool_mean.csv'
    df = pd.read_csv(path,
                     header=1)

    # Aggregate
    stat = 'Peak Inst Freq (Hz)'
    groupby_cols = ['Region', 'Condition', 'Repeat']
    agg_list = ['count', 'mean', 'std', 'sem']
    agg_df, raw_groups = getGroups(df, stat, groupby_cols, agg_list)

    print(f'agg_df:')
    print(agg_df)
    # print(f'raw_groups:')
    # print(raw_groups)

    # Run tests
    results_df = run_pairwise_tests(raw_groups, mannwhitney_u_test, test_name='Mann-Whitney U')
    print(f'results_df:')
    print(results_df)


if __name__ == "__main__":
    run()