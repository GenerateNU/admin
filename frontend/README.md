# Generate Admin — frontend

Next.js admin console for the [backend API](../backend). Sign-in is Entra ID (MSAL, SPA/PKCE
flow, no client secret); once signed in, the app calls the API using the typed client in
[`@generatenu/api`](../packages/api).

## Requirements

- Node 22+ (`.nvmrc` at the repo root; `nvm use` picks it up)
- The backend running locally — see the [root README](../README.md) (`just up && just migrate && just seed && just dev`)

## Setup

```bash
just frontend-install
cp frontend/.env.example frontend/.env.local
```

Fill in `frontend/.env.local`:

| Variable                      | Where it comes from                                                                                    |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_ENTRA_TENANT_ID`  | The Entra tenant ID (same tenant the backend's `ENTRA_TENANT_ID` uses)                                    |
| `NEXT_PUBLIC_ENTRA_CLIENT_ID`  | Client ID of this app's Entra app registration (SPA platform, redirect URI = `http://localhost:3000`)     |
| `NEXT_PUBLIC_API_SCOPE`        | `api://<backend's ENTRA_API_CLIENT_ID>/access_as_user` — the exposed API scope, not Graph                 |
| `NEXT_PUBLIC_API_BASE_URL`     | `http://localhost:8000` for local dev                                                                     |

These are all public identifiers (no secret — MSAL uses PKCE), so it's normal for
`NEXT_PUBLIC_*` values to end up in the browser bundle. If you don't have an app registration
yet, ask a teammate who's set one up, or create one in the Azure Portal under the same tenant
as the backend's.

Then:

```bash
just frontend-dev
```

Open [http://localhost:3000](http://localhost:3000).

## How auth works

- `src/auth/msal.ts` configures MSAL and requests `NEXT_PUBLIC_API_SCOPE` (not a Graph scope) —
  that's what makes Entra mint an access token whose `aud` is the backend's client ID, which is
  what `TokenVerifier` on the backend checks.
- `src/app/providers.tsx` wires up `MsalProvider`, a React Query `QueryClient`, and calls
  `configureApi({ baseUrl, getToken })` from `@generatenu/api` so every generated hook
  automatically attaches a bearer token.
- `src/auth/SessionGate.tsx` wraps the whole app (in `layout.tsx`) and is the only place that
  decides what to render based on `GET /session`'s `access_state`:

  | `access_state` | What's shown |
  | -------------- | ------------ |
  | not signed in  | Sign-in button |
  | `no_access`    | A "request access" form (`POST /session/access-request`) — no invitation and no prior request |
  | `pending`      | "your request is awaiting review" |
  | `denied`       | "your request was denied" |
  | `suspended`    | "your account has been suspended" |
  | `no_roles`     | The app, plus a banner — signed in and provisioned, but no role grants a permission yet |
  | `active`       | The app |

  Signing in with an email that has an open invitation provisions the user automatically (the
  backend accepts the invitation the first time `GET /session` is called for that identity) —
  there's no separate "create account" step.

  Anything rendered inside `SessionGate` can call `useSession()`
  (`src/auth/session-context.tsx`) to get the current `Session`, guaranteed to have a non-null
  `user`.

## Commands

| Recipe                  | What it does                                                             |
| ------------------------ | -------------------------------------------------------------------------- |
| `just frontend-install`  | `npm install` at the repo root (this is an npm workspace, not standalone) |
| `just frontend-dev`      | Dev server (Turbopack)                                                    |
| `just frontend-build`    | Production build (also type-checks)                                      |
| `just frontend-lint`     | ESLint                                                                    |
| `just gen`               | Regenerate `@generatenu/api` from the backend's committed `openapi.json` |

Regenerate the API client whenever backend endpoints change and commit the diff — CI
(`backend-ci.yml`'s `contract` job) fails the build if `packages/api/src/generated` is stale.
