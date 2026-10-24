#!/usr/bin/env python3
"""The hand resolutions for the move from Helium 0.17.2.2 to 0.18.3.1.

port_patch.py left conflicts in nine files. This records how each was settled,
so the move can be repeated: run port_patch.py, then this on its output.
What followed is not recorded here but in MODIFICATIONS.md: Chromium 154 no
longer hands out Browser, so Dual's pane state moved to HeliumDualPaneState;
the toolbar rule was rewritten; the unit tests were dropped.

  resolve_0.18.3.1.py <new stage> <new prepared Helium src>
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


# Helium no longer includes browser.h here; Dual's include stays.
settle('chrome/browser/app_controller_mac.mm',
       '#include "chrome/browser/ui/helium/helium_dual_browser_mac.h"\n')
# Two unrelated additions at the same place.
settle('chrome/browser/chrome_browser_field_trials.cc', 'both')
# Helium dropped the vertical-tabs feature check; Dual's effective layout stays.
settle('chrome/browser/resources/settings/appearance_page/appearance_page.ts',
       '    return this.effectiveBrowserLayout_() === BrowserLayout.VERTICAL;\n')
# Helium moved its layout controller to a target of its own (see below) and
# added targets where Dual's smoke test is declared.
settle('chrome/browser/ui/BUILD.gn',
       '    "helium/helium_dual_limits.h",\n    "helium/helium_dual_state.h",\n',
       'both')
# Helium removed a blank line where Dual reads its saved pane state.
settle('chrome/browser/ui/browser_live_tab_context.cc', 'dual')
# Includes added on both sides.
settle('chrome/browser/ui/helium/helium_layout_state_controller.cc',
       '#include <utility>\n\n#include "base/functional/bind.h"\n#include "chrome/browser/ui/browser_init_state.h"\n')
# Helium no longer includes browser_window.h here; Dual's include stays.
settle('chrome/browser/ui/views/tabs/dragging/tab_drag_controller.cc',
       '#if BUILDFLAG(IS_MAC)\n#include "chrome/browser/ui/helium/helium_dual_browser_mac.h"\n#endif\n')
# The test helper gained two arguments upstream; Dual's fix (the loader
# factory that Helium's own constructor change requires) goes with them.
settle('components/search_engines/template_url_service_test_util.cc',
       '      pref_service_,\n'
       '      base::MakeRefCounted<network::WeakWrapperSharedURLLoaderFactory>(nullptr),\n'
       '      *search_engine_choice_service_,\n'
       '      *prepopulate_data_resolver_.get(), *regional_capabilities_service_,\n'
       '      *profile_metrics_service_, std::make_unique<SearchTermsData>(),\n',
       '      pref_service(),\n'
       '      base::MakeRefCounted<network::WeakWrapperSharedURLLoaderFactory>(nullptr),\n'
       '      search_engine_choice_service(),\n'
       '      prepopulate_data_resolver(), regional_capabilities_service(),\n'
       '      profile_metrics_service(), std::make_unique<SearchTermsData>(),\n')

# Helium 0.18 rebuilt the toolbar layout around the lines Dual had changed.
# Dual's rule for narrow panes, written against the old layout, is dropped
# here: the file is Helium's again. (It was written anew for the new layout
# afterwards, once the build showed it was still needed.)
(STAGE / 'chrome/browser/ui/views/toolbar/toolbar_view.cc').unlink()

left = [str(p.relative_to(STAGE)) for p in STAGE.rglob('*')
        if p.is_file() and b'<<<<<<< Dual' in p.read_bytes()]
print('conflict markers left in:', left or 'none')
sys.exit(1 if left else 0)
