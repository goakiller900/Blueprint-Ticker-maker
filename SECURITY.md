# Security policy

## Supported version

The latest version on the default branch is supported.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting or open a private security
advisory for this repository. Do not publish exploit details in a public issue
before the maintainer has had a reasonable opportunity to investigate.

## Runtime scope

The desktop application is intentionally offline and uses only the Python
standard library at runtime. PyInstaller is used only during the build process.
Generated executables are not code-signed; operating systems may therefore
show an unknown-publisher warning.
