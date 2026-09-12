# Vendored third-party assets

These files are third-party libraries and fonts bundled deliberately
rather than loaded from a public CDN.

**Why they are bundled:** Bug-Gira is deployed on internal networks that
may have no outbound internet access. Loading these assets from a CDN
would cause them to fail silently — in the case of SortableJS, the
Kanban board's drag-and-drop would stop working. Bundling them makes the
application fully self-contained with no external runtime dependencies.

These files are **not** authored by the Bug-Gira maintainer. See the
project root `AUTHORS.md` and `LICENSE` for the application's own
authorship and licence.

---

## Sortable.min.js

| | |
|---|---|
| **Library** | SortableJS |
| **Version** | 1.15.0 |
| **Purpose** | Drag-and-drop reordering on the Kanban board |
| **Source** | https://github.com/SortableJS/Sortable |
| **Obtained from** | https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js |
| **Licence** | MIT |

## inter-400.woff2, inter-600.woff2

| | |
|---|---|
| **Font** | Inter (Regular 400, SemiBold 600) |
| **Purpose** | Application typeface |
| **Source** | https://github.com/rsms/inter |
| **Licence** | SIL Open Font License 1.1 |

Only the two weights actually used are bundled, to keep the deployment
package small. Heavier weights are synthesised by the browser.

---

## Updating these files

1. Download the new version from the source listed above.
2. Replace the file here, keeping the same filename (or update the
   reference in `style.css` / `project_board.html` if the name changes).
3. Update the version recorded in this file.
4. Run `python manage.py collectstatic` and verify the application still
   loads the asset locally — check the browser Network tab shows the file
   served from the application host, not an external domain.
5. Run `python manage.py test` before committing.