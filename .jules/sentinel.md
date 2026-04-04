## 2024-04-04 - [Raw DOM HTML Injection in React]
**Vulnerability:** Raw SVG strings returned by Mermaid were assigned directly to a DOM element via `ref.current.innerHTML`, bypassing React's built-in XSS protections.
**Learning:** Even well-known visualization libraries like Mermaid can output malicious or malformed SVGs that include script tags, which get executed if manually assigned via `innerHTML`.
**Prevention:** In React, always bind raw HTML or SVG content to state variables and use the `dangerouslySetInnerHTML` prop. This alerts developers during code reviews that XSS protections are bypassed and forces explicit acknowledgement of the risk.
