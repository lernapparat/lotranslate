import uno
import unohelper
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.frame import XPopupMenuController
from com.sun.star.awt import XMenuListener
from com.sun.star.beans import PropertyValue
from com.sun.star.awt.MessageBoxType import ERRORBOX
from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK

import traceback
import collections

import lotranslate_backend


def message_box(message_text):
    ctx = uno.getComponentContext()
    sManager = ctx.ServiceManager
    toolkit = sManager.createInstance("com.sun.star.awt.Toolkit")
    msgbox = toolkit.createMessageBox(None, ERRORBOX, BUTTONS_OK, "Error",
                                      message_text)
    return msgbox.execute()


def configuration_access(path, write=False):
    """Creates a XNameAccess instance for read and write access to the
    configuration at the given node path."""

    ctx = uno.getComponentContext()
    configurationProvider = ctx.ServiceManager.createInstance(
        'com.sun.star.configuration.ConfigurationProvider')
    value = PropertyValue()
    value.Name = 'nodepath'
    value.Value = path
    if write:
        servicename = 'com.sun.star.configuration.ConfigurationUpdateAccess'
    else:
        servicename = 'com.sun.star.configuration.ConfigurationAccess'
    configurationAccess = configurationProvider.createInstanceWithArguments(
        servicename, (value,))
    return configurationAccess


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# thread safety?!
class ConfigurationManager(metaclass=Singleton):
    def __init__(self):
        self.models = []
        self.listeners = []
        self.load_config()

    def add_listener(self, listener):
        self.listeners.append(listener)

    def load_model_config(self, url):
        path = unohelper.fileUrlToSystemPath(url)
        cfg = lotranslate_backend.load_model_config(path)
        if cfg is not None:
            cfg['lotranslate-path-url'] = url
        return cfg

    def load_config(self):
        # import pydevd; pydevd.settrace()  # noqa: E702
        cfg_access = configuration_access(
            "/de.lernapparat.lotranslate.Options/Options")
        self.edit_before_replace = cfg_access.getByName('chkEditBeforeReplace')
        model_urls = cfg_access.getByName('lstTranslationModels')
        self.models.clear()
        for u in model_urls:
            cfg = self.load_model_config(u)
            if cfg is not None:
                self.models.append(cfg)
        self.notify_listeners()

    def notify_listeners(self):
        for l in self.listeners:
            l()

    def add_model(self, fn):
        cfg = self.load_model_config(fn)
        if cfg is not None:
            self.models.append(cfg)
            self.notify_listeners()
        else:
            message_box("Could not load model config")

    def save_config(self):
        # import pydevd; pydevd.settrace()
        update_access = configuration_access(
            "/de.lernapparat.lotranslate.Options/Options", write=True)
        update_access.setPropertyValue('chkEditBeforeReplace',
                                       self.edit_before_replace)
        urls = tuple(m['lotranslate-path-url'] for m in self.models)
        # update_access.setPropertyValue('lstTranslationModels', urls)
        # does not work
        # see https://bugs.documentfoundation.org/show_bug.cgi?id=125307
        uno.invoke(update_access, "setPropertyValue",
                   (('lstTranslationModels', uno.Any("[]string", urls))))
        update_access.commitChanges()


