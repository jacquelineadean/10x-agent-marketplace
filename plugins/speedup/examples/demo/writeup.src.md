# How we made Lumen {{headline.geomean_speedup}} faster

Lumen got {{headline.geomean_speedup}} faster across {{headline.journeys_measured}} user journeys at p75 between the baseline week of {{windows.baseline.since}} and the week ending {{windows.current.until}}. The biggest single win was a fresh load to a typeable composer, which went from {{journeys.fresh-load.baseline|s}} to {{journeys.fresh-load.current|s}}. We shipped {{headline.changes_shipped}} changes and rolled back {{headline.changes_rolled_back}}. This post covers how we chose what to measure, the fixes that moved the numbers, and how we keep them from sliding back.

## What we measured

We measured journeys: things a person does, timed from their side of the screen until they can act. Page-level averages hide where people wait. A journey names the wait.

| Journey | Baseline | Now | Speedup | Target |
| --- | --- | --- | --- | --- |
| Fresh load to typeable composer | {{journeys.fresh-load.baseline}} | {{journeys.fresh-load.current}} | {{journeys.fresh-load.speedup}} | {{journeys.fresh-load.target}} |
| Switch conversation | {{journeys.conversation-switch.baseline}} | {{journeys.conversation-switch.current}} | {{journeys.conversation-switch.speedup}} | {{journeys.conversation-switch.target}} |
| New chat ready | {{journeys.new-chat.baseline}} | {{journeys.new-chat.current}} | {{journeys.new-chat.speedup}} | {{journeys.new-chat.target}} |
| Send to first painted token | {{journeys.send-to-paint.baseline}} | {{journeys.send-to-paint.current}} | {{journeys.send-to-paint.speedup}} | {{journeys.send-to-paint.target}} |
| Open sidebar | {{journeys.sidebar-open.baseline}} | {{journeys.sidebar-open.current}} | {{journeys.sidebar-open.speedup}} | {{journeys.sidebar-open.target}} |
| Search results shown | {{journeys.search-results.baseline}} | {{journeys.search-results.current}} | {{journeys.search-results.speedup}} | {{journeys.search-results.target}} |
| Desktop app cold start | {{journeys.desktop-cold-start.baseline}} | {{journeys.desktop-cold-start.current}} | {{journeys.desktop-cold-start.speedup}} | {{journeys.desktop-cold-start.target}} |
| Scroll a long thread (INP) | {{journeys.long-thread-scroll.baseline}} | {{journeys.long-thread-scroll.current}} | {{journeys.long-thread-scroll.speedup}} | {{journeys.long-thread-scroll.target}} |
| Conversation history API | {{journeys.history-api.baseline}} | {{journeys.history-api.current}} | {{journeys.history-api.speedup}} | {{journeys.history-api.target}} |

Every value is field data at p75. A day's value is the median of that day's points, and a week's value is the median of its days. Browser journeys come from Datadog RUM, the send-to-paint and desktop journeys from Datadog metrics, and the history API from Prometheus. The overall figure is a geometric mean, so one big win cannot hide a loss elsewhere.

## Finding the work

Each journey got a target and a weight for how many people hit it and how much it matters. We ranked the work by gap to target times weight, with regressions first. The first load and conversation switching carried the most weight, so they went first. [ADD: why these targets, and who set them]

## What we changed

### Type before the app boots

The composer waited for the whole React tree. We put a static composer in the HTML and moved the typed text into the real one on mount. DOM mutations before the composer was ready fell from {{changes.c-0001.proxy.before}} to {{changes.c-0001.proxy.after}}, a cut of {{changes.c-0001.proxy.reduction_pct}}. In the field, the fresh load improved by {{changes.c-0001.impact.fresh-load.improvement_pct}} (p {{changes.c-0001.impact.fresh-load.p}}). Two other first-load changes shipped within the same week, so they share that effect.

### Resolve each message ID once

Assembling the message tree looked up the same message IDs inside a loop. Resolving each one once cut the instruction count from {{changes.c-0002.proxy.before}} to {{changes.c-0002.proxy.after}}, {{changes.c-0002.proxy.reduction_pct}} fewer. Switching conversations improved by {{changes.c-0002.impact.conversation-switch.improvement_pct}} and send to first paint by {{changes.c-0002.impact.send-to-paint.improvement_pct}}.

### Keep reply markdown on the fast path

One em dash in a reply made V8 store the whole string as UTF-16, and every syntax-highlighting regex slowed down with it. Keeping the markdown in Latin-1 strings cut rendering instructions by {{changes.c-0009.proxy.reduction_pct}}. Send to first paint went from {{changes.c-0009.impact.send-to-paint.before}} to {{changes.c-0009.impact.send-to-paint.after}}.

### Precompile the desktop code cache

The desktop main process compiled its JavaScript on every launch. A V8 code cache built at package time cut boot instructions by {{changes.c-0004.proxy.reduction_pct}}, and cold start improved by {{changes.c-0004.impact.desktop-cold-start.improvement_pct}}. Lazy-loading the menus and updater took another {{changes.c-0012.impact.desktop-cold-start.improvement_pct}}.

### Stop re-rendering the sidebar

Opening the sidebar re-rendered every conversation row. React commits on open fell from {{changes.c-0006.proxy.before}} to {{changes.c-0006.proxy.after}}, and the journey improved by {{changes.c-0006.impact.sidebar-open.improvement_pct}}.

## Keeping it fast

Wall-clock time is too noisy to gate code on. Each hot path got a proxy that prints the same number on every run: instruction counts under valgrind for pure JavaScript, React commits and DOM mutations for interactions. CI fails a pull request that pushes a proxy over its ceiling. A daily job lowers each ceiling when the number drops, and nothing raises one without a person and a reason.

Since the first run, the message tree ceiling is down {{benchmarks.message-tree.ceiling_reduction_pct}}, markdown rendering {{benchmarks.markdown-render.ceiling_reduction_pct}}, desktop boot {{benchmarks.main-boot.ceiling_reduction_pct}} and composer mutations {{benchmarks.composer-mutations.ceiling_reduction_pct}}. The median cut across all {{headline.guardrails}} guardrails is {{headline.median_ceiling_reduction_pct}}.

## Shipping safely

Risky changes went out behind flags: employees first, then a small share of users, then everyone. We added {{headline.flags_added}} flags and have removed {{headline.flags_removed}}. {{headline.changes_at_full_rollout}} changes are at full rollout, and {{headline.changes_rolled_back}} were rolled back.

## Where it stands

{{headline.journeys_at_target}} of {{headline.journeys_with_target}} journeys meet their target. Search regressed this week: it is {{journeys.search-results.vs_previous_pct|signed}} against the week before (p {{journeys.search-results.vs_previous_p}}). The suspect is c-0019, attachment previews in search results, which shipped behind a flag that is still open. Search is now {{journeys.search-results.gap_to_target_pct}} over target and leads the list. The history API is next at {{journeys.history-api.gap_to_target_pct}} over target.

## What we would tell another team

- Measure journeys, not pages. The first load alone went from {{journeys.fresh-load.baseline}} to {{journeys.fresh-load.current}} once we timed the moment people could type.
- Gate on proxies, not stopwatches. A ceiling that only moves down kept every proxy within its limit after the sprint ended.
- Log every change with its flag. When search slowed, the change log named a suspect in minutes.
- Keep measuring daily. The regression showed up within one week of shipping.
- [ADD: what the team would do differently]
