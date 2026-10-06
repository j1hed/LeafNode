# LeafNode

React + TypeScript + Vite frontend with the existing landing page and greenhouse dashboard.

## Configure and run

From this directory:

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Set the backend URL in `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Restart Vite after changing environment variables. Vite embeds this public URL at build time; do not put secrets in VITE_* variables.
Open http://localhost:5173 for the landing page or http://localhost:5173/#/dashboard for the dashboard.
The FastAPI server must allow the frontend origin (normally http://localhost:5173) through CORS. An HTTPS deployment needs a reachable HTTPS API URL; localhost always refers to the browser's machine.

```powershell
npm run build
npm run preview
npm test
```

## API integration

- `src/services/api.ts`: shared HTTP client, JSON bodies, error handling, 12-second request timeout, abort support, and endpoint methods.
- `src/app/DashboardContext.tsx`: dashboard resources, recommendation session state, and shared polling. Read-only dashboard requests run concurrently; the next cycle starts five seconds after completion so cycles never overlap. Unmount aborts outstanding requests and clears the timer.
- Dashboard panels use real `/api/latest`, sensor/detection history, analysis, status, and commands. Failed resources are cleared and reported independently; readings never fall back to mock data.
- Null ESP32 or Jetson data shows waiting/unavailable states. No image-feed endpoint or physical actuator-state endpoint was supplied, so neither is simulated.
- Recommendation flow: choose/enter plant type, generate a session, review `recommendation_json`, approve or reject, and refresh the session. Session state survives dashboard page navigation. Only a click can generate, approve, reject, or submit a manual command. No POST is made by polling.
- Approval and manual-command success mean queued/pending, not executed. An uncertain approval response locks repeat decisions for that session. Check session details and the command queue after any ambiguous failure.
- Manual controls read device/action enum values (including local schema references) from `/openapi.json`. They stay disabled when those values cannot be verified. No hardware aliases are guessed.
- The history view preserves original rows and can export JSON. Charts plot numeric temperature, soil and humidity fields in flat records or an `esp32` object. Valid `timestamp` fields determine ordering; otherwise backend order is retained. Other row layouts remain visible in history.
- Optional public landing-page contact/social settings remain in `.env.example`. Mock mode is no longer used by the dashboard.

## Verification and unresolved schema details

The local backend was unreachable during implementation, so live response schemas, supported device/action values, CORS, and the complete recommendation workflow could not be verified. The provided endpoint contract is used without inventing recommendation fields: recommendation, alert, and analysis content is rendered directly as returned data. History row structures and units for light, pressure and gas were not specified; those units are intentionally omitted. The manual duration field uses positive minutes from the provided example; any additional backend restrictions are reported through HTTP validation errors.

Tests use stubbed fetch responses only and never send real hardware commands. The public landing page retains its illustrative product/demo content and images, separate from the live dashboard.
