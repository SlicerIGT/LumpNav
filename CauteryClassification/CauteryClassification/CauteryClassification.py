import os
import time

import numpy as np
import vtk, qt, ctk, slicer

import logging
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from vtk.util import numpy_support

try:
  import matplotlib.pyplot as plt
except:
  slicer.util.pip_install('matplotlib')
  import matplotlib.pyplot as plt

try:
  from sklearn import datasets
except:
  slicer.util.pip_install('scikit-learn')
  from sklearn import datasets

from sklearn import svm
from sklearn import metrics
from sklearn.model_selection import train_test_split
from sklearn.metrics import plot_roc_curve
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import roc_curve, auc

try:
  from mlxtend.plotting import plot_decision_regions
except:
  slicer.util.pip_install('mlxtend')
  from mlxtend.plotting import plot_decision_regions

import pickle

from pandas.io.formats.format import buffer_put_lines
import numpy as np
from sklearn import svm
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
import pandas as pd
from mlxtend.plotting import plot_decision_regions
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.ensemble import RandomForestClassifier
from scipy.fft import fft, ifft, rfft, rfftfreq
from scipy.signal import detrend, resample

#
# CauteryClassification
#

class CauteryClassification(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "CauteryClassification"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#CauteryClassification">module documentation</a>.
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

  # CauteryClassification1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='CauteryClassification',
    sampleName='CauteryClassification1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'CauteryClassification1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='CauteryClassification1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='CauteryClassification1'
  )

  # CauteryClassification2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='CauteryClassification',
    sampleName='CauteryClassification2',
    thumbnailFileName=os.path.join(iconsPath, 'CauteryClassification2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='CauteryClassification2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='CauteryClassification2'
  )

#
# CauteryClassificationWidget
#

class CauteryClassificationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/CauteryClassification.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = CauteryClassificationLogic()
    self.logic.setup()
    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    # Oscilloscope
    self.ui.displayFftResults.connect('clicked()', self.displayFftResults)
    self.ui.streamGraphButton.connect('toggled(bool)', self.onStreamGraphButton)
    self.ui.collectOffButton.connect('toggled(bool)', self.onCollectOffToggled)
    self.ui.collectCutAirButton.connect('toggled(bool)', self.onCollectCutAirToggled)
    self.ui.collectCutTissueButton.connect('toggled(bool)', self.onCollectCutTissueToggled)
    self.ui.collectCoagAirButton.connect('toggled(bool)', self.onCollectCoagAirToggled)
    self.ui.collectCoagTissueButton.connect('toggled(bool)', self.onCollectCoagTissueToggled)
    self.ui.trainAndImplementModelButton.connect('clicked()', self.onTrainAndImplementModelClicked)
    self.ui.useModelButton.connect('toggled(bool)', self.onUseModelClicked)
    self.ui.resetModelButton.connect('clicked()', self.onResetModelClicked)

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

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

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  def displayFftResults(self):
    logging.info('onDisplaySampleGraphButton')
    self.logic.displayFftResults()

  def onStreamGraphButton(self, toggled):
    logging.info('onStreamGraphButton')
    self.logic.setStreamGraphButton(toggled)

  def onCollectOffToggled(self, toggled):
    logging.info('onCollectOffToggled({})'.format(toggled))
    self.logic.setCollectOff(toggled)

  def onCollectCutAirToggled(self, toggled):
    logging.info('onCollectCutAirToggled')
    self.logic.setCollectCutAir(toggled)

  def onCollectCutTissueToggled(self, toggled):
    logging.info('onCollectCutTissueToggled')
    self.logic.setCollectCutTissue(toggled)

  def onCollectCoagAirToggled(self, toggled):
    logging.info('onCollectCoagAirToggled')
    self.logic.setCollectCoagAir(toggled)

  def onCollectCoagTissueToggled(self, toggled):
    logging.info('onCollectCoagTissueToggled')
    self.logic.setCollectCoagTissue(toggled)

  def onTrainAndImplementModelClicked(self):
    logging.info('onTrainAndImplementModelClicked')
    self.logic.setTrainAndImplementModel()
    return

  def onUseModelClicked(self, toggled):
    logging.info('onUseModelClicked')
    self.logic.setUseModelClicked(toggled)

    return
  def onResetModelClicked(self):
    logging.info('onResetModelClicked')
    return
#
# CauteryClassificationLogic
#

class CauteryClassificationLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # OpenIGTLink PLUS connection

  CONFIG_FILE_SETTING = "LumpNav2/PlusConfigFile"
  CONFIG_FILE_DEFAULT = "LumpNavDefault.xml"  # Default config file if the user doesn't set another.
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"
  PLUS_REMOTE_NODE = "PlusRemoteNode"

  # Oscilloscope

  SIGNAL_SIGNAL = 'Signal_Signal'

  CONTOUR_STATUS = "ContourStatus"
  CONTOUR_ADDING = "ContourAdding"
  CONTOUR_ERASING = "ContourErasing"
  CONTOUR_UNSELECTED = "ContourUnselected"

  POINTS_ERASING = "PointsErasing"
  POINTS_ADDING = "PointsAdding"
  POINTS_STATUS = "PointsStatus"
  POINTS_UNSELECTED = "PointsUnselected"

  CHA_CHARTNODE = "ChannelAScopePlotChartNode"
  CHA_ARRAYNODE = "ChannelAArrayNode"
  CHA_ARRAY = "ChannelAArray"

  SCOPE_OFF_VOLUME_A = "ScopeOffVolumeA"
  SCOPE_CUT_AIR_VOLUME_A = "ScopeCutAirVolumeA"
  SCOPE_CUT_TISSUE_VOLUME_A = "ScopeCutTissueVolumeA"
  SCOPE_COAG_AIR_VOLUME_A = "ScopeCoagAirVolumeAScopeCoagAirVolumeA"
  SCOPE_COAG_TISSUE_VOLUME_A = "ScopeCoagTissueVolumeA"

  SCOPE_OFF_VOLUME_B = "ScopeOffVolumeB"
  SCOPE_CUT_AIR_VOLUME_B = "ScopeCutAirVolumeB"
  SCOPE_CUT_TISSUE_VOLUME_B = "ScopeCutTissueVolumeB"
  SCOPE_COAG_AIR_VOLUME_B = "ScopeCoagAirVolumeAScopeCoagAirVolumeB"
  SCOPE_COAG_TISSUE_VOLUME_B = "ScopeCoagTissueVolumeB"

  COLLECT_OFF_SEQUENCE_BROWSER = "CollectOffSequenceBrowser"
  COLLECT_CUT_AIR_SEQUENCE_BROWSER = "CollectCutAirSequenceBrowser"
  COLLECT_CUT_TISSUE_SEQUENCE_BROWSER = "CollectCutTissueSequenceBrowser"
  COLLECT_COAG_AIR_SEQUENCE_BROWSER = "CollectCoagAirSequenceBrowser"
  COLLECT_COAG_TISSUE_SEQUENCE_BROWSER = "CollectCoagTissueSequenceBrowser"

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    slicer.mymodL = self
    VTKObservationMixin.__init__(self)

  def resourcePath(self, filename):
    """
    Returns the full path to the given resource file.
    :param filename: str, resource file name
    :returns: str, full path to file specified
    """
    moduleDir = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(moduleDir, "Resources", filename)

  def setup(self):

    """
    Called when the user opens the module the first time and the widget is initialized.
    """

    parameterNode = self.getParameterNode()
    self.setupPlusServer()

    sequenceLogic = slicer.modules.sequences.logic()

    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    if signal_Signal is None:
      signal_Signal = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode', self.SIGNAL_SIGNAL)
      signal_Signal.CreateDefaultDisplayNodes()
      signalArray = np.zeros((3900, 3, 1), dtype="uint8")
      slicer.util.updateVolumeFromArray(signal_Signal, signalArray)
      parameterNode.SetNodeReferenceID(self.SIGNAL_SIGNAL, signal_Signal.GetID())
    self.addObserver(signal_Signal, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.scopeSignalModified)

    sequenceBrowserScopeCollectOff = parameterNode.GetNodeReference(self.COLLECT_OFF_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectOff is None:
      sequenceBrowserScopeCollectOff = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode",
                                                                          self.COLLECT_OFF_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_OFF_SEQUENCE_BROWSER, sequenceBrowserScopeCollectOff.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectOff)
    sequenceBrowserScopeCollectOff.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetRecordingActive(False)
    # TODO: why do we include sequenceNode as parameters in these lines?

    sequenceBrowserScopeCollectCutAir = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCutAir is None:
      sequenceBrowserScopeCollectCutAir = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode",
                                                                             self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER, sequenceBrowserScopeCollectCutAir.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCutAir)
    sequenceBrowserScopeCollectCutAir.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetRecordingActive(False)

    sequenceBrowserScopeCollectCutTissue = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCutTissue is None:
      sequenceBrowserScopeCollectCutTissue = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode",
                                                                                self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER,
                                       sequenceBrowserScopeCollectCutTissue.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCutTissue)
    sequenceBrowserScopeCollectCutTissue.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetRecordingActive(False)

    sequenceBrowserScopeCollectCoagAir = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCoagAir is None:
      sequenceBrowserScopeCollectCoagAir = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode",
                                                                              self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER,
                                       sequenceBrowserScopeCollectCoagAir.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCoagAir)
    sequenceBrowserScopeCollectCoagAir.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetRecordingActive(False)

    sequenceBrowserScopeCollectCoagTissue = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCoagTissue is None:
      sequenceBrowserScopeCollectCoagTissue = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode",
                                                                                 self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER,
                                       sequenceBrowserScopeCollectCoagTissue.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCoagTissue)
    sequenceBrowserScopeCollectCoagTissue.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetRecordingActive(False)

    scopeOffVolumeA = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_A)
    if scopeOffVolumeA is None:
      scopeOffVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_OFF_VOLUME_A)
      scopeOffVolumeA.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeOffVolumeA.SetSpacing([1, 1, 1])
      scopeOffVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeOffVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_OFF_VOLUME_A, scopeOffVolumeA.GetID())

    scopeCutAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_A)
    if scopeCutAirVolumeA is None:
      scopeCutAirVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_AIR_VOLUME_A)
      scopeCutAirVolumeA.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutAirVolumeA.SetSpacing([1, 1, 1])
      scopeCutAirVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutAirVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_AIR_VOLUME_A, scopeCutAirVolumeA.GetID())

    scopeCutTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_A)
    if scopeCutTissueVolumeA is None:
      scopeCutTissueVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                                 self.SCOPE_CUT_TISSUE_VOLUME_A)
      scopeCutTissueVolumeA.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutTissueVolumeA.SetSpacing([1, 1, 1])
      scopeCutTissueVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutTissueVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_TISSUE_VOLUME_A, scopeCutTissueVolumeA.GetID())

    scopeCoagTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_A)
    if scopeCoagTissueVolumeA is None:
      scopeCoagTissueVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                                  self.SCOPE_COAG_AIR_VOLUME_A)
      scopeCoagTissueVolumeA.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagTissueVolumeA.SetSpacing([1, 1, 1])
      scopeCoagTissueVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagTissueVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_AIR_VOLUME_A, scopeCoagTissueVolumeA.GetID())

    scopeCoagAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_A)
    if scopeCoagAirVolumeA is None:
      scopeCoagAirVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                               self.SCOPE_COAG_TISSUE_VOLUME_A)
      scopeCoagAirVolumeA.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagAirVolumeA.SetSpacing([1, 1, 1])
      scopeCoagAirVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagAirVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_TISSUE_VOLUME_A, scopeCoagAirVolumeA.GetID())

    scopeOffVolumeB = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_B)
    if scopeOffVolumeB is None:
      scopeOffVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_OFF_VOLUME_B)
      scopeOffVolumeB.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeOffVolumeB.SetSpacing([1, 1, 1])
      scopeOffVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeOffVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_OFF_VOLUME_B, scopeOffVolumeB.GetID())

    scopeCutAirVolume_B = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_B)
    if scopeCutAirVolume_B is None:
      scopeCutAirVolume_B = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_AIR_VOLUME_B)
      scopeCutAirVolume_B.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutAirVolume_B.SetSpacing([1, 1, 1])
      scopeCutAirVolume_B.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutAirVolume_B.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_AIR_VOLUME_B, scopeCutAirVolume_B.GetID())

    scopeCutTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_B)
    if scopeCutTissueVolumeB is None:
      scopeCutTissueVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                                 self.SCOPE_CUT_TISSUE_VOLUME_B)
      scopeCutTissueVolumeB.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutTissueVolumeB.SetSpacing([1, 1, 1])
      scopeCutTissueVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutTissueVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_TISSUE_VOLUME_B, scopeCutTissueVolumeB.GetID())

    scopeCoagTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_B)
    if scopeCoagTissueVolumeB is None:
      scopeCoagTissueVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                                  self.SCOPE_COAG_AIR_VOLUME_B)
      scopeCoagTissueVolumeB.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagTissueVolumeB.SetSpacing([1, 1, 1])
      scopeCoagTissueVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagTissueVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_AIR_VOLUME_B, scopeCoagTissueVolumeB.GetID())

    scopeCoagAirVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_B)
    if scopeCoagAirVolumeB is None:
      scopeCoagAirVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode",
                                                               self.SCOPE_COAG_TISSUE_VOLUME_B)
      scopeCoagAirVolumeB.SetOrigin([0, 0, 0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagAirVolumeB.SetSpacing([1, 1, 1])
      scopeCoagAirVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagAirVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_TISSUE_VOLUME_B, scopeCoagAirVolumeB.GetID())

  def setupPlusServer(self):
    """
    Creates PLUS server and OpenIGTLink connection if it doesn't exist already.
    """
    parameterNode = self.getParameterNode()

    # Check if config file is specified in settings. Set and use default if not.

    configFullpath = slicer.util.settingsValue(self.CONFIG_FILE_SETTING, '')
    if configFullpath == '':
      configFullpath = self.resourcePath(self.CONFIG_FILE_DEFAULT)
      settings = qt.QSettings()
      settings.setValue(self.CONFIG_FILE_SETTING, configFullpath)

    # Make sure text node for config file exists

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

    # Make sure PLUS server and launcher exist, and launcher references server

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

    # TODO: may not be the right way to start server?
    plusRemoteNode = parameterNode.GetNodeReference(self.PLUS_REMOTE_NODE)
    if not plusRemoteNode:
      plusRemoteNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLIGTLConnectorNode", self.PLUS_REMOTE_NODE)
      plusRemoteNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.PLUS_REMOTE_NODE, plusRemoteNode.GetID())

  def displayFftResults(self):
    #logging.info('setDisplaySampleGraphButton')

    time, ChA, ChB = self.getOscilloscopeChannels()
    print(self.fftFreqAmpSingle(ChA))
    '''
    time, ChA, ChB = self.getOscilloscopeChannels()
    time = np.array(time)
    ChA = np.transpose(np.array(ChA))
    ChB = np.transpose(np.array(ChB))
    plt.plot(time, ChA, time, ChB)
    plt.title("Coagulate Air")
    plt.xlabel("time (us)")
    plt.ylabel("Voltage (V)")
    plt.savefig("D:\Research\Oscilloscope\Saved Burns\Saved Figures\ChA_Array.png")
    plt.clf()
    '''

  def getOscilloscopeChannels(self):
    #logging.info("getOscilloscopeChannels")
    parameterNode = self.getParameterNode()
    oscilloscopeVolume = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    oscilloscopeArray = slicer.util.arrayFromVolume(oscilloscopeVolume)
    #TODO: create parameter node reference for arrays.
    time = oscilloscopeArray[0,0]
    ChA = oscilloscopeArray[0,1]
    ChB = oscilloscopeArray[0,2]
    #TODO: create parameter node reference for arrays.
    return time, ChA, ChB

  def scopeSignalModified(self, caller, eventid):

    #logging.info('scopeSignalModified')
    plotchart = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLPlotChartNode')
    plotseries = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLPlotSeriesNode')
    table = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLTableNode')
    slicer.mrmlScene.RemoveNode(plotchart)
    slicer.mrmlScene.RemoveNode(plotseries)
    slicer.mrmlScene.RemoveNode(table)
    time, ChA, ChB = self.getOscilloscopeChannels()
    ChA_Array = np.array([time, ChA])
    ChA_Array = np.transpose(ChA_Array)
    ChA_ChartNode = slicer.util.plot(ChA_Array, 0)
    layoutManager = slicer.app.layoutManager()
    layoutWithPlot = slicer.modules.plots.logic().GetLayoutWithPlot(layoutManager.layout)
    layoutManager.setLayout(layoutWithPlot)
    plotWidget = layoutManager.plotWidget(0)
    plotViewNode = plotWidget.mrmlPlotViewNode()
    plotViewNode.SetPlotChartNodeID(ChA_ChartNode.GetID())

    import time
    print("time:", time.time())


  def setStreamGraphButton(toggled):
    logging.info('setStreamGraphButton')
    #if toggled:
    #add observer

    #else:
    #remove observer
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Inver t"):
      parameterNode.SetParameter("Invert", "false")

  def setCollectOff(self, recording):
    # logging.info("setCollectOff")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_OFF_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop
    return

  def setCollectCutAir(self, recording):
    # logging.info("setCollectCutAir")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop

  def setCollectCutTissue(self, recording):
    # logging.info("setCollectCutTissue")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop

  def setCollectCoagAir(self, recording):
    # logging.info("setCollectCoagAir")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop

  def setCollectCoagTissue(self, recording):
    # logging.info("setCollectCoagTissue")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording)  # stop

  def setTrainAndImplementModel(self):
    logging.info("setTrainAndImplementModel")
    parameterNode = self.getParameterNode()
    collectOffSeqBr = parameterNode.GetNodeReference(self.COLLECT_OFF_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectOffSeqBr.GetNumberOfItems()
    collectOffSeqBr.SelectFirstItem()
    channelACollectOff = np.empty([n, 3900])
    channelBCollectOff = np.empty([n, 3900])
    featureCollectOff = np.empty([n, 6])
    Y_CollectOff = np.full((n, 1), 0)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0, 1]
      ChB = oscilloscopeArray[0, 2]
      channelACollectOff[i] = ChA
      channelBCollectOff[i] = ChB
      # TODO: take this outside the for loop
      featureCollectOff[i][0] = self.lmrSum(ChA, ChB)
      featureCollectOff[i][1] = self.maximum(ChB)
      featureCollectOff[i][2] = self.fftPeakFreq(ChA)
      featureCollectOff[i][3] = self.fftPeakAmp(ChA)
      featureCollectOff[i][4] = self.absSum(ChA)
      featureCollectOff[i][5] = self.absSum(ChB)
      item = collectOffSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    np.save("D:/Research/Oscilloscope/featureCollectOff.npy", featureCollectOff)
    np.save("D:/Research/Oscilloscope/channelACollectOff.npy", channelACollectOff)
    np.save("D:/Research/Oscilloscope/channelBCollectOff.npy", channelBCollectOff)

    collectCutAirSeqBr = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCutAirSeqBr.GetNumberOfItems()
    collectCutAirSeqBr.SelectFirstItem()
    channelACollectCutAir = np.empty([n, 3900])
    channelBCollectCutAir = np.empty([n, 3900])
    featureCollectCutAir = np.empty([n, 6])
    Y_CollectCutAir = np.full((n, 1), 1)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0, 1]
      ChB = oscilloscopeArray[0, 2]
      channelACollectCutAir[i] = ChA
      channelBCollectCutAir[i] = ChB
      featureCollectCutAir[i][0] = self.lmrSum(ChA, ChB)
      featureCollectCutAir[i][1] = self.maximum(ChB)
      featureCollectCutAir[i][2] = self.fftPeakFreq(ChA)
      featureCollectCutAir[i][3] = self.fftPeakAmp(ChA)
      featureCollectCutAir[i][4] = self.lmrSum(ChA, ChB)
      featureCollectCutAir[i][5] = self.maximum(ChB)
      collectCutAirSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    np.save("D:/Research/Oscilloscope/featureCollectCutAir.npy", featureCollectCutAir)
    np.save("D:/Research/Oscilloscope/channelACollectCutAir.npy", channelACollectCutAir)
    np.save("D:/Research/Oscilloscope/channelBCollectCutAir.npy", channelBCollectCutAir)

    collectCutTissueSeqBr = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCutTissueSeqBr.GetNumberOfItems()
    collectCutTissueSeqBr.SelectFirstItem()
    channelACollectCutTissue = np.empty([n, 3900])
    channelBCollectCutTissue = np.empty([n, 3900])
    featureCollectCutTissue = np.empty([n, 6])
    Y_CollectCutTissue = np.full((n, 1), 2)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0, 1]
      ChB = oscilloscopeArray[0, 2]
      channelACollectCutTissue[i] = ChA
      channelBCollectCutTissue[i] = ChB
      featureCollectCutTissue[i][0] = self.lmrSum(ChA, ChB)
      featureCollectCutTissue[i][1] = self.maximum(ChB)
      featureCollectCutTissue[i][2] = self.fftPeakFreq(ChA)
      featureCollectCutTissue[i][3] = self.fftPeakAmp(ChA)
      featureCollectCutTissue[i][4] = self.maximum(ChB)
      featureCollectCutTissue[i][5] = self.maximum(ChB)
      collectCutTissueSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)

    np.save("D:/Research/Oscilloscope/featureCollectCutTissue.npy", featureCollectCutTissue)
    np.save("D:/Research/Oscilloscope/channelACollectCutTissue.npy", channelACollectCutTissue)
    np.save("D:/Research/Oscilloscope/channelBCollectCutTissue.npy", channelBCollectCutTissue)

    collectCoagAirSeqBr = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCoagAirSeqBr.GetNumberOfItems()
    collectCoagAirSeqBr.SelectFirstItem()
    channelACollectCoagAir = np.empty([n, 3900])
    channelBCollectCoagAir = np.empty([n, 3900])
    featureCollectCoagAir = np.empty([n, 6])
    Y_CollectCoagAir = np.full((n, 1), 3)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0, 1]
      ChB = oscilloscopeArray[0, 2]
      channelACollectCoagAir[i] = ChA
      channelBCollectCoagAir[i] = ChB
      featureCollectCoagAir[i][0] = self.lmrSum(ChA, ChB)
      featureCollectCoagAir[i][1] = self.maximum(ChB)
      featureCollectCoagAir[i][2] = self.fftPeakFreq(ChA)
      featureCollectCoagAir[i][3] = self.fftPeakAmp(ChA)
      featureCollectCoagAir[i][4] = self.lmrSum(ChA, ChB)
      featureCollectCoagAir[i][5] = self.maximum(ChB)
      collectCoagAirSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)

    np.save("D:/Research/Oscilloscope/featureCollectCoagAir.npy", featureCollectCoagAir)
    np.save("D:/Research/Oscilloscope/channelACollectCoagAir.npy", channelACollectCoagAir)
    np.save("D:/Research/Oscilloscope/channelBCollectCoagAir.npy", channelBCollectCoagAir)

    collectCoagTissueSeqBr = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCoagTissueSeqBr.GetNumberOfItems()
    collectCoagTissueSeqBr.SelectFirstItem()
    channelACollectCoagTissue = np.empty([n, 3900])
    channelBCollectCoagTissue = np.empty([n, 3900])
    featureCollectCoagTissue = np.empty([n, 6])
    Y_CollectCoagTissue = np.full((n, 1), 4)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0, 1]
      ChB = oscilloscopeArray[0, 2]
      channelACollectCoagTissue[i] = ChA
      channelBCollectCoagTissue[i] = ChB
      featureCollectCoagTissue[i][0] = self.lmrSum(ChA, ChB)
      featureCollectCoagTissue[i][1] = self.maximum(ChB)
      featureCollectCoagTissue[i][2] = self.fftPeakFreq(ChA)
      featureCollectCoagTissue[i][3] = self.fftPeakAmp(ChA)
      featureCollectCoagTissue[i][4] = self.lmrSum(ChA, ChB)
      featureCollectCoagTissue[i][5] = self.maximum(ChB)
      collectCoagTissueSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    np.save("D:/Research/Oscilloscope/featureCollectCoagTissue.npy", featureCollectCoagTissue)
    np.save("D:/Research/Oscilloscope/channelACollectCoagTissue.npy", channelACollectCoagTissue)
    np.save("D:/Research/Oscilloscope/channelBCollectCoagTissue.npy", channelBCollectCoagTissue)

    # append arrays, build X and Y\
    features = np.append(featureCollectOff[:, 2:5], featureCollectCutAir[:, 2:5], axis=0)
    features = np.append(features, featureCollectCutTissue[:, 2:5], axis=0)
    features = np.append(features, featureCollectCoagAir[:, 2:5], axis=0)
    features = np.append(features, featureCollectCoagTissue[:, 2:5], axis=0)
    Y = np.append(Y_CollectOff, Y_CollectCutAir)
    Y = np.append(Y, Y_CollectCutTissue)
    Y = np.append(Y, Y_CollectCoagAir)
    Y = np.append(Y, Y_CollectCoagTissue)

    np.save("D:/Research/Oscilloscope/Y_collections.npy", Y)

    print("collect off")
    print(featureCollectOff)
    print("coag air")
    print(featureCollectCoagAir)
    print("coag tissue")
    print(featureCollectCoagTissue)
    self.buildScopeModel(features, Y)

  def buildScopeModel(self, features, Y):
    logging.info("buildScopeModel")
    X_training, X_test, Y_train, Y_test = train_test_split(features, Y, test_size=0.2)

    ##svc = svm.LinearSVC().fit(X_training, Y_train)
    svc = svm.SVC(kernel = 'linear', decision_function_shape='ovo').fit(X_training, Y_train) #kernel = 'linear', C=1.0
    # lin =
    # rbf = svm.SVC(kernel = 'rbf', gamma = 0.9, C=1.0).fit(X_training, Y_train)
    # poly = svm.SVC(kernel = 'poly', degree = 3, C = 1.0).fit(X_training, Y_train)

    filename_svc = "D:\Research\Oscilloscope\cauteryModelSVM_svc.sav"
    # filename_lin = "D:\Research\Oscilloscope\cauteryModelSVM_lin.sav"
    # filename_rbf = "D:\Research\Oscilloscope\cauteryModelSVM_rbf.sav"
    # filename_poly = "D:\Research\Oscilloscope\cauteryModelSVM_poly.sav"

    pickle.dump(svc, open(filename_svc, "wb"))
    # pickle.dump(lin, open(filename_lin, "wb"))
    # pickle.dump(rbf, open(filename_rbf, "wb"))
    # pickle.dump(poly, open(filename_poly, "wb"))

    loaded_module_svc = pickle.load(open(filename_svc, "rb"))
    # loaded_module_lin = pickle.load(open(filename_lin, "rb"))
    # loaded_module_rbf = pickle.load(open(filename_rbf, "rb"))
    # loaded_module_poly = pickle.load(open(filename_poly, "rb"))

    result = loaded_module_svc.score(X_test, Y_test)
    predict = loaded_module_svc.predict(X_test)
    print("----SVC------")
    print("Prediction", predict)
    print("Y test", Y_test)
    print("result", result)

    # print("-----LIN------")
    # result = loaded_module_lin.score(X_test, Y_test)
    # predict = loaded_module_lin.predict(X_test)
    # print("Prediction", predict)
    # print("Y test", Y_test)
    # print("result", result)
    # print("-----RBF------")
    # result = loaded_module_rbf.score(X_test, Y_test)
    # predict = loaded_module_rbf.predict(X_test)
    # print("Prediction", predict)
    # print("Y test", Y_test)
    # print("result", result)
    # np.save("D:/Research/Oscilloscope/features.npy", features)
    # np.save("D:/Research/Oscilloscope/Y.npy", Y)
    # print("-----POLY------")
    # result_poly = loaded_module_poly.score(X_test, Y_test)
    # predict_poly = loaded_module_poly.predict(X_test)
    # print("Prediction", predict_poly)
    # print("Y test", Y_test)
    # print("result", result_poly)

    # h = 0.02  # step size in the mesh
    #
    # # create a mesh to plot in
    #
    # X_train_min, X_train_max = X_training[:,0].min() - 1, X_training[:,0].max() + 1
    # Y_train_min, Y_train_max = X_training[:,1].min() - 1, X_training[:,1].max() + 1
    # X_train, yy = np.meshgrid(np.float32(np.arange(X_train_min, X_train_max, h)), np.float32(np.arange(Y_train_min, Y_train_max, h)))
    # # title for the plots
    # titles = ['SVC with linear kernel',
    #     'LinearSVC (linear kernel)',
    #       'SVC with RBF kernel',
    #       'SVC with polynomial (degree 3) kernel']
    #
    # for i, clf in enumerate((svc, lin_svc, rbf_svc, poly_svc)):
    #   # Plot the decision boundarY_train. For that, we will assign a color to each
    #   # point in the mesh [X_train_min, X_train_max]X_train[Y_train_min, Y_train_max].

    #
    #   plt.subplot(2, 2, i + 1)
    #   plt.subplots_adjust(wspace=0.4, hspace=0.4)
    #
    #   Z = clf.predict(np.c_[X_train.ravel(), yy.ravel()])
    #
    #   # Put the result into a color plot
    #   Z = Z.reshape(X_train.shape)
    #   plt.contourf(X_train, yy, Z, cmap=plt.cm.coolwarm, alpha=0.8)
    #
    #   # Plot also the training points
    #   plt.scatter(X_training[:,0], X_training[:,1], c = Y_train, cmap=plt.cm.coolwarm)
    #   plt.xlabel('lmr')
    #   plt.ylabel('mMean')
    #   plt.xlim(X_train.min(), X_train.max())
    #   plt.ylim(yy.min(), yy.max())
    #   plt.xticks(())
    #   plt.yticks(())
    #   plt.title(titles[i])
    #   plot_decision_regions(X_training, Y_train, clf = clf, legend=2)
    #   d = {"Off": 0, "CutAir": 1, "CutTissue": 2, "CoagAir": 3, "CoagTissue": 4}
    #   handles, labels =  plt.gca().get_legend_handles_labels()
    #   d_rev = {y:x for x,y in d.items()}
    #   plt.legend(handles, list(map(d_rev.get, [int(i) for i in d_rev])))

    # plt.savefig('/Users/Josh Ehrlich/Desktop/SVM.png')

    # #save arrays as volume
    # scopeOffVolumeA = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_A)
    # vtkGrayscale = numpy_support.numpy_to_vtk(channelACollectOff.flatten(order='C'), deep=True, array_type=vtk.VTK_DOUBLE)
    # # Convert the image to vtkImageData object
    # sliceImageData = vtk.vtkImageData()
    # sliceImageData.SetDimensions(len(channelACollectOff[0]), len(channelACollectOff), 1)
    # sliceImageData.SetOrigin(0.0, 0.0, 0.0)
    # sliceImageData.GetPointData().SetScalars(vtkGrayscale)
    # scopeOffVolumeA.SetAndObserveImageData(sliceImageData)

    # scopeOffVolumeB = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_B)
    # vtkGrayscale = numpy_support.numpy_to_vtk(channelACollectOff.flatten(order='C'), deep=True, array_type=vtk.VTK_DOUBLE)
    # # Convert the image to vtkImageData object
    # sliceImageData = vtk.vtkImageData()
    # sliceImageData.SetDimensions(len(channelACollectOff[0]), len(channelACollectOff), 1)
    # sliceImageData.SetOrigin(0.0, 0.0, 0.0)
    # sliceImageData.GetPointData().SetScalars(vtkGrayscale)
    # scopeOffVolumeB.SetAndObserveImageData(sliceImageData)

    # self.buildScopeModel()

  # def buildScopeModel(self):
  #   parameterNode = self.getParameterNode()
  #   scopeOffVolumeA = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_A)
  #   scopeOffArrayA = slicer.util.arrayFromVolume(scopeOffVolumeA)
  #   scopeCutAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_A)
  #   scopeCutAirArrayA = slicer.util.arrayFromVolume(scopeCutAirVolumeA)
  #   scopeCutTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_A)
  #   scopeCutTissueArrayA = slicer.util.arrayFromVolume(scopeCutTissueVolumeA)
  #   scopeCoagAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_A)
  #   scopeCoagAirArrayA = slicer.util.arrayFromVolume(scopeCoagAirVolumeA)
  #   scopeCoagTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_A)
  #   scopeCoagTissueArrayA = slicer.util.arrayFromVolume(scopeCoagTissueVolumeA)

  #   scopeOffVolumeB = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_B)
  #   scopeOffArrayB = slicer.util.arrayFromVolume(scopeOffVolumeB)
  #   scopeCutAirVolumeB = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_B)
  #   scopeCutAirArrayB = slicer.util.arrayFromVolume(scopeCutAirVolumeB)
  #   scopeCutTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_B)
  #   scopeCutTissueArrayB = slicer.util.arrayFromVolume(scopeCutTissueVolumeB)
  #   scopeCoagAirVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_B)
  #   scopeCoagAirArrayB = slicer.util.arrayFromVolume(scopeCoagAirVolumeB)
  #   scopeCoagTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_B)
  #   scopeCoagTissueArrayB = slicer.util.arrayFromVolume(scopeCoagTissueVolumeB)

  def setUseModelClicked(self, clicked):
    parameterNode = self.getParameterNode()
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    if clicked:
      self.addObserver(signal_Signal, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.useModelModified)
    else:
      self.removeObserver(signal_Signal, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent,
                          self.useModelModified)

  def useModelModified(self, observer, eventID):
    #TODO: is there a better way to load and run the model?
    scriptPath = os.path.dirname(os.path.abspath(__file__))
    modelsPath = str(scriptPath) + "\Models"
    fileName_SVM = modelsPath + "\April1_apple_40W_20000_SVM.sav"
    fileName_RF = modelsPath + "\April1_apple_40W_20000_RF.sav"
    svm = pickle.load(open(fileName_SVM, "rb"))
    rf = pickle.load(open(fileName_RF, "rb"))
    parameterNode = self.getParameterNode()
    oscilloscopeVolume = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    oscilloscopeArray = slicer.util.arrayFromVolume(oscilloscopeVolume)
    oscilloscopeArray = slicer.util.arrayFromVolume(oscilloscopeVolume)
    ChA = oscilloscopeArray[0, 1]
    fs = 4e3
    x = ChA
    maxVoltage = np.max(x)
    X = detrend(x)
    X = resample(X, int(fs * 0.1))
    t = np.linspace(0, 0.1, int(fs * 0.1))
    F = rfftfreq(len(X), 1 / fs)
    X = np.abs(rfft(X))
    maxFreq = np.max(X)
    index = np.where(X == maxFreq)
    amplitude = F[index][0]
    sumX = np.sum(X)
    features = np.empty([1, 3])
    features[0][0] = maxVoltage
    features[0][1] = maxFreq
    features[0][2] = amplitude
    print(maxVoltage, maxFreq, amplitude)
    predict_svm = svm.predict(features)
    predict_rf = rf.predict(features)
    print("Prediction", predict_svm)
    print("Prediction", predict_rf)

  def mean(self, channel):
    mean = np.mean(channel)
    return mean

  def fft(self, channel):
    frequency = np.mean((np.fft.fft(channel))).real
    return frequency

  def testFreq(self, channel):
    testFreq = sy.fft(channel).real
    return testFreq

  def minumum(self, channel):
    minimum = np.minimum(channel)
    return minimum

  def maximum(self, channel):
    maximum = np.amax(channel)
    return maximum

  def absSum(self, channel):
    absSum = np.sum(np.absolute(channel))
    return absSum

  def absMean(self, channel):
    absMean = np.mean(np.absolute(channel))
    return absMean

  def stdev(self, channel):
    stdev = np.std(channeL)
    return stdev

  def absStdev(self, channel):
    absStdev = ((np.std(np.absolute(channel))) * 100)
    return absStdev

  def lmrSum(self, channelA, channelB):
    lmrSum = (self.absSum(channelB) - self.absSum(channelA))
    return lmrSum

  def lmrMean(self, channelA, channelB):
    lmrMean = (self.absMean(channelA - channelB)) * 10000
    return lmrMean

  def mMean(self, channelA, channelB):
    mMean = (self.absMean(channelA) * self.absSum(channelB)) * 100
    return mMean

  def fftFreqAmpSingle(self, channelA):
    fs = 4e3
    x = channelA
    x = detrend(x)
    x = resample(x, int(fs * 0.1))
    t = np.linspace(0, 0.1, int(fs * 0.1))
    F = rfftfreq(len(x), 1 / fs)
    X = np.abs(rfft(x))
    maxFreq = np.max(X)
    index = np.where(X == maxFreq)
    amplitude = F[index][0]
    return [maxFreq,amplitude]

  def fftPeakFreq(self, channelA):
    fs = 4e3
    x = channelA
    x = detrend(x)
    x = resample(x, int(fs * 0.1))
    t = np.linspace(0, 0.1, int(fs * 0.1))
    F = rfftfreq(len(x), 1 / fs)
    X = np.abs(rfft(x))
    maxFreq = np.max(X)
    index = np.where(X == maxFreq)
    amplitude = F[index][0]
    return maxFreq

  def fftPeakAmp(self, channelA):
    fs = 4e3
    x = channelA
    x = detrend(x)
    x = resample(x, int(fs * 0.1))
    t = np.linspace(0, 0.1, int(fs * 0.1))
    F = rfftfreq(len(x), 1 / fs)
    X = np.abs(rfft(x))
    maxFreq = np.max(X)
    index = np.where(X == maxFreq)
    amplitude = F[index][0]
    return amplitude

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
    logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')

#
# CauteryClassificationTest
#

class CauteryClassificationTest(ScriptedLoadableModuleTest):
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
    self.test_CauteryClassification1()

  def test_CauteryClassification1(self):
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
    inputVolume = SampleData.downloadSample('CauteryClassification1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = CauteryClassificationLogic()

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
