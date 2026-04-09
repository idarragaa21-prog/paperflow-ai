## 2024-05-18 - Safe Defaults for Keyboard Navigation in Dialogs
**Learning:** Destructive actions (like Delete) in confirmation dialogs are dangerously easy to trigger accidentally for keyboard users when `autoFocus` is either missing or placed on the confirm action.
**Action:** Always place `autoFocus` on the safe/cancel action (`<button autoFocus>Cancel</button>`) in destructive dialogs to prevent accidental confirmations via the Enter or Space key.

## 2024-05-18 - Semantic Labels for rc-kicker Elements
**Learning:** Form labels using the `rc-kicker` class are sometimes implemented as semantic-less `<div>` elements, reducing accessibility for screen reader users and preventing click-to-focus behavior.
**Action:** Always convert these `div.rc-kicker` elements to `<label htmlFor="...">` tags and apply `style={{ display: 'block' }}` to preserve their original block-level rendering, alongside adding the matching `id` to the associated input.
