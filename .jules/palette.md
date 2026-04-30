## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## $(date +%Y-%m-%d) - [Accessible refresh buttons]
**Learning:** Icon-only refresh buttons often lack text explanations for screen readers. When these buttons are spread throughout a design system they cause recurring accessibility faults for those users.
**Action:** Always add `aria-label` along with `title` attributes (for visually impaired users but also for tooltips for everyone else) to icon-only action buttons.
## $(date +%Y-%m-%d) - [RTL Querying anti-pattern]
**Learning:** Using `container.querySelectorAll` is a React Testing Library anti-pattern and often leads to brittle tests.
**Action:** Prefer semantic queries like `screen.getByLabelText` or `screen.getByPlaceholderText` over CSS selectors when querying elements in tests.
