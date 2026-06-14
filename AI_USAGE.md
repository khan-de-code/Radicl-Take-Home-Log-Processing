# AI Usage Disclosure

This document discloses the usage of AI tools during the development of the Log Normalizer service.

## Tools Used
- **Antigravity**: Used throughout pair-programming, code generation, refactoring, and test writing.

## Usage Details
- **Boilerplate & Infrastructure**: Generated the initial scaffolding, directory layout, and TCP asyncio server code.
- **Parsing & Normalization Logic**: Co-designed and implemented the ISO 8601 UTC timezone normalization, leap year lookup adjustments for Feb 29, and sentinel filtering logic.
- **Testing**: Assisted in writing the pytest unit tests, golden snapshot validation, performance load test client scripts, and BDD integration feature files.
- **Refactoring & Debugging**: Used to debug the Windows Event subject/target username fallback logic and clean up the ruff formatting.

## Written Manually vs. AI-Generated
- **AI-Generated**: Initial asyncio TCP boilerplate, parsing regex/date patterns, mock performance test structure, and BDD step-definition wrappers.
- **Manually Written/Steered**: Critical edge case fixes, adjustments for leap-year handling constraints, specific fallback condition ordering, standard null SID handling, and command configurations in the `justfile`.
