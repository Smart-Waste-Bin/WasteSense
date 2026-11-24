# WasteSense Login: A Simple Guide

This guide explains how signing in works and how to run it. It describes the
process in everyday terms, without needing to understand the source code.

## What the login page does

1. A person enters the email address or phone number and password.
2. The web page sends those details to the WasteSense server.
3. The server checks whether the account exists and whether the password is correct.
4. If the details are valid, the server creates a temporary sign-in pass and sends
   the person to the dashboard.
5. If the details are not valid, the page shows a clear message and keeps the
   person on the login screen.

The password is never placed on the screen or saved by the web page. The server
stores a protected password value, not the original password.

## Remember me

- If **Remember me** is selected, the browser keeps the sign-in pass until it
  expires or the person signs out.
- If it is not selected, the browser clears the sign-in pass when the browser
  tab/session ends.

Remember me is a convenience, not a permanent password. Signing out removes the
active session.

## Starting the system

### 1. Start the backend

From the repository root:

```powershell
docker compose up
```

In a browser, open `http://localhost:8000/api/health`. It should say that the
server is healthy.

### 2. Start the web page

In a second terminal:

```powershell
cd Frontend\Web
npm install
npm run dev
```

Open the address printed by Vite, usually `http://localhost:5173`.

### 3. Sign in

Use an account created by an administrator or one of the seeded accounts. The
seed passwords come from `SEED_ADMIN_PASSWORD`, `SEED_SUPERVISOR_PASSWORD`, and
`SEED_COLLECTOR_PASSWORD` in the root `.env` file.

## What happens after sign-in

The dashboard first asks the server who the current person is. This prevents a
screen from opening merely because the browser has old data.

The user's name and role appear in the dashboard header. Signing out tells the
server to end the session and removes the temporary sign-in information from
the browser.

## Common messages

- **Wrong email/phone or password:** the account details did not match.
- **Too many failed logins:** the account is temporarily locked after repeated
  failed attempts.
- **This account has been deactivated:** an administrator disabled the account.
- **Server could not be reached:** the backend may not be running or the web
  app may be using the wrong API address.

## Configuration

The web app normally uses `http://localhost:8000`. If the API runs somewhere
else, create `Frontend/Web/.env.local`:

```text
VITE_API_URL=http://your-api-address
```

Restart `npm run dev` after changing this value.

## Keeping access safe

- Do not share passwords or sign-in tokens.
- Do not put passwords or tokens in screenshots, chats, notes, or source control.
- Use the sign-out button at the end of a session.
- Use HTTPS and `COOKIE_SECURE=true` in a deployed website.
