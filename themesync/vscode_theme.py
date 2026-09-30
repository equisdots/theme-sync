# ═══════════════════════════════════════════════════════════════════════════
# vscode_theme — intelligent base16 → VS Code color mapping.
#
# Generates `workbench.colorCustomizations`, `editor.tokenColorCustomizations`
# and `editor.semanticTokenColorCustomizations` for ANY palette, including
# community/ and user-created ones. Nothing here is palette-specific: the
# mapping is derived from the palette's base16 slots (optionally refined by
# its `roles`, using the same role names as the shell: accent, blue, green,
# red, mauve, teal...).
#
# Rules:
#   · surfaces are mixed from background→foreground (works for dark AND light
#     palettes: mixing toward the fg always increases separation),
#   · selection/hover derive from the accent,
#   · every foreground is contrast-checked (WCAG) against its background,
#   · text on accents picks whichever of bg/fg contrasts most.
# ═══════════════════════════════════════════════════════════════════════════
from __future__ import annotations

from .core import best_fg, contrast, luminance, mix, palette_bg_fg, palette_hex

MIN_CONTRAST = 4.5


def _readable(bg: str, prefer: str) -> str:
    """`prefer` if it clears WCAG AA on `bg`, else the best of white/black."""
    if contrast(bg, prefer) >= MIN_CONTRAST:
        return prefer
    return max([prefer, "#ffffff", "#000000"], key=lambda c: contrast(bg, c))


