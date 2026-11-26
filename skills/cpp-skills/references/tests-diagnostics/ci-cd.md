# CI/CD Quality and Static Analysis Tools

Guidelines for automated formatting, static analysis, and quality gates in modern C++ projects.

---

## Clang-Format

- **Automated Formatting:** Enforce consistent indentation, brace style, and spacing across C++ source and header files.
- **Reference Configuration:** See [`.clang-format`](./.clang-format).

---

## Clang-Tidy

- **Static Analysis:** Detect modern C++ anti-patterns, lifetime or ownership issues, and potential bugs using a compilation database (`compile_commands.json`).
- **Reference Configuration:** See [`.clang-tidy`](./.clang-tidy).

---

## Quality Gates and CI Checks

- **Focus on Changed Code:** Enforce strict formatting and static analysis checks primarily on pull requests and modified files so legacy code does not block day-to-day changes.
- **Centralized Quality Tracking:** Track maintainability, code smells, and security issues across branches using tools such as SonarQube when needed.
- **Complementary Layer:** Combine static analysis and formatting checks with strict compiler warnings and runtime sanitizers—static tools do not replace runtime testing.
