---
description: An animated architecture diagram from a component list. Checks that the TAD kind is picked, the SVG builds, the parts match the list, steps stay between 3 and 6 and the one number is a fact token.
tags: [full, animation]
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Skill, Read, Glob, Grep, Bash, Write, Edit, TodoWrite]
expected_outcome: chronicle-runs/ride-request/build/animation.svg exists; animation.json is a tad with the 11 listed parts, 3 to 6 steps, and the match time held in facts.json.
---

Animate how a ride request moves through our system, for the architecture page on our docs site. I want an SVG and an HTML embed. Put the run in chronicle-runs/ride-request. The point: a rider is matched to a driver on one synchronous path, and everything slow happens on events afterwards.

Components, from the dispatch design doc (rev 4, October 2026):
- Rider app (React Native, iOS and Android)
- API gateway (Envoy)
- Ride service (Go); it writes rides to the rides database and publishes ride.requested and ride.matched to the event bus
- Matching service (Rust); the ride service calls it over gRPC, and it reads driver locations from the location store
- Location store (Redis)
- Rides database (PostgreSQL 16)
- Event bus (Kafka)
- Notification worker (Python); consumes ride.matched and sends the rider an SMS through Twilio
- Receipts worker (Python); consumes ride.matched and stores the receipt in S3
- Twilio, a vendor
- Receipt archive (Amazon S3)

Everything except the rider app and Twilio runs in our production VPC. Median match time is 1.8 seconds, from the Grafana "Matching" dashboard for October 2026.
