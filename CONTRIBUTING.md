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
5. CI must pass (the `ci-ok` check, see the CI section in the README) and the branch must be up to date with `main`.
   An approval is not required, but asking a teammate to look at it is encouraged.
6. Merge, then delete the branch.

Nobody pushes straight to `main`. It is protected, and all changes go through a pull request.
A failing CI run blocks the merge.

## Ownership

| Area | Owner |
| --- | --- |
| `Backend/` (API, routing, simulator) | Joshua |
| `Frontend/Web/`, `Frontend/Mobile/` | Nana |
| `Firmware/` | Mujahid |

Ask the owner before making big changes in their folder.
