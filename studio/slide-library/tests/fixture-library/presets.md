# fixture-library presets

## Presets

<!-- One entry per named composition: a prose intro paragraph followed by a fenced YAML block. -->

### nimbus-intro-en

First-touch Nimbus introduction for a prospect (English). Opens on the co-branded cover, frames the three pillars, names the problems, shows how Nimbus works, proves it with metrics, and closes. Use this when the audience is meeting Nimbus for the first time; swap `pricing-options` in only when commercials are on the table.

```yaml
preset: nimbus-intro-en
lang: en
title: Nimbus Introduction
audience: prospect
slides: [cover-nimbus.en, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider,
         proof-metrics, closing-nimbus]
```

### nimbus-intro-pt

Brazilian-Portuguese first-touch introduction. Same spine as nimbus-intro-en with the Portuguese cover.

```yaml
preset: nimbus-intro-pt
lang: pt
slides: [cover-nimbus.pt, intro-pillars, problem-cards, how-nimbus-works, nimbus-divider, proof-metrics, closing-nimbus]
```