class TranslationMenuController(unohelper.Base, XPopupMenuController, XMenuListener):
    def __init__(self, context, *args):
        # import pydevd; pydevd.settrace()  # noqa: E702
        self.ctx = context
        self.cfg_man = ConfigurationManager()

    def setPopupMenu(self, popup_menu):
        self.popup = popup_menu
        # import pydevd; pydevd.settrace()  # noqa: E702
        popup_menu.removeItem(0, popup_menu.getItemCount())
        if self.cfg_man.models:
            for i, m in enumerate(self.cfg_man.models):
                # use Language specific menu entry instead of '*'
                # insertItem(id, txt, style, pos)
                popup_menu.insertItem(i + 1, m['menu_entry']['*'], 0, i)
                popup_menu.setCommand(i + 1, 'de.lernapparat.lotranslate.TranslateCommand?{}'.format(i))
        else:
            popup_menu.insertItem(1, "No models", 0, 0)
            popup_menu.enableItem(1, False)
        popup_menu.addMenuListener(self)

    def updatePopupMenu(self):
        # import pydevd; pydevd.settrace()  # noqa: E702
        pass

    def translate(self, cfg):
        desktop = self.ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.ctx)
        try:
            component = desktop.getCurrentComponent()
            controller = component.CurrentController
            cursor = controller.ViewCursor
            documentText = cursor.getText()
            modelCursor = documentText.createTextCursorByRange(cursor)  # .getStart())

            text = component.Text

            # note: words is not a list of words, but a list of similarly formatted bits
            words = []
            trs = []
            # import pydevd; pydevd.settrace()  # noqa: E702
            for tc in list(modelCursor):  # .textContent
                for tr in list(tc):  # textRange, TextPortion
                    if tr.TextPortionType == "Text":
                        words.append(tr.String)
                        pnames = [c for c in dir(tr) if c.startswith('Char')]
                        trs.append(collections.OrderedDict(zip(pnames, tr.getPropertyValues(pnames))))
            translated_words = lotranslate_backend.translate(cfg, words)
            modelCursor.collapseToEnd()
            text.insertString(modelCursor, "\n", 0)
            modelCursor.collapseToEnd()
            #modelCursorBeginning = (type(modelCursor))(modelCursor)
            #cursor.collapseToEnd()
            insertedchars = 0
            for s, ref_tr in translated_words:
                d = trs[ref_tr]
                pnames = [c for c in dir(tr) if c.startswith('Char') if c in d and c not in {'CharInteropGrabBag',
                                                                                             'CharStyleName',
                                                                                             'CharAutoStyleName'}]
                pvals = [d[c] for c in pnames]
                for n, v in zip(pnames, pvals):
                    modelCursor.setPropertyValue(n, v)
                # modelCursor.setPropertyValues(pnames, pvals)
                text.insertString(modelCursor, s, 0)
                insertedchars += len(s)
            # import pydevd; pydevd.settrace()  # noqa: E702
            modelCursor.goLeft(insertedchars, True)  # somehow gotoRange with extend=True doesn't seem to work...
            annot = component.createInstance("com.sun.star.text.textfield.Annotation")
            annot.Content = ''.join(words)
            annot.Author = "LOTranslate"
            text.insertTextContent(modelCursor, annot, False)
            annot.attach(modelCursor)
        except Exception as e:  # noqa: F841
            component = desktop.getCurrentComponent()
            text = component.Text
            cursor = text.createTextCursor()
            text.insertString(cursor, traceback.format_exc()+"\n", 0)
            raise

    def itemSelected(self, event):
        # import pydevd; pydevd.settrace()  # noqa: E702
        cmd = event.Source.getCommand(event.MenuId)
        parts = cmd.split('?')
        if parts[0] == "de.lernapparat.lotranslate.TranslateCommand" and len(parts) == 2:
            model_idx = int(parts[1])
            self.translate(self.cfg_man.models[model_idx])
        else:
            pass  # error?

    def itemHighlighted(self, event):
        # import pydevd; pydevd.settrace()  # noqa: E702
        pass

    def itemActivated(self, event):
        # import pydevd; pydevd.settrace()  # noqa: E702
        pass

    def itemDeactivated(self, event):
        # import pydevd; pydevd.settrace()  # noqa: E702
        pass

    def disposing(self, source):
        pass


class CfgDialogEventHandler(unohelper.Base, XContainerWindowEventHandler):
    def __init__(self, context):
        # import pydevd; pydevd.settrace()
        self.ctx = context
        # Names of the controls which are supported by this handler. All these
        # controls must have a "Text" property.
        self.controlNames = {"chkEditBeforeReplace", "lstTranslationModels"}

        self.edit_before_replace = True
        self.window = None
        self.cfg_man = ConfigurationManager()
        self.cfg_man.add_listener(self.update_dialog)
        # self.__serviceName = "org.openoffice.demo.DialogEventHandler"

    def add_model(self, window):
        sman = self.ctx.getServiceManager()
        filepicker = sman.createInstanceWithContext(
            "com.sun.star.ui.dialogs.FilePicker", self.ctx)
        if filepicker.execute():
            # d = filepicker.getDisplayDirectory()
            fns = filepicker.getFiles()
            fn = fns[0] if fns else None
        else:
            fn = None
        filepicker.dispose()
        if fn is not None:
            self.cfg_man.add_model(fn)

    def update_dialog(self):
        if self.window is None:
            return
        model_list = self.window.getControl("lstTranslationModels")
        model_list.removeItems(0, model_list.getItemCount())
        # use Language specific menu entry instead of '*'
        model_list.addItems([m['menu_entry']['*'] for m in self.cfg_man.models], 0)

    def callHandlerMethod(self, window, event, method):
        # method is a string
        # event can be string or an object (e.g. ActionEvent object)
        # window is com.sun.star.awt.XWindow, but really XContainerWindow
        # first: "external_event" event: "initialize"
        # NewModel button: "actionNewModel" (defined in xdl), event: ActionEvent object
        if window is not None:
            self.window = window
        if method == "external_event":
            if event == "initialize" or event == "back":  # initialization or "Reset" button
                self.cfg_man.load_config()
                return True
            elif event == "ok":
                self.cfg_man.save_config()
                return True
            else:
                import pydevd; pydevd.settrace()  # noqa: E702
                return False
        elif method == "actionNewModel":
            self.add_model(window)
            return True
        elif method == "actionEditModel":
            return True  # edit model button
        elif method == "actionDeleteModel":
            return True  # delete model button
        else:
            import pydevd; pydevd.settrace()  # noqa: E702
            return False
        return False

    def getSupportedMethodNames(self):
        # import pydevd; pydevd.settrace()
        return ["external_event"]  # is this needed? seems to not be called...

    def createUnoService(self, name):
        pass
