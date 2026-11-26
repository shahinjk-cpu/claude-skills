---
name: dissertation-research-pro
description: >-
  Guides academic research, literature review synthesis, dissertation/thesis writing,
  methodology design, statistical reporting, and citation formatting (APA 7, IEEE,
  Harvard, GOST, BibTeX/LaTeX). Use when the user is researching a scientific topic,
  writing a dissertation, thesis, or journal paper, or analyzing academic literature.
---

# Academic Research & Dissertation Co-Author

Pairs with your installed scientific literature skills (`literature-search-arxiv`, `literature-search-openalex`, `literature-search-europepmc`, `pubmed-database`) to support rigorous dissertation, thesis, and scientific paper authoring.

## 1. Zero-Hallucination Citation & Literature Protocol

1. **Never Invent Citations or DOIs**:
   - Every cited paper, author, year, and DOI **must** be verified via `literature-search-openalex`, `literature-search-arxiv`, `literature-search-europepmc`, `pubmed-database`, or `search_web`.
   - If a specific source cannot be verified, explicitly mark it as `[Citation Needed — Verify Source]` rather than guessing a DOI or author list.
2. **Systematic Literature Review Workflow**:
   - **Step 1 (Discovery)**: Query OpenAlex / arXiv / EuropePMC across foundational (highly cited) papers and recent frontier studies (last 3–5 years).
   - **Step 2 (Synthesis Matrix)**: Group literature by **Theme / Methodology / Findings / Limitations** instead of writing disconnected paper-by-paper summaries.
   - **Step 3 (Research Gap Identification)**: Explicitly articulate what existing studies solved, where they fall short, and how the dissertation's hypothesis/contribution bridges that gap.

## 2. Dissertation & Thesis Structural Standards

Support both international (**IMRaD** / Monograph) and regional (**AAK / GOST** dissertation) structures:

- **Giriş (Introduction)**:
  - Mövzunun aktuallığı və işlənmə dərəcəsi (Relevance & State of the Art)
  - Tədqiqatın məqsədi və vəzifələri (Aim & Objectives)
  - Tədqiqatın obyekti və predmeti (Object & Subject of Research)
  - Tədqiqat metodları (Research Methods)
  - Mühafiəyə çıxarılan əsas müddəalar (Key Provisions Defended)
  - Tədqiqatın elmi yeniliyi (Scientific Novelty)
  - Tədqiqatın nəzəri və praktiki əhəmiyyəti (Theoretical & Practical Significance)
- **Fəsil I (Literature Review & Theoretical Framework)**: Critical comparison of existing theories, algorithms, and models with summary comparison tables.
- **Fəsil II (Methodology & System Architecture)**: Mathematical formulations, formal models, algorithms, dataset characteristics, and architectural diagrams (Mermaid / LaTeX TikZ).
- **Fəsil III (Experimental Evaluation & Results)**: Quantitative benchmarks, ablation studies, statistical significance ($p$-values, confidence intervals, RMSE/F1/AUC metrics), and error analysis.
- **Nəticə (Conclusion & Future Work)**: Numbered conclusions mapping 1-to-1 back to the objectives stated in the Introduction.

## 3. Academic Style & Formatting Rules

1. **Tone & Precision**:
   - Maintain formal, objective third-person academic prose (in Azerbaijani, English, or Russian as requested).
   - Define every acronym upon first use (e.g., *Retrieval-Augmented Generation (RAG)*).
2. **Equations, Tables, and Figures**:
   - Number all equations `(1.1)`, tables `Cədvəl 1.1`, and figures `Şəkil 1.1` consistently by chapter.
   - Every table and figure must be referenced and interpreted in the main text.
3. **Bibliography Management**:
   - Format references strictly in the user's chosen standard (**APA 7th**, **IEEE `[1]`**, **Harvard**, or **AZS/GOST**), and maintain a clean `.bib` (BibTeX) file when working with LaTeX.
