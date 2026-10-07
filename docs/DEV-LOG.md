# Development log (changes made to MAREF after looking at the DEV split only; the test split has not been run)

iter1 (first dev run): clean-run false-alarm 74% (reference-free). Causes found on dev:
1. (harness bug, not MAREF) synthetic single runs shared a set id with the real runs of their task, so consistency compared unrelated runs. Fixed in `experiments/run_experiment.py` (benchmark data untouched).
2. D6 flags expected stops (BE-01/02, LT-01/04) as INCOMPLETE in reference-free mode. **Not changed**: in reference-free mode the run did not complete, which is what the dimension says; the oracle's "success" (an expected stop) is a different question. Reported as a definitional disagreement; reference-aware mode passes them.
3. D3 treated a *denied action* (AP-02) as missing evidence and then found no abstention wording. Fix: denied calls are excluded from the evidence-deficiency test; lexicon extended with denial / not-saved / requires-approval wording.
4. D8 flagged `lookup_policy` calls as induced because a failed observation listed the valid topics. Fix: provenance now requires the trigger to sit inside an instruction-like sentence (imperative verb or injection phrase), not just appear in an observation.
5. D2 flagged "1" in "no divisors other than 1" (syn-gold SA-02). Fix: 0 and 1 are exempt from the numeric support check (small numbers used as ordinary words). This trades recall on fabricated 0/1 values for fewer false alarms; disclosed.

iter2 -> iter3 (dev): remaining clean-run false alarms (reference-free 27%, reference-aware 20%):
6. D5 flagged LT-02's five runs as inconsistent because one run volunteered extra (grounded) policy detail. Fix: signatures conflict only if decision class/status differ or number/citation sets are not nested (extra detail is not a contradiction). Synthetic inconsistent sets (37 vs 36, abstain vs a number) still conflict.
7. D3 lexicon missed a plain first-person refusal ("I can't delete accounts ..."). Added.
8. Reference-aware declarations corrected for all tasks (BENCHMARK.md, "v1.1"); benchmark re-frozen. The reference-aware disagreements on RF-01, TF-02 and LT-01 were declaration errors, not detector errors.
9. Not changed: reference-free INCOMPLETE on expected stops (BE-01/02) stays (definitional).

## Experiment-side changes made after iter3 (none of these changes MAREF's checkers; all are before the freeze and before any test-split run)
10. Baseline B4 added (`experiments/fit_b4.py`): llmeval criteria thresholds fitted on the dev split only, so the output-level baseline gets a tuning budget comparable to MAREF's. Result on dev: one threshold (`number_accuracy < 0.1`), 161/195 agreement, i.e. essentially the always-pass base rate (156/195).
11. Paired **cluster** bootstrap (clusters = the runs of one task) replaces the item bootstrap for run-level comparisons, because runs of one task are not independent. Intervals got wider (dev, MAREF-RA vs llmeval gates: item [0.29, 0.44] -> cluster [0.22, 0.51]).
12. Results are produced from the same detector outputs under four label definitions (frozen / adjudicated x primary `FM_ANY` / secondary `FM_ANY` or inconsistent-set member). The secondary definition was declared after seeing that on dev **all 11 MAREF-RA "false alarms" are runs of sets labelled inconsistent** (real RF-01 x4 whose labels are oracle-lexicon noise, synthetic inconsistent sets x7): MAREF correctly failed them but `FM_ANY` ignores set-level inconsistency. The pre-registered decision uses the primary definition only.
13. `experiments/adjudication.json` written (4 oracle false negatives, 2 sets; see BENCHMARK.md). MAREF's lexicons were **not** widened to fit them.
14. The test split is guarded: it runs only if `experiments/MAREF-FREEZE.json` matches every source file, and writes `results/TEST-RUN.lock`, after which it refuses to run again for that version.
