---
id: IMP-010
type: imp
layer: evolution
home: evolution/implemented/decide-the-list-of-listings.md
title: Decide the list of listings
summary: Listings share the one listing counter and the book prints no list of listings
date: 2026-11-04
status: implemented
---

# Decide the list of listings

Papers II–VI keep 12 code listings in `listing` floats (`OPS-002`).
The book prints a list of figures and a list of tables and no list of listings; that part is settled.
**Decision:**

- Listings share the one `listing` counter whichever form carries them.
- Verified: inside `figure*` with `\captionsetup{type=listing}`, a plain `\caption` numbers from `listing`.
- The earlier `lstlisting` `caption=`-key form numbered from `lstlisting` and was removed (Paper III `5d3c63a`, Paper II `0b082d5`; parent `991ef8b` documents the convention).
- Both forms are documented in `OPS-002`.
- The book prints no list of listings; a reader who meets `Listing III.4` in the body has no list surface that locates it.
**Evidence:**

- `thesis/temp/thesis.lof` holds 51 lines and `thesis/temp/thesis.lot` 37 lines after `python3 thesis/build.py`.
- `thesis/temp/` holds no `thesis.lop`.
- The rendered PDF prints `List of Figures` and `List of Tables` in the front matter.
- `thesis/temp/thesis.txt` carries the labels `Listing II.1`, `Listing II.2`, and `Listing III.1` to `Listing III.10`.
- Paper II carries 2 listings and Paper III 10; Papers IV–VI carry none.
**Out of scope:**

- The listing float, its counter, and the global `\lstset` (`OPS-002`).
- The build gate and its reference page count (`VER-002`).
- The appendix page budget (`IMP-008`).