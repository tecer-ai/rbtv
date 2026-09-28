---
description: "Read BEFORE making any ANIMATION out of an image model — a looping GIF, a loading animation, a sprite that walks, runs, waves or spins, an animated banner or sticker. Image models draw stills; this is how to get frames that stay consistent AND visibly move, which architecture to pick, every failure met on the way and its fix, and how to cut, register, colour and loop the frames."
tags: [design, generate-image]
---

# Animated loops — getting a GIF out of a still-image model

An image model draws ONE picture per call. It has no idea of "the next frame". Every animation made
with it is therefore an assembly problem with two opposite ways to fail:

- **Drift** — the frames do not match each other (a character's hair, size, colours or position
  change from frame to frame), so the loop SHIMMERS or JUMPS instead of moving.
- **Stillness** — the frames match so well that nothing moves, so the loop reads as a frozen
  picture.

Push the model toward consistency and you get stillness; push it toward motion and you get drift.
Everything below is about getting both at once. It was learned on a real run — a small looping scene
of four cartoon characters racing across a scrolling landscape, judged by a demanding owner over
three trials — and it generalises to any subject: a mascot waving, a product rotating, a logo
bouncing, animals running, a person walking.

Read `consistent-sets.md` too: the two-part prompt (a shared style text + one subject sentence) and
calibrating with reference images apply to animation frames exactly as to a set of icons.

---

## 1. Choose the architecture BEFORE the first call

| Way | What the model draws | What code does | Buys | Costs |
|---|---|---|---|---|
| **A. Cut-out ("puppet")** | Each part once — background, each figure, each effect — on a chroma background | Moves, bobs, flickers and scales the parts per frame | Zero drift, seamless loops, very cheap | Motion is stiff unless the parts are posed well; the figures never change pose |
| **B. Model-drawn frames** | The poses themselves, as frames | Cuts, registers, colours and assembles them | Real, lively motion — limbs, faces, squash | Drift and stillness both lurk; needs the fixes below |
| **C. One still + effects** | One finished picture | Pulses, palette-cycles, flashes lights | Cheapest and calmest | Barely alive |

The strongest result in practice is a **hybrid of A and B**: the model draws the POSES of each moving
figure (B), everything else is a separate still that code moves (A). That is the recipe in § 3.
State the architecture to the person before spending — it decides what "done" can look like.

---

## 2. What failed, in order — do not repeat these

Each row is a real attempt, what it produced, and why.

| # | Attempt | Result | Why |
|---|---|---|---|
| F1 | Draw frame 1, then ask image-to-image for frames 2-4 as edits OF FRAME 1 ("same image, next pose, background shifted left") | **Stillness.** The edits were near-copies: poses hardly changed, the background did not scroll, and small redraw noise made the loop shimmer | Image-to-image is tuned to PRESERVE the input. "Change only the motion" is read as "change almost nothing" |
| F2 | One call: a 2x2 sheet of four frames of the WHOLE scene (background + all figures) | **Drift.** Style and characters were consistent across panels and the poses did change — but the model drew each panel a few pixels off from the others (the loop jumped), figures sat at slightly different spots inside each panel (jitter no alignment can fix), and the background barely scrolled, so the figures ran in place | A model composes each panel as its own picture; "keep everything at the same place" is not something it can guarantee |
| F3 | Background separated out (drawn once, scrolled by code); one call for ALL FOUR figures, eight frames, on a chroma background | **Stillness.** The owner: *"the characters are not moving at all"*. The model drew one group pose and copied it eight times with tiny changes | Asked to animate several figures at once, the model spends its effort on keeping the group consistent and cheats on motion |
| ✅ | **One call PER FIGURE**, four key poses each, every pose DESCRIBED explicitly and EXAGGERATED ("legs a blurred spinning wheel", "a huge leap, legs wide apart", "squashed on landing, eyes squeezed"); code adds squash/stretch and an out-of-step hop per figure; background drawn once and scrolled by code | **Both.** Poses genuinely different and on-model; the loop reads as lively and comical. The owner: *"love it"* | One figure per call lets the model spend its attention on that figure's poses; named extreme poses leave it no room to copy |

**The two laws the run proved:**

