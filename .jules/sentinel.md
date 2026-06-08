## 2024-04-04 - [Raw DOM HTML Injection in React]
**Vulnerability:** Raw SVG strings returned by Mermaid were assigned directly to a DOM element via `ref.current.innerHTML`, bypassing React's built-in XSS protections.
**Learning:** Even well-known visualization libraries like Mermaid can output malicious or malformed SVGs that include script tags, which get executed if manually assigned via `innerHTML`.
**Prevention:** In React, always bind raw HTML or SVG content to state variables and use the `dangerouslySetInnerHTML` prop. This alerts developers during code reviews that XSS protections are bypassed and forces explicit acknowledgement of the risk.

## 2024-04-04 - [Critical Authentication Bypass]
**Vulnerability:** The login API in `backend/app/api/auth.py` was explicitly taking the provided password and overwriting the database hash for existing users (`user.password_hash = hash_password(credentials.password)`). This meant ANY password would log you into ANY account.
**Learning:** Development backdoors (like automatically creating users or bypassing password checks for ease of local testing) MUST be rigorously removed or strictly isolated behind environment flags (`if ENV != "production"`). They should never make it into the main production route path.
**Prevention:** Never overwrite an authentication secret during a login verification path. Ensure all auth attempts run through `verify_password()`. Write robust, automated integration tests that explicitly try to login with a bad password to prevent these kinds of backdoors from reaching production.

## 2024-05-24 - Authentication Backdoor Removed
**Vulnerability:** The `/login` endpoint was overwriting the password hash of any existing user with the password provided during the login attempt, effectively bypassing authentication for any account. It also created new accounts for non-existent users automatically.
**Learning:** Development backdoors that bypass authentication (e.g., overwriting password hashes with user input or automatically creating users for easy login) must be rigorously removed or strictly isolated behind environment flags. Never overwrite an authentication secret during the login verification path.
**Prevention:** Ensure strict separation between registration and login flows. Never modify a user's password during a login attempt. Review authentication logic for debugging or development artifacts before committing to production.

## 2024-04-08 - Rate Limiting Added to Authentication Mutation Endpoints
**Vulnerability:** The `/register`, `/forgot-password`, and `/reset-password` endpoints lacked rate limiting, exposing the system to brute-force attacks and email enumeration (via timing or spam).
**Learning:** While the `/login` endpoint had rate limits applied, other sensitive authentication mutation endpoints were overlooked. Security layers must be applied consistently across all endpoints that handle sensitive state transitions or external messaging.
**Prevention:** Always verify that newly added authentication or identity-related endpoints utilize the established `auth_rate_limit` utility to enforce appropriate IP and identifier-based limits.

## 2024-05-24 - [Username Enumeration via Timing Attack]
**Vulnerability:** The login endpoint bypassed password verification when a user didn't exist, leading to significantly faster response times for non-existent users, which allows attackers to enumerate valid usernames.
**Learning:** Short-circuit evaluation in authentication checks (`if not user or not verify_password()`) leaks information through timing differences.
**Prevention:** Always perform a dummy password verification (`pwd_context.dummy_verify()`) when a user is not found to ensure constant-time execution across both successful and failed authentication attempts.
