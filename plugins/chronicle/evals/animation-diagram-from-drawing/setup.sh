#!/bin/bash
# The user's own drawing of the paging path, with an id on every part and path.
set -euo pipefail
mkdir -p docs
cat > docs/paging-path.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 300">
  <g id="alert">
    <rect x="20" y="100" width="150" height="80" rx="6" fill="#fff" stroke="#222"/>
    <text x="95" y="145" text-anchor="middle">Alert fires</text>
  </g>
  <g id="pager">
    <rect x="220" y="100" width="150" height="80" rx="6" fill="#fff" stroke="#222"/>
    <text x="295" y="145" text-anchor="middle">PagerDuty</text>
  </g>
  <g id="oncall">
    <rect x="420" y="100" width="150" height="80" rx="6" fill="#fff" stroke="#222"/>
    <text x="495" y="145" text-anchor="middle">On-call engineer</text>
  </g>
  <g id="channel">
    <rect x="620" y="100" width="150" height="80" rx="6" fill="#fff" stroke="#222"/>
    <text x="695" y="145" text-anchor="middle">Incident channel</text>
  </g>
  <g id="statuspage">
    <rect x="820" y="100" width="160" height="80" rx="6" fill="#fff" stroke="#222"/>
    <text x="900" y="145" text-anchor="middle">Status page</text>
  </g>
  <path id="p1" d="M170 140 L220 140" stroke="#222" fill="none"/>
  <path id="p2" d="M370 140 L420 140" stroke="#222" fill="none"/>
  <path id="p3" d="M570 140 L620 140" stroke="#222" fill="none"/>
  <path id="p4" d="M770 140 L820 140" stroke="#222" fill="none"/>
</svg>
SVG
