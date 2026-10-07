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
