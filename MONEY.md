# Monetizable Problem Categories for the Prime-Topology / CRT Framework

This note captures the commercial take: the money angle is not "generic NP-hard solver." That is too broad and not credible. The money angle is:

> small-alphabet, high-constraint, high-cost-of-mistakes assignment problems where preserving partial decisions exactly matters.

That is where the CRT jump machinery is strongest.

## Core Commercial Positioning

Best fit:

- variables have a small menu of legal options;
- constraints are hard, local, and expensive to violate;
- users often lock part of a solution and want the rest repaired without destroying what already works;
- the business value comes from lower planner time, fewer mistakes, better utilization, or faster re-planning.

Not the pitch:

- "we solved NP-hardness";
- "universal SAT engine";
- "manifolds beat combinatorics."

Better pitch:

- "constraint assignment engine that preserves valid commitments exactly and repairs locally instead of rerunning everything."

## Strong Scheduling / Assignment Wedges

### 1. Staff Rostering

Examples:

- hospitals
- call centers
- security firms
- field services

Decision variables:

- worker `i` gets one shift pattern from a small legal menu.

Constraints:

- coverage minimums
- certifications
- rest windows
- union rules
- overtime caps
- incompatible pairings

Why it fits:

- each worker has a small option set;
- many constraints are local or pairwise;
- preserving already-fixed assignments matters because planners manually lock chunks of the roster.

Why people pay:

- scheduling pain is constant and expensive;
- small improvements in overtime, compliance, or planner hours are easy to value.

### 2. Last-Mile Dispatch With Commitments

Examples:

- home services
- repair fleets
- medical sample pickup
- B2B delivery

Decision variables:

- each job chooses one of a few feasible technician/route/time-window slots.

Constraints:

- travel feasibility
- technician skills
- SLA windows
- region balancing
- promised appointments

Why it fits:

- operations teams often pre-generate a small feasible option list per job;
- the hard part is then conflict-free assignment;
- preserving committed appointments is critical.

Why people pay:

- missed windows and poor dispatch quality hit revenue directly.

### 3. Ad Campaign / Budget Allocation With Hard Delivery Constraints

Decision variables:

- each campaign chooses one of a few budget/channel/daypart bundles.

Constraints:

- total budget
- audience overlap
- pacing
- brand safety exclusions
- account-level caps

Why it fits:

- after discretizing candidate bundles, the problem becomes constrained assignment;
- client commitments can be locked while the rest is repaired.

Why people pay:

- improvements in ROAS and reduced waste are easy to monetize.

### 4. Manufacturing Job-to-Machine Assignment

Examples:

- CNC shops
- packaging plants
- batch manufacturing

Decision variables:

- each job chooses one machine/start-window/setup profile.

Constraints:

- machine eligibility
- setup compatibility
- operator availability
- due dates
- maintenance windows

Why it fits:

- limited feasible placements per job;
- expensive conflicts;
- constant re-planning.

Why people pay:

- lateness, idle time, and changeover inefficiency are visible costs.

### 5. University / Training / Exam Scheduling

Decision variables:

- each exam or class gets one slot-room-proctor option.

Constraints:

- student overlap
- room capacities
- instructor/proctor conflicts
- accessibility requirements

Why it fits:

- nearly identical to the hypergraph timetabling demo;
- straightforward productization.

Why people pay:

- recurring pain, weak incumbent software, and obvious admin cost.

### 6. Sales Territory / Account Ownership Assignment

Decision variables:

- each account cluster chooses one rep/territory package.

Constraints:

- capacity
- industry specialization
- geographic overlap
- named-account protections
- fairness

Why it fits:

- small menu of legal owners per account;
- locked strategic assignments matter.

Why people pay:

- tied directly to revenue operations.

## Categories Apart From Scheduling

The broader category is not "scheduling." It is:

> discrete commitment allocation under hard constraints.

Below are categories outside classic scheduling that still fit.

### 1. Pricing and Packaging Configuration

Examples:

- enterprise SaaS quote construction
- telecom plans
- insurance bundle selection

Decision variables:

- each customer segment, account, or quote line picks one option from a small legal menu.

Constraints:

- margin floors
- bundling rules
- regional compliance
- discount caps
- compatibility rules

Why it fits:

- options are discrete and small in number;
- partial deal structures are often already locked;
- sales teams need local repair, not full re-optimization.

