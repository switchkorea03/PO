# Inventory lookup preparation plan

User scope: add a stock-check menu now; transfer source through GitHub later and connect desktop-installed iCUBE on that desktop. No ERP endpoint or credentials currently available.

- [x] Add authenticated /inventory/ page with company item catalog, search, unit-specific PO outstanding totals and honest unavailable stock values.
- [x] Isolate ERP snapshot lookup behind inventory provider contract; default disconnected provider never returns synthetic zero stock or makes external calls.
- [x] Add navigation, responsive stock table, connection status and desktop connection preparation instructions.
- [x] Verify remaining quantities exclude cancelled/deleted POs and cancelled shipments, preserve separate units, login protection and unknown stock states. Verify PC/mobile UI.
- [x] Write source/data/config handoff instructions; restart local web app after checks. No GitHub upload or database migration in this task.

Files: server/inventory/{__init__,urls,views,queries,providers}.py; inventory/tests.py; templates/inventory/list.html; templates/base.html; static/po/workspace.css; e2e/inventory.spec.mjs; docs/operations/2026-11-09-desktop-erp-handoff.md.

Validation: full existing/new backend suite148 passed; after review alias search fix inventory4 passed; desktop/mobile browser2 passed. System check clean, no migration changes. Real ERP remains disconnected. GitHub/source transfer is a later step; no remote upload made.
