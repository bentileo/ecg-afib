# Security

What this application protects, what it does not, and why.

## Data handling

**Uploaded recordings are never stored.** A waveform exists in memory for the
duration of one screening and is discarded when the session ends. It is not
written to disk, not sent to the database, and not written to logs.

**Only outcomes are recorded.** A row in the `predictions` table holds a
timestamp, a source label (a sample name or the word "upload"), a probability, a
boolean, a heart rate, and a variability measure. No filename, no IP address, no
session identifier, and no part of the signal.

**Do not upload identifiable patient data.** This project operates under no
agreement permitting the handling of protected health information.

## Credentials

Two Supabase keys are used, with different scopes:

| Key | Where it lives | What it can do |
| --- | --- | --- |
| Publishable | In the application; assume public | Insert a screening result |
| Secret | `.env` on the server only | Read results |

Row-level security enforces this. The publishable key has an INSERT policy and
no SELECT policy, so extracting it from the application yields write-only
access. Verify with:

```sql
select policyname, cmd from pg_policies where tablename = 'predictions';
```

The secret key is safe on the server because Streamlit renders server-side. The
Python never reaches a browser.

## Input validation

Uploads are bounded before any processing:

- 2 MB maximum file size, against a typical recording of roughly 20 KB
- between 200 and 360,000 samples
- at least 90% of rows must parse as numbers
- amplitudes beyond ±50 mV are rejected as a unit error

Malformed files produce a readable message rather than a stack trace.

## Database

- Inserts are limited to 60 per hour by a trigger
- A check constraint rejects values the model could not have produced
- Rows older than thirty days can be pruned by a maintenance function

## Server

- SSH accepts keys only; password authentication and root login are disabled
- The application runs as an unprivileged user under systemd
- Streamlit binds to localhost; nginx terminates TLS and proxies to it
- The service account may restart only its own unit, via a scoped sudoers rule
- Certificates renew automatically

## What is not protected

Stated plainly, because a security document that claims completeness is not
credible.

**The admin password has no rate limit.** It can be guessed at repeatedly. A
long random password makes this impractical, but there is no lockout.

**Insert flooding is slowed, not prevented.** The rate limit is global rather
than per-client, so a determined attacker can still consume the hourly budget
and deny writes to legitimate users.

**There is no audit log.** Nothing records who read the history view.

**The model artifact is unverified.** It reaches the server by `scp` with no
checksum, so corruption or substitution would go unnoticed.

**This is a portfolio project.** The database holds screening results from
public research recordings. Fully compromised, an attacker obtains a list of
timestamps and heart rates. The controls above are proportionate to that, and
would need revisiting before the application accepted real clinical data.

## Reporting

Security issues: open an issue at
[github.com/bentileo/ecg-afib/issues](https://github.com/bentileo/ecg-afib/issues).
