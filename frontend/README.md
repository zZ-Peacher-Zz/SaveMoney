# Calendar UI

The calendar is adapted from the MIT-licensed shadcn/ui Calendar source:
https://ui.shadcn.com/r/styles/new-york/calendar.json

See [LICENSE-shadcn.md](./LICENSE-shadcn.md). The component uses React DayPicker,
with local Button and class-name helpers and Tailwind utilities without preflight
to coexist with the Bootstrap application. Vietnamese locale comes from date-fns.

The React entry point mounts small calendar widgets around existing inputs. It
preserves ISO input values and native change events used by the existing app.
No backend or database change is required.

To rebuild after editing:

```sh
npm ci
npm run build
```

Commit the generated `static/calendar.js` and `static/calendar.css` with source
changes. Render can serve these assets using its existing Python startup command;
Node is required only for rebuilding the frontend assets.