1. **Motion must be NAMED, pose by pose.** "A run cycle" or "the next frame" gets a copy. "Panel 1:
   X; panel 2: Y; panel 3: Z; panel 4: W", each one visibly, physically different, gets motion.
   Words that helped: *wildly exaggerated*, *comical*, *like an old animated cartoon*, *clearly,
   obviously different from each other*.
2. **One moving figure per call.** Group sheets trade motion for group consistency. Figures are
   combined later, by code.

---

## 3. The recipe

1. **Background, one call, no figures in it.** Wide (about 3:1), side-on, with *"nothing moving in
   it"*, and — if figures will stand on it — *"the ground's top edge is one perfectly straight
   horizontal line across the whole width"*. Measure where that line lands on the result; the figures'
   feet go there.
2. **Each moving figure, one call.** A strip of FOUR panels, each pose described (law 1), same
   figure, same size, facing the same way, side view, on a plain chroma background (bright magenta
   is the usual choice; see § 5 when the figure itself contains that colour). Add the style
   text and, if the set has them, style references (`consistent-sets.md` § 2).
3. **Cut, clean, register, colour** each figure's panels (§§ 4-6).
4. **Add the cheap motion in code** — this is what turns good poses into a lively loop:
   - **Squash and stretch:** scale a pose to about 112 % wide / 86 % tall on the landing pose and
     92 % / 110 % at the top of a jump. Do it on the pixel grid with nearest-neighbour scaling.
   - **Hop:** lift each pose by a small table — e.g. 0, -3, -6, -2 grid pixels for contact,
     rising, top, falling.
   - **Out of step:** give each figure its own phase in the cycle, so they bounce independently.
     Figures in lockstep read as one stiff block.
5. **Loop the background** (§ 7) and composite: background, then each figure's current pose with
   its feet on the ground line plus its hop.
6. **Timing:** 100-120 ms per pose reads as lively for a cartoon run; a 4-pose cycle under half a
   second, an 8-pose cycle under a second.

---

## 4. Cutting a sheet — every trap met

- **The layout you asked for is not the layout you get.** Asked for 1 row of 4 → got 4 x 2 (eight
  panels) on every call. Asked for 4 x 2 → got 2 x 4. Never hard-code the grid: detect it (a gutter
  or panel-frame line shows as a near-uniform line across the middle; or choose the layout whose
  panel shape best fits the subject — a line of four runners is wide, one runner is tall). Extra
  panels are a gift: use them as a second, slightly different cycle.
- **Gutters and panel frames leak into the cut.** Trim a margin at every cut (about 16 px on a
  ~1300 px sheet cleared both the gutter and the thin dark frame the model draws round each panel).
- **An off-centre gutter becomes a BAND inside the panel.** One sheet carried a 24 px white band
  along the top of every panel. It also counted in the figure's height, so that figure came out too
  small. Clear flat rows/columns (over 85 % one near-white or near-black colour) **pixel by
  pixel**.
  ⚠ **Do NOT clear them by deleting whole connected pieces**: a figure touching the band is ONE
  piece with it, and that rule deleted entire figures from some frames. Then clear any remaining
  thin line pieces (at most ~6 px thick, spanning over a quarter of the panel).
- **The chroma colour is not uniform across a sheet.** One sheet's top row came back a lighter
  purple than its bottom row. Key EACH PANEL on its own corner colour, never the whole sheet on
  one sample.
- **"Clear" and "transparent" materials key out from the inside** — name glass, water and screens
  as tinted and opaque (`consistent-sets.md`).
- **Motion blur keeps a chroma fringe.** A "blurred spinning wheel of legs" leaves a pink halo
  around the blur; accept it or clear chroma-tinted edge pixels.
- **A call sometimes returns only text** ("I have created..."), no image. It is a delivery failure,
  not a bad picture — resend that call once.

---

## 5. Registration — making the poses sit still where they should

- **Crop each pose to its own bounding box, then scale ALL poses of one figure by ONE factor**
  (the tallest pose to the target height). Fitting each pose to the same box separately makes the
  figure pump in size from frame to frame.
- **Anchor by the feet.** Place every pose bottom-centred on the ground line. The eye tracks the
  contact point; a pose anchored by its top floats and sinks.
