# cast decisions

Standing decisions about cast. Each states the decision and its reason; the pages of `capabilities/` describe the resulting design.

## A launch falls back only on a failure to start

A launch runs its model's fallback when the harness cannot be started or exits with a failure in its first 15 seconds, and in no other case. Reason: a later failure can follow work the agent already did, and running the task again on another model would repeat or collide with that work. The 15 seconds are a bound on "no work yet", taken from measured start failures of 2.4 to 3.2 seconds; a harness that retries a provider limit for longer than that ends as an ordinary failure.

## A stalled job is never relaunched

`cast monitor` reports a job that is alive without progress, and nothing kills or relaunches a job on that report. Reason: the monitor's stall verdict has been wrong on a healthy job, and a fallback on a stall would need to kill the first run.

## The fallback belongs to the model, in the model catalog

The fallback is two cells of the model's row, not a field of an agent's record. Reason: a provider's limit or outage stops every agent and every launch on that model together, and a launch that names a harness and a model has no agent record to read.

## The fallback's own failure is final

A launch runs at most one fallback. Reason: two rows that name each other would otherwise relaunch without end, and a second stand-in for a stand-in has no stated use.
