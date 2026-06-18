# Security policy

Tuck Meet is a student-built prototype intended for a supervised MHWI pilot.

## Reporting a vulnerability

If you find a security or privacy issue, please email the maintainer rather
than opening a public issue, so it can be addressed before disclosure.

## Security posture (summary)

- Access restricted to a configured Tuck email domain; email verification
  required before sign-in or matching.
- Passwords stored as salted PBKDF2-SHA256 hashes (never plaintext).
- CSRF protection and server-side validation on all forms.
- ORM-only database access (no raw SQL).
- Hardened session cookies and security headers; HSTS in production.
- All secrets supplied via environment variables; none committed to the repo.

See the "Security & privacy" section of the README for details.
