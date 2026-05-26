## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2023-10-27 - Refactor Setting Form Labels
**Learning:** React wrapper divs styled as field labels (e.g., `<div className="rc-kicker">`) without associated `<input>` connection hurt form accessibility. Changing the wrapper element to a `<label>` provides semantic connection while applying `style={{ display: 'block' }}` maintains visual layout flow without breaking design.
**Action:** Always prefer semantic `<label>` elements wrapping the `<input>` or using `htmlFor` over purely stylistic `<div>` wrappers for form inputs. Update associated Vitest tests that relied on index-based querying or structure.
## 2023-10-27 - Search Result ARIA enhancements
**Learning:** Toggle buttons for expanding content should always use aria-expanded and aria-controls linking to the content ID to ensure screen reader users understand the state and target of the action.
**Action:** Always add aria-expanded, aria-controls, and clear aria-labels to 'Read more'/'Show less' style toggle buttons.
