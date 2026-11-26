# Changelog

- **1.5.3** (2026-11-24): **Results first** (the maintainer's principle): nothing matters more than a result the user wants; save tokens by cutting waste, never by cutting a check, an option or a revise pass the result needs. Full text is rule 0 in `reference/house-rules.md`.
- **1.5.2** (2026-11-23): Gives the exact build line with `--out .proofs/pages/<name>.html`, the one folder the optional `open` allow rule covers, so the page can be opened. A spec's asset path that is not found next to the spec is now tried from the working directory, and the error names both paths.
- **1.5.1** (2026-11-22): Says to run `--smoke` every time: if it reports Playwright missing, run the one-line install it prints (no browser download) and run it again; if it still cannot run, say on the page and in chat that the self-check did not run. It no longer reads as optional when Playwright is absent.
- **1.5.0** (2026-11-22): Runs its scripts (`review_page.py`) through `${CLAUDE_PLUGIN_ROOT}` and pre-approves them and reads of the plugin's own files, so a session no longer asks permission for each one.
- **1.4.0** (2026-11-19): The page's header now starts with the proofs mark and a `article-copy-edit` pill, then the project and the session (accented), on a slim line above the heading. Fill `project.session`; a page without it still builds, with a warning.
- **1.3.2** (2026-11-19): Delivers the page as "Where the page goes" says rather than always via artifacts. Says plainly that it needs the whole plugin.
- **1.3.1** (2026-11-18): Description trimmed to the trigger and how it differs from its nearest sibling; the detail it used to carry is in the body. No change in behavior.
- **1.3.0** (2026-11-18): The review page is now built by the shared, tested builder (`shared/review_page`): Claude writes the spec and the Original/Edit panes, the builder supplies the four decision buttons, sticky tally, export and clipboard fallback. Same page and export for the reviewer; a plain accept exports as `ACCEPT (Use Edit)`.
- **1.2.3** (2026-11-18): Moved 'Where the page goes' to a shared reference file and the changelog to CHANGELOG.md; no change in behavior.
- **1.2.2** (2026-11-17): Copy buttons now fall back to a selectable text box when the clipboard is unavailable (as on a Wi-Fi-served page), and `wifi` mode is limited to a private network you trust.
- **1.2.1** (2026-11-16): New section "Where the page goes": a project can choose an artifact, a local file, or a file served on its own Wi-Fi.
- **1.2.0** (2026-11-16): Merged into proofs: generic, no project-specific steps.
