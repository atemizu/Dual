#!/usr/bin/env python3
"""The hand resolutions for the move from Helium 0.18.3.1 to 0.20.1.1.

port_patch.py left conflicts in fourteen files, and Helium had moved two of
the places Dual changes into new files:
  - the vertical tab strip state controller is now an interface
    (vertical_tab_strip_state_controller.{h,cc}) with its body in
    vertical_tab_strip_state_controller_impl.{h,cc};
  - the browser layout settings left the appearance page for their own page
    (appearance_layout_page.{ts,html.ts}).
This records how each was settled, so the move can be repeated: run
port_patch.py, then this on its output.

  resolve_0.20.1.1.py <new stage> <new prepared Helium src>
"""
import re, shutil, sys
from pathlib import Path

STAGE, NEW = Path(sys.argv[1]), Path(sys.argv[2])
BLOCK = re.compile(r'<<<<<<< Dual\n(.*?)\|\|\|\|\|\|\| old Helium\n(.*?)=======\n(.*?)>>>>>>> new Helium\n', re.S)


def settle(name, *choices):
    """Replace the file's conflicts, in order. A choice is 'dual', 'helium',
    'both' (Dual's lines, then Helium's) or the text to put there."""
    path = STAGE / name
    text = path.read_text()
    blocks = BLOCK.findall(text)
    assert len(blocks) == len(choices), (name, len(blocks), len(choices))
    picks = iter(choices)

    def pick(match):
        ours, _, theirs = match.groups()
        choice = next(picks)
        return {'dual': ours, 'helium': theirs, 'both': ours + theirs}.get(choice, choice)

    path.write_text(BLOCK.sub(pick, text))


def edit(name, *pairs, source=None):
    """Replace, in the staged file (or first copy it from the new Helium
    source), each old text that must occur exactly once by its new text."""
    path = STAGE / name
    if source or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(NEW / name, path)
    text = path.read_text()
    for old, new in zip(pairs[::2], pairs[1::2]):
        assert text.count(old) == 1, (name, old[:80], text.count(old))
        text = text.replace(old, new)
    path.write_text(text)


def drop(name):
    """Dual no longer changes this file."""
    (STAGE / name).unlink()


# Helium removed its own TODO block; Dual's macOS feature override stays.
settle('chrome/browser/chrome_browser_field_trials.cc', '''\
#if BUILDFLAG(IS_MAC)
  // CATransactionV2 was disabled upstream for resize flicker (crbug.com/519500878).
  // Dual presents GPU IOSurfaces through the browser's local layer tree instead
  // of replacing remote CAContexts for every divider position. The browser can
  // then commit each new surface with both native pane frames.
  // Respect explicit command-line overrides for diagnostic comparisons.
  feature_overrides.DisableFeature(features::kCATransactionV2);
#endif

''')

# Helium now includes associated_receiver.h; Dual's receiver.h stays.
settle('third_party/blink/renderer/core/testing/fake_remote_frame_host.h', '''\
#include "mojo/public/cpp/bindings/associated_receiver.h"
#include "mojo/public/cpp/bindings/receiver.h"
''')

# Helium reformatted the file and dropped a node flag; Dual still passes paths
# relative to the build directory (rollup and vite refuse some absolute paths).
settle('components/helium_onboarding/BUILD.gn', '''\
  script = "//third_party/node/node.py"
  dist_dir = "$target_gen_dir/dist"

  args = [
    rebase_path("node_modules/vite/bin/vite.js", root_build_dir),
    "build",
    rebase_path(".", root_build_dir),
    "--outDir",
    rebase_path(dist_dir, "."),
  ]

  inputs = [
    "index.html",
    "src",
    "public",
    "package.json",
    "vite.config.ts",
    "svelte.config.js",
  ]

  deps = [ ":localized_strings" ]
  outputs = [ "$dist_dir/index.html" ]
''', '''\
  script = "//third_party/node/node.py"
  node_script = "./util/generate-grd.mts"
  dist_dir = "$target_gen_dir/dist"

  args = [
    rebase_path(node_script, root_build_dir),
    rebase_path(dist_dir, root_build_dir),
    rebase_path("$target_gen_dir/resources.grd", root_build_dir),
  ]

  inputs = [
    node_script,
    "$dist_dir/index.html",
  ]

  outputs = [ "$target_gen_dir/resources.grd" ]
  deps = [ ":build" ]
''')

