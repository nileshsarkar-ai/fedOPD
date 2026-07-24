# fedOPD

Hospital networks must plan capacity department by department, which requires a demand
forecast for each, but a single central model is both impossible and inadequate: sites
will not pool raw activity data, and they differ widely in size and casemix, yet their
demand moves together, so there is shared structure worth learning jointly. fedOPD
addresses exactly this regime with cross-silo federated learning: each hospital is a
client that trains a shared neural demand forecaster by exchanging model updates, never
raw data, with per-client fine-tuning so the global model does not flatten local
differences. The testbed is England's NHS Referral-to-Treatment data, 96 monthly files
(2018-2026) spanning the COVID shock, where each NHS trust is a real federated client,
each treatment function a department, and new referrals the demand signal, reduced to a
single validated table of trust × department × month. The framing is operations research
plus distributed machine learning, not clinical work, and success is measured honestly:
against a hard persistence baseline, against isolated per-hospital training, and against
the privacy-violating ceiling of pooling all data.

A forecast alone plans nothing, so the second half is an agentic decision layer that
converts forecasts into action. From the same files the system recovers each service's
operational state, throughput, waiting-list backlog and the bed-linked admission queue,
which obey a simple accounting identity (backlog ≈ previous backlog + demand −
completions). A per-service agent compares forecast demand against trailing throughput,
projects the backlog against the 18-week standard, classifies shortfalls as transient,
sustained or regime change, and raises a structured, evidence-backed capacity request in
treatments per month; requests flow up the real NHS hierarchy (trust → ICB → national)
into a human-in-the-loop board queue where they are approved, refused or deferred, and
allocations are released again once a service recovers. COVID serves as the built-in
stress test: the forecaster must be robust to the shock while the agent is evaluated on
it, detecting the collapse, escalating through the recovery, and normalising afterwards.
The result is a system that demonstrates, on public data and real institutions, that
privacy-preserving federation plus transparent agentic decision-making can drive
operational efficiency in a multi-site health system.