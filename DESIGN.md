# UI design tokens (from `references/`)

Source: four ProfitPilot-style mobile finance mockups plus type and colour boards. The brief's own look wins, so follow it rather than inventing a new one.

**Colour:** mint `#C8E9CA` (primary surface/accent), sky `#87DCFB` (secondary accent, actions), charcoal `#201F1F` (text, dark cards, primary buttons), white `#FFFFFF` (page and cards), neutral grey page tint for contrast with white cards. Green `+` and red `-` only for signed amounts.

**Type:** SF Pro Display (fallback: system-ui, Inter). Weights thin to bold used within one headline, e.g. light "Your" over bold "Financial". Tight negative tracking on large display text; numerals large and light. Card/account numbers in a rounded monospace.

**Shape:** very large radii (cards ~28px, pills fully rounded), black pill primary buttons, frosted/glass floating cards, soft diffuse shadows, thin outline line-art for icons, floating pill bottom nav, a 7-point star mark and a single hand-drawn curl as ornaments.

**Layout:** generous white space, one hero number per card, stacked overlapping cards, transaction-style lists (icon chip, label, time, signed amount). Dark starfield backdrop only for showcase surfaces.

**Mapping to transact3:** cost-breakdown card = mint card; selected/cheapest path = charcoal card; actions and links = sky; each cost term (C_gas ... C_reg) is a list row with signed amount. Always show a `Synthetic data` chip while `source_kind=synthetic`, and the research disclaimer in the footer.
