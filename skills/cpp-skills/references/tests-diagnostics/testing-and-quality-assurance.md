# Testing and Quality Assurance
## Overview

Guidelines for writing deterministic, maintainable unit and integration tests, isolating dependencies, and enforcing regression safety across C++ codebases.

## Unit Testing Frameworks

- **Google Test (GTest):** Recommended for structured, large-scale unit and integration testing suites with rich assertion and fixture support (`TEST`, `TEST_F`, `TYPED_TEST`).
- **Catch2:** Suitable for expressive test cases and BDD-style grouping (`TEST_CASE`, `SECTION`, `REQUIRE`, `CHECK`) with lightweight test authoring.
- **Test Independence:** Keep tests isolated, order-independent, and free of shared mutable global state so they can run reliably in parallel.

## Mocking & Isolation

- **Google Mock (GMock):** Use interface-driven mocks (`MOCK_METHOD`) to isolate units from external systems (network, filesystem, clocks, hardware) and verify interaction contracts (`EXPECT_CALL`).
- **Prefer Fakes/Stubs Over Over-Mocking:** Favor lightweight in-memory fakes or pure functions over brittle mock chains when testing behavior rather than internal call sequences.
- **Design for Testability:** Inject dependencies via constructors or template/concept parameters instead of hardcoding global singletons.

## Test Coverage & Scenarios

- **Happy Path & Invariants:** Verify expected outputs and post-conditions/class invariants after operations.
- **Edge Cases:** Explicitly test boundary values, integer overflow/underflow limits, empty containers/views (`std::string_view`, `std::span`), and invalid or out-of-range states.
- **Error Conditions:** Verify both exception paths (`noexcept` vs throwing contracts) and explicit error-handling paths (`std::expected`, `std::error_code`, status types).
- **Regression Tests:** Add a targeted test case whenever fixing a bug to prevent reintroduction.

## Continuous Integration (CI)

- **Automated Gatekeeping:** Run unit and integration test suites automatically on pull requests and commits before merging.
- **Multi-Configuration Matrix:** Test across key compilers, C++ standards, build modes (`Debug`/`Release`), and platforms relevant to the project.
- **Combine with Sanitizers & Static Analysis:** Pair test execution with ASan, UBSan, TSan, and static analysis checks to catch subtle runtime and undefined-behavior defects early.