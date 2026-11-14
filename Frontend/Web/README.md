# WasteSense Web

The WasteSense web app is the browser-based interface for the Smart Waste Bin 
project. It is built with React, TypeScript, Vite, and Tailwind CSS.

The current frontend is an initial shell that renders the WasteSense welcome
view. Backend and bin-monitoring integrations will be added as the dashboard
features are implemented.

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
