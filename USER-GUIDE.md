# Regional KPI Dashboard User Guide (Non-Technical)

## 1. What this dashboard is for
The Regional KPI Dashboard helps you:
- View key performance metrics for your region
- Explore results over time
- Drill down into the records behind each metric
- View case studies
- Build custom reports

You do **not** need technical knowledge to use it.

---

## 2. Signing in
1. Open the dashboard link.
2. Enter your email and password.
3. If prompted, change your password.

If you cannot sign in, contact an Admin user.

---

## 3. Roles and access
The app supports four roles:
- `RPL`
- `ML` (Mountain Leader)
- `Manager`
- `Admin`

Your role controls what you can see in the sidebar and which actions you can perform.

---

## 4. Main areas of the app
Use **View Mode** in the left sidebar:
- `KPI Dashboard`
- `Custom Reports Dashboard`
- `Case Studies`
- `Admin Dashboard` (Admin only)
- `ML Dashboard` (Mountain Leaders only)

---

## 5. Using the KPI Dashboard
The KPI Dashboard is split into tabs:
- Governance
- Partnerships
- Delivery
- Income
- Comms
- Case Studies

### Region and date filters
In the sidebar:
1. Choose `All Regions` or pick a specific region.
2. Choose timeframe (`All Time`, `Year`, `Quarter`, `Month`, `Week`, `Custom Range`).

All numbers and charts update automatically based on these filters.

---

## 6. How metric drill-down works
Each KPI tile can be clicked.

When you click a KPI tile:
1. A popup opens with related rows.
2. You can select a row for deeper detail.
3. The selected record is shown in a readable format.
4. If needed, open **Technical View (JSON)** for advanced detail.

### Important for Delivery > Total Participants
- You can select an event and see participant details.
- `ML`, `Manager`, and `Admin` users can view attendee names/IDs when available.
- `RPL` users can view attendee totals only.
- If names exist in source data, names are shown (for roles with attendee detail access).
- If only IDs exist, IDs are shown (for roles with attendee detail access).
- If only a count exists, detail-access roles see placeholder entries (for example, `Participant 1 (name unavailable)`).

---

## 7. Delivery demographics
The Delivery tab includes a demographics chart.

The chart title tells you the source:
- `Participant Cohorts (from people type tags)` when tag data is available
- `Delivery Split (by event type)` when cohort tags are missing
- Fallback representation when limited data exists

---

## 8. Case Studies
In `Case Studies`:
- Read existing case studies
- Filter by date and region
- Upload new case studies (if your role allows it)

If you can access all regions, use the sidebar region controls for case studies.

---

## 9. Custom Reports Dashboard
Use this area to:
- Select datasets (People, Organisations, Events, Payments, Grants)
- Apply date and region filters
- Build charts and tables
- Export CSV reports

---

## 10. Admin-only actions
If you are an Admin, you may also have access to:
- User management
- Manual Beacon sync
- CSV import
- Audit logs
- System refresh actions

Use these carefully, as they affect all users.

---

## 11. Troubleshooting
## The page looks slow
- Wait a few seconds after changing filters.
- Avoid very broad filters if you only need one region/time period.
- Try refreshing the browser tab.

## I cannot see participant names
- Names depend on source data from Beacon.
- Some events only provide counts, not names.
- After sync updates, attendee data may improve.

## A dropdown/list is hard to read
- The app includes high-contrast styles for drill-down controls.
- If you still see readability issues, report the exact tab and metric.

## I see no data
- Check your region and timeframe filters.
- Try `All Time` and `All Regions` to confirm data exists.

---

## 12. Best practice tips
- Start with `All Time`, then narrow down.
- Use drill-down to validate any unusual KPI value.
- For presentations, use the summary view; for investigations, use row-level detail.
- Download CSV from Custom Reports when you need offline analysis.

---

## 13. Glossary
- `KPI`: Key Performance Indicator (headline metric)
- `Drill-down`: Viewing detailed rows behind a KPI
- `Timeframe`: Date range filter applied to all metrics
- `Global`: All regions combined

--- 

## 14. ML Dashboard

Only Mountain Leaders (`ML` role) can see this dashboard. It filters Beacon events by region and timeframe, and it opens a single event at a time:
1. Pick a region with the sidebar controls (or leave `All Regions` enabled) and choose your timeframe.
2. Use the drop-down to select the event you need; the rest of the page updates automatically.
3. Review the highlighted event details (location, type, total participants, description) plus the attendee list and IDs when the data is present.
4. Scroll to the Medical Information and Emergency Contact sections to surface any supporting notes baked into the Beacon payload.

## 15. Need help?
If something is unclear:
1. Take a screenshot
2. Note the tab, metric, region, and timeframe
3. Send this to your Admin/support contact
