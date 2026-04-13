## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-04-13 - [Semantic Labels for Custom Input Groups]
**Learning:** In the frontend codebase, form labels using the `rc-kicker` class are sometimes implemented as semantic-less `<div>` elements. When improving accessibility, convert these to `<label htmlFor="...">` tags and apply `style={{ display: 'block' }}` to preserve their original block-level rendering, alongside adding the matching `id` to the associated input.
**Action:** When working on form inputs with "kicker" headers, always check if they are semantic `<label>` elements. If they are `<div>` elements, convert them to `<label>` to improve screen reader accessibility and enable clicking the label to focus the input.
