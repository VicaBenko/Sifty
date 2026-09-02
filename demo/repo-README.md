# Sifty

**Clean up a photo library by describing what you want gone.**

Photo galleries let you search by date, face and place — never by "that whiteboard from the course."
Sifty lets you write the description instead: *"documents on a desk"*, *"screenshots of receipts"* —
and it finds those photos for you.

**Live demo:** https://USERNAME.github.io/sifty/

## How it works

1. **Index once.** Every photo is read a single time and stored as a structured record — an object list plus a caption.
2. **Query as an intersection.** A description is broken into predicates and matched exactly against that index, with a full-text channel over the captions as a second signal. "Paper, pen and iPad" is a precise query, not a similarity guess. Each result shows which channel matched it and how confident it is.
3. **Quarantine, then confirm.** Matches are **copied** — never moved — into a quarantine folder. You review it like any other folder, take back anything you want to keep, and only the remainder is deleted, in place, after an explicit confirmation.

Nothing is uploaded and there is no account. The demo gallery is 128 public images from the
COCO 2017 dataset; photos you add yourself are tagged in your browser with TensorFlow.js (COCO-SSD).

## Status

Final project from the Moshal Program – Israel AI workshop, built in three days and still in progress.
It is free to use and nothing is charged. Next up: a vocabulary wider than COCO's 80 object classes,
indexing a real folder on disk, and saved queries that run on new photos.
