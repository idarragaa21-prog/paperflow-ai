## 2024-06-25 - [Add accessibility to overlay elements]
**Learning:** [When making non-semantic elements interactive, standard HTML non-interactive elements (like a `div` serving as a backdrop overlay) lack basic accessibility characteristics such as focus and keyboard operations by default. Simple `onClick` handlers are insufficient.]
**Action:** [Always add `role="button"`, `tabIndex={0}`, an appropriate `aria-label`, and keyboard handling (`onKeyDown` checking for `Enter` and ` `) when repurposing non-semantic elements for interactive purposes to ensure keyboard accessibility.]
