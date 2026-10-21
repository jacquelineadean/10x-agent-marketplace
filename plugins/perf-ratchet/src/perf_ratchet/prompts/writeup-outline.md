# Write-up outline

A blog post on how the application got faster, in the shape of an engineering blog post
such as "How we made claude.ai 3x faster in two weeks". The reader is an engineer at
another company. They want the result, the method, the specific fixes with numbers, how
the wins were kept, and what to copy.

## Title
`# How we made <project> {{headline.geomean_speedup}} faster` when the speedup is above 1.5x.
Otherwise name the biggest win: `# How we cut <journey name> from {{...baseline}} to {{...current}}`.

## Sections, in this order
1. **Opening, no heading.** Two or three sentences. The result first: the overall speedup
   across journeys, the biggest single win with before and after, the span of dates, how many
   changes shipped and the count rolled back. Then one sentence on what the post covers.
2. **What we measured.** The journeys as a table: journey, baseline, now, speedup, target.
   Say the numbers are field data at the project percentile, the median of daily values over
   a window, and where they come from (the Sources line in the digest). Explain in two
   sentences why journeys were chosen over page-level averages.
3. **Finding the work.** How journeys were ranked: weighted gap to target, regressions first.
   Name the top three at the start if the digest shows them, else describe the rule.
4. **What we changed.** Three to six changes with the clearest measured effect, one short
   subsection each (`###` with the change title in user terms). For each: the cost found,
   the fix, the proxy before and after with its reduction, the field effect with its p-value
   and the verdict. Prefer changes with both a proxy and a field effect. Use the change notes.
   If changes overlap on a journey, say the effect is shared.
5. **Keeping it fast.** The ratchet: why wall-clock time is not used as a gate, which proxies
   exist (instruction counts, commits, mutations), how much each ceiling has come down, and
   that CI fails a change that crosses a ceiling while a daily job lowers it.
6. **Shipping safely.** Flags and staged rollout: flags added, removed, still open, changes
   at full rollout, rollbacks. One sentence on the stages used.
7. **Where it stands.** Journeys at target, any regression this window with its numbers,
   and the next gaps from the priority list.
8. **What we would tell another team.** Three to five bullets of method, each tied to a
   number above. `[ADD: ...]` for lessons only a person knows.

## Voice
- Short sentences, active voice, one idea each. Plain words.
- Every measured number is a token. No adjectives where a number fits.
- No em dashes. No "not X, but Y". No closing summary or call to action.
- 900 to 1,400 words. Headings `##` for sections, `###` for changes. Tables in Markdown.
- Write "we" for the team. The project name comes from the digest title.
