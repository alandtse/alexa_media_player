# Alexa Media Player Secure

**⚠️ WARNING: Pre-Alpha Scaffolding - Not Yet Functional**

This is a community fork of [alandtse/alexa_media_player](https://github.com/alandtse/alexa_media_player) with a redesigned authentication system.

## What This Fork Is

A refactored version of the Alexa Media Player integration with the following authentication improvements:

- **No stored passwords or TOTP seeds** – credentials are not persisted to configuration files
- **Paste-URL enrollment** – simpler, more secure authentication flow
- **Refresh-token-only persistence** – integration stores only refresh tokens, not sensitive credentials
- **Designed for coexistence** – new domain (`alexa_media_secure`) runs alongside the original integration

## Status

This is pre-alpha scaffolding. The authentication redesign is in active development. Do not use in production.

## Installation

Once functional, install via HACS by adding this repository as a custom repository:

```
Repository: https://github.com/superbeetle1973/alexa-media-secure
Category: Integration
```

Then install through the HACS UI.

## Design Documentation

See [alexa-auth-redesign](https://github.com/superbeetle1973/alexa-auth-redesign) for the complete design spec and implementation progress.

## Upstream Credit

This fork builds on the excellent work of:

- [Alan Tse](https://github.com/alandtse) – original project maintainer
- [Keaton Taylor](https://github.com/keatontaylor) – original creator

Original project: [alandtse/alexa_media_player](https://github.com/alandtse/alexa_media_player)

## License

This project retains the original Apache License 2.0. See [LICENSE](LICENSE) for details.
