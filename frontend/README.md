# SAARTHI Frontend

React 18 + Vite + Tailwind CSS UI for SAARTHI, the autonomous payment-dispute resolution teammate.

## What this app shows

| Tab | Purpose |
| :--- | :--- |
| **Customer Chat** | Live step indicator (Understand → Investigate → Decide → Gate → Act → Verify → Inform) and a final status chip: `Resolved (Verified)`, `Awaiting Status Change`, or `Escalated`. Includes demo quick-starter pills for Scenarios A–I. |
| **Agent Trace** | Tool calls, policy citations, Permission-Gate decision, verification result, and the immutable audit log for the selected case. |
| **Human Console** | Escalation / approval queue with the structured Case Brief, Approve/Reject, and a reply-to-customer box. |
| **Admin / Scenarios** | Run the 9 benchmark scenarios and toggle upstream chaos modes (lookup fail, timeout, ambiguous status, verification mismatch), plus reset seed data. |
| **Metrics** | Honest prototype run data only, computed from the local database (no fake stats). |

## Run

```bash
npm install
npm run dev      # http://localhost:5173 (expects backend on http://localhost:8000)
```

Build for production:

```bash
npm run build    # outputs to dist/
```

The backend base URL is set in `src/api.js` (`http://localhost:8000/api` by default).