# Chromium 156 split the ui target; tab_helpers and the macOS frame files
# became targets of their own. Dual's files go into the ui target itself.
settle('chrome/browser/ui/BUILD.gn', 'helium', 'helium')
edit('chrome/browser/ui/BUILD.gn',
     '''      "//chrome/browser/chrome_browser_interface_binders_webui_parts_desktop.cc",
''',
     '''      "//chrome/browser/chrome_browser_interface_binders_webui_parts_desktop.cc",
      "helium/helium_dual_limits.h",
      "helium/helium_dual_pane_state.cc",
      "helium/helium_dual_pane_state.h",
      "helium/helium_dual_state.h",
      "helium/helium_dual_tab_auto_close.cc",
      "helium/helium_dual_tab_auto_close.h",
''',
     '''      "views/helium/frame_corner_radius_mac.mm",
''',
     '''      "views/helium/frame_corner_radius_mac.mm",
      "helium/helium_dual_browser_mac.h",
      "helium/helium_dual_browser_mac.mm",
      "helium/helium_dual_window_host_mac.h",
      "helium/helium_dual_window_host_mac.mm",
''')

# Helium now also requires the model to be closing all its tabs.
settle('chrome/browser/ui/tabs/pinned_tab_service.cc', '''\
  bool last_window = TabStripModelObserver::CountObservedModels(this) == 1;
#if BUILDFLAG(IS_MAC)
  // Dual: the two panes of a window close one after the other. If they are
  // all that is open, this is the last window closing: save the pinned tabs
  // while both panes still have theirs.
  last_window = last_window ||
                (TabStripModelObserver::CountObservedModels(this) == 2 &&
                 helium_dual::IsClosingBothPanes(profile_, tab_strip_model));
#endif
  if (tab_strip_model->closing_all() && last_window) {
''')

# Helium dropped the upper bound of the reveal trigger.
settle('chrome/browser/ui/views/frame/browser_view.cc', '''\
#if BUILDFLAG(IS_MAC)
    // A Dual pane's strip faces the window edge along which the page's
    // scroll bar runs. Keep the scroll bar usable: only the outermost point
    // reveals here; the Dual host reveals from its resize band beyond it.
    if (helium_dual::IsPaneWindow(browser())) {
      return point.x() >= width() - 1 && point.x() < width();
    }
#endif
    return point.x() >= width() - kZenModeRevealTriggerThickness;
''')

# Helium rewrote the call with SafeInvoke; Dual's argument stays.
settle('chrome/browser/ui/views/frame/contents_web_view.cc', '''\
  if (!is_animating_bounds_ && use_default_deadline_when_animating_) {
    // Keep the renderer deadline while the surrounding native pane is
    // resizing, even when there is no side-panel/tab-strip animation.
    SafeInvoke(web_contents())
        .Then(&content::WebContents::GetRenderWidgetHostView)
        .Then(
            &content::RenderWidgetHostView::SetShouldUseDefaultDeadlineOnResize,
            /*enable=*/is_resizing_native_view_);
''')

# Two additions at the same place.
settle('chrome/browser/ui/views/frame/browser_frame_view_mac.mm', 'both')

settle('chrome/browser/ui/views/tabs/dragging/tab_drag_controller.cc', 'both', 'both')

