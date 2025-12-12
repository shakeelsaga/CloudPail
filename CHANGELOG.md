# Changelog

All notable changes to the **CloudPail** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.4] - 2025-12-12
### Added
- **Network Resilience:** Implemented `EndpointConnectionError` handling to gracefully manage internet disconnections during active sessions.
- **Startup Checks:** Added automatic connectivity checks (`sts.get_caller_identity`) upon profile initialization.

### Changed
- **UI Polish:** Refactored `main.py` banner alignment and padding for better visual centering.
- **Code Refactoring:** Improved whitespace consistency and readability across the core logic.

## [1.0.3] - 2025-12-11
### Added
- **Modern Packaging:** Introduced `pyproject.toml` for standardized build configuration.
- **Licensing:** Added `LICENSE` file (MIT).

### Changed
- **Documentation:** Complete rewrite of `README.md` to remove casual language/emojis and focus on technical architectural details.
- **UI Refinement:** Replaced emojis in terminal output with professional status symbols (`✖`, `⚠`, `✔`).

### Removed
- **Legacy Config:** Removed `setup.py` in favor of `pyproject.toml`.

## [1.0.0] - 2025-12-11
### Added
- Initial release of CloudPail.
- Core features: Bucket management, Object operations, and Profile switching.