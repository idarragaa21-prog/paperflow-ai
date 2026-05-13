## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-13 - Semantic Labels Over Pseudo-Labels
**Learning:** In the Settings page, form inputs used `<div>` with `className="rc-kicker"` as pseudo-labels. This caused accessibility issues for screen readers and made testing brittle (relying on `getAllByDisplayValue('')` instead of `getByLabelText`).
**Action:** Always use semantic `<label>` tags with `htmlFor` matching the input's `id`. Apply `style={{ display: 'block' }}` if the label needs to occupy its own line to preserve vertical flow.
