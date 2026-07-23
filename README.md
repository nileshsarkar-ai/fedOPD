# FedOPD

Federated OPD demand forecasting — an operations-research prototype.

Cross-silo federated forecasting of hospital outpatient / departmental demand, where each
provider (hospital trust) participates as a federated client. Providers collaboratively
train a shared forecasting model without pooling their raw activity data.

## Why

Hospital networks want accurate, per-department demand forecasts to plan staffing and
capacity, but patient-level data typically cannot leave each site. Federated learning lets
every provider contribute to a shared model while keeping its own records local.