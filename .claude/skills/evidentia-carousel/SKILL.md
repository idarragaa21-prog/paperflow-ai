---
name: evidentia-carousel
description: Build premium EVIDENTIA Instagram carousels — an expert critical analysis of a scientific paper, rendered in the real @evidentia_co brand (navy/gold, Montserrat + Playfair). Use when asked to create, build, design, author, or render an EVIDENTIA carousel, an Instagram carousel for @evidentia_co, or branded slides that critically analyze a medical / scientific article. Driver: build_deck.py → render.sh → 1080×1350 PNGs.
---

# EVIDENTIA — carousel generator

Produces publication-ready Instagram carousels (1080×1350, exported 2× = 2160×2700)
that read like a high-impact journal adapted to Instagram: **an expert critical
analysis of one scientific paper**, in the authentic @evidentia_co visual system.

**How it's driven:** a Python script emits one self-contained HTML file per slide
into `out/`; headless Chromium screenshots each to PNG. All paths below are relative
to this skill directory (`.claude/skills/evidentia-carousel/`).

The pipeline is proven end-to-end in this repo — running it reproduces the reference
deck (RECOT 2024 fibular-malleolus carousel, 13 slides).

---

## Act as (the brief)

Adopt **all** of these voices at once — this is what makes the output elite:

- **Creative Director** of a premium international branding agency.
- **Senior designer** of viral, editorial Instagram carousels.
- **Digital-marketing strategist** for medical / scientific brands.
- **Scientific-storytelling copywriter.**
- **Peer reviewer / journal editor** (Lancet, JBJS, Bone & Joint, JAAOS level).
- **Subspecialty clinician** for the paper's topic.
- **Epidemiologist** fluent in PRISMA, GRADE, RoB 2, ROBINS-I, AMSTAR 2.

Mission: teach **evidence-based medicine applied to practice**. A reader should
think *"this account analyses the literature at a level above everyone else."*
Not a summary. Not a translation. A **critical discussion**.

---

## The process (do these in order)

1. **Get the paper — from PubMed, never Wikipedia.** Use the PubMed tools
   (`search_articles`, `convert_article_ids`, `get_full_text_article`) or the
   publisher's open-access page. Read it **completely**: objective, design, level
   of evidence, population, intervention/comparator, results, conclusions,
   limitations, strengths, bias, applicability. **Never cite Wikipedia as a source.**
2. **Appraise it like a reviewer.** Don't accept conclusions. Ask: are they backed
   by the data? Risk of bias? Recommendations too strong for the evidence level?
   What's missing? How does it compare to newer literature? What would actually
   change in practice? The declared "Level of evidence" is often inflated (a
   narrative review is Level V regardless of its label) — say so.
3. **Source the paper's real figures** (algorithm, radiographs, CT) from the OA
   article, downscale, and **credit them on every slide** ("Tomada de … et al.,
   <journal> <year>"). Respect the license (e.g. CC BY-NC-ND → educational,
   non-commercial, attributed).
4. **Generate brand illustrations if needed** (anatomy, mechanism) with Higgsfield
   `generate_image` (model `nano_banana_pro`) prompted in the brand palette. Import
   a reference with `media_import_url`, poll with `job_display`. NOTE: **video
   (`generate_video`) needs a paid Higgsfield plan**; image generation works on the
   free tier.
5. **Author the deck** — edit the CONTENT block of `build_deck.py` (see below).
6. **Render** — `python3 build_deck.py && bash render.sh`.
7. **Package** — write an Instagram caption (expert tone, ends on a debate question,
   with the source line + ~12 hashtags) and the slide order.

---

## The slide arc (13, adapt freely)

