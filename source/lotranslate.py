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

import uno, unohelper
from com.sun.star.task import XJobExecutor
from com.sun.star.document import XEventListener
import traceback
import collections
import sys
import glob
import os
sys.dont_write_bytecode = True
sys.path.append(glob.glob(os.path.expanduser('~/libreoffice/loeclipse-prep/eclipse/plugins/org.python.pydev.core_*/pysrc/'))[-1])
#sys.path.append(os.path.expanduser('~/python/pytorch/opennmt-py'))
# import pydevd; pydevd.settrace()

sys.path.append(os.path.join(os.path.dirname(__file__), '../classes'))

import lotranslate_backend
import dialog_event_handler

translator = lotranslate_backend.TranslationModel()

class lotranslate(unohelper.Base, XJobExecutor, XEventListener):
    
    def trigger(self, args):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        model = desktop.getCurrentComponent()
        text = model.Text
        cursor = text.createTextCursor()
        try:
            #import pydevd; pydevd.settrace()
            #self.translator = translate.TranslationModel()

            model = desktop.getCurrentComponent()
            controller = model.CurrentController
            cursor = controller.ViewCursor
            documentText = cursor.getText()
            modelCursor = documentText.createTextCursorByRange(cursor) #.getStart())
    
            text = model.Text
            #cursor = text.createTextCursor()
            #text.insertString(cursor, "Hello World! \n", 0)
            
            #sn = modelCursor.getAvailableServiceNames()     
            #import pydevd; pydevd.settrace()
            # note: words is not a list of words, but a list of similarly formatted bits
            words = []
            trs = []
            for tc in list(modelCursor): #.textContent
                for tr in list(tc): # textRange
                    words.append(tr.String)
                    pnames = [c for c in dir(tr) if c.startswith('Char')]
                    trs.append(collections.OrderedDict(zip(pnames, tr.getPropertyValues(pnames))))
            translated_words = self.translator.translate(words)
            modelCursor.collapseToEnd()
            text.insertString(modelCursor, "\n", 0)
            cursor.collapseToEnd()
            for s, ref_tr in translated_words:
                d = trs[ref_tr]
                #import pydevd; pydevd.settrace()
                pnames = [c for c in dir(tr) if c.startswith('Char') if c in d and c not in {'CharInteropGrabBag',
                                                                                             'CharStyleName',
                                                                                             'CharAutoStyleName'}]
                pvals = [d[c] for c in pnames]
                for n,v in zip(pnames, pvals):
                    modelCursor.setPropertyValue(n, v)
                #modelCursor.setPropertyValues(pnames, pvals)
                text.insertString(modelCursor, s, 0)
            
        except Exception as e:
            #print(e, file=open("/tmp/error.log", "a"))
            import pydevd; pydevd.settrace()
            model = desktop.getCurrentComponent()
            text = model.Text
            cursor = text.createTextCursor()
            text.insertString(cursor, traceback.format_exc()+"\n", 0)
            raise
        
    # boilerplate code below this point
    def __init__(self, context):
        self.ctx = context
        try:
            self.translator = translator #lotranslate_backend.TranslationModel()
        except Exception as e:
            import pydevd; pydevd.settrace()
            print (e, outfile=open('/tmp/x.txt', 'w'))

    def createUnoService(self, name):
        pass

    def disposing(self, args):
        pass

    def notifyEvent(self, args):
        pass

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    lotranslate,
    "de.lernapparat.lotranslate.TranslateMenu",
    ("com.sun.star.task.JobExecutor",))
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
