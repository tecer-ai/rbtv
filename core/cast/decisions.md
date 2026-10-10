# cast decisions

Standing decisions about cast. Each states the decision and its reason; the pages of `capabilities/` describe the resulting design.

## A launch falls back only on a failure to start

A launch runs a fallback when the harness cannot be started or exits with a failure in its first 15 seconds, and in no other case. Reason: a later failure can follow work the agent already did, and running the task again on another model would repeat or collide with that work. The 15 seconds are a bound on "no work yet", taken from measured start failures of 2.4 to 4 seconds; a harness that retries a provider limit for longer than that ends as an ordinary failure.

## A stalled job is never relaunched

`cast monitor` reports a job that is alive without progress, and nothing kills or relaunches a job on that report. Reason: the monitor's stall verdict has been wrong on a healthy job, and a fallback on a stall would need to kill the first run.

## A job's first verdict never reports a freeze

The first time `cast monitor` judges a job, it has watched the job's processes for 1.2 seconds only, and a job that shows no life in that time reads `SUSPECT`, never `STALLED` or `NO-SIGNAL`. A one-shot roster therefore never shows those two states, and `cast monitor --watch` reports a frozen job on its second poll of that job at the earliest. Reason: a read of one instant or of 1.2 seconds has been wrong on healthy jobs, which stay quiet for longer while they wait on a reply or a sleeping child, and a wrong "frozen" has cost a killed job. `provider-limit` and `DEADLINE` are reported on the first verdict, because neither rests on that read.

## The fallback is chosen from the model catalog, not named per model or per agent

A launch finds its fallback by ranking the other models of the failed model's level, the way `cast route` ranks. Reason: a column or an agent field that names one stand-in per model is a second table to fill and to keep valid each time a model is replaced, and the model catalog already holds what the choice needs.

## A fallback stays inside its level, and may try the same provider

A launch tries every candidate of the level in ranking order, including models of the provider that just failed, and stops when the level is used up; it names the best model of the next level down and does not launch it. Reason: a model of a lower level is a silent drop in quality, which the owner decides, and trying a model whose provider is down costs a few seconds while a rule that skips providers would also skip a model that works.

## Fallback is off until an installation turns it on

`fallback` in the installation's defaults is `off` unless set. Reason: a fallback launches models on other providers' plans, and an installation that never asked for that must not start spending them.

## A fallback ranks quality on both scores added

Reason: a launch does not say whether its task is code or text, so the stand-in has to be good at both.

## An installation decides the two overrides and which models are selected; rbtv proposes the rest

`cast models update` copies level, scores, cost, effort count and image flag from the shipped model catalog and never changes an override or which models are selected. The shipped model catalog leaves both override cells blank for every model. Reason: the first group describes the model and changes when the model does; an override is one installation's favorite, and a favorite shipped by rbtv would win a level in every installation that never chose it.

## A selected model is eligible; no column takes it out of routing

Every row of the model catalog in force competes for `cast route` verdicts, fallbacks and panel seats, subject to its login, its level and what it can do. The model catalog has no `use` column, and a file that still names one is refused as a file with an unknown column. Reason: selection already says which models an installation wants, and a second switch on each row gave two places to look for why a model was never named. A model that must not be routed is unselected.

## An image model has no level and no score

An image-generation model's row carries `image=Y` and blank `level`, `reasoning` and `coding`; `cast route --caps image` selects it, and no class, fallback or panel does, whatever its other cells hold. Reason: the levels and scores rank text and code work, and a level or a zero written for an image model put a number into rankings it has no place in.

## The shipped model catalog lists pinned versions and list prices

One row per model line names a pinned version, never a moving alias such as a `-latest` name. `cost` is the provider's standard API list price for output tokens at its base rate; a cost that is not known is blank, never a placeholder number. Reason: an alias changes what a row launches with no change to the row, and a placeholder cost ranks as a real price.