# The strip's children now live in a content area view.
settle('chrome/browser/ui/views/frame/vertical_tab_strip_region_view.cc', '''\
#include "chrome/browser/ui/views/tabs/shared/tab_strip_flat_edge_button.h"
#include "components/vector_icons/vector_icons.h"
#include "ui/base/ui_base_features.h"
#if BUILDFLAG(IS_MAC)
#include "chrome/browser/browser_process.h"
#include "chrome/browser/ui/helium/helium_dual_browser_mac.h"
#include "chrome/browser/ui/helium/helium_dual_pane_state.h"
#endif
''', '''\
#if BUILDFLAG(IS_MAC)
  if (helium_dual::IsPaneWindow(browser_view->browser())) {
    auto button = std::make_unique<TabStripFlatEdgeButton>();
    button->SetCallback(base::BindRepeating([](BrowserView* view) {
      helium_dual::SetPaneHidden(view, true);
    }, base::Unretained(browser_view)));
    button->SetIconSize(16);
    button->SetCornerRadius(GetLayoutConstant(LayoutConstant::kVerticalTabCornerRadius));
    button->SetForegroundColorId(kColorToolbarButtonIconDisabled);
    // Use a real close glyph in every button state. Rotating an add glyph's
    // image view is not stable when LabelButton refreshes its hover image.
    button->UpdateIcon(ui::ImageModel::FromVectorIcon(
        features::IsRoundedIconsEnabled() ? vector_icons::kCloseIcon
                                          : vector_icons::kCloseOldIcon,
        kColorToolbarButtonIconDisabled, 16));
    // Toward the window's outer edge, like the strip itself.
    button->SetHorizontalAlignment(state_controller_->IsTabStripRightAligned()
                                       ? gfx::HorizontalAlignment::ALIGN_RIGHT
                                       : gfx::HorizontalAlignment::ALIGN_LEFT);
    button->SetLabelInsets(gfx::Insets::VH(4, 7), gfx::Insets::VH(4, 7));
    button->SetShouldShowLabel(false);
    button->SetPreferredSize(gfx::Size(-1, GetLayoutConstant(LayoutConstant::kVerticalTabHeight)));
    // Japanese when that is the app's language, English otherwise.
    const std::u16string hide_label =
        g_browser_process &&
                g_browser_process->GetApplicationLocale().starts_with("ja")
            ? u"タブを残してこの画面を非表示"
            : u"Hide this browser, keeping its tabs";
    button->SetTooltipText(hide_label);
    button->GetViewAccessibility().SetName(hide_label);
    button->SetProperty(views::kMarginsKey, gfx::Insets::VH(2, region_horizontal_padding));
    dual_hide_button_ = content_area_view_->AddChildView(std::move(button));
    // Hidden panes must reopen regardless of expand-on-hover preferences.
    AddPreTargetHandler(&click_handler_);
  }
#endif

  bottom_button_container_ = content_area_view_->AddChildView(
      std::make_unique<VerticalTabStripBottomContainer>(
''', '''\
int VerticalTabStripRegionView::GetDualFirstRowTop() const {
  const views::View* row = GetTabViewAt(0);
  if (!row || !row->GetVisible()) {
    return content_area_view_ ? content_area_view_->y() : 0;
  }
  // Measured from the strip's own top, so a hide button row above the tab
  // list is skipped.
  return views::View::ConvertRectToTarget(row, this, row->GetLocalBounds())
      .y();
}

void VerticalTabStripRegionView::SetFloatingStyleForLayout(FloatingStyle style,
                                                           int corner_radius,
                                                           bool below_toolbar) {
  if (floating_style_ == style && floating_corner_radius_ == corner_radius &&
      floating_below_toolbar_ == below_toolbar) {
''', '''\
#if BUILDFLAG(IS_MAC)
  if (dual_hide_button_) {
    const bool can_hide = helium_dual::CanHidePane(browser_view());
    dual_hide_button_->SetVisible(can_hide || helium_dual::IsPaneHidden(browser_view()));
    dual_hide_button_->SetEnabled(can_hide);
  }
#endif
  LayoutSuperclass<BaseTabStripRegionView>(this);

  // When animating the organizer panel in, as soon as it is visible, focus it.
  const bool organizer_panel_visible =
      organizer_panel_view_ && organizer_panel_view_->GetVisible();
  if (!organizer_panel_was_visible_ && organizer_panel_visible) {
    // This may also trigger expand-on-hover.
    GetFocusManager()->SetFocusedView(organizer_panel_view_);
  }
  organizer_panel_was_visible_ = organizer_panel_visible;
''')

# The vertical tab strip state controller became an interface; Dual's rules
# (a pane is always vertical, its strip faces the window's outer edge, and its
# width does not become every window's default) move to the implementation.
for name in ('chrome/browser/ui/tabs/vertical_tab_strip_state_controller.h',
             'chrome/browser/ui/tabs/vertical_tab_strip_state_controller.cc'):
    drop(name)
IMPL = 'chrome/browser/ui/tabs/vertical_tab_strip_state_controller_impl'
edit(IMPL + '.h',
     '#include "chrome/browser/ui/browser_window/public/global_browser_collection.h"\n',
     '#include "chrome/browser/ui/browser_window/public/global_browser_collection.h"\n'
     '#include "chrome/browser/ui/helium/helium_dual_state.h"\n',
     '  bool is_vertical_tabs_enabled_ = false;\n',
     '  // Dual: the pane this window is, if it is one.\n'
     '  HeliumDualRole helium_dual_role_ = HeliumDualRole::kNone;\n'
     '  bool is_vertical_tabs_enabled_ = false;\n')
