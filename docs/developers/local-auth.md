# Local development authentication

The local dev stack runs with session-based authentication by default.
When you start `./dev-tail.sh`, the API container picks up
`/auth-config/auth.yaml`, which is bind-mounted from `.dev-auth.yaml`
at the repo root.

This means the login flow works end-to-end out of the box: visit
`http://localhost:3000`, click "Dev stub login", and pick a user.

## The committed dev fixtures

`.dev-auth.yaml` defines three test users that every contributor shares:

- **alice** — admin of `project:tomcat`, member of `project:httpd`. Use
  this user for most workflows; you'll see workspace switching, role-
  scoped UI, and the standard "logged in as a project member"
  experience.
- **bob** — emeritus, no workspace memberships. Useful for testing the
  *deny* path: bob's login should be rejected with a "no workspaces
  available" error rather than completing successfully. If you find a
  way for bob to land on the home page, that's a bug.
- **site_admin_1** — listed in `site_admins` at the bottom of the file,
  so this user logs in as a cross-workspace site administrator. Use
  this to test admin-only views and operations.

These fixtures are committed deliberately. They have no real secrets
(the dev_stub provider grants login on uid alone with no credential
check) and sharing them keeps everyone testing the same code paths.

## Customizing for your own testing

If you need different users — say, to mirror your organization's
LDAP UIDs while testing membership lookup, or to add a fourth role
that doesn't exist in the shared fixture — copy the file:

```bash
cp .dev-auth.yaml .dev-auth.local.yaml
$EDITOR .dev-auth.local.yaml
```

`.dev-auth.local.yaml` is gitignored, so personal edits don't risk
ending up in a commit.

To make the dev stack use your local copy, edit the compose file's
`volumes` line for the api service to point at `.dev-auth.local.yaml`
instead, then re-run `./dev-tail.sh`. (A future improvement: have
dev-tail.sh prefer a `.dev-auth.local.yaml` if one exists.)

## Production deployments

The committed `.dev-auth.yaml` is **never appropriate for production**.
The dev_stub provider grants admin access via uid alone with no
credential verification — anyone who can reach `/auth/login/dev_stub`
becomes whichever user they ask to be.

For production, see `docs/examples/auth.example.yaml` for a template
that wires up real providers (ASF, Google, Microsoft, GitHub). Your
deployment process should:

1. Mount the production `auth.yaml` at a path of your choosing
   (typically from a secret manager, not the filesystem).
2. Set `AUTH_CONFIG_PATH` to point at it.
3. Either remove `dev_stub` from `auth.providers` or set
   `enabled: false` for that entry. The dev_stub provider should
   never be enabled in any environment that's reachable from the
   public internet.
4. Set `legacy_firebase_enabled: false` once your migration off
   Firebase is complete.

## Disabling auth locally

If you want to run the local stack without auth — for instance, while
poking at code paths that don't need an authenticated user — set the
frontend's auth provider to `mock` in
`webapp/packages/config/environments/local.js`:

```javascript
auth: {
  provider: 'mock',
},
```

The backend still mounts the auth routes (because the auth.yaml is
still bind-mounted), but the frontend won't try to use them; it uses
the `mockAuth` implementation that grants instant local-dev-user
access with no login page. Switch back to `'session'` to re-enable.

## Troubleshooting

**"Dev stub login" button missing on /login.** The frontend probes
`/auth/providers` to decide which buttons to render. If the API
container started without `AUTH_CONFIG_PATH` set, that endpoint
returns an empty list. Restart the api container:

```bash
docker compose restart api
```

**Login completes but lands back on /login.** The session cookie was
set, but the frontend isn't recognizing it. Check that
`webapp/packages/config/environments/local.js` has
`auth: { provider: 'session' }` — `'mock'` and `'firebase'` will both
ignore the session cookie.

**`{"detail":"Not Found"}` after picking a user.** The OAuth callback
redirected to `/login` against the wrong host. Check
`webapp/packages/api/user-service/routes_auth.py` — the redirect
target should be prefixed with `FRONTEND_URL`.

**bob lands on the home page.** This shouldn't happen — bob has no
workspace memberships and the auth callback should reject the login.
If you see this, check that `legacy_firebase_enabled: true` isn't
short-circuiting the workspace check, and file an issue.