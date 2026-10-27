---
type: llm
focus: { source: file, path: chronicle-runs/ride-request/animation.json }
weight: 2
---
The user listed 11 components: rider app, API gateway, ride service, matching service, location store (Redis), rides database (PostgreSQL), event bus (Kafka), notification worker, receipts worker, Twilio (a vendor), receipt archive (S3). The ride service calls the matching service over gRPC. ride.requested and ride.matched are events on the bus. Everything except the rider app and Twilio is in the production VPC.

You are shown the animation.json file the agent wrote. Its "tad" object lists nodes, groups, edges and flows.

PASS if all of these hold: every one of the 11 components is a node (names may differ slightly); no node is a component the user did not list (a person node for the rider is fine); Twilio sits in a group separate from the production VPC; the edges for ride.requested or ride.matched use "style": "async"; and at least one flow's path runs from the rider app through the gateway to the ride service and the matching service.
FAIL if any component is missing, an unlisted component was added, the events are drawn only as sync edges, or no flow follows the request path.
