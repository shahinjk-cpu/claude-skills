# Writing tasks for the runner role

The runner does best with narrow, fully specified tasks. Every runner task has four parts:

1. **One action.** "Search for ...", "Read ... and extract ...", "Compare ... on ...".
2. **Explicit scope.** Which models, products, dates, or sources; "use only the vendor's own page" when that matters; "results published in 2026 only".
3. **Fixed output format.** One line per item, named fields, and what to write when nothing is found ("no data", "NOT FOUND").
4. **Length cap.** "No other text. Maximum 15 lines."

Example:

```text
Search the web and X for published code review benchmarks that report recall and precision for
these models: <model list>.
Output format: one line per model: model name, score, benchmark name, source URL.
If no published result exists for a model, write 'no data'. Use only results published in 2026.
No other text. Maximum 15 lines.
```

Split broad questions into several such tasks and run them in parallel. Treat every result as unverified until Claude has opened the source.