text = (STAGE / (IMPL + '.h')).read_text()
# A private helper beside the others.
anchor = '  void OnLockDestroyed();\n'
assert text.count(anchor) == 1
(STAGE / (IMPL + '.h')).write_text(text.replace(
    anchor, anchor + '  bool IsVerticalLayoutEnabled() const;\n'))

LAYOUT_IS_VERTICAL = '''pref_service_->GetInteger(prefs::kHeliumLayout) ==
      std::to_underlying(HeliumLayoutType::kVertical);'''
edit(IMPL + '.cc',
     '#include "chrome/browser/ui/browser_element_identifiers.h"\n',
     '#include "chrome/browser/ui/browser_element_identifiers.h"\n'
     '#include "chrome/browser/ui/browser_init_state.h"\n',
     '''  pref_change_registrar_.Init(pref_service_);

  is_vertical_tabs_enabled_ =
      ''' + LAYOUT_IS_VERTICAL,
     '''  if (const auto* init_state = BrowserInitState::From(&*browser_window_)) {
    helium_dual_role_ = init_state->create_params().helium_dual_role;
  }
  pref_change_registrar_.Init(pref_service_);

  is_vertical_tabs_enabled_ = IsVerticalLayoutEnabled();''',
     '''::SetVerticalTabsEnabled(bool enabled) {
''',
     '''::SetVerticalTabsEnabled(bool enabled) {
  // Dual panes always use the vertical layout.
  if (helium_dual::IsPane(helium_dual_role_)) {
    return;
  }
''',
     '''::IsTabStripRightAligned() const {
  return pref_service_->GetBoolean(prefs::kHeliumVerticalRightAligned);
}''',
     '''::IsTabStripRightAligned() const {
  // Each pane's strip faces the outer edge of the shared window.
  if (helium_dual::IsPane(helium_dual_role_)) {
    return helium_dual_role_ == HeliumDualRole::kRight;
  }
  return pref_service_->GetBoolean(prefs::kHeliumVerticalRightAligned);
}

bool VerticalTabStripStateControllerImpl::IsVerticalLayoutEnabled() const {
  return helium_dual::IsPane(helium_dual_role_) ||
         pref_service_->GetInteger(prefs::kHeliumLayout) ==
             std::to_underlying(HeliumLayoutType::kVertical);
}''',
     '''    bool right_aligned) {
  pref_service_->SetBoolean''',
     '''    bool right_aligned) {
  if (helium_dual::IsPane(helium_dual_role_)) {
    return;
  }
  pref_service_->SetBoolean''',
     '''  const bool new_enabled =
      ''' + LAYOUT_IS_VERTICAL,
     '''  const bool new_enabled = IsVerticalLayoutEnabled();''',
     '''    is_vertical_tabs_enabled_ =
        pref_service_->GetInteger(prefs::kHeliumLayout) ==
        std::to_underlying(HeliumLayoutType::kVertical);''',
     '''    is_vertical_tabs_enabled_ = IsVerticalLayoutEnabled();''',
     '''::UpdatePrefService() {
''',
     '''::UpdatePrefService() {
  // Pane width/collapse state must not change other windows' defaults.
  if (helium_dual::IsPane(helium_dual_role_)) {
    return;
  }
''')

