---
name: scientific-statistics-latex
description: Performs rigorous scientific statistical analysis (hypothesis testing, ANOVA, regression, survival analysis, Bayesian inference, effect sizes) in Python/R and typesets publication-ready LaTeX documents, TikZ diagrams, booktabs tables, and algorithm2e pseudocode. Use for academic papers, dissertations, experimental data analysis, and journal submissions.
---

# Scientific Statistics & Advanced LaTeX Typesetting Skill

Specialized skill for conducting publication-grade statistical inference in Python (`scipy`, `statsmodels`, `pingouin`, `seaborn`) and typesetting complex mathematical/scientific manuscripts in LaTeX (IEEE, Springer, Elsevier, ACM, and AAK/GOST dissertation standards).

---

## 1. Rigorous Statistical Workflow

Never report a bare $p$-value without checking assumptions and reporting effect sizes + confidence intervals.

### Step 1: Assumption Checking
Before choosing a parametric vs. non-parametric test:
1. **Normality**: Shapiro-Wilk test (`scipy.stats.shapiro`) for $n < 50$ or D'Agostino's $K^2$ / Q-Q plots for larger samples.
2. **Homoscedasticity (Equal Variance)**: Levene's test (`scipy.stats.levene`) or Bartlett's test.

### Step 2: Decision Matrix for Hypothesis Testing

| Comparison Goal | Parametric (Normal + Equal Var) | Non-Parametric (Skewed / Ordinal) | Effect Size Metric |
|---|---|---|---|
| **2 Independent Groups** | Student's / Welch's $t$-test (`ttest_ind(equal_var=False)`) | Mann-Whitney $U$ test (`mannwhitneyu`) | Cohen's $d$ / Hedge's $g$ / Rank-biserial $r_{rb}$ |
| **2 Paired Groups** | Paired $t$-test (`ttest_rel`) | Wilcoxon signed-rank (`wilcoxon`) | Cohen's $d_z$ |
| **$\ge 3$ Independent Groups** | One-way ANOVA (`f_oneway`) + Tukey HSD | Kruskal-Wallis $H$ (`kruskal`) + Dunn's post-hoc | Eta-squared ($\eta^2$) / Omega-squared ($\omega^2$) |
| **$\ge 3$ Repeated Measures** | Repeated Measures ANOVA (`AnovaRM`) | Friedman test (`friedmanchisquare`) | Kendall's $W$ / Partial $\eta_p^2$ |
| **Categorical Association** | Pearson's $\chi^2$ (`chi2_contingency`) | Fisher's Exact Test (`fisher_exact` for $2\times2$) | Cramér's $V$ / Odds Ratio (OR) |
| **Correlation** | Pearson's $r$ (`pearsonr`) | Spearman's $\rho$ (`spearmanr`) / Kendall's $\tau$ | $r$ with 95% CI |

### Step 3: Multiple Comparisons Correction
When running multiple hypothesis tests ($m > 1$), always apply family-wise error rate (FWER) or false discovery rate (FDR) correction via `statsmodels.stats.multipletests`:
- **Bonferroni** or **Holm-Bonferroni** (`method='holm'`) for strict FWER control.
- **Benjamini-Hochberg** (`method='fdr_bh'`) for exploratory genomics/high-dimensional metrics.

### Step 4: APA / Journal Reporting Format
Always format statistical results in text with exact test statistics, degrees of freedom, $p$-value, effect size, and 95% CI:
> *Example*: "The proposed architecture significantly reduced inference latency compared to the baseline, $t(48) = -6.42, p < .001, \text{Hedges' } g = 1.82, 95\% \text{ CI } [1.15, 2.49]$."

---

## 2. Publication-Quality Figures (`matplotlib` / `seaborn`)

Configure plots for high-DPI vector/raster journal export (`.pdf`, `.eps`, `.png` at 300+ DPI):

```python
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})
```

---

## 3. Advanced LaTeX Typesetting Standards

### A. Professional Tables (`booktabs` + `siunitx`)
Never use vertical lines (`|`) or double horizontal rules (`\hline\hline`) in academic LaTeX tables. Always use `\toprule`, `\midrule`, and `\bottomrule` from `booktabs`:

```latex
\usepackage{booktabs}
\usepackage{siunitx}
\usepackage{multirow}

\begin{table}[htbp]
  \centering
  \caption{Performance Comparison Across Benchmark Datasets ($\text{Mean} \pm \text{SD}$ over 5 runs).}
  \label{tab:benchmark-results}
  \begin{tabular}{l S[table-format=2.2] S[table-format=2.2] S[table-format=1.3] r}
    \toprule
    \textbf{Model Architecture} & {\textbf{Accuracy (\%)}} & {\textbf{F1-Score (\%)}} & {\textbf{ROC-AUC}} & {\textbf{Latency (ms)}} \\
    \midrule
    Baseline CNN                & 84.20                   & 83.15                   & 0.892              & $42.1 \pm 1.8$ \\
    Transformer-Small           & 89.45                   & 88.90                   & 0.941              & $68.4 \pm 2.3$ \\
    \midrule
    \textbf{Ours (Hybrid-RAG)}  & \textbf{94.82}          & \textbf{94.50}          & \textbf{0.984}     & $\mathbf{31.5 \pm 1.1}$ \\
    \bottomrule
  \end{tabular}
\end{table}
```

### B. Algorithms (`algorithm2e` / `algpseudocode`)
Write formal mathematical pseudocode with explicit `\KwIn`, `\KwOut`, time/space complexity annotations, and vector notation ($\mathbf{x} \in \mathbb{R}^d$).
