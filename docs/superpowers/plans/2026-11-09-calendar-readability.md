# Calendar readability implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

Approved design: show company-first calendar summaries, separate company and unfinished-task counts, at most three schedule cards per day with a remaining-items link, and the selected day's complete agenda grouped by company. Keep existing PO/task actions and calendar API contract.

- [x] Add presentation helper and regression tests for crowded days, distinct companies, mixed completion, due-only days and selected agendas without truncation.
- [x] Connect presentation data in work/views.py; update work/calendar.html with clear statuses, due markers and accessible links to the selected agenda.
- [x] Add scoped responsive CSS. Preserve month/week navigation and customer/type filters. Use page scrolling on mobile and agenda scrolling on desktop.
- [x] Run focused backend and desktop/mobile browser checks with synthetic records in the isolated e2e database. Restart only the local PO web server after checks pass.

No schema or real PO data changes. Files: work/calendar_presentation.py, work/views.py, templates/work/calendar.html, static/po/workspace.css, templates/base.html (cache version), work/tests/test_calendar_presentation.py, e2e/calendar-readability.spec.mjs.

Validation: 145 backend tests passed; 2 desktop/mobile Playwright checks passed. System check clean, no migration changes. Local server restarted and login/CSS returned HTTP 200. All browser fixture records stayed in po_calendar_e2e.

Rulings: prioritize distinct companies in the three preview cards so one company cannot occupy every preview; preserve cancelled tasks in an expandable history section without adding them to pending counts.

Approved follow-up: remove right-side agenda and undated panels, make calendar full width, remove pending-count and planned labels. Date/more links now open the selected day in a native dialog, with close button, Escape and backdrop close. No always-visible agenda panel. Validation: 22 work tests and 2 desktop/mobile browser checks passed; production local server restarted, dialog script HTTP200.

Final approved revision: display every active company/work/due entry directly inside the day cell, grouped under one company heading with all PO task links. Remove preview cap, remaining links and dialog markup/scripts from calendar. Day/week rows grow naturally without vertical clipping or inner day scrolling. Preserve full calendar width and removal of pending/planned text. Validation: 22 work tests, 2 desktop/mobile browser checks, system check, local server HTTP200.
