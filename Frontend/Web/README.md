# WasteSense Web

The WasteSense web app is the browser-based interface for the Smart Waste Bin 
project. It is built with React, TypeScript, Vite, and Tailwind CSS.

The web frontend includes the login page and connects it to the WasteSense
authentication service. It also opens the dashboard only after the server
confirms who the user is.

## Requirements

- Node.js 20 or newer
- npm 10 or newer

## Getting started

From the repository root:

```bash
cd Frontend/web
npm install
npm run dev
```

Vite prints the local development URL in the terminal, usually
`http://localhost:5173`.

In another terminal, make sure the backend is running at
`http://localhost:8000`. The web app uses that address by default. To use a
different address, create `Frontend/Web/.env.local` and add:

```text
VITE_API_URL=http://localhost:8000
```

For the account setup and a plain-language explanation of sign-in, see
[Login authentication guide](./LOGIN_AUTH_GUIDE.md).

## Available scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite development server with hot module replacement. |
| `npm run build` | Type-check the project and create a production build in `dist/`. |
| `npm run lint` | Run ESLint against the frontend source. |
| `npm run preview` | Serve the production build locally after running `npm run build`. |

## Project structure

```text
web/
├── src/
│   ├── App.tsx       # Root application component
│   ├── index.css     # Tailwind CSS entry point
│   └── main.tsx      # React application entry point
├── index.html        # Vite HTML entry point
├── package.json      # Scripts and dependencies
├── tsconfig*.json    # TypeScript configuration
└── vite.config.ts    # Vite, React, Tailwind, and React Compiler setup
```

## Development workflow

1. Make changes under `src/`.
2. Keep components and data access separate as dashboard features are added.
3. Run `npm run lint` and `npm run build` before opening a pull request.

The web app is part of the larger repository. For database, MQTT, backend, and
mobile setup instructions, see the repository
[README](../../README.md).
