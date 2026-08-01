# output/ - report artifacts

Built by `src/13_report_figures.ipynb` from the stored csvs in `data/processed/` only.
No model, split, band or decision is recomputed here; `data/processed/` remains the single source of truth.
`figures/from_notebooks/` holds every image embedded in the executed notebooks, harvested by
`src/18_extract_figures.ipynb`; its `manifest.csv` maps each file to its notebook and cell.

| artifact | source csv | shows |
|---|---|---|
| `figures/fig_system_architecture.png` | `pipeline structure (src/01-17)` | monochrome system architecture: sources, panel, features, three modelling layers, sealed one-shot |
| `figures/fig_fl_architecture.png` | `pipeline structure (src/11, 14, 16)` | federated round: local fit, parameter upload, weighted average, broadcast |
| `figures/fig_agent_architecture.png` | `pipeline structure (src/10, 15)` | agent decision flow: pressure components, two frozen rule sets, decision classes, outcome check |
| `figures/fig_national_trend.png` | `rtt_incomplete_panel.csv` | national waiting-list level by month |
| `figures/fig_national_longwait_shares.png` | `rtt_incomplete_panel.csv` | monthly >18w and >52w shares |
| `figures/fig_national_beds_kh03.png` | `kh03_monthly_panel.csv` | national G&A beds open and occupied, and the occupancy rate feeding the pressure score |
| `evals/eval_national_pre_post.csv` | `rtt_incomplete_panel.csv` | era means of the monthly national series (pre: 23 months, post: 73) |
| `evals/eval_specialty_pre_post.csv` | `rtt_incomplete_panel.csv` | per-specialty era summary (24 specialties) |
| `evals/eval_provider_pre_post.csv` | `rtt_incomplete_panel.csv` | per-provider era summary (651 providers) |
| `evals/eval_provider_specialty_pre_post.csv` | `rtt_incomplete_panel.csv` | per (provider, specialty) era summary - departments within hospitals |
| `figures/fig_c110_horizon_mae_by_grain.png` | `val_horizons_c110.csv + val_horizons_coarse_c110.csv` | MAE by horizon and grain, persistence vs drift-full vs seasonal |
| `evals/eval_c110_persistence_mae_by_month_h1.csv` | `val_forecasts_c110_public_clients.csv` | persistence MAE per forecast-origin month, FY 2024-25 |
| `evals/eval_c110_provider_mae_h1.csv` | `val_forecasts_c110_public_clients.csv` | per-provider 1-month persistence MAE, FY 2024-25 |
| `figures/fig_c110_provider_mae_h1.png` | `val_forecasts_c110_public_clients.csv` | distribution of per-provider 1-month persistence MAE |
| `figures/fig_c110_conformal_bands_h1.png` | `val_conformal_bands_c110.csv` | 90% persistence band half-width per horizon and its out-of-year empirical coverage |
| `evals/eval_c110_agent_provider_h6.csv` | `agent_decisions_h6_c110.csv` | capacity (v1_) and redistribution (v2_) decision counts per provider (132 providers) |
| `evals/eval_c110_agent_icb_h6.csv` | `agent_decisions_h6_c110.csv` | redistribution decision counts, provider count and in-ICB receiver share per ICB |
| `evals/eval_c110_agent_stress_h6.csv` | `agent_decisions_h6_c110.csv` | redistribution class sizes and medians in three consecutive 6-month origin windows |
| `figures/fig_c110_agent_v2_h6.png` | `agent_decisions_h6_c110.csv` | redistribution class sizes and median realized 6-month change per class |
| `figures/fig_c110_agent_sender_split_h6.png` | `agent_decisions_h6_c110.csv` | peer-based vs lone-ICB REDISTRIBUTE_OUT flags and the pressure each group carries |
| `figures/fig_c110_fl_models_h1.png` | `fl_summary_c110.csv` | MAE per FL model and regime vs persistence |
| `figures/fig_fl_algorithms_by_specialty_h1.png` | `fl_scaleup_by_specialty.csv` | per-specialty gap to persistence for all four linear information regimes |
| `figures/fig_c110_fl_linear_vs_neural_h1.png` | `fl_neural_summary.csv` | linear vs neural FL at C_110, both regimes, identical eligible rows |
| `figures/fig_neural_vs_linear_4panel_h1.png` | `fl_neural_summary.csv` | neural vs linear MAE per specialty for pooled and FedAvg in both regimes |
| `figures/fig_fl_covid_regime_effect_h1.png` | `fl_scaleup_by_specialty.csv + fl_neural_summary.csv` | per-specialty cost of training on post-Covid data only, linear and neural FedAvg |
| `figures/fig_fl_regime_effect_4panel_h1.png` | `fl_scaleup_by_specialty.csv` | per-specialty post-minus-full MAE for all four linear information regimes |
| `figures/fig_fl_neural_gap_by_specialty_h1.png` | `fl_neural_summary.csv` | per-specialty MAE gap, neural minus linear FedAvg, both regimes |
| `figures/fig_fl_neural_gap_vs_size_h1.png` | `fl_neural_summary.csv` | relative neural-linear gap vs specialty validation size, full regime |
| `figures/fig_c110_sealed_one_shot_h1.png` | `sealed_year_eval.csv` | C_110 validation vs sealed-year MAE for every model, one-shot verdict |
| `figures/fig_sealed_gap_by_specialty_h1.png` | `sealed_year_eval.csv` | per-specialty sealed-year MAE gap to persistence, three final-cut models |
| `figures/fig_sealed_persistence_drift_h1.png` | `sealed_year_eval.csv` | per-specialty % change in persistence MAE from validation to sealed year |
| `figures/fig_c110_cohort_sensitivity_h1.png` | `cohort_sensitivity.csv` | validation MAE per model under the stored and the strictly prospective eligibility rule |
| `RESULTS.md` | `all result csvs` | headline results list, generated from stored csvs |
