# Ranking with TypeSafe

The result: the items of a large set, ordered by how likely each is to be one you need, so that you open the likely ones first and spend no reading on the rest. Inputs: the set, as file paths or as records; one question that separates the items you need from the others; and the goal the question refers to, when it takes more than a sentence to state.

Do not send a file that holds credentials or keys, or one the owner marked private: every item's text leaves the machine.

## 1. Write the question

Write the exact condition, as a yes/no question about one item. The model reads the words literally: "Does this page say how a tool reads its key?" is answered; "Is this relevant?" is not, because the model is never told relevant to what.

When the goal is longer than a sentence, write it to a file and name it in the question in backticks, as step 2 shows. Keep counts, dates and arithmetic out of the question; compute those yourself.

Send the part the question is about. An item that is long and mostly about other things ranks poorly, because the unrelated text outweighs the passage that matters. When one part of each item carries the signal (its opening, its summary, one field), put that part on one line per item and rank those lines as records.

## 2. Run it once over the whole set

For files, give the paths on standard input:

```
ls notes/*.md | typesafe yesno "Would this file help with the task in `goal`?" \
    --each-file --state goal=goal.txt --sort high
```

For records, give one JSON value per line and use `--each` in place of `--each-file`; beside a `--state` file the record is the part named `item`. `typesafe yesno --help` states every option and what the output means.

One run judges every item, eight at a time, and prints them from most to least likely with the probability of yes. Add `--tiers 0.7,0.3` to group them, with thresholds you choose for this set.

## 3. Read from the top, and decide yourself

Open the items from the top of the list. Stop when what you have read answers your need, or when the probabilities have fallen to the level of items that proved useless.

The order is a suggestion. Open an item the list ranked low when its name or what you already know says you need it. A probability near 0.5 means the model could not tell, not that the item is half useful.

An item reported as failed was not judged: it was unreadable or longer than one request holds. Decide about it yourself.

## 4. Say what you did

When you leave items unread because of their rank, say so in your result: that the set was ranked by TypeSafe with the question you asked, how many items you opened and how many you left. A reader must be able to tell a set read in full from a set ranked.

## When the run fails

A refusal for a missing key, or a failed call, leaves you where you were: choose what to read without it and continue. Do not retry in a loop, and do not report the task as blocked.
