# Tuck Meet

**Find your people. No pressure.**

Tuck Meet is a lightweight tool that helps members of the Tuck community make
low-pressure social connections. Students opt in, enter their availability, and
choose what they're open to — coffee, a walk, eating out, or a small-group meal.
Once a day the system looks for overlaps and emails a friendly introduction.

It is intentionally minimal: **no chat, no profiles, no social feed, and no
location tracking.** It collects only what's needed to make an introduction.

> Built as a prototype for a Mental Health & Wellness Initiative (MHWI) pilot.
> See [Security & privacy](#security--privacy) for the design choices that
> matter to an IT review.

---

## Table of contents
- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running the daily match (5 PM)](#running-the-daily-match-5-pm)
- [Email delivery](#email-delivery)
- [Project layout](#project-layout)
- [Testing](#testing)
- [Security & privacy](#security--privacy)
- [Data we store (and don't)](#data-we-store-and-dont)
- [Roadmap / integration notes](#roadmap--integration-notes)
- [License](#license)

---

## What it does

1. A student signs up with their **@tuck.dartmouth.edu** email and verifies it.
2. They pick their **availability** (day × time-of-day) and the **activities**
   they're open to.
3. They flip on **"I'm open to being matched."**
4. **Every day at 5:00 PM**, the matching engine pairs people (or forms small
   groups for meals) who share an activity and an available time slot, while
   avoiding re-matching the same people within a cooldown window.
5. Each person receives a short intro email with their match's name and email.
   There's no obligation — meet if it works, skip if it doesn't.

## Tech stack

- **Python 3.10+ / Flask** — small, readable, easy to audit.
- **SQLite** via SQLAlchemy (swap to Postgres with one env var in production).
- **Flask-Login** for sessions, **Flask-WTF** for CSRF + form validation.
- **Standard-library SMTP** for email; no third-party email SDK required.
- No frontend framework — server-rendered HTML and a single CSS file.

## Quick start

```bash
git clone <your-repo-url> tuck-meet
cd tuck-meet

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # paste into SECRET_KEY

python run.py                    # http://127.0.0.1:5000
```

The database tables are created automatically on first run.

## Configuration

All configuration is read from environment variables (see `.env.example`).
Nothing sensitive is hard-coded. Key settings:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs sessions and email-verification tokens. **Required in production.** |
| `DATABASE_URL` | Database connection string (defaults to local SQLite). |
| `ALLOWED_EMAIL_DOMAIN` | Only addresses on this domain may register. Defaults to `tuck.dartmouth.edu`. |
| `EMAIL_BACKEND` | `stub` (default, no real send) or `smtp`. |
| `REMATCH_COOLDOWN_DAYS` | Days before two people can be matched again (default 21). |
| `MATCHING_TRIGGER_TOKEN` | Bearer token protecting the HTTP matching trigger. |

## Running the daily match (5 PM)

Pick whichever fits your environment.

**Option A — Flask CLI via cron** (recommended on Linux/macOS):
```cron
# Every day at 17:00
0 17 * * * cd /path/to/tuck-meet && /path/to/.venv/bin/flask run-matching
```

**Option B — standalone script:**
```cron
0 17 * * * cd /path/to/tuck-meet && /path/to/.venv/bin/python scripts/run_matching.py
```

**Option C — HTTP trigger** (for a hosted scheduler):
```bash
curl -X POST https://your-host/tasks/run-matching \
     -H "Authorization: Bearer $MATCHING_TRIGGER_TOKEN"
```

On **Windows**, use Task Scheduler to run `scripts/run_matching.py` daily at 17:00.

## Email delivery

The app never hard-codes mail credentials. Two backends, switched with
`EMAIL_BACKEND`:

- **`stub`** (default): nothing leaves the machine. Each message is logged and
  written to `./outbox/*.txt` so you can preview exactly what *would* be sent.
  Ideal for demos and review.
- **`smtp`**: sends through a real SMTP server using the `SMTP_*` settings.
  Intended to point at an approved Tuck/Dartmouth relay rather than a personal
  account.

## Project layout

```
tuck-meet/
├── app/
│   ├── __init__.py      # app factory, security headers, CLI commands
│   ├── config.py        # (see ../config.py) env-driven settings
│   ├── extensions.py    # db, login manager, CSRF singletons
│   ├── models.py        # User, Availability, ActivityPreference, Match, ...
│   ├── forms.py         # validated, CSRF-protected forms
│   ├── tokens.py        # signed, expiring email-verification tokens
│   ├── auth.py          # register / verify / login / logout
│   ├── main.py          # landing, dashboard, preferences, match trigger
│   ├── matching.py      # the matching engine (pure, testable)
│   ├── emailer.py       # stub + SMTP backends
│   ├── templates/       # server-rendered HTML
│   └── static/style.css
├── scripts/run_matching.py
├── tests/               # pytest suite (auth + matching)
├── config.py
├── run.py
├── requirements.txt
├── .env.example
└── README.md
```

## Testing

```bash
pytest
```

The suite covers domain restriction, password hashing, email-verification
gating, and the matching rules (shared slot + activity, cooldown, small-group
formation, opt-in/verification filtering).

## Security & privacy

Design choices made with an IT/security review in mind:

- **Restricted access.** Registration is limited to the configured Tuck email
  domain, and accounts must verify their email (signed, expiring token) before
  they can sign in or be matched.
- **Passwords** are stored only as salted **PBKDF2-SHA256** hashes
  (via Werkzeug); plaintext is never written. Minimum length is enforced.
- **CSRF protection** on every form (Flask-WTF). All input is validated
  server-side.
- **No SQL injection surface** — all queries go through the SQLAlchemy ORM
  (parameterized).
- **Session hardening** — `HttpOnly`, `SameSite=Lax`, and `Secure` cookies in
  production; 12-hour session lifetime.
- **Security headers** on every response — `Content-Security-Policy`
  (first-party only), `X-Frame-Options: DENY`, `X-Content-Type-Options:
  nosniff`, `Referrer-Policy`, and HSTS in production.
- **No open redirects** — post-login redirects are restricted to same-site paths.
- **Account-enumeration resistant** — registration and login return generic
  messages rather than revealing whether an address exists.
- **Protected automation** — the HTTP matching trigger requires a bearer token
  compared in constant time.
- **Secrets via environment only** — `.env` is git-ignored; `.env.example`
  documents every setting with no real values.

## Data we store (and don't)

**Stored:** display name, verified Tuck email, password hash, coarse
availability (day + morning/afternoon/evening), activity opt-ins, and a history
of past matches (to enforce the cooldown).

**Not stored / not collected:** chat messages, profiles or bios, photos, phone
numbers, precise calendars, and any location data. There is no social feed and
no third-party analytics.

## Roadmap / integration notes

- **NetID / SAML SSO.** This prototype uses email + password so it runs
  standalone. Auth is isolated in `app/auth.py`, so swapping in Dartmouth NetID
  SSO would replace registration/login without touching the matching logic.
- **Approved mail relay.** Point `EMAIL_BACKEND=smtp` at a sanctioned
  Tuck/Dartmouth SMTP relay so introductions come from an official address.
- **Admin view.** A simple MHWI admin dashboard (counts, opt-in totals, manual
  run) is a natural next step; `make-admin` and the `is_admin` flag are already
  in place.

## License

MIT — see [LICENSE](LICENSE).
