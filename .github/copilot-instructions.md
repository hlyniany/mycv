## EXECUTION DISCIPLINE

- **Do only what was asked** — Execute the requested task. Do not invent
  additional steps (creating new scripts, refactoring related files) unless asked.
- **"Run X" means run X** — Not: find X, read X, plan how to run X, create a
  helper for X, then run it. Just run it with needed prerequisites.
- Reading files for context needed to complete the requested action is permitted.

## ERROR AND OBSTACLE HANDLING

When an action fails or hits an obstacle:
- You MAY attempt to fix the error within the current strategy (retry, adjust
  parameters, install a missing dependency to unblock the original command).
- You MUST NOT switch to a different strategy, tool, or approach without asking
  the user first.
- If the fix attempt also fails, STOP and report what happened. Let the user
  decide the next step.

Forbidden:
- Silently switching to a fallback or alternative strategy after a failure
- Choosing a different tool, command, or workflow on your own
- Expanding scope (e.g., error in one file → refactoring three files)
- "Recovering" by doing something the user did not request
