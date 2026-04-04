## 2024-05-18 - Safe Defaults for Keyboard Navigation in Dialogs
**Learning:** Destructive actions (like Delete) in confirmation dialogs are dangerously easy to trigger accidentally for keyboard users when `autoFocus` is either missing or placed on the confirm action.
**Action:** Always place `autoFocus` on the safe/cancel action (`<button autoFocus>Cancel</button>`) in destructive dialogs to prevent accidental confirmations via the Enter or Space key.
