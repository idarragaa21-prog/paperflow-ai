## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-05-18 - [Form Accessibility and Semantic Testing]
**Learning:** Using `div.rc-kicker` for custom input descriptions lacks proper screen reader support and causes brittle tests when using `getAllByDisplayValue('')`. Adding explicit `<label htmlFor="...">` tags solves the accessibility issue and enables robust semantic testing (`getByLabelText`).
**Action:** When working on legacy forms using custom `rc-kicker` pseudo-labels, explicitly refactor them to `<label>` tags with matching `htmlFor` properties and update Vitest tests to use `.getByLabelText`.