1. **Hook** (cover) — a provocative one-liner; no article title. Forces the swipe.
2. **The article** — identity card: real title, authors, journal, DOI, license, declared level of evidence.
3. **Anatomy** — the structures you must know (real illustration + labels).
4. **Biomechanics** — *why* it behaves as it does (the mechanism the paper hinges on).
5. **The design** (epidemiologist) — what kind of study is this, really? What that means.
6. **Figure capture** — the paper's core figure (e.g. its algorithm), with a critical note.
7. **The one clinical message** — the single most important takeaway.
8–10. **Figure captures** — the key evidence images, each with a sharp note.
11. **The uncomfortable datum** (stat) — one number that reframes the debate.
12. **Apply it** — a checklist: what you'd do differently tomorrow.
13. **Conclusion + question** — the message *after* critique (not the authors'), ending on a
    question that starts a real debate among specialists.

## Copy rules

- Statement slides: keep the visible headline short (≈ ≤ 15 words), readable in
  < 10 s. Depth lives across the deck, not in one wall of text.
- Expert tone, **never influencer**. No sensationalism.
- **Never** write "dale like / comparte / síguenos". End on a smart debate question.
- Captions, figure credits and labels are design furniture — they don't count
  against the "short headline" rule.

## Brand system (already implemented in `build_deck.py` + `orn.py`)

- **Colors:** navy `#17294D`, gold `#BE9B49`, warm white `#F8F6F1`, red `#C0272D`
  (emphasis/negation only), body `#2B3A57`.
- **Type:** Montserrat (heavy display headlines), Playfair Display (EVIDENTIA
  wordmark), EB Garamond (serif body/subtitles).
- **Furniture:** the `—·EVIDENTIA·—` top lockup, navy corner blobs + gold dot-grids
  + thin gold circles, the gold diamond divider, the bulb-magnifier icon, and the
  bottom EVIDENTIA wordmark with gold underline + slide counter + progress bar.
- Slide `kind`s: `cover` / `statement` / `stat` / `closing` are centered;
  `content` is top-aligned (for figures, checklists, two-column dossiers).
  Helpers: `add(body, dark, kind)`, `cap(img, label, note, rad=True)` (figure frame),
  `dvd(width)` (diamond rule), CSS classes `kick / h-hero|xl|lg|md / sub / lead /
  idcard / cols2 / anatrow / rows / stat / qbox`.

---

## Run (agent path)

Prerequisites: a Chromium build (this environment ships one under
`/opt/pw-browsers/`) and Python 3 with Pillow (`pip install Pillow`, only needed if
you (re)process images). Fonts are bundled in `fonts/` and installed by `render.sh`;
Montserrat is embedded as base64 in the CSS.

```bash
cd .claude/skills/evidentia-carousel
python3 build_deck.py     # writes out/slide-01..NN.html
bash render.sh            # installs fonts, screenshots each -> out/slide-*.png (2160×2700)
```

Output: `out/slide-*.png`, Instagram-ready. Inspect them (open/READ the PNGs) before
delivering — a slide that overflows or lost a font is only visible by looking.

## Authoring a NEW carousel

1. Put the new article's figures / illustrations in `example_assets/` (or a new
   folder) and point `FIG` / `ANAT` / `LIG` at them (top of `build_deck.py`).
2. Replace the `add(f'''…''', kind=…)` calls in the CONTENT section with your
   slides, following the arc above. Set `TOTAL` to the slide count.
3. `python3 build_deck.py && bash render.sh`, then look at every `out/*.png`.

## Gotchas

- **Chromium screenshot sizing:** `--window-size=1080,1350 --force-device-scale-factor=2`
  yields exactly 2160×2700. Don't add `--headless=old`; use `--headless=new`.
- **Fonts must be installed before rendering**, or headlines silently fall back to a
  system serif. `render.sh` copies `fonts/*.ttf` to `~/.fonts` and runs `fc-cache -f`.
  Verify with `fc-list | grep -iE 'playfair|garamond'`.
- **Embed every asset** (images, fonts) as `data:` URIs — Chromium renders each HTML
  file in isolation with no server, so external/relative refs won't load.
- **The QR "nametag" gradient is NOT the brand.** @evidentia_co's Instagram QR uses
  Instagram's stock orange→pink→purple; the real palette is navy + gold + white
  (sampled from the logo badge and published carousels).
- **Higgsfield video is gated:** `generate_video` returns 403
  `job_minimum_basic_plan_required` on the free tier; `generate_image` works.
- **Posting:** there is no connected Instagram publishing integration here — deliver
  the PNGs + caption and let the user post via Meta Business Suite / the app.

## Troubleshooting

- `NameError: name 'LIG' is not defined` — you referenced an image var that isn't
  defined at the top of `build_deck.py`. Add it via `data_uri("example_assets/…")`.
- Headlines look like a plain serif, not the heavy geometric sans — fonts weren't
  installed; re-run `render.sh` (it installs them) or `fc-cache -f`.
- A slide's text overflows the canvas — shorten copy or reduce the `h-*` size / image
  width; there's no scrollbar, content just clips.
