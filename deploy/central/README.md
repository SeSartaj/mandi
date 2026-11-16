# Central distribution integration

`scripts/setup.sh` checks out the pinned upstream release
(v2026.3.1, 7d6de621955c5bb6a68e098ca10c9cbb92285cdf) and its `server` submodule
into `deploy/runtime/central`. Central's Dockerfiles are built from that local
checkout; a remote Git build cannot include the submodule. The nginx and Redis
configuration templates in this directory are copied from that release; their
upstream license is preserved in LICENSE.md. `rsa.private` is upstream's empty
placeholder, not a private key. `odk.conf.template` also replaces upstream's
Sentry CSP proxy with an empty `204` response, so self-hosting does not need
ODK's Sentry credentials.

The root Compose file wires the same runtime components into one project, using
network aliases expected by upstream. A fresh PostgreSQL 14.24 database starts
with the normal official image entrypoint; the legacy 9.6→14 migration sidecar
is intentionally unnecessary for this new installation. Existing old Central
volumes require upstream's upgrade procedure before using this layout.

start-central.sh runs upstream startup/migrations and then bootstrap.mjs inside
Central to initialize its administrator and project-scoped integration account.
Only public CA certificates are shared with Node processes for local HTTPS;
Central and Enketo do not receive Caddy's CA signing key. Public hostnames resolve
to the proxy within Docker as well as on the host.
