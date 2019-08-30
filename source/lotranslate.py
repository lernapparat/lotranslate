# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# For Debugging type pydevd and request a code-completion.
# Choose the first suggestion and you will see something like:
#    import sys;sys.path.append(r/some/path/eclipse/plugins/org.python.pydev.core_6.5.0.201809011628/pysrc)
#    import pydevd;pydevd.settrace()
# Place pydevd.settrace() before the line you want the debugger to stop and
# start debugging your extension (right click on project -> Debug As -> LibreOffice extension)
# You need to manually switch to debug view in Eclipse then.

import uno  # noqa: F401
import unohelper

import sys
import glob
import os

if not hasattr(sys, "argv"):  # seems to be the case on Windows with LO 6.3.0
    sys.argv = ['libreoffice-translate']
elif not sys.argv:
    sys.argv.append('libreoffice-translate')
sys.dont_write_bytecode = True

#sys.path.append(glob.glob(os.path.expanduser(
#    '~/libreoffice/loeclipse-prep/eclipse/plugins/org.python.pydev.core_*/pysrc/'))[-1])

# import pydevd; pydevd.settrace()

sys.path.append(os.path.join(os.path.dirname(__file__), '../classes'))

import dialog_event_handler  # noqa: E402

g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    dialog_event_handler.CfgDialogEventHandler,
    "de.lernapparat.lotranslate.CfgDialogEventHandler",
    ("com.sun.star.awt.ContainerWindowEventHandler",))
g_ImplementationHelper.addImplementation(
    dialog_event_handler.TranslationMenuController,
    "de.lernapparat.lotranslate.TranslationMenuController",
    ("com.sun.star.frame.PopupMenuController",
     "com.sun.star.awt.MenuListener"))
g_ImplementationHelper.addImplementation(
    dialog_event_handler.TranslationMenuController,
    "de.lernapparat.lotranslate.TranslationMenu",
    ("com.sun.star.frame.PopupMenuController",
     "com.sun.star.awt.MenuListener"))