def build(pal: dict) -> dict:
    """All three customizations for a palette dict (base16 + optional roles)."""
    bg, fg_raw = palette_bg_fg(pal)
    fg = _readable(bg, fg_raw)
    dark = luminance(bg) <= 0.5
    roles = pal.get("roles") or {}

    def slot(n: int) -> str:
        return palette_hex(pal, "color%d" % n)

    def role(name: str, fallback: str) -> str:
        value = roles.get(name)
        return value if isinstance(value, str) and value.strip() else fallback

    red = role("red", slot(1))
    green = role("green", slot(2))
    yellow = role("yellow", slot(3))
    blue = role("blue", slot(4))
    mauve = role("mauve", slot(5))
    cyan = role("teal", slot(6))
    peach = role("peach", slot(9))
    pink = role("pink", slot(13))
    accent = role("accent", mauve)
    accent2 = role("accent2", blue)

    dim = mix(fg, bg, 0.35)
    faint = mix(fg, bg, 0.55)
    s0 = mix(bg, fg, 0.05)
    s1 = mix(bg, fg, 0.10)
    s2 = mix(bg, fg, 0.17)
    overlay = mix(bg, fg, 0.30)
    sel = mix(bg, accent, 0.35)
    sel_inactive = mix(bg, accent, 0.18)
    hover = mix(bg, fg, 0.09)
    shadow = "#00000080" if dark else "#00000026"
    on_accent = best_fg(accent, bg, fg)
    on_accent2 = best_fg(accent2, bg, fg)

    workbench = {
        # base
        "foreground": fg,
        "descriptionForeground": dim,
        "errorForeground": red,
        "icon.foreground": fg,
        "focusBorder": accent,
        "selection.background": sel,
        "widget.border": s1,
        "widget.shadow": shadow,
        "sash.hoverBorder": accent,

        # editor surface
        "editor.background": bg,
        "editor.foreground": fg,
        "editorCursor.foreground": accent,
        "editor.lineHighlightBackground": s0,
        "editor.lineHighlightBorder": "#00000000",
        "editor.selectionBackground": sel,
        "editor.inactiveSelectionBackground": sel_inactive,
        "editor.selectionHighlightBackground": mix(bg, accent, 0.25),
        "editor.selectionHighlightBorder": "#00000000",
        "editor.wordHighlightBackground": mix(bg, blue, 0.22),
        "editor.wordHighlightStrongBackground": mix(bg, accent2, 0.22),
        "editor.findMatchBackground": mix(bg, yellow, 0.45),
        "editor.findMatchHighlightBackground": mix(bg, yellow, 0.25),
        "editor.findRangeHighlightBackground": s0,
        "editor.rangeHighlightBackground": s0,
        "editor.hoverHighlightBackground": mix(bg, accent, 0.15),
        "editorLineNumber.foreground": faint,
        "editorLineNumber.activeForeground": accent,
        "editorIndentGuide.background1": s1,
        "editorIndentGuide.activeBackground1": overlay,
        "editorWhitespace.foreground": s2,
        "editorRuler.foreground": s1,
        "editorCodeLens.foreground": faint,
        "editorLink.activeForeground": blue,
        "editorBracketMatch.background": mix(bg, accent, 0.20),
        "editorBracketMatch.border": accent,
        "editorBracketHighlight.foreground1": red,
        "editorBracketHighlight.foreground2": yellow,
        "editorBracketHighlight.foreground3": green,
        "editorBracketHighlight.foreground4": cyan,
        "editorBracketHighlight.foreground5": blue,
        "editorBracketHighlight.foreground6": mauve,
        "editorGutter.background": bg,
        "editorGutter.modifiedBackground": yellow,
        "editorGutter.addedBackground": green,
        "editorGutter.deletedBackground": red,
        "editorError.foreground": red,
        "editorWarning.foreground": yellow,
        "editorInfo.foreground": blue,
        "editorHint.foreground": cyan,
        "editorOverviewRuler.border": s1,
        "editorOverviewRuler.errorForeground": red,
        "editorOverviewRuler.warningForeground": yellow,
        "editorOverviewRuler.infoForeground": blue,

        # widgets
        "editorWidget.background": s0,
        "editorWidget.foreground": fg,
        "editorWidget.border": s1,
        "editorHoverWidget.background": s0,
        "editorHoverWidget.foreground": fg,
        "editorHoverWidget.border": s1,
        "editorSuggestWidget.background": s0,
        "editorSuggestWidget.foreground": fg,
        "editorSuggestWidget.border": s1,
        "editorSuggestWidget.selectedBackground": sel,
        "editorSuggestWidget.highlightForeground": accent,
        "editorSuggestWidget.focusHighlightForeground": accent2,
        "editorSuggestWidgetStatus.foreground": dim,
        "editorMarkerNavigation.background": s0,
        "editorMarkerNavigationError.background": red,
        "editorMarkerNavigationWarning.background": yellow,
        "editorMarkerNavigationInfo.background": blue,
        "problemsErrorIcon.foreground": red,
        "problemsWarningIcon.foreground": yellow,
        "problemsInfoIcon.foreground": blue,

        # workbench chrome
        "activityBar.background": s0,
        "activityBar.foreground": fg,
        "activityBar.inactiveForeground": faint,
        "activityBar.border": s1,
        "activityBar.activeBorder": accent,
        "activityBar.activeBackground": mix(bg, accent, 0.14),
        "activityBar.dropBorder": accent,
        "activityBarBadge.background": accent,
        "activityBarBadge.foreground": on_accent,
        "sideBar.background": bg,
        "sideBar.foreground": fg,
        "sideBar.border": s1,
        "sideBarTitle.foreground": fg,
        "sideBarSectionHeader.background": s0,
        "sideBarSectionHeader.foreground": fg,
        "sideBarSectionHeader.border": s1,
        "panel.background": bg,
        "panel.border": s1,
        "panelTitle.activeForeground": fg,
        "panelTitle.activeBorder": accent,
        "panelTitle.inactiveForeground": faint,
        "panelInput.border": s1,
        "panelSection.border": s1,
        "panelSectionHeader.background": s0,
        "statusBar.background": s1,
        "statusBar.foreground": fg,
        "statusBar.border": s1,
        "statusBar.noFolderBackground": s0,
        "statusBarItem.hoverBackground": s2,
        "statusBarItem.remoteBackground": accent,
        "statusBarItem.remoteForeground": on_accent,
        "statusBarItem.errorBackground": red,
        "statusBarItem.errorForeground": best_fg(red, bg, fg),
        "statusBarItem.warningBackground": yellow,
        "statusBarItem.warningForeground": best_fg(yellow, bg, fg),
        "titleBar.activeBackground": s0,
        "titleBar.activeForeground": fg,
        "titleBar.inactiveBackground": s0,
        "titleBar.inactiveForeground": faint,
        "titleBar.border": s1,
        "menu.background": s0,
        "menu.foreground": fg,
        "menu.border": s1,
        "menu.selectionBackground": sel,
        "menu.selectionForeground": fg,
        "menu.separatorBackground": s1,
        "menubar.selectionBackground": s1,
        "menubar.selectionForeground": fg,

        # tabs / groups
        "editorGroup.border": s1,
        "editorGroup.dropBackground": sel_inactive,
        "editorGroupHeader.tabsBackground": s0,
        "editorGroupHeader.tabsBorder": s1,
        "editorGroupHeader.noTabsBackground": s0,
        "tab.activeBackground": bg,
        "tab.activeForeground": fg,
        "tab.activeBorderTop": accent,
        "tab.activeBorder": "#00000000",
        "tab.inactiveBackground": s0,
        "tab.inactiveForeground": faint,
        "tab.border": s1,
        "tab.hoverBackground": s1,
        "tab.unfocusedActiveBackground": s0,
        "tab.unfocusedInactiveForeground": faint,
        "tab.lastPinnedBorder": s1,

        # lists / inputs / buttons
        "list.activeSelectionBackground": sel,
        "list.activeSelectionForeground": fg,
        "list.inactiveSelectionBackground": mix(bg, fg, 0.12),
        "list.inactiveSelectionForeground": fg,
        "list.hoverBackground": hover,
        "list.hoverForeground": fg,
        "list.focusBackground": sel,
        "list.focusForeground": fg,
        "list.focusOutline": accent,
        "list.highlightForeground": accent,
        "list.errorForeground": red,
        "list.warningForeground": yellow,
        "list.deemphasizedForeground": faint,
        "input.background": s0,
        "input.foreground": fg,
        "input.border": s1,
        "input.placeholderForeground": faint,
        "inputOption.activeBorder": accent,
        "inputOption.activeBackground": mix(bg, accent, 0.20),
        "inputValidation.errorBackground": mix(bg, red, 0.25),
        "inputValidation.errorBorder": red,
        "inputValidation.warningBackground": mix(bg, yellow, 0.25),
        "inputValidation.warningBorder": yellow,
        "inputValidation.infoBackground": mix(bg, blue, 0.25),
        "inputValidation.infoBorder": blue,
        "dropdown.background": s0,
        "dropdown.foreground": fg,
        "dropdown.border": s1,
        "button.background": accent,
        "button.foreground": on_accent,
        "button.hoverBackground": mix(accent, fg, 0.15),
        "button.secondaryBackground": s1,
        "button.secondaryForeground": fg,
        "badge.background": accent,
        "badge.foreground": on_accent,
        "progressBar.background": accent,
        "checkbox.background": s0,
        "checkbox.foreground": fg,
        "checkbox.border": s1,

        # scrollbars / minimap / diff / misc
        "scrollbar.shadow": shadow,
        "scrollbarSlider.background": mix(bg, fg, 0.18),
        "scrollbarSlider.hoverBackground": mix(bg, fg, 0.28),
        "scrollbarSlider.activeBackground": mix(bg, fg, 0.35),
        "minimap.background": bg,
        "minimap.selectionHighlight": sel,
        "minimap.findMatchHighlight": mix(bg, yellow, 0.45),
        "quickInput.background": s0,
        "quickInput.foreground": fg,
        "quickInputList.focusBackground": sel,
        "quickInputList.focusForeground": fg,
        "peekView.border": accent,
        "peekViewEditor.background": s0,
        "peekViewEditor.matchHighlightBackground": mix(bg, yellow, 0.30),
        "peekViewResult.background": bg,
        "peekViewResult.selectionBackground": sel,
        "peekViewTitle.background": s0,
        "breadcrumb.foreground": dim,
        "breadcrumb.focusForeground": fg,
        "breadcrumb.activeSelectionForeground": accent,
        "breadcrumbPicker.background": s0,
        "gitDecoration.addedResourceForeground": green,
        "gitDecoration.modifiedResourceForeground": yellow,
        "gitDecoration.deletedResourceForeground": red,
        "gitDecoration.untrackedResourceForeground": green,
        "gitDecoration.ignoredResourceForeground": faint,
        "gitDecoration.conflictingResourceForeground": red,
        "diffEditor.insertedTextBackground": mix(bg, green, 0.18),
        "diffEditor.removedTextBackground": mix(bg, red, 0.18),
        "diffEditor.insertedLineBackground": mix(bg, green, 0.10),
        "diffEditor.removedLineBackground": mix(bg, red, 0.10),
        "notifications.background": s0,
        "notifications.foreground": fg,
        "notifications.border": s1,
        "notificationCenterHeader.background": s1,
        "notificationLink.foreground": blue,
        "extensionButton.prominentBackground": accent,
        "extensionButton.prominentForeground": on_accent,
        "extensionBadge.remoteBackground": accent,
        "extensionBadge.remoteForeground": on_accent,
        "settings.headerForeground": fg,
        "settings.modifiedItemIndicator": accent,
        "textLink.foreground": blue,
        "textLink.activeForeground": cyan,
        "textPreformat.foreground": peach,
        "textBlockQuote.background": s0,
        "textBlockQuote.border": s1,
        "textCodeBlock.background": s0,
        "pickerGroup.border": s1,
        "pickerGroup.foreground": accent,
        "debugToolBar.background": s0,
        "debugConsole.infoForeground": blue,
        "debugConsole.warningForeground": yellow,
        "debugConsole.errorForeground": red,
        "debugConsole.sourceForeground": dim,
        "debugIcon.breakpointForeground": red,
        "debugIcon.breakpointCurrentStackframeForeground": yellow,
        "ports.iconRunningProcessForeground": green,
        "testing.iconPassed": green,
        "testing.iconFailed": red,
        "testing.iconQueued": yellow,
        "testing.iconUnset": faint,
        "testing.iconSkipped": pink,
        "charts.red": red,
        "charts.blue": blue,
        "charts.yellow": yellow,
        "charts.orange": peach,
        "charts.green": green,
        "charts.purple": mauve,
        "charts.foreground": fg,
        "charts.lines": dim,

        # terminal
        "terminal.background": bg,
        "terminal.foreground": fg,
        "terminalCursor.foreground": accent,
        "terminalCursor.background": bg,
        "terminal.selectionBackground": sel,
        "terminal.inactiveSelectionBackground": sel_inactive,
        "terminal.ansiBlack": slot(0),
        "terminal.ansiRed": slot(1),
        "terminal.ansiGreen": slot(2),
        "terminal.ansiYellow": slot(3),
        "terminal.ansiBlue": slot(4),
        "terminal.ansiMagenta": slot(5),
        "terminal.ansiCyan": slot(6),
        "terminal.ansiWhite": slot(7),
        "terminal.ansiBrightBlack": slot(8),
        "terminal.ansiBrightRed": slot(9),
        "terminal.ansiBrightGreen": slot(10),
        "terminal.ansiBrightYellow": slot(11),
        "terminal.ansiBrightBlue": slot(12),
        "terminal.ansiBrightMagenta": slot(13),
        "terminal.ansiBrightCyan": slot(14),
        "terminal.ansiBrightWhite": slot(15),
    }

    token_rules = [
        {"scope": ["comment", "punctuation.definition.comment"], "settings": {"foreground": faint, "fontStyle": "italic"}},
        {"scope": ["keyword", "storage", "storage.type", "storage.modifier", "keyword.control", "keyword.operator.new", "variable.language"], "settings": {"foreground": mauve}},
        {"scope": ["string", "string.quoted", "punctuation.definition.string"], "settings": {"foreground": green}},
        {"scope": ["string.regexp", "constant.regexp"], "settings": {"foreground": cyan}},
        {"scope": ["constant.numeric", "constant.language", "constant.character", "support.constant", "constant.other"], "settings": {"foreground": peach}},
        {"scope": ["entity.name.function", "support.function", "meta.function-call", "meta.function-call.generic"], "settings": {"foreground": blue}},
        {"scope": ["entity.name.type", "entity.name.class", "entity.name.namespace", "support.type", "support.class", "entity.other.inherited-class"], "settings": {"foreground": cyan}},
        {"scope": ["entity.name.tag", "punctuation.definition.tag"], "settings": {"foreground": red}},
        {"scope": ["entity.other.attribute-name", "meta.object-literal.key"], "settings": {"foreground": yellow}},
        {"scope": ["variable", "variable.other", "meta.definition.variable"], "settings": {"foreground": fg}},
        {"scope": ["variable.parameter"], "settings": {"foreground": peach}},
        {"scope": ["meta.property-name", "variable.other.property", "support.variable.property"], "settings": {"foreground": blue}},
        {"scope": ["keyword.operator", "punctuation.separator", "punctuation.terminator"], "settings": {"foreground": dim}},
        {"scope": ["markup.heading", "markup.heading entity.name"], "settings": {"foreground": accent, "fontStyle": "bold"}},
        {"scope": ["markup.bold"], "settings": {"fontStyle": "bold"}},
        {"scope": ["markup.italic"], "settings": {"fontStyle": "italic"}},
        {"scope": ["markup.inserted", "markup.inserted.git_gutter"], "settings": {"foreground": green}},
        {"scope": ["markup.deleted", "markup.deleted.git_gutter"], "settings": {"foreground": red}},
        {"scope": ["markup.changed"], "settings": {"foreground": yellow}},
        {"scope": ["markup.quote"], "settings": {"foreground": dim, "fontStyle": "italic"}},
        {"scope": ["markup.raw", "markup.inline.raw"], "settings": {"foreground": green}},
        {"scope": ["markup.link", "markup.underline.link"], "settings": {"foreground": blue}},
        {"scope": ["invalid", "invalid.illegal"], "settings": {"foreground": red}},
        {"scope": ["invalid.deprecated"], "settings": {"foreground": peach}},
    ]

    semantic = {
        "enabled": True,
        "rules": {
            "keyword": {"foreground": mauve},
            "operator": {"foreground": accent},
            "namespace": {"foreground": cyan},
            "type": {"foreground": cyan},
            "class": {"foreground": cyan},
            "struct": {"foreground": cyan},
            "interface": {"foreground": cyan},
            "enum": {"foreground": cyan},
            "enumMember": {"foreground": peach},
            "function": {"foreground": blue},
            "method": {"foreground": blue},
            "property": {"foreground": blue},
            "variable": {"foreground": fg},
            "parameter": {"foreground": peach},
            "string": {"foreground": green},
            "number": {"foreground": peach},
            "comment": {"foreground": faint, "italic": True},
            "decorator": {"foreground": accent2},
            "*.deprecated": {"foreground": peach, "strikethrough": True},
            "*.declaration": {"bold": False},
        },
    }

    return {"workbench": workbench, "tokenRules": token_rules, "semantic": semantic}
