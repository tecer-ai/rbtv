---
description: "Read BEFORE generating the second picture of a set that must look like it belongs with the first — icons, cards, illustrations, product shots, chapter headers. How to calibrate a model with reference images, grow a reference library, and iterate without losing what was already approved."
tags: [design, generate-image]
---

# Consistent sets — making many pictures look like one set

One picture only has to be good. A SET has a second job: every member has to look like it was made
by the same hand, on the same day, for the same thing. A text prompt alone rarely carries that —
two calls with the same words drift apart in palette, line weight, level of detail and framing.

The techniques below are ordered by how much consistency they buy. Each one is cheap; together they
turn a pile of separate pictures into a set. They were built from a real run: 52 pictures for one
interface, remade over one evening with an owner reviewing each batch.

---

## 1. Split the prompt in two — this is the backbone

```
prompt = SHARED STYLE TEXT  +  THIS PICTURE'S SUBJECT SENTENCE
```

The **style half** is one block of text — medium, palette discipline, edge treatment, lighting,
composition, background, prohibitions — and it is **byte-identical for every picture in the set**.
The **subject half** is the only thing that changes.

Keep the style half in ONE place that the generator reads (a constant in a script, a file the
prompt is assembled from). The moment two pictures are generated from two hand-typed prompts, the
set has two styles and nobody can say which is canonical.

Write the subject half as **a description an illustrator could work from**, not a label. "A desk
telephone" produces a generic object; "a chunky vintage desk telephone, handset resting on its
cradle, round rotary dial, short thick coiled cord" produces a specific one. Name the object, its
material, its colours, its pose, and one telling detail.

---

## 2. Calibrate with reference images

Most image APIs accept input images alongside the prompt. Send the pictures you ALREADY like from
this set, and say in the prompt that they are there for STYLE only:

> The attached images are existing pictures from the same set, given only to show the style. Do not
> copy their subjects, shapes, compositions or colours — draw only the subject described above.

Then, per reference, one line on what you like about it. "You can feel the object's age, it is
unmistakably pixel art and still has enough detail" steers far better than "good style".

What the run measured:

- **Few beats many.** Two references the owner liked without reservation produced better, more
  consistent results than eight references carrying mixed comments ("I like the drawing, not the
  border"). Mixed comments give the model contradictory instructions and it splits the difference.
- **Only send pictures you like WITHOUT reservation.** A reference you are half-happy with teaches
  the half you dislike.
- **Never send the picture you are replacing.** It anchors the model to the version you are trying
  to improve, and you get a variation of it instead of a fresh take.
- **Two to four references is a good working range.** Past that, each one dilutes the rest.

⚠ References amplify the style half; they do not replace it. Both together is what holds a set.

---

## 3. Grow a reference library as you go

Start with whatever you have — one picture you like, even a rough one. Generate the next few with
it attached. When one of the new results is better than what you started with, **promote it into
the reference set** and use it for the next batch.

This compounds: the set teaches itself. Half-way through the run above, two newly approved pictures
joined the two originals, and the later batches came back closer to the target on the first try.

Keep the library small and curated. Promote only pictures approved without reservation, and say
out loud (in the file that holds the list) why each one is in there. A reference library nobody
curates becomes eight mixed references and loses its power — see above.

---

## 4. Keep the exact prompt beside the picture

A reference-made picture **cannot be reproduced from the subject sentence alone** — the references
were part of the input. Save the full prompt text next to each output (most CLIs can write it for
you), and note on the subject's own row that this picture was made with references.

Without this, the next person regenerates from the subject sentence, gets something different, and
the set quietly drifts.

---

## 5. Never lose an approved picture

Before replacing a picture the reviewer already approved, **park the old version** somewhere
retrievable, and only then write the new one. Regeneration is a roll of the dice: you can lose a
picture everybody liked and be unable to get it back.

This matters most when a rule changes mid-set ("no borders any more") and there is a temptation to
regenerate everything. Regenerate deliberately, one at a time, with the old version parked.

---

## 6. Iterate on the SENTENCE, not the picture

When a result is wrong, the fix is a better subject sentence, not another roll of the same one.
Re-rolling costs money and teaches nobody anything; a reworded sentence fixes the picture AND every
future regeneration of it. Record WHY the wording changed, next to the sentence.

Wording that repeatedly earned its place:

| Problem in the result | Wording that fixed it |
|---|---|
| The object reads as cut off | "the whole X, from top to bottom, fully inside the frame" — and check whether the drawing simply ENDS abruptly (a stump with no base reads as cropped even with space around it) |
| A scene appears behind the object | "standing alone, with no sky, no ground and no scenery behind it" — some models add a backdrop no matter what the style text says |
| Details vanish at final size | "few, large parts" plus naming the two or three parts that matter |
| Colours drift from the set | name the actual colours: "painted teal-green and red tin", not "colourful" |
| One picture feels flat next to the others | check §8 before rewording |

**Cost discipline:** one call per picture. Re-send only when a call comes back with NO image (a
failed delivery — it happens, and a good runner skips that key rather than crashing the batch).
Never re-send just because you dislike the result.

**Batch size:** three to six pictures per round, with a review between rounds. Big batches multiply
a bad style decision across everything before anyone notices.

---

## 7. Judge at final size, on the real background, with real spacing

A set is judged where it will be used, not at full resolution on your screen:

- Render each picture at its **final size**, and place it on a **light and a dark background** — a
  dark-bodied object can vanish on a dark surface even though it looked fine on white.
- Give each picture **the same margin it will have in the product**. A contact sheet that packs
  pictures edge to edge makes tall objects look cropped, and you will chase a bug that is not there
  (that exact false alarm cost a round in the run above).
- Show the current picture and the new one **side by side**, labelled.

---

## 8. When one picture feels "basic" and nobody can say why

Look for a rule the rest of the set follows and that one breaks. In the run above, one picture was
a drawn symbol while every other member of its group was a manufactured object with real material —
and the reviewer's complaint was exactly "it feels too basic compared to all of the others". No
amount of extra detail on a symbol fixes that; changing it into an object does.

Write the set's rules down as you discover them (what the pictures depict, what they must never be)
and check a weak picture against them before rewording anything.

---

## 9. Post-processing is part of the look

If the pictures pass through a conversion — background removal, palette reduction, downscaling,
cropping — then that conversion is as much a part of the style as the prompt, and it must run
**identically over the whole set**. A set generated consistently and converted with per-picture
tweaks is not consistent.

Two hazards worth knowing before you choose a pipeline:

- **A chroma-key background only works when the key colour is absent from the subjects.** Ask for a
  plain background in a colour nothing in the set contains. Where the subject legitimately shares
  that hue, a naive "remove this colour everywhere" step will punch holes in the object.
- **Compression smears the background into dark edges.** A JPEG returned by an image API carries a
  band of key-tinted pixels along every dark outline; a cleaner that measures "distance from the
  key colour" misses them because they are dark. Judging an edge pixel against the object's colour
  just INSIDE it separates spill from a legitimately coloured edge.

---

## 10. What did not work

Recorded so nobody pays for it twice:

- Eight references with "I like this, not that" comments — worse than two clean ones.
- Sending the picture being replaced as one of the references.
- Fighting the medium with composition rules: forcing a subject into an orientation that suits the
  cleaner rather than the object produced a picture the reviewer called the worst of the run.
- Re-rolling the same prompt hoping for a better draw.
