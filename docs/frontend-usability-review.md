# Frontend usability and reliability review

Reviewed on 2026-11-15. Changes build on the existing AFDA CMS components and preserve the English, Dari, Pashto, calendar, theme, and permission systems. Existing workspace work was retained. This review does not deploy the application or certify that the complete system is free of defects.

## Nielsen's 10 usability heuristics

| Heuristic | Applied changes |
| --- | --- |
| Visibility of system status | Sign-in/save pending labels, busy forms, announced loading/error states, consistent checklist deployment badges, active filter chips. |
| Match with the real world | Establishment names and checklist names in filters, readable navigation, contextual guidance explaining upload/deploy/sync and coverage versus visit counts. |
| User control and freedom | Cancel/close remain explicit; dirty forms offer Keep editing or Discard changes; leaving the browser warns about unsaved form edits. Browser history restores inspection filters and list URLs. |
| Consistency and standards | Shared page title sizing, semantic heading levels, section dividers, deployment badges, responsive action placement, calendar-aware checklist date inputs. |
| Error prevention | Reject reversed date bounds, guard duplicate submissions while busy, disable inputs during saves, review deployment and source disconnection before execution, preserve dirty metadata values. |
| Recognition rather than recall | Visible Filters label, filter chips, valid breadcrumb parents instead of raw IDs or dead intermediate routes, visible date labels, required-field markers. |
| Flexibility and efficiency | URL-backed inspection, establishment, and checklist-submission browsing; debounced source searches; cancelled stale list requests; keyboard sorting and scrollable tables; skip-to-content link. |
| Aesthetic and minimalist design | Responsive header/action layouts, consistent primary titles and smaller section titles, restrained report tiles, wrapping long text, removal of stale global integration-disconnected claims. Individual demo badges remain. |
| Help with error recovery | Retry controls, recoverable page-render/chunk errors, explicit missing-record/network/server messages, sign-in after a rejected session, visible inspection-history failures instead of false empty results. |
| Help and documentation | Localized Help dialog in the header explaining the principal workflows and permission-dependent actions. |

## Structure and behavior

- Feature pages load on demand. The earlier 756 kB application chunk is split into feature/shared chunks; the build no longer reports a chunk above its 500 kB warning threshold. Total download and runtime performance still depend on device, caching, and data volume.
- `useListParams` owns reusable URL list state; inspection filter parsing and writing use an allowlist in `filter-state.ts`.
- `DeploymentBadge` is shared by checklist list/detail pages, so deploying and failed states are not mislabeled as simply not deployed.
- `AppDialog` and `CustomForm` share dirty/busy state. Overlay clicks do not dismiss dialogs by default. Successful save callbacks close directly; user cancellation prompts only when edits exist.
- Session rejection is limited to an HTTP 401 for the current token. A 403 or a response from an older token does not sign out a newer session. Local sign-out still completes if its network request fails.
- A page failure retains the surrounding navigation. The outer application boundary handles failures before the authenticated shell mounts.
- Supplemental employee/group/checklist queries respect the corresponding UI permissions. Backend authorization remains authoritative.
- Table containers are keyboard-focusable for horizontal scrolling; sortable headers use buttons and expose sort state. Password visibility is keyboard-operable and localized. Checkbox labels use unique IDs rather than label text as IDs.
- Reduced-motion preferences are respected. Route changes reset the main scroll position, focus the main landmark, and update the browser title.

## Automated verification

Run from the repository root:

```sh
npm --prefix mandi_frontend run build
npm --prefix mandi_frontend test
npm --prefix mandi_frontend run lint
npm --prefix mandi_frontend run format:check
git diff --check
```

Eight regression tests cover permissions, calendar round trips, complete inspection-filter URL round trips, clearing filters, reversed/open date ranges, invalid pagination input, safe API error messages, and session-expiry races. The production TypeScript/Vite build and formatting checks pass. Lint has no errors and 16 warnings; existing copied-component warnings about effects and mixed component/helper exports remain. This work also removed the unstable random sidebar skeleton width, an unused radio-card styling prop, and unstable answer memo dependencies.

## Browser verification

Use an isolated temporary Django settings module/database and a second Vite instance for smoke checks; do not reset the working database or reuse real inspection records for mutation tests. Review records are synthetic. The review exercised sign-in, dashboard rendering, required establishment fields, dirty-form cancellation, filter application and visible URL state, checklist/submission and employee pages, deployment review/cancellation without publishing, zero/one answer rendering, Dari/Pashto switching, localized help, and a 390px RTL layout without document/main overflow. Wide tables scroll within their own containers.

Browser smoke checks supplement the regression tests; they are not a complete accessibility audit or a substitute for end-user acceptance testing. Live KoBo publishing and live upstream source modifications are outside these frontend checks.

## Production boundary

Frontend improvements alone do not establish production readiness for the whole service. Before a release, verify the actual deployment's HTTPS and origin configuration, API authorization, authentication/token policy, static-file SPA fallback and asset-cache behavior, monitoring, backup/restore, and live integration behavior. Do not infer that these are configured from a passing frontend build. The existing session-storage token approach is retained; no authentication protocol or backend permissions were replaced in this change.
