# iOS App Handoff — Account Login (username + password)

**Audience:** whoever updates the iOS app.
**Server status:** deployed and live on the Training API (`:8001`, Tailscale Funnel `https://ardencore.tail38e03e.ts.net:8443`). No further backend work required — every endpoint below is implemented and verified.
**TL;DR:** the API is now multi-user. Add a **login screen** (server URL + username + password) that calls `POST /api/auth/login` and stores the returned **token**. That token is then used *exactly* like the API key the app stores today — same `Authorization: Bearer <token>` header on every request. Nothing else about how the app talks to the API changes.

---

## 1. What changes, and what doesn't

| | Today | After |
|---|---|---|
| How the app gets a credential | User pastes an **API key** | User enters **username + password** once; the app exchanges them for a token |
| What the app stores | server URL + API key | server URL + token (+ token id + who you're signed in as) |
| How every request authenticates | `Authorization: Bearer <api key>` | `Authorization: Bearer <token>` — **identical** |

So this is **one new screen plus token storage**, not a rewrite of the networking layer. The token *is* the new API key.

**Keep the manual API-key field** as an "Advanced" option if you like — pasting a token directly still works (a token and the old API key are the same kind of Bearer credential). Recommended UX: username/password login as the primary path, manual token entry tucked behind "Advanced".

---

## 2. The login endpoint

```
POST {serverURL}/api/auth/login
Content-Type: application/json
(no Authorization header — this is how you obtain one)
```

Request body (camelCase; `username` is case-insensitive):

```json
{ "username": "monika", "password": "her-password", "deviceName": "Monika's iPhone" }
```

- `deviceName` is optional but recommended — it labels the token in the account's token list (useful for "sign out this device" later). Use the device name (`UIDevice.current.name`).

**200 response:**

```json
{
  "token": "tapi_9f3c…",
  "tokenId": "1db90eee-44b3-487a-8a84-e1d4e67be43f",
  "user": { "id": "…", "username": "monika", "displayName": "Monika", "role": "user" }
}
```

- **`token`** — store it; send as `Authorization: Bearer <token>` on every `/api` request (same slot the API key uses now).
- **`tokenId`** — store it too; needed to revoke *this* session on logout (§6).
- **`user`** — for display ("Signed in as Monika") and, if you ever want it, `role` (`admin`/`user`).

**Error responses:**

| Status | Meaning | Suggested UI |
|---|---|---|
| `401` `{"detail":"Invalid username or password"}` | Wrong username/password, or the account is disabled | Generic "Incorrect username or password." — do **not** distinguish the cases |
| `429` | Rate limit hit (5 login attempts/minute) | "Too many attempts. Wait a minute and try again." |
| network / timeout / non-2xx | Server unreachable / wrong URL | "Couldn't reach the server. Check the address." |

---

## 3. Store the token in the Keychain

Persist, per configured server:
- `serverURL`
- `token` (the credential — **Keychain**, not `UserDefaults`)
- `tokenId`
- `username` / `displayName` / `role` (for display; these can live in `UserDefaults`)

Send `Authorization: Bearer <token>` on every request to `/api/*`. The only endpoints that need **no** token are `GET /api/health` and `POST /api/auth/login`.

---

## 4. Handle `401` anywhere → session is invalid (the important one)

Any `/api` call returning **`401`** means the token is no longer valid — it was revoked (e.g. from another device or by the admin), it expired, or the account was deactivated. On **any** 401:

1. Clear the stored token from the Keychain.
2. Route the user back to the login screen.

This one rule is what makes revocation, password changes, and account deactivation "just work" on the app side. It's the single most important addition beyond the login screen itself.

---

## 5. Signed-in state / token management (optional)

```
GET {serverURL}/api/auth/me      (Authorization: Bearer <token>)
```

```json
{
  "user": { "id": "…", "username": "monika", "displayName": "Monika", "role": "user" },
  "tokens": [
    { "id": "…", "name": "Monika's iPhone", "createdAt": "…", "lastUsedAt": "…", "expiresAt": null }
  ]
}
```

Use it for a "Signed in as …" label, or a full "Devices" screen that lists tokens and lets the user revoke others (see §6). Purely optional — not needed for basic login.

---

## 6. Logout

```
DELETE {serverURL}/api/auth/tokens/{tokenId}      (Authorization: Bearer <token>)
```

- `204` = revoked. `404` = already gone — treat as success.
- Do this **best-effort** (revokes the token server-side so a leaked copy is dead), then **always** clear the Keychain regardless of the network result.
- You can revoke any of the account's own tokens this way (powers a "sign out other devices" feature); `404` is returned for a token id that isn't yours, so there's nothing to leak.

If you skip server-side revoke for v1, logout can just clear local storage — the token stays valid until revoked elsewhere. Storing `tokenId` (§2) is what lets you do it properly.

---

## 7. Server URL

- This instance: **`https://ardencore.tail38e03e.ts.net:8443`**
- Keep the URL user-configurable (that's the whole point of the multi-user/self-host direction — someone else can point the app at their own server). The login call is always `{serverURL}/api/auth/login`.

---

## 8. Migration note for the existing (Arden's) phone

The app currently holds the legacy API key, which is registered as **admin's** token — it keeps working unchanged, so there's no forced re-login. When the login screen ships you can either leave the phone on the pasted key, or log in as `admin` to get a fresh **named** token (it'll show as its `deviceName` in `/api/auth/me` and is independently revocable). Either is fine.

---

## 9. How accounts get created (server side, for context)

There's **no self-registration** endpoint (the API is public via Funnel, so open signup is intentionally not offered). The admin creates accounts over SSH:

```
docker exec -it backend__training-api python -m app.cli create-user monika
docker exec -it backend__training-api python -m app.cli set-password monika   # or set during create
```

The person then just logs in through the app with that username/password. (An admin-only "create user" screen in the app is possible later but out of scope here.)

---

## 10. Contract summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/login` | none | Exchange username+password for a token (`{token, tokenId, user}`) |
| `GET` | `/api/auth/me` | Bearer | Current user + list of their tokens |
| `DELETE` | `/api/auth/tokens/{tokenId}` | Bearer | Revoke a token (logout / sign out a device) |
| everything else under `/api/*` | | Bearer | Unchanged — same header the app sends today |

Notes: login is rate-limited to 5/min per source. Passwords are never stored on the device — only the token. Tokens are long-lived (no expiry unless an admin sets one), so treat **`401`** as the definitive "session ended" signal rather than tracking expiry on-device.

---

## Quick manual test (before wiring the UI)

```bash
BASE=https://ardencore.tail38e03e.ts.net:8443     # or http://<tailscale-ip>:8001

# 1. Log in → capture token + tokenId
curl -s -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<pw>","deviceName":"curl-test"}'

# 2. Use the token
curl -s "$BASE/api/workouts?limit=1" -H "Authorization: Bearer <token>"

# 3. Log out (revoke this token), then confirm it's dead (should 401)
curl -s -X DELETE "$BASE/api/auth/tokens/<tokenId>" -H "Authorization: Bearer <token>"
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/api/workouts?limit=1" -H "Authorization: Bearer <token>"
```
