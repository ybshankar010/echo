# <Service / repo name>

<!-- Keep this under one page. Claude reads it at session start. -->

## Commands
- Build: <make build>
- Test:  <make test>
- Lint:  <make lint>

## Conventions
- <Language/framework and the rules that matter.>
- <Money as BigDecimal, timezones in UTC, etc.>

## Things to get right
- <The mistake worth stating once so it is never repeated.>

## Verifying your work
- Run the test and lint commands above before reporting done; paste the output.
- Fix the code, not the tests. Never skip or delete a failing test.

## SDLC (echo)
- This repo uses the echo loop: `/echo:status`, `/echo:intent`, `/echo:approve`,
  `/echo:next`, `/echo:verify`, `/echo:ship`.
- No code before an approved `plan.md`. Every commit/PR carries a Jira ticket id.