Why people pay:

- better quote quality and faster approvals move revenue.

### 2. Inventory Allocation and Order Promising

Examples:

- allocate scarce stock to orders
- choose fulfillment source per order
- reserve units across warehouses

Decision variables:

- each order chooses one of a few legal fulfillment plans.

Constraints:

- stock limits
- shipping SLA
- split-shipment rules
- warehouse capacity
- customer priority

Why it fits:

- each order can be given a small set of feasible plans first;
- then the assignment engine resolves conflicts exactly;
- locked enterprise orders can be preserved.

Why people pay:

- directly affects conversion, cancellations, and working capital.

### 3. Compute / GPU / Cluster Allocation

Examples:

- AI training jobs
- batch inference queues
- internal shared clusters

Decision variables:

- each job chooses one of a few feasible cluster/start/config bundles.

Constraints:

- GPU type compatibility
- memory needs
- time windows
- quota/fairness rules
- reserved capacity

Why it fits:

- jobs typically have a short list of feasible placements;
- reserved high-priority workloads must stay fixed;
- repair after failures or urgent jobs is valuable.

Why people pay:

- GPU waste is expensive and visible.

### 4. Sales Lead / Case / Ticket Routing

Examples:

- SDR lead routing
- support case assignment
- claims triage

Decision variables:

- each lead or case chooses one of a few legal owners.

Constraints:

- skills
- geography
- language
- capacity
- VIP/account ownership rules

Why it fits:

- small legal owner set per item;
- locked relationships matter;
- local reassignment after absences or surges is common.

Why people pay:

- response time and conversion improvements are measurable.

### 5. Marketplace Matching

Examples:

- lenders to borrowers
- carriers to loads
- suppliers to purchase requests

Decision variables:

- each demand item chooses one of a few eligible counterparties.

Constraints:

- capacity
- eligibility
- region
- contract rules
- exposure limits

Why it fits:

- naturally a constrained assignment problem;
- some matches are already committed and cannot be broken.

Why people pay:

- fill rate and margin are direct commercial levers.

### 6. Access Control / Policy Configuration

Examples:

- role assignment
- permission bundle assignment
- tenant policy selection

Decision variables:

- each user/system/resource picks one of a few policy bundles.

Constraints:

- separation of duties
- least privilege
- regulatory requirements
- environment compatibility

Why it fits:

- small menu of admissible bundles;
- existing commitments often need to remain unchanged;
- exact local repair is safer than global rewrite.

Why people pay:

- compliance and security mistakes are costly.

### 7. Product Catalog and Assortment Optimization

Examples:

- store-level assortment
- regional SKU activation
- marketplace listing selection

Decision variables:

- each store or region chooses one of a few assortment bundles.

Constraints:

- shelf/capacity limits
- vendor agreements
- cannibalization rules
- compliance
- regional demand

Why it fits:

- finite option bundles per location;
- some assortments are fixed by contract or season;
- local repair matters.

Why people pay:

- revenue, margin, and inventory turns.

## Categories That Do Not Fit Well

Bad fits:

- raw unconstrained search with huge open-ended action spaces;
- domains where candidate options are not pre-generated;
- problems where preserving partial decisions has no business value;
- settings where continuous optimization over many real-valued parameters dominates the difficulty.

Concrete examples:

- generic SAT product
- consumer puzzle solving
- unconstrained route generation from scratch
- end-to-end gradient model training

## Best Commercial Wedges

Strongest near-term bets:

1. staff rostering
2. field-service dispatch
3. inventory allocation / order promising
4. compute / GPU allocation
5. exam / class scheduling

Why these win:

- painful;
- frequent;
- measurable ROI;
- small feasible option sets;
- lock-and-repair workflow is normal.

## Recommended Next Build

If the goal is revenue, the strongest next demo is probably:

- `prime_nurse_rostering.py`

Why:

- obvious money;
- compliance-heavy constraints;
- ugly incumbents;
- easy to show lock-and-repair value;
- easy to demo disruption: a sick-call event forces local repair without destroying the full roster.

Best non-scheduling demo:

- `prime_inventory_allocation.py`

Why:

- easy ROI story;
- exact commitment preservation matters;
- discrete option menus are natural;
- useful for e-commerce, B2B ops, and marketplaces.
