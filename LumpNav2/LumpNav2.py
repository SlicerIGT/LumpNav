import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# LumpNav2
#

class LumpNav2(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "LumpNav2"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["IGT"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Perk Lab (Queen's University)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#LumpNav2">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # LumpNav21
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='LumpNav2',
    sampleName='LumpNav21',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'LumpNav21.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='LumpNav21.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='LumpNav21'
  )

  # LumpNav22
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='LumpNav2',
    sampleName='LumpNav22',
    thumbnailFileName=os.path.join(iconsPath, 'LumpNav22.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='LumpNav22.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='LumpNav22'
  )


# Event filter for LumpNav widget main window

class LumpNavEventFilter(qt.QWidget):
  """
  Install this event filter to overwrite default behavior of main window events like closing the window or saving the
  scene.
  """

  def __init__(self, moduleWidget):
    qt.QWidget.__init__(self)
    self.moduleWidget = moduleWidget

  def eventFilter(self, object, event):
    if self.moduleWidget.getSlicerInterfaceVisible():
      return False

    if event.type() == qt.QEvent.Close:
      if self.moduleWidget.confirmExit():
        slicer.app.quit()
        return True
      else:
        event.ignore()
        return True

    # elif (event.type() == qt.QEvent.KeyPress and event.key() == qt.Qt.Key_S and (event.modifiers() & qt.Qt.ControlModifier)):
    #   print("CTRL + S intercepted")
    #   return True

    return False


#
# LumpNav2Widget
#

class LumpNav2Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/LumpNav2.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = LumpNav2Logic()
    self._updatingGUIFromParameterNode = True
    self.logic.setup()
    self._updatingGUIFromParameterNode = False

    # Install event filter for main window.

    self.eventFilter = LumpNavEventFilter(self)
    slicer.util.mainWindow().installEventFilter(self.eventFilter)

    # Set state of custom UI button

    self.setCustomStyle(not self.getSlicerInterfaceVisible())

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # Buttons
    self.ui.customUiButton.connect('toggled(bool)', self.onCustomUiClicked)
    self.ui.startPlusButton.connect('toggled(bool)', self.onStartPlusClicked)

    self.ui.toolsCollapsibleButton.connect('contentsCollapsed(bool)', self.onToolsCollapsed)
    self.ui.contouringCollapsibleButton.connect('contentsCollapsed(bool)', self.onContouringCollapsed)
    self.ui.navigationCollapsibleButton.connect('contentsCollapsed(bool)', self.onNavigationCollapsed)

    self.ui.needleVisibilityButton.connect('toggled(bool)', self.onNeedleVisibilityToggled)
    self.ui.cauteryVisibilityButton.connect('toggled(bool)', self.onCauteryVisibilityToggled)

    self.ui.threeDViewButton.connect('toggled(bool)', self.on3DViewsToggled)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    # Set state of cautery visibility button

    self.setCauteryVisibility(self.getCauteryVisibility())

    # Add custom layouts

    self.logic.addCustomLayouts()

  def confirmExit(self):
    msgBox = qt.QMessageBox()
    msgBox.setStyleSheet(slicer.util.mainWindow().styleSheet)
    msgBox.setWindowTitle("Confirm exit")
    msgBox.setText("Some data may not have been saved yet. Do you want to exit and discard the current scene?")
    discardButton = msgBox.addButton("Exit", qt.QMessageBox.DestructiveRole)
    cancelButton = msgBox.addButton("Cancel", qt.QMessageBox.RejectRole)
    msgBox.setModal(True)
    msgBox.exec()

    if msgBox.clickedButton() == discardButton:
      return True
    else:
      return False

  def onNeedleVisibilityToggled(self, toggled):
    self.logic.setNeedleVisibility(toggled)

  def onCauteryVisibilityToggled(self, toggled):
    self.setCauteryVisibility(toggled)

  def setCauteryVisibility(self, visible):
    settings = qt.QSettings()
    settings.setValue('LumpNav2/CauteryVisibility', visible)

    cauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    cauteryModel.SetDisplayVisibility(visible)

    self.ui.cauteryVisibilityButton.checked = visible
    if visible:
      self.ui.cauteryVisibilityButton.text = "Hide cautery model"
    else:
      self.ui.cauteryVisibilityButton.text = "Show cautery model"

  def getCauteryVisibility(self):
    return slicer.util.settingsValue('LumpNav2/CauteryVisibility', False, converter=slicer.util.toBool)

  def onToolsCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.contouringCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)

  def onContouringCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(6)

  def onNavigationCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.contouringCollapsibleButton.collapsed = True
      self.on3DViewsToggled(False)

  def on3DViewsToggled(self, toggled):
    self.ui.threeDViewButton.checked = toggled
    if toggled:
      self.ui.threeDViewButton.text = "Triple 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_DUAL3D)
    else:
      self.ui.threeDViewButton.text = "Dual 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_TRIPLE3D)

  def onStartPlusClicked(self, toggled):
    plusServerNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_NODE)
    if plusServerNode:
      if toggled == True:
        plusServerNode.StartServer()
      else:
        # self.ui.startPlusButton.text
        plusServerNode.StopServer()

  def onCustomUiClicked(self, checked):
    self.setCustomStyle(checked)

  def setCustomStyle(self, visible):
    """
    Applies UI customization. Hide Slicer widgets and apply custom stylesheet.
    :param visible: True to apply custom style.
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue('LumpNav2/SlicerInterfaceVisible', not visible)

    slicer.util.setToolbarsVisible(not visible)
    slicer.util.setMenuBarsVisible(not visible)
    slicer.util.setApplicationLogoVisible(not visible)
    slicer.util.setModuleHelpSectionVisible(not visible)
    slicer.util.setModulePanelTitleVisible(not visible)
    slicer.util.setDataProbeVisible(not visible)
    slicer.util.setStatusBarVisible(not visible)

    if visible:
      styleFile = self.resourcePath("LumpNav.qss")
      f = qt.QFile(styleFile)
      f.open(qt.QFile.ReadOnly | qt.QFile.Text)
      ts = qt.QTextStream(f)
      stylesheet = ts.readAll()
      slicer.util.mainWindow().setStyleSheet(stylesheet)
    else:
      slicer.util.mainWindow().setStyleSheet("")

    self.ui.customUiButton.checked = visible

  def getSlicerInterfaceVisible(self):
    return slicer.util.settingsValue('LumpNav2/SlicerInterfaceVisible', False, converter=slicer.util.toBool)

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """

    plusServerNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_NODE)
    if plusServerNode:
      plusServerNode.StopServer()

    slicer.util.mainWindow().removeEventFilter(self.eventFilter)

    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

    slicer.util.setDataProbeVisible(False)
    slicer.util.setApplicationLogoVisible(False)
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)

    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(self.logic.LAYOUT_2D3D)

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    slicer.util.setDataProbeVisible(True)
    slicer.util.setApplicationLogoVisible(True)
    slicer.util.setModuleHelpSectionVisible(True)
    slicer.util.setModulePanelTitleVisible(True)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())


  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Model visibility control

    needleModelVisibleStr = self._parameterNode.GetParameter(self.logic.NEEDLE_MODEL_VISIBLE)
    if needleModelVisibleStr.lower() == 'true':
      needleModelVisible = True
    else:
      needleModelVisible = False

    if needleModelVisible:
      self.ui.needleVisibilityButton.checked = True
      self.ui.needleVisibilityButton.text = "Hide needle model"
    else:
      self.ui.needleVisibilityButton.checked = False
      self.ui.needleVisibilityButton.text = "Show needle model"

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    needleVisible = self.ui.needleVisibilityButton.checked
    if needleVisible:
      self._parameterNode.SetParameter(self.logic.NEEDLE_MODEL_VISIBLE, "true")
    else:
      self._parameterNode.SetParameter(self.logic.NEEDLE_MODEL_VISIBLE, "false")

    self._parameterNode.EndModify(wasModified)


