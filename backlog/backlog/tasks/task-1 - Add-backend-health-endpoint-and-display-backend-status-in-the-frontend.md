---
id: TASK-1
title: Add backend health endpoint and display backend status in the frontend
status: To Do
assignee:
  - '@agent'
created_date: '2026-06-05 14:11'
updated_date: '2026-06-05 15:14'
labels:
  - backend
  - frontend
  - integration
dependencies: []
references:
  - feature/task-1-health-endpoint-frontend-status
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The frontend currently has no way to know whether the backend is running. We need a health endpoint on the FastAPI backend and a status indicator in the React frontend that consumes it. This is the first end-to-end integration between the two projects and establishes the pattern (HTTP client setup, cross-origin handling, error states) that future features will follow.

Context:
- Backend is FastAPI (backend/, runs on http://localhost:8000 via uvicorn) and currently has zero routes.
- Frontend is React 18 + TypeScript with Vite (frontend/, runs on http://localhost:5173) and currently renders an empty main element.
- The two run on different ports, so cross-origin requests must be handled (CORS middleware on the backend or a Vite dev-server proxy — implementer's choice, document the decision).
- E2E tests (e2e/, Playwright) start the frontend automatically via webServer config but do not start the backend; backend must be started and the frontend must handle an unreachable backend gracefully.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GET /health on the backend returns HTTP 200 with a JSON body containing at minimum a status field with value "ok"
- [ ] #2 The frontend fetches the health endpoint on initial page load and displays the backend status visibly on the page
- [ ] #3 When the backend is unreachable, the frontend displays a clear unavailable/error state instead of crashing or showing nothing
- [ ] #4 The health request from the frontend dev server (localhost:5173) to the backend (localhost:8000) succeeds without CORS errors
- [ ] #5 Backend unit tests cover the /health endpoint response (status code and body)
- [ ] #6 Frontend unit tests cover both the success state (status displayed) and the failure state (unavailable message displayed)
- [ ] #7 E2E tests cover a healthy and unhealthy check
<!-- AC:END -->
