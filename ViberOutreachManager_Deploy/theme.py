# =============================================================================
#  theme.py  —  Cyber-Industrial Dark Mode Design Tokens
#  CRM UI/UX Overhaul  |  CustomTkinter
# =============================================================================
#
#  Palette Concept: "Deep Work Terminal"
#  Inspired by Linear, Vercel Dashboard, and VS Code's darkest variant.
#  No pure blacks, no gradients — just rich layered grays with one sharp
#  Viber Purple accent that cuts through the darkness.
# =============================================================================


# ── Backgrounds ───────────────────────────────────────────────────────────────

BG_ROOT          = "#1A1A1A"   # Main window canvas — deepest layer
BG_NAV           = "#7360F2"   # Top nav bar  (Viber Purple takeover)
BG_NAV_ALT       = "#252526"   # Alternative nav: muted gunmetal (swap if subtle is preferred)
BG_ROW           = "#252526"   # Data row frame background
BG_ROW_HOVER     = "#2E2E30"   # Row hover state (subtle lift)
BG_DROPDOWN      = "#2E2E30"   # OptionMenu background
BG_DROPDOWN_HOVER= "#3A3A3D"   # OptionMenu hover / open state
BG_MODAL         = "#1E1E1E"   # Modal / popover surface


# ── Accent Colors ─────────────────────────────────────────────────────────────

ACCENT_PRIMARY   = "#7360F2"   # Viber Purple  — primary actions, active states
ACCENT_HOVER     = "#8B7CF6"   # Lightened purple for button hover
ACCENT_PRESSED   = "#5B4BD4"   # Darkened purple for button press / active
ACCENT_MUTED     = "#3D3360"   # Very muted purple — subtle highlights, borders


# ── Status Colors ─────────────────────────────────────────────────────────────

STATUS_FALSE_BG      = "#2A2A2A"   # "Not Contacted" pill — dark hollow
STATUS_FALSE_BORDER  = "#3F3F3F"   # Border for the hollow pill
STATUS_FALSE_TEXT    = "#6B6B6B"   # Muted gray text — de-emphasised

STATUS_TRUE_BG       = "#0D3326"   # "Contacted" pill — deep emerald base
STATUS_TRUE_BORDER   = "#22C55E"   # Vibrant emerald border glow
STATUS_TRUE_TEXT     = "#22C55E"   # Emerald text — high contrast on dark base
STATUS_TRUE_HOVER    = "#16A34A"   # Slightly deeper on hover


# ── Filter / Nav Buttons ──────────────────────────────────────────────────────

FILTER_DEFAULT_BG    = "#8472F5"    # Slightly lighter purple — ghost button on purple nav
FILTER_DEFAULT_TEXT  = "#E0DEFF"    # Soft lavender white
FILTER_ACTIVE_BG     = "#FFFFFF"    # Solid white pill when active
FILTER_ACTIVE_TEXT   = "#7360F2"    # Purple text on white — crisp inversion

SYNC_BTN_BG          = "#FFFFFF"    # Sync button: white on purple nav
SYNC_BTN_TEXT        = "#7360F2"    # Purple label — mirrors the inversion pattern
SYNC_BTN_HOVER       = "#F0EDFF"    # Warm off-white on hover


# ── Typography ────────────────────────────────────────────────────────────────

FONT_FAMILY          = "Helvetica Neue"   # Falls back gracefully on all platforms
FONT_FAMILY_FALLBACK = "Helvetica"

TEXT_PRIMARY         = "#F0F0F0"    # Main body text
TEXT_SECONDARY       = "#9A9A9A"    # Labels, placeholder text
TEXT_MUTED           = "#5A5A5A"    # Disabled or de-emphasised
TEXT_ON_ACCENT       = "#FFFFFF"    # Text sitting on purple backgrounds

FONT_SIZE_XS   = 10
FONT_SIZE_SM   = 12
FONT_SIZE_BASE = 13
FONT_SIZE_MD   = 14
FONT_SIZE_LG   = 16
FONT_SIZE_XL   = 20

FONT_WEIGHT_NORMAL = "normal"
FONT_WEIGHT_BOLD   = "bold"


# ── Spacing & Geometry ────────────────────────────────────────────────────────

PAD_XS   = 4
PAD_SM   = 8
PAD_BASE = 10
PAD_MD   = 15
PAD_LG   = 20
PAD_XL   = 28

CORNER_RADIUS_SM   = 6    # Tags, small chips
CORNER_RADIUS_BASE = 8    # Row frames, cards
CORNER_RADIUS_LG   = 12   # Modals, large panels
CORNER_RADIUS_PILL = 20   # Pill-shaped status/action buttons

NAV_HEIGHT         = 52   # px — top nav bar fixed height
ROW_HEIGHT         = 54   # px — data row min height
DROPDOWN_WIDTH     = 120  # px — SIM OptionMenu width


# ── Borders & Dividers ────────────────────────────────────────────────────────

BORDER_SUBTLE  = "#2F2F2F"   # Between rows, very faint
BORDER_DEFAULT = "#3A3A3A"   # Card outlines, input borders
BORDER_FOCUS   = "#7360F2"   # Focused input ring (reuses accent)


# ── Convenience: Pre-built font tuples (for CTk `font=` param) ───────────────

def font(size=FONT_SIZE_BASE, weight=FONT_WEIGHT_NORMAL):
    """Return a (family, size, weight) tuple for use in CTk widgets."""
    return (FONT_FAMILY, size, weight)

FONT_BODY    = font(FONT_SIZE_BASE)
FONT_BODY_B  = font(FONT_SIZE_BASE, FONT_WEIGHT_BOLD)
FONT_LABEL   = font(FONT_SIZE_SM)
FONT_NAV     = font(FONT_SIZE_MD, FONT_WEIGHT_BOLD)
FONT_STATUS  = font(FONT_SIZE_SM, FONT_WEIGHT_BOLD)
FONT_HEADING = font(FONT_SIZE_XL, FONT_WEIGHT_BOLD)
