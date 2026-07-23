# FedOPD — Problem statement

*(conference-paper framing, fixed 2026-07-23)*

## Problem

A multi-site hospital group (e.g., a Manipal-style network: an HQ/board plus branch hospitals
across cities and regions, each branch running 5–6 departments — cardiology, oncology,
orthopaedics, gynaecology, reproductive medicine (ART), …) must continually decide **where to
add capacity**: which department, at which branch, funded from one shared budget. Today these
decisions are manual, slow, and made on lagged, siloed reports — each branch sees only its own
demand; HQ sees only summaries; and patient-level data cannot be pooled across sites for
privacy/governance reasons.

## Goal

1. **Learn jointly without sharing data**: branches collaboratively train one OPD demand
   forecaster via federated learning — model updates travel, raw data never does.
2. **Decide with agents**: an agentic layer turns forecasts into an auditable workflow —
   per-department demand-forecast agents detect sustained pressure (demand vs capacity,
   backlog growth) → the branch coordinator raises a structured capacity request ("ART @
   Delhi needs +N slots/month") → a region coordinator aggregates → the HQ strategic agent
   ranks all requests under a budget (capacity expansion, staff allocation, service-line
   enhancement, centre/region segregation) → the human board approves → the allocation
   executes, and next cycle's data shows whether it relieved the pressure (closed loop).

**Thesis: hospitals can jointly learn a demand forecaster without sharing raw data, and the
resulting forecasts can drive real capacity-allocation decisions.**

## Instantiation on public data

No hospital group publishes internal OPD data, so the design is instantiated on NHS England's
RTT dataset — the public analogue of the same structure:

| Concept (group) | Implementation (public data) |
|---|---|
| Branch hospital (Manipal Kolkata, Delhi, …) | NHS trust (35 clients, top-5 per region) |
| Region (North / South / East) | NHS England region (7) |
| HQ / board | ICB / NHS England |
| Department (5–6 per branch) | Specialty (16–23 complete series per trust) |
| OPD demand | Part_3 new RTT periods (monthly) |
| Backlog pressure | Part_2 incomplete pathways + waiting bands |
| Capacity delivered | Part_1A/1B completed pathways |

## Contributions

1. An audited, reproducible federated pipeline on real multi-site demand data (60 months,
   35 sites, deterministic selection rule independently re-derived).
2. An honest comparison ladder — naive / seasonal-naive / local-only / FedAvg / FedProx /
   FedAdam / +fine-tune / centralized — with time-based splits, val-only selection, and
   multi-seed error bars.
3. An agentic decision layer (monitor → plan → request → allocate → approve → verify) driven
   by the federated forecasts, with thresholds tied to operational standards.
4. A case study: capacity-gap ranking and allocation decisions on real backlog data
   (2026-03: 482/694 units RED; ~132k extra treatments/month network gap).
