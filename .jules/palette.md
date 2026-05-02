## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-02 - Form Labels and Test Robustness
**Learning:** Using `div`s styled as labels instead of actual semantic `<label>` elements not only breaks screen reader accessibility but also encourages writing fragile unit tests (like `screen.getAllByDisplayValue('')` instead of `screen.getByLabelText()`). Replacing these with proper labels improves both user experience and developer experience by making tests resilient to form layout changes.
**Action:** When adding or refactoring forms, always use semantic `<label htmlFor="...">` elements with corresponding `id`s on inputs. In Vitest/React Testing Library tests, immediately refactor any index-based input queries to use `getByLabelText`.
