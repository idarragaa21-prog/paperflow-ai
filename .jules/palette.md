## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-19 - Added ARIA labels and disabled states tooltips to checkboxes
**Learning:** In SearchResultCards, checkbox functionality and download operations lack appropriate ARIA descriptions and context for users. When these controls are disabled (`!canDownload`), users are unaware of why unless the state is visually and semantically explained.
**Action:** Adding explicit `aria-label` associated with the data point's title, dynamic `title` tooltips, and `cursor: not-allowed` CSS properties vastly improves the UX of non-interactive states while fully enabling screen reader support.
