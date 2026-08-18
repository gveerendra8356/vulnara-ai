# Bundled fonts

Outfit, Inter, and JetBrains Mono, bundled locally so the app never depends
on a live network fetch for its own typography (see the comment in
`../../pubspec.yaml`'s `flutter: fonts:` block for the full "why").

Each file is the upstream variable-weight `.ttf` from Google's own font
repository (github.com/google/fonts), the same source `google_fonts`
itself would have downloaded at runtime:

- `Outfit.ttf`       <- ofl/outfit/Outfit[wght].ttf
- `Inter.ttf`         <- ofl/inter/Inter[opsz,wght].ttf
- `JetBrainsMono.ttf` <- ofl/jetbrainsmono/JetBrainsMono[wght].ttf

All three are licensed under the SIL Open Font License 1.1 -- see the
`OFL-*.txt` files in this directory (one per family, required by the
license's redistribution terms).

`pubspec.yaml` declares each family under multiple `weight:` entries
pointing at the same file -- the standard Flutter pattern for pinning
specific static instances out of a variable font -- covering every weight
actually used by `lib/theme/vulnara_theme.dart` and its callers (400/600/700
for Outfit, 400/500/600/700 for Inter, 400/700 for JetBrains Mono).