- **Whole-scene frames (architecture B on a full scene)** can be registered by brute-forcing the
  pixel shift that best matches frame 1 (a few pixels either way) and cropping to the common area.
  It fixes a panel drawn 2-4 px off; it cannot fix figures that moved WITHIN the panel.
- **Chroma choice per figure.** A pink figure keys out on magenta — draw it on bright green (and
  then keep green out of its props, e.g. a display base). A black figure vanishes on a dark page —
  choose its colour for the background it will be shown on.

---

## 6. Colour — one palette per figure, across all its poses

Pixel-art conversion cuts the palette (and a GIF must). **Quantise all poses of one figure
TOGETHER** — paste them into one strip, cut the palette once, split back. Quantising each frame
alone gives each a slightly different palette, and the loop flickers between them. The background
gets its own palette; it does not change per frame.

For pixel art, the conversion that holds up: crop, **box-filter DOWN** to the pixel grid, cut the
palette, **nearest-neighbour UP** to display size. Resizing straight to the display size blurs every
edge.

---

## 7. Looping the background

- **Tile it with its mirror image.** A picture followed by its horizontal mirror always joins
  without a seam — no hunting for a seamless edge, no inpainting. Landscapes read naturally
  mirrored.
- **Parallax from one picture:** split it at the ground line into bands and scroll the far band
  slower than the near one (e.g. 1 and 3 grid pixels per frame). Figures on the near band look fast.
- **Use an UNWRAPPED frame counter for the scroll** (take the offset modulo the strip width), and a
  wrapped one for the poses. Wrapping the scroll at the pose cycle makes the background jump back.
- **A seamless scroll rarely fits in a small baked loop.** Background and pose cycle only line up
  again after LCM(strip width / speed, pose cycle) frames — often hundreds. If the target can draw
  (a program, a game, a web page), **compose live from the clock**: two background blits, one blit
  per figure. Bake a fixed frame sheet or a GIF only when the target can only play frames, and then
  choose the strip width and speeds so the loop closes.

---

## 8. Judging it

- **An agent cannot watch a GIF.** Lay the frames side by side in a strip and look at that: are all
  figures present in every frame, do the poses differ, does anything jump? Two defects in this run
  were found only this way: a leftover line in one figure's panels, and figures missing entirely
  from one frame.
- **Also look at the cut-out poses alone**, zoomed, on a neutral grey: frame leftovers, halos and
  bad crops show there before they are hidden in the scene.
- **The person judges the moving GIF**, at the real display size, before anything is installed.
  Make it at the real size and on the real page colour.
- **If the target draws the animation itself, render the preview FROM the target's own drawing
  code** (feed its compose function into an image library) — that proves the installed assets and
  layout reproduce what was approved.

---

## 9. Cost and iteration, from the run

| Trial | Calls | Outcome |
|---|---|---|
| F1 + F2 compared side by side | 5 | F2's direction chosen; F1 dropped |
| F3 (background separate, group sheet) | 2 | Background kept; figures rejected as still |
| ✅ one sheet per figure | 4 | Approved |

Eleven image calls from idea to an approved, installed animation. Everything else was free code:
cutting, keying, registering, palette, squash, hop, parallax, preview. **Retune in code before
paying for new pictures** — speed, size, hop height and spacing all cost nothing.

---

## 10. Checklist

- [ ] Architecture chosen and stated (§ 1); hybrid A+B for figures over a moving background.
- [ ] Background: one call, no figures, straight ground line, measured.
- [ ] One call per moving figure; every pose named and exaggerated; plain chroma background that
      the figure does not contain.
- [ ] Sheet layout DETECTED, margins trimmed, each panel keyed on its own corner.
- [ ] Flat bands cleared pixel-wise; thin lines cleared; every figure present in every frame.
- [ ] One scale factor per figure; poses anchored by the feet.
- [ ] One palette per figure across its poses.
- [ ] Squash/stretch, hop and out-of-step phase added in code.
- [ ] Background mirror-tiled; parallax bands; unwrapped scroll counter.
- [ ] Frames checked as a strip; cut-outs checked zoomed; GIF shown at real size before install.