#
# LumpNav2Logic
#

class LumpNav2Logic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # Transform names

  REFERENCE_TO_RAS = "ReferenceToRas"
  NEEDLE_TO_REFERENCE = "NeedleToReference"
  NEEDLETIP_TO_NEEDLE = "NeedleTipToNeedle"
  CAUTERY_TO_REFERENCE = "CauteryToReference"
  CAUTERYTIP_TO_CAUTERY = "CauteryTipToCautery"

  # OpenIGTLink PLUS connection

  CONFIG_FILE = "Childrens_2020.xml"
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"

  # Model names

  NEEDLE_MODEL = "NeedleModel"
  NEEDLE_MODEL_VISIBLE = "NeedleModelVisibile"
  CAUTERY_MODEL = "CauteryModel"
  CAUTERY_MODEL_FILENAME = "CauteryModel.stl"

  # Layout codes

  LAYOUT_2D3D = 501
  LAYOUT_TRIPLE3D = 502
  LAYOUT_DUAL3D = 503

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

    if not parameterNode.GetParameter(self.NEEDLE_MODEL_VISIBLE):
      parameterNode.SetParameter(self.NEEDLE_MODEL_VISIBLE, "true")

  def addCustomLayouts(self):
    layout2D3D =\
    """
    <layout type="horizontal" split="true">
      <item splitSize="500">
        <view class="vtkMRMLViewNode" singletontag="1">
          <property name="viewlabel" action="default">1</property>
        </view>
      </item>
      <item splitSize="500">
        <view class="vtkMRMLSliceNode" singletontag="Red">
          <property name="orientation" action="default">Axial</property>
          <property name="viewlabel" action="default">R</property>
          <property name="viewcolor" action="default">#F34A33</property>
        </view>
      </item>
    </layout>
    """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_2D3D, layout2D3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_2D3D, layout2D3D)

    layoutTriple3D =\
    """
    <layout type="vertical" split="true">
      <item splitSize="500">
        <layout type="horizontal">
          <item splitSize="500">
            <view class="vtkMRMLViewNode" singletontag="1">
              <property name="viewLabel" action="default">1</property>
            </view>
          </item>
          <item splitSize="500">
            <view class="vtkMRMLViewNode" singletontag="2" type="secondary">
              <property name="viewLabel" action="default">2</property>
            </view>
          </item>
        </layout>  
      </item>
      <item splitSize="500">
        <view class="vtkMRMLViewNode" singletontag="3" type="tertiary">
          <property name="viewLabel" action="default">3</property>
        </view>
      </item>
    </layout>
    """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_TRIPLE3D, layoutTriple3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_TRIPLE3D, layoutTriple3D)

    layoutDual3D = \
      """
      <layout type="horizontal" split="true">
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="1">
            <property name="viewLabel" action="default">1</property>
          </view>
        </item>
        <item splitSize="500">
          <view class="vtkMRMLViewNode" singletontag="2" type="secondary">
            <property name="viewLabel" action="default">2</property>
          </view>
        </item>
      </layout>
      """

    layoutManager = slicer.app.layoutManager()
    if not layoutManager.layoutLogic().GetLayoutNode().SetLayoutDescription(self.LAYOUT_DUAL3D, layoutDual3D):
      layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.LAYOUT_DUAL3D, layoutDual3D)

  def setNeedleVisibility(self, visible):
    parameterNode = self.getParameterNode()

    if visible:
      parameterNode.SetParameter(self.NEEDLE_MODEL_VISIBLE, "true")
    else:
      parameterNode.SetParameter(self.NEEDLE_MODEL_VISIBLE, "false")

    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    needleModel.SetDisplayVisibility(visible)

  def process(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    import time
    startTime = time.time()
    logging.info('Processing started')

    # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Above' if invert else 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    slicer.mrmlScene.RemoveNode(cliNode)

    stopTime = time.time()
    logging.info('Processing completed in {0:.2f} seconds'.format(stopTime-startTime))

  def setup(self):
    """
    Sets up the Slicer scene. Creates nodes if they are missing.
    """
    parameterNode = self.getParameterNode()

    self.setupTransformHierarchy()

    # Create models

    createModelsLogic = slicer.modules.createmodels.logic()

    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is None:
      needleModel = createModelsLogic.CreateNeedle(60.0, 1.0, 2.0, 0)
      needleModel.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
      needleModel.SetName(self.NEEDLE_MODEL)
      needleModel.GetDisplayNode().SliceIntersectionVisibilityOn()
      parameterNode.SetNodeReferenceID(self.NEEDLE_MODEL, needleModel.GetID())

    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleModel.SetAndObserveTransformNodeID(needleTipToNeedle.GetID())

    moduleDir = os.path.dirname(slicer.modules.lumpnav2.path)
    cauteryModelFullpath = os.path.join(moduleDir, "Resources", self.CAUTERY_MODEL_FILENAME)

    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    if cauteryModel is None:
      cauteryModel = slicer.util.loadModel(cauteryModelFullpath)
      cauteryModel.GetDisplayNode().SetColor(1.0, 1.0, 0.0)
      cauteryModel.SetName(self.CAUTERY_MODEL)
      parameterNode.SetNodeReferenceID(self.CAUTERY_MODEL, cauteryModel.GetID())
    
    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    cauteryModel.SetAndObserveTransformNodeID(cauteryTipToCautery.GetID())

    self.setupPlusServer()

  def setupTransformHierarchy(self):
    """
    Sets up transform nodes in the scene if they don't exist yet.
    """
    parameterNode = self.getParameterNode()

    referenceToRas = parameterNode.GetNodeReference(self.REFERENCE_TO_RAS)
    if referenceToRas is None:
      referenceToRas = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.REFERENCE_TO_RAS)
      parameterNode.SetNodeReferenceID(self.REFERENCE_TO_RAS, referenceToRas.GetID())

    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    if needleToReference is None:
      needleToReference = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.NEEDLE_TO_REFERENCE)
      parameterNode.SetNodeReferenceID(self.NEEDLE_TO_REFERENCE, needleToReference.GetID())
    needleToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    if needleTipToNeedle is None:
      needleTipToNeedle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.NEEDLETIP_TO_NEEDLE)
      parameterNode.SetNodeReferenceID(self.NEEDLETIP_TO_NEEDLE, needleTipToNeedle.GetID())
    needleTipToNeedle.SetAndObserveTransformNodeID(needleToReference.GetID())

    cauteryToReference = parameterNode.GetNodeReference(self.CAUTERY_TO_REFERENCE)
    if cauteryToReference is None:
      cauteryToReference = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERY_TO_REFERENCE)
      parameterNode.SetNodeReferenceID(self.CAUTERY_TO_REFERENCE, cauteryToReference.GetID())
    cauteryToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    if cauteryTipToCautery is None:
      cauteryTipToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYTIP_TO_CAUTERY)
      parameterNode.SetNodeReferenceID(self.CAUTERYTIP_TO_CAUTERY, cauteryTipToCautery.GetID())
    cauteryTipToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

  def setupPlusServer(self):
    """
    Creates PLUS server and OpenIGTLink connection if it doesn't exist already.
    """
    parameterNode = self.getParameterNode()

    moduleDir = os.path.dirname(slicer.modules.lumpnav2.path)
    configFullpath = os.path.join(moduleDir, "Resources", self.CONFIG_FILE)

    configTextNode = parameterNode.GetNodeReference(self.CONFIG_TEXT_NODE)
    if configTextNode is None:
      configTextNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", self.CONFIG_TEXT_NODE)
      configTextNode.SaveWithSceneOff()
      configTextNode.SetForceCreateStorageNode(slicer.vtkMRMLTextNode.CreateStorageNodeAlways)
      parameterNode.SetNodeReferenceID(self.CONFIG_TEXT_NODE, configTextNode.GetID())
    if not configTextNode.GetStorageNode():
      configTextNode.AddDefaultStorageNode()
    configTextStorageNode = configTextNode.GetStorageNode()
    configTextStorageNode.SaveWithSceneOff()
    configTextStorageNode.SetFileName(configFullpath)
    configTextStorageNode.ReadData(configTextNode)

    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    if not plusServerNode:
      plusServerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerNode", self.PLUS_SERVER_NODE)
      plusServerNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.PLUS_SERVER_NODE, plusServerNode.GetID())
    plusServerNode.SetAndObserveConfigNode(configTextNode)

    plusServerLauncherNode = parameterNode.GetNodeReference(self.PLUS_SERVER_LAUNCHER_NODE)
    if not plusServerLauncherNode:
      plusServerLauncherNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerLauncherNode", self.PLUS_SERVER_LAUNCHER_NODE)
      plusServerLauncherNode.SaveWithSceneOff()

    if plusServerLauncherNode.GetNodeReferenceID('plusServerRef') != plusServerNode.GetID():
      plusServerLauncherNode.AddAndObserveServerNode(plusServerNode)


#
# LumpNav2Test
#

class LumpNav2Test(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_LumpNav21()

  def test_LumpNav21(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('LumpNav21')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = LumpNav2Logic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
