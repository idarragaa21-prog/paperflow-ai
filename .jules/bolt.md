## 2026-04-02 - React.memo Regression Risks
**Learning:** Extracting an inline list row into a separate React component and wrapping it with `React.memo` to improve rendering performance can easily introduce regressions if the parent component passes unstable callback references (like `toggleTrace` depending on changing states).
**Action:** Always use the functional form of state setters (e.g., `setState(prev => ...)`) inside `useCallback` to ensure the function reference remains perfectly stable, maximizing the impact of `React.memo`.

## 2026-04-02 - Hallucinated Fallback Values
**Learning:** Extracting logic from an inline JSX file into a standalone component can lead to accidental hallucination of constants or dictionaries (like `SOURCE_LABELS` having standard LLM guesses rather than the app's real data sources).
**Action:** Strictly copy and paste the required constants and typings directly from the original source file when extracting components, and never rely on intuition for business-logic mappings.
