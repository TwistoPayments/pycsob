# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added
- Logging requests and responses.

### Changed
- Upgrade the current code to the [Basic-Payment] version 1.9.

### Fixed
- Close file handles in importing key.

### Removed
- Oneclick functions removed.

## [0.7] - 2020-09-22

### Changed
- Replaced CircleCI with GitHub Actions.
- Updated pycryptodome dependency, remove version pinning.

### Removed
- Remove Python 2 support.

## [0.6] - 2019-10-18

### Added
- Add CHANGELOG.md.

### Changed
- Fix begins/ends whitespaces on cart name.

## [0.5] - 2019-05-15

### Changed
- Support of API v1.7 - Merchant data.
- Add dttm_decode.
- Fix invalid language code type (country code).
- Add circleci config.

## [0.4]

### Added
- Add function button into CsobClient.

[Basic-Payment]: https://github.com/csob/paymentgateway/wiki/Basic-Payment
