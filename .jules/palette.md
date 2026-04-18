## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-04-18 - Missing ARIA Labels on Icon/Avatar Buttons
**Learning:** Found that `rc-logout-btn` uses `title` attribute for tooltip support but lacks proper ARIA labels for screen reader accessibility in `src/components/AuthedLayout.tsx`.
**Action:** Need to replace or append `aria-label` to these components to improve accessibility, as the `title` attribute isn't sufficient for all screen readers.
## 2024-04-18 - Replacing Empty Display Value Selectors with Semantic Elements
**Learning:** Encountered brittle tests breaking in `SettingsPage.test.tsx` because of `getAllByDisplayValue('')` selections to find password form inputs. Any changes to the UI structure (even unrelated form fields loading) caused tests to fail. Also, the form inputs lacked proper semantic labels (`<label htmlFor>`).
**Action:** Replaced semantic-less wrapper `<div>`s with block-rendered `<label>` elements matching input `id`s for better accessibility. Also updated tests to use robust `data-testid` queries rather than fragile empty display value lookups.