# The layout settings have a page of their own now. A Dual pane shows the
# layout it always has (vertical) with Dual's explanation, instead of the
# choice, and no right-alignment switch; nothing shows before that is known.
drop('chrome/browser/resources/settings/appearance_page/appearance_page.ts')
drop('chrome/browser/resources/settings/appearance_page/appearance_page.html.ts')
LAYOUT = 'chrome/browser/resources/settings/appearance_page/appearance_layout_page'
edit(LAYOUT + '.ts',
     "import {loadTimeData} from '../i18n_setup.js';\n",
     "import {loadTimeData} from '../i18n_setup.js';\n\n"
     "import {AppearanceBrowserProxyImpl} from './appearance_browser_proxy.js';\n",
     '      browserLayoutPref_: {type: Object},\n',
     '      browserLayoutPref_: {type: Object},\n'
     '      heliumDualPaneMode_: {type: Boolean},\n',
     '''  protected accessor browserLayoutPref_: PrefObject<number>|undefined =
      undefined;
''',
     '''  protected accessor browserLayoutPref_: PrefObject<number>|undefined =
      undefined;

  // Dual: whether this page belongs to a pane of a Dual window. Resolved per
  // page, not through profile-shared load data.
  protected accessor heliumDualPaneMode_: boolean|undefined = undefined;
  private heliumDualPaneModeRequest_: number = 0;
  private refreshHeliumDualPaneMode_ = () => {
    const request = ++this.heliumDualPaneModeRequest_;
    AppearanceBrowserProxyImpl.getInstance().getHeliumDualPaneMode().then(
        isDual => {
          if (this.isConnected && request === this.heliumDualPaneModeRequest_) {
            this.heliumDualPaneMode_ = isDual;
          }
        }).catch(() => {
          // Keep the last resolved state; a later window focus retries the
          // query. An unresolved first query must not expose controls with
          // false effects.
        });
  };
''',
     '''  override connectedCallback() {
    super.connectedCallback();
''',
     '''  override connectedCallback() {
    super.connectedCallback();
    window.addEventListener('focus', this.refreshHeliumDualPaneMode_);
    this.refreshHeliumDualPaneMode_();
''',
     '''  protected showVerticalSettings_(): boolean {
    return this.browserLayoutPref_?.value === BrowserLayout.VERTICAL;
  }''',
     '''  override disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('focus', this.refreshHeliumDualPaneMode_);
    ++this.heliumDualPaneModeRequest_;
  }

  private effectiveBrowserLayout_(): number|undefined {
    return this.heliumDualPaneMode_ ? BrowserLayout.VERTICAL :
                                    this.browserLayoutPref_?.value;
  }

  protected showVerticalSettings_(): boolean {
    return this.effectiveBrowserLayout_() === BrowserLayout.VERTICAL;
  }''',
     '''  protected showCenteredLocationBarSetting_(): boolean {
    return this.browserLayoutPref_?.value !== BrowserLayout.COMPACT;
  }''',
     '''  protected showCenteredLocationBarSetting_(): boolean {
    return this.effectiveBrowserLayout_() !== BrowserLayout.COMPACT;
  }''')
edit(LAYOUT + '.html.ts',
     '''<settings-section page-title="$i18n{layoutPageTitle}">
  <settings-radio-group''',
     '''<settings-section page-title="$i18n{layoutPageTitle}">
  ${this.heliumDualPaneMode_ !== undefined ? html`
  ${this.heliumDualPaneMode_ ? html`
  <div class="cr-row first">
    <div class="flex cr-padded-text">
      <div id="dualBrowserLayout">$i18n{browserLayoutVertical}</div>
      <div class="secondary">$i18n{heliumDualLayoutDescription}</div>
    </div>
  </div>
  ` : html`
  <settings-radio-group''',
     '''  </settings-radio-group>
  <settings-toggle-button class="hr"
      ?hidden="${!this.showVerticalSettings_()}"
      pref-key="helium.browser.vertical_right_aligned"''',
     '''  </settings-radio-group>
  `}
  <settings-toggle-button class="hr"
      ?hidden="${!this.showVerticalSettings_() || this.heliumDualPaneMode_ === true}"
      pref-key="helium.browser.vertical_right_aligned"''',
     '''  </div>
</settings-section>''',
     '''  </div>
  ` : ''}
</settings-section>''')

# Helium removed this script; the inspector overlay is built another way now.
drop('third_party/devtools-frontend/src/scripts/build/build_inspector_overlay.py')
# Chromium 156 / Helium 0.20 API changes in files that merged cleanly.
# The vertical strip's floating style became a style, a radius and whether a
# toolbar is above it.
edit('chrome/browser/ui/views/frame/layout/browser_view_layout_impl.cc',
     '      rail->SetZenModeFloatingStyleForLayout(floating);',
     '      using FloatingStyle = VerticalTabStripRegionView::FloatingStyle;\n'
     '      rail->SetFloatingStyleForLayout(\n'
     '          floating ? FloatingStyle::kDetached : FloatingStyle::kNone,\n'
     '          GetGenericFrameRadius(), /*below_toolbar=*/false);',
     '#include "chrome/browser/ui/views/frame/vertical_tab_strip_region_view.h"\n#endif',
     '#include "chrome/browser/ui/views/frame/vertical_tab_strip_region_view.h"\n'
     '#include "chrome/browser/ui/views/helium/frame_corner_radius.h"\n#endif')
# Chromium 156 renamed the unload controller's calls for closing a window
# with its beforeunload handlers.
edit('chrome/browser/ui/helium/helium_dual_browser_mac.mm',
     '->ResetTryToCloseWindow()', '->ResetBeforeUnloadForShutdown()',
     '->TryToCloseWindow(', '->RunBeforeUnloadForShutdown(')
print('resolved')
