#import com.sun.star.beans.PropertyState;
#import com.sun.star.beans.PropertyValue;
#import com.sun.star.container.XNameAccess;
#import com.sun.star.lang.XMultiServiceFactory;
#import com.sun.star.uno.UnoRuntime;
#import com.sun.star.uno.XComponentContext;

import uno, unohelper
from com.sun.star.awt import XContainerWindowEventHandler
from com.sun.star.awt import XActionListener
from com.sun.star.lang import XServiceInfo
from com.sun.star.beans import PropertyValue
#from com.sun.star.task import XJobExecutor
#from com.sun.star.document import XEventListener

ctx = uno.getComponentContext()
configurationProvider = ctx.ServiceManager.createInstance('com.sun.star.configuration.ConfigurationProvider')

def configuration_access(path):
    """Creates a XNameAccess instance for read and write access to the
    configuration at the given node path."""

    value = PropertyValue()
    value.Name = 'nodepath'
    value.Value = path
    configurationAccess = configurationProvider.createInstanceWithArguments('com.sun.star.configuration.ConfigurationAccess', (value,))
    return configurationAccess


class CfgDialogEventHandler(unohelper.Base, XContainerWindowEventHandler, XActionListener): # XServiceInfo

    def __init__(self, context):
        #import pydevd; pydevd.settrace()
        self.context = context
        # Names of the controls which are supported by this handler. All these 
        # controls must have a "Text" property.
        self.controlNames = {"chkEditBeforeReplace", "lstTranslationModels"}

        self.accessLeaves = configuration_access("/de.lernapparat.lotranslate.Options/Leaves")
        # self.__serviceName = "org.openoffice.demo.DialogEventHandler"


    # getSupportedServiceNames(): return serviceNames

    #def supportsService(sServiceName):
    #  return sServiceName == self.__serviceName

    #public String getImplementationName()

    def callHandlerMethod(self, window, event, method):
        # method is a string, event can be string or an object (e.g. ActionEvent object)
        # window is com.sun.star.awt.XWindow 
        # first: "external_event" event: "initialize"
        # NewModel button: "actionNewModel" (defined in xdl), event: ActionEvent object 
        if method == "external_event":
            if event == "initialize":
                return True  # initializing
            elif event == "ok":
                return True  # apply button
            elif event == "back":
                return True  # reset button
            else:
                import pydevd; pydevd.settrace()
                return False
        elif method == "actionNewModel":
            return True # new model button
        elif method == "actionEditModel":
            return True # edit model button
        elif method == "actionDeleteModel":
            return True # delete model button
        else:
            import pydevd; pydevd.settrace()
            return False
        return False

    def getSupportedMethodNames(self):
        #import pydevd; pydevd.settrace()
        return ["external_event"]  # is this needed? seems to not be called...

    def createUnoService(self, name):
        pass



"""
      try
      {
        String sMethod = AnyConverter.toString(aEventObject);
        if (sMethod.equals("ok"))
        {
          saveData(aWindow);
        }
        else if (sMethod.equals("back") || sMethod.equals("initialize"))
        {
          loadData(aWindow);
        }
      }
      catch (com.sun.star.lang.IllegalArgumentException ex)
      {
        ex.printStackTrace();
          throw new com.sun.star.lang.IllegalArgumentException(
            "Method external_event requires a string in the event object argument.",
            this, (short) -1);
      }
      return true;
      """
    
