## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-04-17 - [Accessible Form Labels for rc-kicker]
**Learning:** Found multiple instances where the `rc-kicker` class was used on `<div>` tags to serve as form labels, lacking semantic association with inputs. Converting these into `<label htmlFor="...">` and assigning matching IDs to the inputs fixes the accessibility issue.
**Action:** Replaced `<div>` kickers with `<label>` tags and added `style={{ display: 'block' }}` to preserve original layout without touching the CSS file. Remember to ensure matching IDs on target inputs whenever using this pattern.
