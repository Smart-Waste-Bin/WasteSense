# Contributing

## Workflow

1. Pick a ticket (SB-xx).
2. Create a branch from `main` named `SB-<key>-short-name`, for example `SB-12-mqtt-ingest`.
   ```bash
   git switch main
   git pull
   git switch -c SB-12-mqtt-ingest
   ```
3. Commit as you go. Commit messages are free style. Mentioning the ticket key
   (e.g. `SB-12 add MQTT client`) is encouraged but not required.
4. Push the branch and open a pull request into `main`. Fill in the PR template.
5. Another team member reviews it. Each PR needs **one approval** before it can be merged.
6. Merge, then delete the branch.

Nobody pushes straight to `main`. It is protected, and all changes go through a pull request.

## Ownership

| Area | Owner |
| --- | --- |
| `Backend/` (API, routing, simulator) | Joshua |
| `Frontend/Web/`, `Frontend/Mobile/` | Nana |
| `Firmware/` | Mujahid |

Ask the owner before making big changes in their folder.