"""
    /**
     * Saves data from the dialog into the configuration.
     * @param aWindow
     * @throws com.sun.star.lang.IllegalArgumentException
     * @throws com.sun.star.uno.Exception
     */
    private void saveData(com.sun.star.awt.XWindow aWindow)
      throws com.sun.star.lang.IllegalArgumentException, com.sun.star.uno.Exception
    {
      // Determine the name of the options page. This serves two purposes. First, if this
      // options page is supported by this handler and second we use the name two locate
      // the corresponding data in the registry.
      String sWindowName = getWindowName(aWindow);
      if (sWindowName == null)
        throw new com.sun.star.lang.IllegalArgumentException(
          "This window is not supported by this handler", this, (short) -1);

      // To access the separate controls of the window we need to obtain the
      // XControlContainer from the window implementation
      XControlContainer xContainer = (XControlContainer) UnoRuntime.queryInterface(
        XControlContainer.class, aWindow);
      if (xContainer == null)
        throw new com.sun.star.uno.Exception(
          "Could not get XControlContainer from window.", this);

      // This is an implementation which will be used for several options pages
      // which all have the same controls. m_arStringControls is an array which
      // contains the names.
      for (int i = 0; i < ControlNames.length; i++)
      {
        // To obtain the data from the controls we need to get their model.
        // First get the respective control from the XControlContainer.
        XControl xControl = xContainer.getControl(ControlNames[i]);

        // This generic handler and the corresponding registry schema support
        // up to five text controls. However, if a options page does not use all
        // five controls then we will not complain here.
        if (xControl == null)
          continue;

        // From the control we get the model, which in turn supports the
        // XPropertySet interface, which we finally use to get the data from
        // the control.
        XPropertySet xProp = (XPropertySet) UnoRuntime.queryInterface(
          XPropertySet.class, xControl.getModel());

        if (xProp == null)
          throw new com.sun.star.uno.Exception(
            "Could not get XPropertySet from control.", this);

        // Retrieve the data we want to store from the components.
        // We do not know which property contains data we want, so
        // we decide through the components name. This only works if all
        // components have been named properly:
        // Text fields start with "txt",
        // Check boxes with "chk",
        // List boxes with "lst"
        // You should adapt this behavior to your needs.
        Object   aObj  = null;
        Object[] value = new Object[1];
        String[] keys  = new String[] {ControlNames[i]};
        try
        {
          if(ControlNames[i].startsWith("txt"))
          {
            aObj     = xProp.getPropertyValue("Text");
            value[0] = AnyConverter.toString(aObj);
          }
          else if(ControlNames[i].startsWith("lst"))
          {
            keys  = new String[]{ControlNames[i] + "Selected", ControlNames[i]};
            value = new Object[2];

            // Read out indices of selected items
            aObj     = xProp.getPropertyValue("SelectedItems");
            value[0] = AnyConverter.toArray(aObj);

            // Read out items (they are read-only though, but perhaps someone wants to change this)
            aObj     = xProp.getPropertyValue("StringItemList");
            value[1] = AnyConverter.toArray(aObj);
          }
          else if(ControlNames[i].startsWith("chk"))
          {
            aObj     = xProp.getPropertyValue("State");
            value[0] = new Short(AnyConverter.toShort(aObj)).toString();
          }
        }
        catch (com.sun.star.lang.IllegalArgumentException ex)
        {
          ex.printStackTrace();
          throw new com.sun.star.lang.IllegalArgumentException(
            "Wrong property type.", this, (short) -1);
        }

        // Now we have the actual string value of the control. What we need now is
        // the XPropertySet of the respective property in the registry, so that we
        // can store the value.
        // To access the registry we have previously created a service instance
        // of com.sun.star.configuration.ConfigurationUpdateAccess which supports
        // com.sun.star.container.XNameAccess. The XNameAccess is used to get the
        // particular registry node which represents this options page.
        // Fortunately the name of the window is the same as the registry node.
        XPropertySet xLeaf = (XPropertySet) UnoRuntime.queryInterface(
          XPropertySet.class, accessLeaves.getByName(sWindowName));
        if (xLeaf == null)
          throw new com.sun.star.uno.Exception("XPropertySet not supported.", this);

        // Finally we can set the values
        for(int n = 0; n < keys.length; n++)
          xLeaf.setPropertyValue(keys[n], value[n]);
      }

      // Committing the changes will cause or changes to be written to the registry.
      XChangesBatch xUpdateCommit =
      (XChangesBatch) UnoRuntime.queryInterface(XChangesBatch.class, accessLeaves);
      xUpdateCommit.commitChanges();
    }

    /**
     * Loads data from the configuration into the dialog.
     * @param aWindow
     * @throws com.sun.star.uno.Exception
     */
    private void loadData(com.sun.star.awt.XWindow aWindow)
      throws com.sun.star.uno.Exception
    {
      // Determine the name of the window. This serves two purposes. First, if this
      // window is supported by this handler and second we use the name two locate
      // the corresponding data in the registry.
      String sWindowName = getWindowName(aWindow);
      if (sWindowName == null)
        throw new com.sun.star.lang.IllegalArgumentException(
          "The window is not supported by this handler", this, (short) -1);

      // To acces the separate controls of the window we need to obtain the
      // XControlContainer from window implementation
      XControlContainer xContainer = (XControlContainer) UnoRuntime.queryInterface(
        XControlContainer.class, aWindow);
      if (xContainer == null)
        throw new com.sun.star.uno.Exception(
          "Could not get XControlContainer from window.", this);

      // This is an implementation which will be used for several options pages
      // which all have the same controls. m_arStringControls is an array which
      // contains the names.
      for (int i = 0; i < ControlNames.length; i++)
      {
        // load the values from the registry
        // To access the registry we have previously created a service instance
        // of com.sun.star.configuration.ConfigurationUpdateAccess which supports
        // com.sun.star.container.XNameAccess. We obtain now the section
        // of the registry which is assigned to this options page.
        XPropertySet xLeaf = (XPropertySet) UnoRuntime.queryInterface(
          XPropertySet.class, this.accessLeaves.getByName(sWindowName));
        if (xLeaf == null)
          throw new com.sun.star.uno.Exception("XPropertySet not supported.", this);

        // The properties in the registry have the same name as the respective
        // controls. We use the names now to obtain the property values.
        Object aValue = xLeaf.getPropertyValue(ControlNames[i]);

        // Now that we have the value we need to set it at the corresponding
        // control in the window. The XControlContainer, which we obtained earlier
        // is the means to get hold of all the controls.
        XControl xControl = xContainer.getControl(ControlNames[i]);

        // This generic handler and the corresponding registry schema support
        // up to five text controls. However, if a options page does not use all
        // five controls then we will not complain here.
        if (xControl == null)
          continue;

        // From the control we get the model, which in turn supports the
        // XPropertySet interface, which we finally use to set the data at the
        // control
        XPropertySet xProp = (XPropertySet) UnoRuntime.queryInterface(
          XPropertySet.class, xControl.getModel());

        if (xProp == null)
          throw new com.sun.star.uno.Exception("Could not get XPropertySet from control.", this);

        // Some default handlings: you can freely adapt the behaviour to your
        // needs, this is only an example.
        // For text controls we set the "Text" property.
        if(ControlNames[i].startsWith("txt"))
        {
          xProp.setPropertyValue("Text", aValue);
        }
        // The available properties for a checkbox are defined in file
        // offapi/com/sun/star/awt/UnoControlCheckBoxModel.idl
        else if(ControlNames[i].startsWith("chk"))
        {
          xProp.setPropertyValue("State", aValue);
        }
        // The available properties for a checkbox are defined in file
        // offapi/com/sun/star/awt/UnoControlListBoxModel.idl
        else if(ControlNames[i].startsWith("lst"))
        {
          xProp.setPropertyValue("StringItemList", aValue);
          
          aValue = xLeaf.getPropertyValue(ControlNames[i] + "Selected");
          xProp.setPropertyValue("SelectedItems", aValue);
        }
      }
    }

    // Checks if the name property of the window is one of the supported names and returns
    // always a valid string or null
    private String getWindowName(com.sun.star.awt.XWindow aWindow)
      throws com.sun.star.uno.Exception
    {
      if (aWindow == null)
        new com.sun.star.lang.IllegalArgumentException(
          "Method external_event requires that a window is passed as argument",
          this, (short) -1);

      // We need to get the control model of the window. Therefore the first step is
      // to query for it.
      XControl xControlDlg = (XControl) UnoRuntime.queryInterface(
        XControl.class, aWindow);

      if (xControlDlg == null)
        throw new com.sun.star.uno.Exception(
          "Cannot obtain XControl from XWindow in method external_event.");
      // Now get model
      XControlModel xModelDlg = xControlDlg.getModel();

      if (xModelDlg == null)
        throw new com.sun.star.uno.Exception(
          "Cannot obtain XControlModel from XWindow in method external_event.", this);
      
      // The model itself does not provide any information except that its
      // implementation supports XPropertySet which is used to access the data.
      XPropertySet xPropDlg = (XPropertySet) UnoRuntime.queryInterface(
        XPropertySet.class, xModelDlg);
      if (xPropDlg == null)
        throw new com.sun.star.uno.Exception(
          "Cannot obtain XPropertySet from window in method external_event.", this);

      // Get the "Name" property of the window
      Object aWindowName = xPropDlg.getPropertyValue("Name");

      // Get the string from the returned com.sun.star.uno.Any
      String sName = null;
      try
      {
        sName = AnyConverter.toString(aWindowName);
      }
      catch (com.sun.star.lang.IllegalArgumentException ex)
      {
        ex.printStackTrace();
        throw new com.sun.star.uno.Exception(
          "Name - property of window is not a string.", this);
      }

      // Eventually we can check if we this handler can "handle" this options page.
      // The class has a member m_arWindowNames which contains all names of windows
      // for which it is intended
      if sName in {"OptionsPage"}:
        return sName
      return None
    }
  }



#### HELPER:::::

  /**
   * Gives a factory for creating the service.
   * This method is called by the CentralRegistrationClass.
   * @return returns a <code>XSingleComponentFactory</code> for creating
   * the component
   * @param sImplName the name of the implementation for which a
   * service is desired
   * @see com.sun.star.comp.loader.JavaLoader
   */
  public static XSingleComponentFactory __getComponentFactory(String sImplName)
  {
    System.out.println("DialogEventHandler::_getComponentFactory");
    XSingleComponentFactory xFactory = null;

    if ( sImplName.equals( _DialogEventHandler.class.getName() ) )
    xFactory = Factory.createComponentFactory(_DialogEventHandler.class,
    _DialogEventHandler.getServiceNames());

    return xFactory;
  }

  /**
   * Writes the service information into the given registry key.
   * This method is called by the CentralRegistrationClass.
   * @return returns true if the operation succeeded
   * @param regKey the registryKey
   * @see com.sun.star.comp.loader.JavaLoader
   */
  public static boolean __writeRegistryServiceInfo(XRegistryKey regKey)
  {
    System.out.println("DialogEventHandler::__writeRegistryServiceInfo");
    return Factory.writeRegistryServiceInfo(_DialogEventHandler.class.getName(),
      _DialogEventHandler.getServiceNames(),
      regKey);
  }

  /**
   * This method is a member of the interface for initializing an object
   * directly after its creation.
   * @param object This array of arbitrary objects will be passed to the
   * component after its creation.
   * @throws Exception Every exception will not be handled, but will be
   * passed to the caller.
   */
  public void initialize( Object[] object )
    throws com.sun.star.uno.Exception
  {}
}
"""