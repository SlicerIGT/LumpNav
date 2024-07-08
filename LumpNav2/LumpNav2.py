import os
import datetime
import time
import json
from packaging import version

import numpy as np
import vtk, qt, ctk, slicer

import logging
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import Viewpoint

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

try:
  from mlxtend.plotting import plot_decision_regions
except:
  slicer.util.pip_install('mlxtend')
  from mlxtend.plotting import plot_decision_regions

try:
  import pandas as pd
except:
  slicer.util.pip_install('pandas')
  import pandas as pd

#
# LumpNav2
#


class LumpNav2(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "LumpNav2"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Perk Lab (Queen's University)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#LumpNav2">module documentation</a>.
"""
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

  # Variables to store widget state
  SLICER_RECOMMENDED_VERSION = "5.0.0"
  SLICER_INTERFACE_VISIBLE = "LumpNav2/SlicerInterfaceVisible"
  NORMAL_BRIGHTNESS = 300
  BRIGHT_BRIGHTNESS = 220
  BRIGHTEST_BRIGHTNESS = 140
  FONT_SIZE_DEFAULT = 20
  VIEW_COORD_HEIGHT_LIMIT = 0.6
  VIEW_COORD_WIDTH_LIMIT = 0.9
  SAVE_FOLDER_SETTING = "LumpNav2/LastSaveFolder"

  # Tool calibration
  PIVOT_CALIBRATION = 0
  SPIN_CALIBRATION = 1
  PIVOT_CALIBRATION_TIME_SEC = 5.0
  CAUTERY_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/CauteryCalibrationThresholdMm"
  CAUTERY_CALIBRATION_THRESHOLD_DEFAULT = 1.0
  LAST_PIVOT_CALIBRATION_RESULT = "LastPivotCalibrationResult"
  NEEDLE_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/NeedleCalibrationThresholdMm"
  NEEDLE_CALIBRATION_THRESHOLD_DEFAULT = 1.0

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    slicer.mymodW = self  # then in python interactor, call "self = slicer.mymod" to use
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    self._updatingGUIFromMRML = False
    self._updatingGui = False
    self.saveTime = vtk.vtkTimeStamp()
    self.observedNeedleModel = None
    self.observedCauteryModel = None
    self.observedTrackingSeqBrNode = None
    self.observedUltrasoundSeqBrNode = None
    self.observedEventTableNode = None
    self.observedPlusServerLauncherNode = None

    # Timer for pivot calibration controls
    self.pivotCalibrationLogic = slicer.modules.pivotcalibration.logic()
    self.pivotCalibrationStopTime = 0
    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(1000)
    self.pivotSamplingTimer.setSingleShot(False)
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION  # Default value, but it is always set when starting pivot calibration
    self.pivotCalibrationResultNode = None

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    # Check Slicer version and display message if older than recommended
    currentSlicerVersion = str(slicer.app.mainApplicationMajorVersion) + "." + \
                           str(slicer.app.mainApplicationMinorVersion) + "." + \
                           str(slicer.app.mainApplicationPatchVersion)
    if version.parse(currentSlicerVersion) < version.parse(self.SLICER_RECOMMENDED_VERSION):
      msg = qt.QMessageBox()
      msg.setIcon(qt.QMessageBox.Information)
      msg.setTextFormat(qt.Qt.RichText)
      msg.setText(f"Current 3D Slicer version ({currentSlicerVersion}) is older than the recommended version "
                  f"({self.SLICER_RECOMMENDED_VERSION}). This may lead to unexpected behaviour.")
      msg.setInformativeText("3D Slicer releases can be downloaded <a href='https://download.slicer.org/'>here</a>.")
      msg.setWindowTitle("3D Slicer")
      msg.setStandardButtons(qt.QMessageBox.Ok)
      msg.setModal(True)
      msg.exec()

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
    self.logic.updateRecordingTimeCallback = self.updateRecordingTimeLabel
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
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartImportEvent, self.onSceneStartImport)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndImportEvent, self.onSceneEndImport)

    # QT connections
    self.ui.toolsCollapsibleButton.connect('contentsCollapsed(bool)', self.onToolsCollapsed)
    self.ui.contouringCollapsibleButton.connect('contentsCollapsed(bool)', self.onContouringCollapsed)
    self.ui.navigationCollapsibleButton.connect('contentsCollapsed(bool)', self.onNavigationCollapsed)
    self.ui.eventRecordingCollapsibleButton.connect('contentsCollapsed(bool)', self.onEventRecordingCollapsed)

    # Tool calibration
    self.ui.cauteryCalibrationButton.connect('clicked()', self.onCauteryCalibrationButton)
    self.ui.undoCauteryCalibrationButton.connect('clicked()', self.onUndoCauteryCalibrationClicked)
    self.ui.needleMinusFiveButton.connect('clicked()', self.onNeedleMinusFiveClicked)
    self.ui.needleMinusOneButton.connect('clicked()', self.onNeedleMinusOneClicked)
    self.ui.needlePlusOneButton.connect('clicked()', self.onNeedlePlusOneClicked)
    self.ui.needlePlusFiveButton.connect('clicked()', self.onNeedlePlusFiveClicked)
    needleLength = self.logic.getNeedleLength()
    self.ui.needleLengthLabel.text = f"Needle length: {needleLength:.0f}mm"

    # contouring
    self.ui.brightnessButtonGroup.buttonClicked.connect(self.onBrightnessButtonClicked)
    self.ui.depthButtonGroup.buttonClicked.connect(self.onDepthButtonClicked)
    self.ui.normalDepthButton.checked = True
    self.ui.anteriorDistToMarginSpinBox.connect('valueChanged(double)', self.onAnteriorDistToMarginChanged)
    self.ui.posteriorDistToMarginSpinBox.connect('valueChanged(double)', self.onPosteriorDistToMarginChanged)
    self.ui.leftDistToMarginSpinBox.connect('valueChanged(double)', self.onLeftDistToMarginChanged)
    self.ui.rightDistToMarginSpinBox.connect('valueChanged(double)', self.onRightDistToMarginChanged)
    self.ui.superiorDistToMarginSpinBox.connect('valueChanged(double)', self.onSuperiorDistToMarginChanged)
    self.ui.inferiorDistToMarginSpinBox.connect("valueChanged(double)", self.onInferiorDistToMarginChanged)
    self.ui.placeHydromarkButton.connect('toggled(bool)', self.onPlaceHydromarkToggled)
    self.ui.deleteHydromarkButton.connect('clicked()', self.onDeleteHydromarkClicked)
    hydromarkVisibility = slicer.util.settingsValue(self.logic.HYDROMARK_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    self.ui.hydromarkVisibility2DButton.checked = hydromarkVisibility
    self.ui.hydromarkVisibility2DButton.connect('toggled(bool)', self.onHydromarkVisibilityToggled)
    self.ui.markPointsButton.connect('toggled(bool)', self.onMarkPointsToggled)
    self.ui.deleteLastFiducialButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.ui.deleteAllFiducialsButton.connect('clicked()', self.onDeleteAllFiducialsClicked)
    self.ui.selectPointsToEraseButton.connect('toggled(bool)', self.onErasePointsToggled)
    self.ui.markPointCauteryTipButton.connect('clicked()', self.onMarkPointCauteryTipClicked)
    self.ui.startStopRecordingButton.connect('toggled(bool)', self.onStartStopRecordingClicked)
    self.ui.freezeUltrasoundButton.connect('toggled(bool)', self.onFreezeUltrasoundClicked)
    self.ui.applyDilationButton.connect('clicked()', self.onApplyDilationClicked)
    self.pivotSamplingTimer.connect('timeout()', self.onPivotSamplingTimeout)

    # navigation
    self.ui.leftBreastButton.connect('clicked()', self.onLeftBreastButtonClicked)
    self.ui.rightBreastButton.connect('clicked()', self.onRightBreastButtonClicked)
    displayRulerEnabled = slicer.util.settingsValue(self.logic.DISPLAY_RULER_SETTING, True, converter=slicer.util.toBool)
    self.ui.displayRulerButton.checked = displayRulerEnabled
    self.ui.displayRulerButton.connect('toggled(bool)', self.onDisplayRulerButtonClicked)
    displayDistanceEnabled = slicer.util.settingsValue(self.logic.DISPLAY_DISTANCE_SETTING, True, converter=slicer.util.toBool)
    self.ui.displayDistanceButton.checked = displayDistanceEnabled
    self.ui.displayDistanceButton.connect('toggled(bool)', self.onDisplayDistanceClicked)
    self.ui.increaseDistanceFontSizeButton.connect('clicked()', self.onIncreaseDistanceFontSizeClicked)
    self.ui.decreaseDistanceFontSizeButton.connect('clicked()', self.onDecreaseDistanceFontSizeClicked)
    self.ui.leftAutoCenterCameraButton.connect('toggled(bool)', self.onLeftAutoCenterCameraButtonClicked)
    self.ui.rightAutoCenterCameraButton.connect('toggled(bool)', self.onRightAutoCenterCameraButtonClicked)
    self.ui.bottomAutoCenterCameraButton.connect('toggled(bool)', self.onBottomAutoCenterCameraButtonClicked)
    self.ui.leftCauteryCameraButton.connect('toggled(bool)', self.onLeftCauteryCameraButtonClicked)
    self.ui.rightCauteryCameraButton.connect('toggled(bool)', self.onRightCauteryCameraButtonClicked)
    self.ui.bottomCauteryCameraButton.connect('toggled(bool)', self.onBottomCauteryCameraButtonClicked)
    self.ui.deleteLastFiducialNavigationButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    cauteryToolSelected = slicer.util.settingsValue(self.logic.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    self.ui.toolModelButton.setChecked(cauteryToolSelected)
    self.ui.toolModelButton.connect('toggled(bool)', self.onToolModelClicked)
    self.ui.threeDViewButton.connect('toggled(bool)', self.onDual3DViewButton)
    breachMarkupsDisplayEnabled = slicer.util.settingsValue(self.logic.BREACH_MARKUPS_DISPLAY_SETTING, True, converter=slicer.util.toBool)
    self.ui.breachLocationButton.checked = breachMarkupsDisplayEnabled
    self.ui.breachLocationButton.connect('toggled(bool)', self.onBreachLocationButtonClicked)
    self.ui.deleteTumorBreachButton.connect('clicked()', self.onDeleteTumorBreachButtonClicked)
    self.ui.increaseBreachFiducialSize.connect('clicked()', self.onIncreaseBreachFiducialSize)
    self.ui.decreaseBreachFiducialSize.connect('clicked()', self.onDecreaseBreachFiducialSize)
    # Event recording
    self.ui.eventTable.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
    self.ui.eventTable.connect('selectionChanged()', self.onEventSelectionChanged)
    self.ui.addEventButton.connect('clicked()', self.onAddEventButtonClicked)
    self.ui.deleteEventButton.connect('clicked()', self.onDeleteEventButtonClicked)
    self.ui.eventTableExportButton.connect('clicked()', self.onEventTableExportClicked)

    # settings panel
    self.ui.customUiButton.connect('toggled(bool)', self.onCustomUiClicked)
    self.ui.startPlusButton.connect('toggled(bool)', self.onStartPlusClicked)
    self.ui.displayRASButton.connect('toggled(bool)', self.onDisplayRASClicked)
    self.ui.displayCauteryStateButton.connect('toggled(bool)', self.onDisplayCauteryStateClicked)
    needleVisibilitySetting = slicer.util.settingsValue(self.logic.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    self.ui.needleVisibilityButton.checked = needleVisibilitySetting
    self.ui.needleVisibilityButton.connect('toggled(bool)', self.onNeedleVisibilityToggled)
    self.ui.trackingSequenceBrowserButton.connect('toggled(bool)', self.onTrackingSequenceBrowser)
    cauteryVisible = slicer.util.settingsValue(self.logic.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    self.ui.cauteryVisibilityButton.checked = cauteryVisible
    self.ui.cauteryVisibilityButton.connect('toggled(bool)', self.onCauteryVisibilityToggled)
    warningSoundEnabled = slicer.util.settingsValue(self.logic.WARNING_SOUND_SETTING, True, converter=slicer.util.toBool)
    self.ui.warningSoundButton.checked = warningSoundEnabled
    self.ui.warningSoundButton.connect('toggled(bool)', self.onWarningSoundToggled)
    breachMarkupsProximityThreshold = slicer.util.settingsValue(self.logic.BREACH_MARKUPS_PROXIMITY_THRESHOLD, 1, converter=lambda x: int(x))
    self.ui.breachMarkupsThresholdSpinBox.value = breachMarkupsProximityThreshold
    self.ui.breachMarkupsThresholdSpinBox.connect('valueChanged(int)', self.onBreachMarkupsProximityChanged)
    self.ui.exitButton.connect('clicked()', self.onExitButtonClicked)
    self.ui.saveSceneButton.connect('clicked()', self.onSaveSceneClicked)
    lastSavePath = slicer.util.settingsValue(self.SAVE_FOLDER_SETTING, os.path.dirname(slicer.util.modulePath(self.logic.moduleName)))
    self.ui.saveFolderSelector.directory = lastSavePath
    self.ui.saveFolderSelector.connect('directoryChanged(const QString)', self.onSavePathChanged)
    lastHostname = slicer.util.settingsValue(self.logic.HOSTNAME_SETTING, "")
    if lastHostname != "":
      self.ui.hostnameLineEdit.text = lastHostname
    self.ui.hostnameLineEdit.connect('editingFinished()', self.onHostnameChanged)
    configFilepath = slicer.util.settingsValue(self.logic.CONFIG_FILE_SETTING, self.logic.resourcePath(self.logic.CONFIG_FILE_DEFAULT))
    self.ui.plusConfigFileSelector.currentPath = configFilepath
    self.ui.plusConfigFileSelector.connect('currentPathChanged(const QString)', self.onPlusConfigFileChanged)
    self.ui.thresholdSlider.connect("valueChanged(double)", self.onThresholdSliderChanged)
    self.ui.manualVisibilityButton.connect('toggled(bool)', self.onContourVisibilityToggled)
    self.ui.hydromarkVisibilityButton.checked = hydromarkVisibility
    self.ui.hydromarkVisibilityButton.connect('toggled(bool)', self.onHydromarkVisibilityToggled)
    self.ui.automaticVisibilityButton.connect('toggled(bool)', self.onSegmentationVisibilityToggled)
    self.ui.watchedModelButtonGroup.buttonClicked.connect(self.onWatchedModelClicked)
    self.ui.exportCsvButton.connect('clicked()', self.onExportCsvButtonClicked)

    # Add custom layouts
    self.logic.addCustomLayouts()

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

  def onCauteryCalibrationButton(self):
    logging.info('onCauteryCalibrationButton')
    cauteryToNeedle = self._parameterNode.GetNodeReference(self.logic.CAUTERY_TO_NEEDLE)
    cauteryTipToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYTIP_TO_CAUTERY)
    # Save previous pivot calibration to parameter node
    if self.pivotCalibrationResultNode:
      lastPivotCalibration = self._parameterNode.GetNodeReference(self.LAST_PIVOT_CALIBRATION_RESULT)
      if lastPivotCalibration is None:
        lastPivotCalibration = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.LAST_PIVOT_CALIBRATION_RESULT)
        self._parameterNode.SetNodeReferenceID(self.LAST_PIVOT_CALIBRATION_RESULT, lastPivotCalibration.GetID())
      pivotCalibrationResultMatrix = vtk.vtkMatrix4x4()
      self.pivotCalibrationResultNode.GetMatrixTransformToParent(pivotCalibrationResultMatrix)
      lastPivotCalibration.SetMatrixTransformToParent(pivotCalibrationResultMatrix)
    self.startPivotCalibration(cauteryToNeedle, cauteryTipToCautery)

  def startPivotCalibration(self, toolToReferenceTransformNode, toolTipToToolTransformNode):
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION
    self.ui.cauteryCalibrationButton.setEnabled(False)
    self.pivotCalibrationResultNode = toolTipToToolTransformNode
    self.pivotCalibrationLogic.SetAndObserveTransformNode(toolToReferenceTransformNode)
    self.pivotCalibrationStopTime = time.time() + self.PIVOT_CALIBRATION_TIME_SEC
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()

  def onPivotSamplingTimeout(self):
    remainingTime = self.pivotCalibrationStopTime - time.time()
    self.ui.cauteryCalibrationLabel.setText("Calibrating for {0:.0f} more seconds".format(remainingTime))
    if time.time() < self.pivotCalibrationStopTime:
      self.pivotSamplingTimer.start()  # continue
    else:
      self.pivotSamplingTimer.stop()
      self.onStopPivotCalibration()  # calibration completed

  def onStopPivotCalibration(self):
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.ui.cauteryCalibrationButton.setEnabled(True)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      calibrationSuccess = self.pivotCalibrationLogic.ComputePivotCalibration()
    else:
      calibrationSuccess = self.pivotCalibrationLogic.ComputeSpinCalibration()

    calibrationThresholdStr = slicer.util.settingsValue(
      self.CAUTERY_CALIBRATION_THRESHOLD_SETTING, self.CAUTERY_CALIBRATION_THRESHOLD_DEFAULT)
    calibrationThreshold = float(calibrationThresholdStr)

    if not calibrationSuccess:
      self.ui.cauteryCalibrationLabel.setText("Calibration failed: " + self.pivotCalibrationLogic.GetErrorText())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return

    # Warning if RMSE is too high, but still use calibration
    if self.pivotCalibrationLogic.GetPivotRMSE() >= calibrationThreshold:
      self.ui.cauteryCalibrationLabel.setText("Warning: RMSE = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))
    else:
      self.ui.cauteryCalibrationLabel.setText("Success, RMSE = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))

    toolTipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(toolTipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultNode.SetMatrixTransformToParent(toolTipToToolMatrix)

    lastPivotCalibration = self._parameterNode.GetNodeReference(self.LAST_PIVOT_CALIBRATION_RESULT)
    if lastPivotCalibration is not None:
      self.ui.undoCauteryCalibrationButton.enabled = True

    # Save calibration result so this calibration will be loaded in the next session automatically
    pivotCalibrationResultName = self.pivotCalibrationResultNode.GetName()
    pivotCalibrationFileWithPath = self.resourcePath(pivotCalibrationResultName + ".h5")
    slicer.util.saveNode(self.pivotCalibrationResultNode, pivotCalibrationFileWithPath)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      logging.info("Pivot calibration completed. Tool: {0}. RMSE = {1:.2f} mm".format(
        self.pivotCalibrationResultNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    else:
      logging.info("Spin calibration completed.")

  def onUndoCauteryCalibrationClicked(self):
    logging.info("onUndoCauteryCalibrationClicked")
    self.ui.undoCauteryCalibrationButton.enabled = False

    # Replace current calibration with previous one and save
    lastPivotCalibration = self._parameterNode.GetNodeReference(self.LAST_PIVOT_CALIBRATION_RESULT)
    lastPivotCalibrationMatrix = vtk.vtkMatrix4x4()
    lastPivotCalibration.GetMatrixTransformToParent(lastPivotCalibrationMatrix)
    self.pivotCalibrationResultNode.SetMatrixTransformToParent(lastPivotCalibrationMatrix)
    pivotCalibrationResultName = self.pivotCalibrationResultNode.GetName()
    pivotCalibrationFileWithPath = self.resourcePath(pivotCalibrationResultName + ".h5")
    slicer.util.saveNode(self.pivotCalibrationResultNode, pivotCalibrationFileWithPath)
    self.ui.cauteryCalibrationLabel.setText("Pivot calibration reverted")

  def onNeedleMinusFiveClicked(self):
    logging.info("onNeedleMinusFiveClicked")
    self.onChangeNeedleLength(-5)

  def onNeedleMinusOneClicked(self):
    logging.info("onNeedleMinusOneClicked")
    self.onChangeNeedleLength(-1)

  def onNeedlePlusOneClicked(self):
    logging.info("onNeedlePlusOneClicked")
    self.onChangeNeedleLength(1)

  def onNeedlePlusFiveClicked(self):
    logging.info("onNeedlePlusFiveClicked")
    self.onChangeNeedleLength(5)

  def onChangeNeedleLength(self, diff):
    currentOffset = slicer.util.settingsValue(
      self.logic.NEEDLE_LENGTH_OFFSET_SETTING, 0, converter=lambda x: float(x)
    )
    settings = qt.QSettings()
    settings.setValue(self.logic.NEEDLE_LENGTH_OFFSET_SETTING, currentOffset - diff)
    self.logic.setNeedleModel()

  def onExitButtonClicked(self):
    mainwindow = slicer.util.mainWindow()
    mainwindow.close()

  def onSavePathChanged(self, path):
    if path:
      abspath = os.path.abspath(path)
      self.ui.saveFolderSelector.directory = abspath
      settings = qt.QSettings()
      settings.setValue(self.SAVE_FOLDER_SETTING, abspath)
      logging.info(f"onSavePathChanged({abspath})")

  def onSaveSceneClicked(self):  # common
    # Update GUI status label
    self.ui.statusLabel.text = "Saving scene..."

    # save the mrml scene to a temp directory, then zip it
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    sceneSaveDirectory = self.ui.saveFolderSelector.directory
    sceneSaveDirectory = sceneSaveDirectory + "/" + self.logic.moduleName + "-" + time.strftime("%Y%m%d-%H%M%S")
    logging.info("Saving scene to: {0}".format(sceneSaveDirectory))
    if not os.access(sceneSaveDirectory, os.F_OK):
      os.makedirs(sceneSaveDirectory)

    applicationLogic = slicer.app.applicationLogic()
    saveSuccess = applicationLogic.SaveSceneToSlicerDataBundleDirectory(sceneSaveDirectory, None)
    qt.QApplication.restoreOverrideCursor()
    if saveSuccess:
      # Record time stamp of save
      self.saveTime.Modified()
      logging.info("Scene saved to: {0}".format(sceneSaveDirectory))
      slicer.util.showStatusMessage(f"Scene saved to {sceneSaveDirectory}.", 5000)
      self.ui.statusLabel.text = "Scene saved"
    else:
      logging.error("Scene saving failed")
      slicer.util.showStatusMessage(f"Failed to save scene to {sceneSaveDirectory}.", 5000)
      self.ui.statusLabel.text = "Scene saving failed"

  def confirmExit(self):
    msgBox = qt.QMessageBox()
    msgBox.setStyleSheet(slicer.util.mainWindow().styleSheet)
    msgBox.setWindowTitle("Confirm Exit")
    msgBox.setText("Some data may not have been saved yet.")
    msgBox.setInformativeText("Do you still want to exit?")
    saveExitButton = msgBox.addButton("Save and Exit", qt.QMessageBox.DestructiveRole)
    discardButton = msgBox.addButton("Discard and Exit", qt.QMessageBox.DestructiveRole)
    cancelButton = msgBox.addButton("Cancel", qt.QMessageBox.RejectRole)
    msgBox.setModal(True)
    msgBox.exec()

    if msgBox.clickedButton() == saveExitButton:
      # Automatically save if changes were made since last save
      if self._parameterNode.GetMTime() > self.saveTime.GetMTime():
        self.onSaveSceneClicked()
        slicer.util.infoDisplay(f"Scene saved to {self.ui.saveFolderSelector.directory}. Press OK to exit.", windowTitle="Save Scene")
      else:
        logging.info("No changes made since last save. Exiting.")
        slicer.util.showStatusMessage("No changes made since last save. Exiting.", 5000)
        slicer.util.infoDisplay("No changes made since last save. Press OK to exit.", windowTitle="Save Scene")
      return True
    if msgBox.clickedButton() == discardButton:
      return True
    return False

  def onNeedleVisibilityToggled(self, toggled):
    logging.info("onNeedleVisibilityToggled({})".format(toggled))
    self.logic.setNeedleVisibility(toggled)

  def onCauteryVisibilityToggled(self, toggled):
    logging.info("onCauteryVisibilityToggled({})".format(toggled))
    self.logic.setCauteryVisibility(toggled)

  def onWarningSoundToggled(self, toggled):
    logging.info("onWarningSoundToggled({})".format(toggled))
    self.logic.setWarningSound(toggled)

  def onWatchedModelClicked(self, button):
    parameterNode = self._parameterNode
    if button == self.ui.automaticWatchedModelButton:
      modelNode = parameterNode.GetNodeReference(self.logic.TUMOR_MODEL_AI)
      self.logic.setBreachWarning(True)
    elif button == self.ui.hydromarkWatchedModelButton:
      modelNode = parameterNode.GetNodeReference(self.logic.TUMOR_MODEL_HYDROMARK)
      self.logic.setBreachWarning(True)
    else:
      modelNode = parameterNode.GetNodeReference(self.logic.TUMOR_MODEL)
    self.logic.setBreachWarningModel(modelNode)
    parameterNode.Modified()
  
  def onToolsCollapsed(self, collapsed):
    if not collapsed:
      self.ui.statusLabel.text = "Tool calibration"
      self.ui.contouringCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      self.ui.eventRecordingCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)
      viewNode = slicer.app.layoutManager().threeDWidget(0).mrmlViewNode()
      if not self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
        self.enableAutoCenterInViewNode(viewNode)
      slicer.util.resetSliceViews()

      # Start Plus server
      if not self.ui.startPlusButton.checked:
        self.ui.startPlusButton.checked = True

  def onContouringCollapsed(self, collapsed):
    if not collapsed:
      self.ui.statusLabel.text = "Tumor contouring"
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True
      self.ui.eventRecordingCollapsibleButton.collapsed = True
      slicer.app.layoutManager().setLayout(6)
      slicer.app.layoutManager().sliceWidget('Red').sliceController().setCompositingToAdd()
      slicer.util.resetSliceViews()
      self.logic.setBrightness(self.NORMAL_BRIGHTNESS)

      hydromarkMarkupNode = self._parameterNode.GetNodeReference(self.logic.HYDROMARK_MARKUP_NEEDLE)
      hydromarkMarkupNode.GetDisplayNode().SetVisibility(self.ui.hydromarkVisibilityButton.checked)

  def onNavigationCollapsed(self, collapsed):
    """
    Called when the navigation tab is collapsed or expanded
    """
    logging.info(f"onNavigationCollapsed({collapsed})")
    if collapsed:
      if self.ui.markPointsButton.checked:
        self.ui.markPointsButton.setChecked(False)
        self.logic.setMarkPoints(False)
      if self.ui.selectPointsToEraseButton.checked:
        self.ui.selectPointsToEraseButton.setChecked(False)
        self.logic.setErasePoints(False)
    else:
      self.ui.statusLabel.text = "Navigation"
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.contouringCollapsibleButton.collapsed = True
      self.ui.eventRecordingCollapsibleButton.collapsed = True
      self.onDual3DViewButton(self.ui.threeDViewButton.checked)
      # Set 3D view settings
      layoutManager = slicer.app.layoutManager()
      for i in range(layoutManager.threeDViewCount):
        view = layoutManager.threeDWidget(i).mrmlViewNode()
        view.SetOrientationMarkerType(view.OrientationMarkerTypeHuman)
        view.SetOrientationMarkerSize(view.OrientationMarkerSizeLarge)
        view.SetBoxVisible(False)
        view.SetAxisLabelsVisible(False)
      distanceRulerFontSize = slicer.util.settingsValue(self.logic.RULER_FONT_SIZE, self.logic.RULER_DISTANCE_DEFAULT_FONT_SIZE, converter=lambda x: float(x))
      self.logic.setRulerDistanceFontSize(distanceRulerFontSize)
      interactionNode = slicer.app.applicationLogic().GetInteractionNode()
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
      hydromarkMarkupNode = self._parameterNode.GetNodeReference(self.logic.HYDROMARK_MARKUP_NEEDLE)
      hydromarkMarkupNode.GetDisplayNode().VisibilityOff()
      self.updateGUIFromParameterNode()
  
  def onEventRecordingCollapsed(self, collapsed):
    if not collapsed:
      self.ui.toolsCollapsibleButton.collapsed = True
      self.ui.contouringCollapsibleButton.collapsed = True
      self.ui.navigationCollapsibleButton.collapsed = True

  def onDual3DViewButton(self, toggled):
    logging.info(f"onDual3DViewButton({toggled})")
    self.ui.threeDViewButton.checked = toggled
    if toggled:
      self.ui.threeDViewButton.text = "Triple 3D View"
      self.ui.bottomAutoCenterCameraButton.setEnabled(False)
      self.ui.bottomCauteryCameraButton.setEnabled(False)
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_DUAL3D)
    else:
      self.ui.threeDViewButton.text = "Dual 3D View"
      self.ui.bottomAutoCenterCameraButton.setEnabled(True)
      self.ui.bottomCauteryCameraButton.setEnabled(True)
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_TRIPLE3D)

  def onStartStopRecordingClicked(self, toggled):
    if toggled:
      self.ui.startStopRecordingButton.text = "Stop Ultrasound Recording"
    else:
      self.ui.startStopRecordingButton.text = "Start Ultrasound Recording"
    self.logic.onUltrasoundSequenceBrowserClicked(toggled)

  def onBreachLocationButtonClicked(self, toggled):
    logging.info(f"onBreachLocationButtonClicked({toggled})")
    settings = qt.QSettings()
    settings.setValue(self.logic.BREACH_MARKUPS_DISPLAY_SETTING, toggled)
    parameterNode = self._parameterNode
    breachMarkups_Needle = parameterNode.GetNodeReference(self.logic.BREACH_MARKUPS_NEEDLE)
    if toggled:
      breachMarkups_Needle.SetDisplayVisibility(1)
    else:
      breachMarkups_Needle.SetDisplayVisibility(0)

  def onIncreaseBreachFiducialSize(self):
    logging.info("onIncreaseBreachFiducialSize")
    previousFontSize = slicer.util.settingsValue(self.logic.BREACH_MARKUPS_SIZE_SETTING,
                                                 self.logic.BREACH_MARKUPS_SIZE_DEFAULT,
                                                 converter=lambda x: float(x))
    newFontSize = previousFontSize + 1
    settings = qt.QSettings()
    settings.setValue(self.logic.BREACH_MARKUPS_SIZE_SETTING, newFontSize)
    self.logic.setBreachFiducialSize(newFontSize)

  def onDecreaseBreachFiducialSize(self):
    logging.info("onDecreaseBreachFiducialSize")
    previousFontSize = slicer.util.settingsValue(self.logic.BREACH_MARKUPS_SIZE_SETTING,
                                                 self.logic.BREACH_MARKUPS_SIZE_DEFAULT,
                                                 converter=lambda x: float(x))
    newFontSize = previousFontSize - 1
    settings = qt.QSettings()
    settings.setValue(self.logic.BREACH_MARKUPS_SIZE_SETTING, newFontSize)
    self.logic.setBreachFiducialSize(newFontSize)

  def onDeleteTumorBreachButtonClicked(self):
    logging.info("onDeleteTumorBreachButtonClicked")
    parameterNode = self._parameterNode
    breachMarkups_Needle = parameterNode.GetNodeReference(self.logic.BREACH_MARKUPS_NEEDLE)
    breachMarkups_Needle.RemoveAllControlPoints()

  def onDisplayRulerButtonClicked(self, toggled):
    logging.info(f"onDisplayRulerButtonClicked({toggled})")
    settings = qt.QSettings()
    settings.setValue(self.logic.DISPLAY_RULER_SETTING, toggled)
    self.logic.setRulerVisibility(toggled)

  def onDisplayDistanceClicked(self, toggled):
    logging.info("onDisplayDistanceClicked({})".format(toggled))
    settings = qt.QSettings()
    settings.setValue(self.logic.DISPLAY_DISTANCE_SETTING, toggled)
    fontSize = slicer.util.settingsValue(self.logic.RULER_FONT_SIZE, self.logic.RULER_DISTANCE_DEFAULT_FONT_SIZE, converter=lambda x: float(x))
    self.logic.setRulerDistanceFontSize(fontSize)

  def onIncreaseDistanceFontSizeClicked(self):
    logging.info("onIncreaseDistanceFontSizeClicked")
    previousFontSize = slicer.util.settingsValue(self.logic.RULER_FONT_SIZE,
                                                 self.logic.RULER_DISTANCE_DEFAULT_FONT_SIZE,
                                                 converter=lambda x: float(x))
    newFontSize = previousFontSize + 1
    settings = qt.QSettings()
    settings.setValue(self.logic.RULER_FONT_SIZE, newFontSize)
    self.logic.setRulerDistanceFontSize(newFontSize)

  def onDecreaseDistanceFontSizeClicked(self):
    logging.info("onDecreaseDistanceFontSizeClicked")
    previousFontSize = slicer.util.settingsValue(self.logic.RULER_FONT_SIZE,
                                                 self.logic.RULER_DISTANCE_DEFAULT_FONT_SIZE,
                                                 converter=lambda x: float(x))
    newFontSize = previousFontSize - 1
    settings = qt.QSettings()
    settings.setValue(self.logic.RULER_FONT_SIZE, newFontSize)
    self.logic.setRulerDistanceFontSize(newFontSize)

  def onToolModelClicked(self, toggled):
    logging.info('onToolModelClicked')
    if toggled:
      self.ui.toolModelButton.text = "Stick Model"
    else:
      self.ui.toolModelButton.text = "Cautery Model"
    self.logic.setToolModelClicked(toggled)

  def onBreachMarkupsProximityChanged(self, value):
    logging.info(f"onBreachMarkupsProximityChanged({value})")
    settings = qt.QSettings()
    settings.setValue(self.logic.BREACH_MARKUPS_PROXIMITY_THRESHOLD, value)

  def onFreezeUltrasoundClicked(self, toggled):
    logging.info(f"onFreezeUltrasoundClicked({toggled})")
    if toggled:
      self.ui.freezeUltrasoundButton.text = "Un-Freeze"
    else:
      self.ui.freezeUltrasoundButton.text = "Freeze"
    self.logic.setFreezeUltrasoundClicked(toggled)

  def onApplyDilationClicked(self):
    logging.info("onApplyDilationClicked")
    dilationValue = float(self.ui.dilationSpinBox.value)
    checkedButton = self.ui.contourModifyGroup.checkedButton()
    if checkedButton == self.ui.modifyAutomaticButton:
      model = self.logic.TUMOR_MODEL_AI
    elif checkedButton == self.ui.modifyHydromarkButton:
      model = self.logic.TUMOR_MODEL_HYDROMARK
    elif checkedButton == self.ui.modifyManualButton:
      model = self.logic.TUMOR_MODEL
    else:
      logging.info("No model selected to apply dilation")
      return
    self.logic.applyDilation(model, dilationValue)

  def onPlusConfigFileChanged(self, configFilepath):
    logging.info(f"onPlusConfigFileChanged({configFilepath})")
    settings = qt.QSettings()
    settings.setValue(self.logic.CONFIG_FILE_SETTING, configFilepath)
    self.logic.setPlusConfigFile(configFilepath)

  def onHostnameChanged(self):
    newHostname = self.ui.hostnameLineEdit.text
    settings = qt.QSettings()
    settings.setValue(self.logic.HOSTNAME_SETTING, newHostname)
    self.logic.setHostname(newHostname)
    logging.info(f"onHostnameChanged({newHostname})")

  def onStartPlusClicked(self, toggled):
    logging.info(f"onStartPlusClicked({toggled})")
    if toggled:
      self.ui.startPlusButton.text = "Stop PLUS"
      self.ui.plusConfigFileSelector.enabled = False
      self.ui.hostnameLineEdit.enabled = False
    else:
      self.ui.startPlusButton.text = "Start PLUS"
      self.ui.plusConfigFileSelector.enabled = True
      self.ui.hostnameLineEdit.enabled = True
    self.logic.setPlusServerClicked(toggled)

  def onDisplayRASClicked(self, toggled):
    logging.info(f"onDisplayRASClicked({toggled})")
    parameterNode = self._parameterNode
    RASMarkups = parameterNode.GetNodeReference(self.logic.RAS_MARKUPS)
    if toggled:
      RASMarkups.SetDisplayVisibility(1)
    else:
      RASMarkups.SetDisplayVisibility(0)

  def onDisplayCauteryStateClicked(self, toggled):
    logging.info("onDisplayCauteryStateClicked({})".format(toggled))
    self.logic.setDisplayCauteryStateClicked(toggled)

  def onCustomUiClicked(self, checked):
    self.setCustomStyle(checked)

  def updateRecordingTimeLabel(self, time):
    self.ui.recordingTimeLabel.text = f"{time} s"

  def onExportCsvButtonClicked(self):
    csvFilename = f"iKnifeSyncData_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    csvFilePath = os.path.join(self.ui.saveFolderSelector.directory, csvFilename)
    self.logic.exportTrackingDataToCsv(csvFilePath)

  def onTrackingSequenceBrowser(self, toggled):
    logging.info("onTrackingSequenceBrowserToggled({})".format(toggled))
    self.logic.setTrackingSequenceBrowser(toggled)

  def onUltrasoundSequenceBrowser(self, toggled):
    logging.info("onUltrasoundSequenceBrowserToggled({})".format(toggled))
    self.logic.onUltrasoundSequenceBrowserClicked(toggled)

  def onBrightnessButtonClicked(self, button):
    if button == self.ui.normalBrightnessButton:
      self.logic.setBrightness(self.NORMAL_BRIGHTNESS)
    elif button == self.ui.brightBrightnessButton:
      self.logic.setBrightness(self.BRIGHT_BRIGHTNESS)
    else:
      self.logic.setBrightness(self.BRIGHTEST_BRIGHTNESS)
  
  def onDepthButtonClicked(self, button):
    if button == self.ui.normalDepthButton:
      self.logic.setDepth(self.logic.NORMAL_DEPTH_MM)
    else:
      self.logic.setDepth(self.logic.DEEP_DEPTH_MM)
    slicer.util.resetSliceViews()

  def onAnteriorDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.ANTERIOR_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onPosteriorDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.POSTERIOR_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onLeftDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.LEFT_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onRightDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.RIGHT_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onSuperiorDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.SUPERIOR_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onInferiorDistToMarginChanged(self, value):
    if self._updatingGUIFromParameterNode:
      return
    self._parameterNode.SetParameter(self.logic.INFERIOR_DIST_TO_MARGIN, str(value))
    self.logic.createTumorFromHydromark()

  def onPlaceHydromarkToggled(self, toggled):
    logging.info(f"onPlaceHydromarkToggled({toggled})")
    if self._updatingGui:
      return
    self._updatingGui = True
    if toggled:
      self.ui.markPointsButton.setChecked(False)
      self.ui.selectPointsToEraseButton.setChecked(False)
    self.logic.setPlaceHydromark(toggled)
    self._updatingGui = False
  
  def onDeleteHydromarkClicked(self):
    self.logic.deleteHydromarkMarkup()

  def onMarkPointsToggled(self, toggled):
    logging.info(f"onMarkPointsToggled({toggled})")
    if self._updatingGui:
      return
    self._updatingGui = True
    if toggled:
      self.ui.selectPointsToEraseButton.setChecked(False)
    self.logic.setMarkPoints(toggled)
    self._updatingGui = False

  def onErasePointsToggled(self, toggled):
    logging.info(f"onErasePointsToggled({toggled})")
    if self._updatingGui:
      return
    self._updatingGui = True
    if toggled:
      self.ui.markPointsButton.setChecked(False)
    self.logic.setErasePoints(toggled)
    self._updatingGui = False

  def onMarkPointCauteryTipClicked(self):
    logging.info("Mark point at cautery tip clicked")
    self.logic.setMarkPointCauteryTipClicked()

  def onDeleteLastFiducialClicked(self):
    logging.info('onDeleteLastFiducialClicked')
    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
    self.logic.setDeleteLastFiducialClicked(numberOfPoints)

  def onDeleteAllFiducialsClicked(self):
    logging.info('onDeleteAllFiducialsClicked')
    self.logic.setDeleteAllFiducialsClicked()
    self.updateGUIFromParameterNode()

  def onContourVisibilityToggled(self, toggled):
    logging.info("onContourVisibilityToggled")
    self.logic.setContourVisibility(toggled)

  def onHydromarkVisibilityToggled(self, toggled):
    logging.info("onHydromarkVisibilityToggled")
    settings = qt.QSettings()
    settings.setValue(self.logic.HYDROMARK_VISIBILITY_SETTING, toggled)
    if toggled:
      self.ui.hydromarkVisibilityButton.checked = True
      self.ui.hydromarkVisibility2DButton.checked = True
    else:
      self.ui.hydromarkVisibilityButton.checked = False
      self.ui.hydromarkVisibility2DButton.checked = False
    inContouringTab = not self.ui.contouringCollapsibleButton.collapsed
    self.logic.setHydromarkVisibility(toggled, inContouringTab)

  def onSegmentationVisibilityToggled(self, toggled):
    logging.info("onSegmentationVisibilityToggled")
    self.logic.setSegmentationVisibility(toggled)

  def onThresholdSliderChanged(self, value):
    self._parameterNode.SetParameter(self.logic.AI_THRESHOLD, str(value))

  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    logging.debug("getViewNode")
    viewNode = slicer.util.getFirstNodeByName(viewName)
    return viewNode

  def onLeftBreastButtonClicked(self):
    logging.info(f"onLeftButtonClicked()")
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    # TODO: Don't use magic numbers
    cameraNode1.SetPosition(-242.0042709749552, 331.2026122150233, -36.6617924419265)
    cameraNode1.SetViewUp(0.802637869051714, 0.5959392355990031, -0.025077452777348814)
    cameraNode1.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode1.ResetClippingRange()
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode2.ResetClippingRange()
    cameraNode3.SetPosition(0.0, 0.0, -500.0)
    cameraNode3.SetViewUp(0.0, 0.0, 0.0)
    cameraNode3.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode3.ResetClippingRange()
    # Enable auto-center
    for i in range(slicer.app.layoutManager().threeDViewCount):
      viewNode = slicer.app.layoutManager().threeDWidget(i).mrmlViewNode()
      if not self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
        self.enableAutoCenterInViewNode(viewNode)
    self.updateGUIButtons()

  def onRightBreastButtonClicked(self):
    logging.info(f"onRightButtonClicked()")
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    # TODO: magic numbers
    cameraNode1.SetPosition(275.4944476449362, 309.31555951664205, 42.169967768629164)
    cameraNode1.SetViewUp(-0.749449157051234, 0.661802245162601, -0.018540477149624528)
    cameraNode1.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode1.ResetClippingRange()
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(-1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode2.ResetClippingRange()
    cameraNode3.SetPosition(0.0, 0.0, -500.0)
    cameraNode3.SetViewUp(0.0, 0.0, 0.0)
    cameraNode3.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode3.ResetClippingRange()
    # Enable auto-center
    for i in range(slicer.app.layoutManager().threeDViewCount):
      viewNode = slicer.app.layoutManager().threeDWidget(i).mrmlViewNode()
      if not self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
        self.enableAutoCenterInViewNode(viewNode)
    self.updateGUIButtons()

  def onLeftCauteryCameraButtonClicked(self, toggled):
    logging.info("onLeftFollowCameraButtonClicked")
    self.onCauteryCameraButtonClicked("View1")

  def onRightCauteryCameraButtonClicked(self, toggled):
    logging.info("onRightFollowCameraButtonClicked")
    self.onCauteryCameraButtonClicked("View2")

  def onBottomCauteryCameraButtonClicked(self, toggled):
    logging.info("onBottomFollowCameraButtonClicked")
    self.onCauteryCameraButtonClicked("View3")

  def onCauteryCameraButtonClicked(self, viewName):
    viewNode = self.getViewNode(viewName)
    if self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye():
      self.disableBullseyeInViewNode(viewNode)
      self.enableAutoCenterInViewNode(viewNode)
    else:
      self.enableBullseyeInViewNode(viewNode)
    self.updateGUIButtons()

  def disableBullseyeInViewNode(self, viewNode):
    if self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye():
      self.logic.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStop()

  def enableBullseyeInViewNode(self, viewNode):
    self.disableViewpointInViewNode(viewNode)
    cauteryCameraToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYCAMERA_TO_CAUTERY)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetTransformNode(cauteryCameraToCautery)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStart()

  def onLeftAutoCenterCameraButtonClicked(self, toggled):
    logging.info("onLeftAutoCenterButtonClicked")
    self.onAutoCenterButtonClicked('View1')

  def onRightAutoCenterCameraButtonClicked(self, toggled):
    logging.info("onRightAutoCenterCameraButtonClicked")
    self.onAutoCenterButtonClicked('View2')

  def onBottomAutoCenterCameraButtonClicked(self, toggled):
    logging.info("onBottomAutoCenterCameraButtonClicked")
    self.onAutoCenterButtonClicked('View3')

  def onAutoCenterButtonClicked(self, viewName):
    viewNode = self.getViewNode(viewName)
    if self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
      self.disableAutoCenterInViewNode(viewNode)
    else:
      self.enableAutoCenterInViewNode(viewNode)
    self.updateGUIButtons()

  def disableAutoCenterInViewNode(self, viewNode):
    if self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
      self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStop()

  def enableAutoCenterInViewNode(self, viewNode):
    self.disableViewpointInViewNode(viewNode)
    breachWarningNode = self._parameterNode.GetNodeReference(self.logic.BREACH_WARNING)
    watchedModel = breachWarningNode.GetWatchedModelNode()
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMinimum(-self.VIEW_COORD_WIDTH_LIMIT)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMaximum(self.VIEW_COORD_WIDTH_LIMIT)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMinimum(-self.VIEW_COORD_HEIGHT_LIMIT)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMaximum(self.VIEW_COORD_HEIGHT_LIMIT)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetModelNode(watchedModel)
    self.logic.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStart()

  def disableViewpointInViewNode(self, viewNode):
    logging.debug("disableViewpointInViewNode")
    self.disableAutoCenterInViewNode(viewNode)
    self.disableBullseyeInViewNode(viewNode)

  def updateGUIButtons(self):
    # Left view node
    autoCenterBlockSignalState = self.ui.leftAutoCenterCameraButton.blockSignals(True)
    bullseyeBlockSignalState = self.ui.leftCauteryCameraButton.blockSignals(True)
    leftViewNode = self.getViewNode("View1")
    if self.logic.viewpointLogic.getViewpointForViewNode(leftViewNode).isCurrentModeAutoCenter():
      self.ui.leftAutoCenterCameraButton.setChecked(True)
      self.ui.leftCauteryCameraButton.setChecked(False)
    elif self.logic.viewpointLogic.getViewpointForViewNode(leftViewNode).isCurrentModeBullseye():
      self.ui.leftAutoCenterCameraButton.setChecked(False)
      self.ui.leftCauteryCameraButton.setChecked(True)
    else:
      self.ui.leftAutoCenterCameraButton.setChecked(False)
      self.ui.leftCauteryCameraButton.setChecked(False)
    self.ui.leftAutoCenterCameraButton.blockSignals(autoCenterBlockSignalState)
    self.ui.leftCauteryCameraButton.blockSignals(bullseyeBlockSignalState)

    # Right view node
    autoCenterBlockSignalState = self.ui.rightAutoCenterCameraButton.blockSignals(True)
    bullseyeBlockSignalState = self.ui.rightCauteryCameraButton.blockSignals(True)
    rightViewNode = self.getViewNode("View2")
    if self.logic.viewpointLogic.getViewpointForViewNode(rightViewNode).isCurrentModeAutoCenter():
      self.ui.rightAutoCenterCameraButton.setChecked(True)
      self.ui.rightCauteryCameraButton.setChecked(False)
    elif self.logic.viewpointLogic.getViewpointForViewNode(rightViewNode).isCurrentModeBullseye():
      self.ui.rightAutoCenterCameraButton.setChecked(False)
      self.ui.rightCauteryCameraButton.setChecked(True)
    else:
      self.ui.rightAutoCenterCameraButton.setChecked(False)
      self.ui.rightCauteryCameraButton.setChecked(False)
    self.ui.rightAutoCenterCameraButton.blockSignals(autoCenterBlockSignalState)
    self.ui.rightCauteryCameraButton.blockSignals(bullseyeBlockSignalState)

    # Bottom view node
    autoCenterBlockSignalState = self.ui.bottomAutoCenterCameraButton.blockSignals(True)
    bullseyeBlockSignalState = self.ui.bottomCauteryCameraButton.blockSignals(True)
    bottomViewNode = self.getViewNode("View3")
    if self.logic.viewpointLogic.getViewpointForViewNode(bottomViewNode).isCurrentModeAutoCenter():
      self.ui.bottomAutoCenterCameraButton.setChecked(True)
      self.ui.bottomCauteryCameraButton.setChecked(False)
    elif self.logic.viewpointLogic.getViewpointForViewNode(bottomViewNode).isCurrentModeBullseye():
      self.ui.bottomAutoCenterCameraButton.setChecked(False)
      self.ui.bottomCauteryCameraButton.setChecked(True)
    else:
      self.ui.bottomAutoCenterCameraButton.setChecked(False)
      self.ui.bottomCauteryCameraButton.setChecked(False)
    self.ui.bottomAutoCenterCameraButton.blockSignals(autoCenterBlockSignalState)
    self.ui.bottomCauteryCameraButton.blockSignals(bullseyeBlockSignalState)

  def onEventSelectionChanged(self):
    if self.ui.eventTable.selectionModel().isSelected(self.ui.eventTable.currentIndex()):
      self.ui.deleteEventButton.setEnabled(True)
    else:
      self.ui.deleteEventButton.setEnabled(False)

  def onAddEventButtonClicked(self):
    logging.info("onAddEventButtonClicked")
    self.logic.addEvent()

  def onDeleteEventButtonClicked(self):
    logging.info("onDeleteEventButtonClicked")
    selectedRows = self.ui.eventTable.selectionModel().selectedRows()
    for i in range(len(selectedRows) - 1, -1, -1):
      row = selectedRows[i]
      self.logic.deleteEvent(row.row())

  def onEventTableExportClicked(self):
    eventTableNode = self._parameterNode.GetNodeReference(self.logic.EVENT_TABLE_NODE)
    saveDirectory = self.ui.eventTableExportDirectoryButton.directory
    savePath = saveDirectory + "/events.csv"
    try:
      slicer.util.saveNode(eventTableNode, savePath)
      logging.info(f"Events csv saved to: {savePath}")
      slicer.util.messageBox(f"Events csv saved to {savePath}.")
    except Exception as e:
      slicer.util.errorDisplay(f"Events could not be saved: {str(e)}")

  def setCustomStyle(self, visible):
    """
    Applies UI customization. Hide Slicer widgets and apply custom stylesheet.
    :param visible: True to apply custom style.
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue(self.SLICER_INTERFACE_VISIBLE, not visible)

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
    return slicer.util.settingsValue(self.SLICER_INTERFACE_VISIBLE, False, converter=slicer.util.toBool)

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

    # Choose layout based on which collapsible button is open
    if self.ui.toolsCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)
      viewNode = slicer.app.layoutManager().threeDWidget(0).mrmlViewNode()
      if not self.logic.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
        self.enableAutoCenterInViewNode(viewNode)

    if self.ui.contouringCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(6)

    if self.ui.navigationCollapsibleButton.checked:
      self.onNavigationCollapsed(not self.ui.navigationCollapsibleButton.checked)

    self.updateGUIFromParameterNode()
    self.updateGUIFromMRML()

  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    logging.debug("getCamera")
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(self.getViewNode(viewName))
    return camera

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    # self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self.removeObservers(method=self.updateGUIFromParameterNode)
    self.removeObservers(method=self.updateGUIFromMRML)

    # self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    self.observedCauteryModel = None

    # self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    self.observedNeedleModel = None

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
    logging.info("onSceneEndClose")

    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()
  
  def onSceneStartImport(self, caller, event):
    if self.parent.isEntered:
      slicer.mrmlScene.Clear(0)
  
  def onSceneEndImport(self, caller, event):
    if self.parent.isEntered:
      self.logic.setup()
      self.initializeParameterNode()
      self.updateGUIFromParameterNode()
      self.updateGUIFromMRML()

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

    # Read parameter nodes and update GUI accordingly

    # If new MRML nodes are referenced, update observers

    currentNeedleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if self.observedNeedleModel and currentNeedleModel != self.observedNeedleModel:
      self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedNeedleModel = currentNeedleModel
      if self.observedNeedleModel:
        self.addObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)

    currentCauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    if self.observedCauteryModel and currentCauteryModel != self.observedCauteryModel:
      self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedCauteryModel = currentCauteryModel
      if self.observedCauteryModel:
        self.addObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)

    currentTrackingSeqBrNode = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if self.observedTrackingSeqBrNode and currentTrackingSeqBrNode != self.observedTrackingSeqBrNode:
      self.removeObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedTrackingSeqBrNode = currentTrackingSeqBrNode
      if self.observedTrackingSeqBrNode is not None:
        self.addObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    currentUltrasoundSeqBrNode = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if self.observedUltrasoundSeqBrNode and currentUltrasoundSeqBrNode != self.observedUltrasoundSeqBrNode:
      self.removeObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedUltrasoundSeqBrNode = currentUltrasoundSeqBrNode
      if self.observedUltrasoundSeqBrNode is not None:
        self.addObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    needleLength = self.logic.getNeedleLength()
    if needleLength:
      self.ui.needleLengthLabel.text = f"Needle length: {needleLength:.0f}mm"

    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    if tumorMarkups_Needle:
      numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
      if numberOfPoints >= 1:
        self.ui.deleteLastFiducialButton.setEnabled(True)
        self.ui.deleteAllFiducialsButton.setEnabled(True)
        self.ui.deleteLastFiducialNavigationButton.setEnabled(True)
        self.ui.selectPointsToEraseButton.setEnabled(True)
        if self.ui.manualWatchedModelButton.checked:
          self.logic.setBreachWarning(True)

      else:
        self.ui.deleteLastFiducialButton.setEnabled(False)
        self.ui.deleteAllFiducialsButton.setEnabled(False)
        self.ui.deleteLastFiducialNavigationButton.setEnabled(False)
        self.ui.selectPointsToEraseButton.setChecked(False)
        self.ui.selectPointsToEraseButton.setEnabled(False)
        if self.ui.manualWatchedModelButton.checked:
          self.logic.setBreachWarning(False)
    
    hydromarkMarkup_Needle = self._parameterNode.GetNodeReference(self.logic.HYDROMARK_MARKUP_NEEDLE)
    if hydromarkMarkup_Needle:
      numberOfPoints = hydromarkMarkup_Needle.GetNumberOfControlPoints()
      if numberOfPoints >= 1:
        self.ui.placeHydromarkButton.checked = False
        self.ui.placeHydromarkButton.setEnabled(False)
        self.ui.deleteHydromarkButton.setEnabled(True)
      else:
        self.ui.deleteHydromarkButton.setEnabled(False)
        self.ui.placeHydromarkButton.setEnabled(True)

    if anteriorDist := self._parameterNode.GetParameter(self.logic.ANTERIOR_DIST_TO_MARGIN):
      self.ui.anteriorDistToMarginSpinBox.value = float(anteriorDist)

    if posteriorDist := self._parameterNode.GetParameter(self.logic.POSTERIOR_DIST_TO_MARGIN):
      self.ui.posteriorDistToMarginSpinBox.value = float(posteriorDist)

    if leftDist := self._parameterNode.GetParameter(self.logic.LEFT_DIST_TO_MARGIN):
      self.ui.leftDistToMarginSpinBox.value = float(leftDist)

    if rightDist := self._parameterNode.GetParameter(self.logic.RIGHT_DIST_TO_MARGIN):
      self.ui.rightDistToMarginSpinBox.value = float(rightDist)

    if superiorDist := self._parameterNode.GetParameter(self.logic.SUPERIOR_DIST_TO_MARGIN):
      self.ui.superiorDistToMarginSpinBox.value = float(superiorDist)

    if inferiorDist := self._parameterNode.GetParameter(self.logic.INFERIOR_DIST_TO_MARGIN):
      self.ui.inferiorDistToMarginSpinBox.value = float(inferiorDist)

    tumorModelHydromark = self._parameterNode.GetNodeReference(self.logic.TUMOR_MODEL_HYDROMARK)
    if tumorModelHydromark and tumorModelHydromark.GetPolyData():
      self.ui.hydromarkWatchedModelButton.enabled = True
    else:
      self.ui.hydromarkWatchedModelButton.enabled = False

    tumorModelAI = self._parameterNode.GetNodeReference(self.logic.TUMOR_MODEL_AI)
    if tumorModelAI and tumorModelAI.GetPolyData():
      self.ui.automaticWatchedModelButton.enabled = True
    else:
      self.ui.automaticWatchedModelButton.enabled = False

    # Update event UI when event table is changed by tumor breach
    if not self.observedEventTableNode:
      currentEventTableNode = self._parameterNode.GetNodeReference(self.logic.EVENT_TABLE_NODE)
      self.observedEventTableNode = currentEventTableNode
      if self.observedEventTableNode is not None:
        self.addObserver(self.observedEventTableNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    if not self.observedPlusServerLauncherNode:
      plusServerLauncherNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_LAUNCHER_NODE)
      self.observedPlusServerLauncherNode = plusServerLauncherNode
      if self.observedPlusServerLauncherNode is not None:
        self.addObserver(self.observedPlusServerLauncherNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
    
    self.ui.thresholdSlider.value = float(self._parameterNode.GetParameter(self.logic.AI_THRESHOLD))

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateGUIFromMRML(self, caller=None, event=None):
    """
    Updates the GUI from MRML nodes in the scene (except parameter node).
    """
    if self._updatingGUIFromMRML:
      return

    if self._parameterNode is None:
      return

    self._updatingGUIFromMRML = True

    # Needle visibility button
    needleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if needleModel is not None:
      if needleModel.GetDisplayVisibility():
        self.ui.needleVisibilityButton.checked = True
      else:
        self.ui.needleVisibilityButton.checked = False

    # Cautery visibility and tool model buttons
    cauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    stickModel = self._parameterNode.GetNodeReference(self.logic.STICK_MODEL)
    isCauterySelected = slicer.util.settingsValue(self.logic.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    if isCauterySelected:
      selectedModel = cauteryModel
      self.ui.toolModelButton.checked = True
      self.ui.toolModelButton.text = "Stick Model"
    else:
      selectedModel = stickModel
      self.ui.toolModelButton.checked = False
      self.ui.toolModelButton.text = "Cautery Model"
    if selectedModel is not None:
      if selectedModel.GetDisplayVisibility():
        self.ui.cauteryVisibilityButton.checked = True
      else:
        self.ui.cauteryVisibilityButton.checked = False

    trackingSqBr = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if trackingSqBr is not None:
      self.ui.trackingSequenceBrowserButton.checked = trackingSqBr.GetRecordingActive()

    ultrasoundSqBr = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if ultrasoundSqBr is not None:
      self.ui.startStopRecordingButton.checked = ultrasoundSqBr.GetRecordingActive()
    
    eventTable = self._parameterNode.GetNodeReference(self.logic.EVENT_TABLE_NODE)
    if eventTable is not None:
      self.ui.eventTable.setMRMLTableNode(eventTable)
      self.ui.eventTable.horizontalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)

    plusServerLauncherNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_LAUNCHER_NODE)
    if plusServerLauncherNode is not None:
      hostname = plusServerLauncherNode.GetHostname()
      self.ui.hostnameLineEdit.setText(hostname)

    self._updatingGUIFromMRML = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.EndModify(wasModified)


#
# LumpNav2Logic
#

class LumpNav2Logic(ScriptedLoadableModuleLogic, VTKObservationMixin):
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
  CAUTERY_TO_NEEDLE = "CauteryToNeedle"
  CAUTERYTIP_TO_CAUTERY = "CauteryTipToCautery"
  PROBE_TO_REFERENCE = "ProbeToReference"
  IMAGE_TO_PROBE = "ImageToProbe"
  CAUTERYCAMERA_TO_CAUTERY = "CauteryCameraToCautery"
  PROBE_TO_NEEDLE = "ProbeToNeedle"
  PREDICTION_TO_PROBE = "PredictionToProbe"

  POINTS_STATUS = "PointsStatus"
  POINTS_ADDING = "PointsAdding"
  POINTS_ERASING = "PointsErasing"
  POINTS_UNSELECTED = "PointsUnselected"

  # Ultrasound image
  US_DEVICE_ID = "VideoDevice"
  IMAGE_IMAGE = "Image_Image"
  IMAGE_TO_PROBE_NORMAL_PATH = "ImageToProbe50.h5"
  NORMAL_DEPTH_MM = 50.0
  NORMAL_FOCUS_DEPTH_PERCENT = 60
  NORMAL_FREQUENCY = 7.5
  IMAGE_TO_PROBE_DEEP_PATH = "ImageToProbe70.h5"
  DEEP_DEPTH_MM = 70.0
  DEEP_FOCUS_DEPTH_PERCENT = 70
  DEEP_FREQUENCY = 5.0

  # OpenIGTLink PLUS connection
  CONFIG_FILE_SETTING = "LumpNav2/PlusConfigFile"
  CONFIG_FILE_DEFAULT = "LumpNavDefault.xml"  # Default config file if the user doesn't set another.
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"
  HOSTNAME_SETTING = "LumpNav2/LastHostname"
  PREDICTION_CONNECTOR_NODE = "PredictionConnectorNode"
  PREDICTION_HOSTNAME = "localhost"
  PREDICTION_PORT = 18945
  IKNIFE_CONNECTOR_NODE = "iKnifeConnectorNode"
  IKNIFE_HOSTNAME = "localhost"
  IKNIFE_PORT = 18946

  # Preoperative hydromark parameters
  ANTERIOR_DIST_TO_MARGIN = "AnteriorDistToMargin"
  POSTERIOR_DIST_TO_MARGIN = "PosteriorDistToMargin"
  LEFT_DIST_TO_MARGIN = "LeftDistToMargin"
  RIGHT_DIST_TO_MARGIN = "RightDistToMargin"
  SUPERIOR_DIST_TO_MARGIN = "SuperiorDistToMargin"
  INFERIOR_DIST_TO_MARGIN = "InferiorDistToMargin"
  HYDROMARK_TO_NEEDLE = "HydromarkToNeedle"
  HYDROMARK_MARKUP_NEEDLE = "HydromarkMarkup_Needle"
  TUMOR_MODEL_HYDROMARK = "TumorModelHydromark"
  HYDROMARK_VISIBILITY_SETTING = "LumpNav2/HydromarkVisible"

  # Model names and settings
  REFERENCE_TO_RAS_SETTING = "LumpNav2/ReferenceToRas"
  NEEDLE_MODEL = "NeedleModel"
  NEEDLE_LENGTH_DEFAULT = 57
  NEEDLE_VISIBILITY_SETTING = "LumpNav2/NeedleVisible"
  NEEDLE_LENGTH_OFFSET_SETTING = "LumpNav2/NeedleLengthOffset"
  CAUTERY_MODEL = "CauteryModel"
  CAUTERY_VISIBILITY_SETTING = "LumpNav2/CauteryVisible"
  CAUTERY_MODEL_FILENAME = "CauteryModel.stl"
  CAUTERY_MODEL_SELECTED = "LumpNav2/CauteryModelSelected"
  TUMOR_MODEL = "TumorModel"
  STICK_MODEL = "StickModel"
  WARNING_SOUND_SETTING = "LumpNav2/WarningSoundEnabled"
  BREACH_STATUS = "LumpNav2/BreachStatus"
  BREACH_MARKUPS_DISPLAY_SETTING = "LumpNav2/BreachMarkupsDisplaySetting"
  BREACH_MARKUPS_PROXIMITY_THRESHOLD = "LumpNav2/BreachMarkupsProximitySetting"
  BREACH_MARKUPS_SIZE_SETTING = "LumpNav2/BreachMarkupsSize"
  BREACH_MARKUPS_SIZE_DEFAULT = 5
  DISPLAY_RULER_SETTING = "LumpNav2/DistanceRulerEnabled"
  DISPLAY_DISTANCE_SETTING = "LumpNav2/DistanceRulerTextEnabled"
  RULER_DISTANCE_DEFAULT_FONT_SIZE = 5
  RULER_FONT_SIZE = "LumpNav2/RulerFontSize"

  # Model reconstruction
  ROI_NODE = "ROI"
  AI_MODEL_PATH = "BreastSeg_2021-01-05_model_0.h5"
  PREDICTION_VOLUME = "Prediction"
  RECONSTRUCTION_NODE = "ReconstructionNode"
  RECONSTRUCTION_VOLUME = "ReconstructionVolume"
  TUMOR_MODEL_AI = "TumorModelAI"
  AI_THRESHOLD = "ReconstructionThreshold"
  DEFAULT_THRESHOLD = 127.0
  DEFAULT_SMOOTH = 15
  DEFAULT_DECIMATE = 0.25
  AI_VISIBLE = "AIVisible"

  # iKnife connection
  IKNIFE_TIC = "iKnifeTIC"

  # Layout codes
  LAYOUT_2D3D = 501
  LAYOUT_TRIPLE3D = 502
  LAYOUT_DUAL3D = 503

  DISTANCE_TEXT_SCALE = '3'

  # Sequence names
  TRACKING_SEQUENCE_BROWSER = "TrackingSequenceBrowser"
  ULTRASOUND_SEQUENCE_BROWSER = "UltrasoundSequenceBrowser"
  TUMOR_MARKUPS_NEEDLE = "TumorMarkups_Needle"
  BREACH_WARNING = "LumpNavBreachWarning"
  BREACH_MARKUPS_NEEDLE = "BreachMarkups_Needle"
  EVENT_TABLE_NODE = "EventTableNode"
  TIME_COLUMN = 0
  SEQUENCE_TIME_COLUMN = 1
  EVENT_DESCRIPTION_COLUMN = 2
  LAST_COLUMN = 3

  RAS_MARKUPS = "DirectionMarkups_RAS"

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    slicer.mymodL = self
    VTKObservationMixin.__init__(self)

    self.viewpointLogic = Viewpoint.ViewpointLogic()
    
    self.lastTime = 0
    self.lastCauteryTipRAS = np.array([0, 0, 0, 1])
    self.positionMatrix = [[], [], [], [], [], [], [], []]
    self.updateRecordingTimeCallback = None

    self.predictionStarted = False
    self.reconstructionLogic = slicer.modules.volumereconstruction.logic()

    self._connectorNode = None
    self._setDepthCommand = None
    self._setFocusDepthCommand = None
    self._setFrequencyCommand = None

  def resourcePath(self, filename):
    """
    Returns the full path to the given resource file.
    :param filename: str, resource file name
    :returns: str, full path to file specified
    """
    moduleDir = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(moduleDir, "Resources", filename)

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")
    if not parameterNode.GetParameter(self.AI_THRESHOLD):
      parameterNode.SetParameter(self.AI_THRESHOLD, str(self.DEFAULT_THRESHOLD))
    if not parameterNode.GetParameter(self.AI_VISIBLE):
      parameterNode.SetParameter(self.AI_VISIBLE, "False")

    parameterNode = self.getParameterNode()
    parameterNode.SetAttribute("TipToSurfaceDistanceTextScale", "3")

  def addCustomLayouts(self):
    layout2D3D = \
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

    layoutTriple3D = \
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

  def getNeedleLength(self):
    parameterNode = self.getParameterNode()
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    if needleTipToNeedle:
      needleLengthOffset = slicer.util.settingsValue(
        self.NEEDLE_LENGTH_OFFSET_SETTING, 0, converter=lambda x: float(x)
      )
      needleTipToNeedleMatrix = vtk.vtkMatrix4x4()
      needleTipToNeedle.GetMatrixTransformToParent(needleTipToNeedleMatrix)
      needleTipToNeedleLength = needleTipToNeedleMatrix.GetElement(2, 3)
      needleLength = needleTipToNeedleLength - needleLengthOffset
      return needleLength

  def setNeedleModel(self):
    parameterNode = self.getParameterNode()
    # Remove old needle model
    oldNeedleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    slicer.mrmlScene.RemoveNode(oldNeedleModel)
    # Create new needle model
    createModelsLogic = slicer.modules.createmodels.logic()
    needleLength = self.getNeedleLength()
    needleModel = createModelsLogic.CreateNeedle(needleLength, 1.0, 2.0, 0)
    needleModel.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
    needleModel.SetName(self.NEEDLE_MODEL)
    needleModel.GetDisplayNode().Visibility2DOn()
    parameterNode.SetNodeReferenceID(self.NEEDLE_MODEL, needleModel.GetID())
    # Place in NeedleTipToNeedle coordinate system
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleModel.SetAndObserveTransformNodeID(needleTipToNeedle.GetID())
    # Set needle visibility
    needleVisible = slicer.util.settingsValue(self.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    needleModel.SetDisplayVisibility(needleVisible)

  def setNeedleVisibility(self, visible):
    """
    Changes the visibility of the needle model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue(self.NEEDLE_VISIBILITY_SETTING, "True" if visible else "False")
    parameterNode = self.getParameterNode()
    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is not None:
      needleModel.SetDisplayVisibility(visible)

  def setCauteryVisibility(self, visible):
    """
    Changes the visibility of the cautery model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    settings = qt.QSettings()
    settings.setValue(self.CAUTERY_VISIBILITY_SETTING, "True" if visible else "False")
    cauteryModelSelected = slicer.util.settingsValue(self.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    if cauteryModel is not None and stickModel is not None:
      if cauteryModelSelected:
        cauteryModel.SetDisplayVisibility(visible)
      else:
        stickModel.SetDisplayVisibility(visible)

  def setWarningSound(self, enabled):
    breachWarningNode = self.getParameterNode().GetNodeReference(self.BREACH_WARNING)
    if breachWarningNode is not None:
      breachWarningNode.SetPlayWarningSound(enabled)
      settings = qt.QSettings()
      settings.setValue(self.WARNING_SOUND_SETTING, enabled)

  def setup(self):
    """
    Sets up the Slicer scene. Creates nodes if they are missing.
    """
    parameterNode = self.getParameterNode()

    self.setupTransformHierarchy()

    # Create models
    createModelsLogic = slicer.modules.createmodels.logic()

    # Needle model
    needleLength = self.getNeedleLength()
    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is None:
      needleModel = createModelsLogic.CreateNeedle(needleLength, 1.0, 2.0, 0)
      needleModel.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
      needleModel.SetName(self.NEEDLE_MODEL)
      needleModel.GetDisplayNode().Visibility2DOn()
      parameterNode.SetNodeReferenceID(self.NEEDLE_MODEL, needleModel.GetID())

    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleModel.SetAndObserveTransformNodeID(needleTipToNeedle.GetID())

    needleVisible = slicer.util.settingsValue(self.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    needleModel.SetDisplayVisibility(needleVisible)

    # Cautery model
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    if cauteryModel is None:
      cauteryModel = slicer.util.loadModel(self.resourcePath(self.CAUTERY_MODEL_FILENAME))
      cauteryModel.GetDisplayNode().SetColor(1.0, 1.0, 0.0)
      cauteryModel.SetName(self.CAUTERY_MODEL)
      parameterNode.SetNodeReferenceID(self.CAUTERY_MODEL, cauteryModel.GetID())

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    cauteryModel.SetAndObserveTransformNodeID(cauteryTipToCautery.GetID())

    cauteryVisible = slicer.util.settingsValue(self.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    cauteryModel.SetDisplayVisibility(cauteryVisible)

    # Stick Model
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    if stickModel is None:
      stickModel = createModelsLogic.CreateNeedle(100, 1.0, 2.0, 0)
      stickModel.GetDisplayNode().SetColor(1.0, 1.0, 0)
      stickModel.SetName(self.STICK_MODEL)
      stickModel.GetDisplayNode().VisibilityOff()  # Default is only cautery model, turn stick model off visibility
      parameterNode.SetNodeReferenceID(self.STICK_MODEL, stickModel.GetID())

    stickTipToStick = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    stickModel.SetAndObserveTransformNodeID(stickTipToStick.GetID())

    # Determine which cautery model to display from settings
    cauterySelected = slicer.util.settingsValue(self.CAUTERY_MODEL_SELECTED, True, converter=slicer.util.toBool)
    self.setToolModelClicked(cauterySelected)

    # Create tumor model
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    if tumorModel_Needle is None:
      tumorModel_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL)
      tumorModel_Needle.CreateDefaultDisplayNodes()
      modelDisplayNode = tumorModel_Needle.GetDisplayNode()
      modelDisplayNode.SetColor(0, 1, 0)  # Green
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.Visibility2DOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3)  # Between 0-1, 1 being opaque
      parameterNode.SetNodeReferenceID(self.TUMOR_MODEL, tumorModel_Needle.GetID())
    self.addObserver(tumorModel_Needle, slicer.vtkMRMLModelNode.MeshModifiedEvent, self.setRASMarkups)

    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    tumorModel_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())

    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if tumorMarkups_Needle is None:
      tumorMarkups_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.TUMOR_MARKUPS_NEEDLE)
      tumorMarkups_Needle.CreateDefaultDisplayNodes()
      tumorMarkups_Needle.GetDisplayNode().SetTextScale(0)
      tumorMarkups_Needle.LockedOn()
      tumorMarkups_Needle.GetDisplayNode().VisibilityOff()
      parameterNode.SetNodeReferenceID(self.TUMOR_MARKUPS_NEEDLE, tumorMarkups_Needle.GetID())
    tumorMarkups_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())
    self.removeObservers(method=self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.modifyPoints)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.onTumorMarkupsNodeModified)

    parameterNode.SetNodeReferenceID(self.TUMOR_MARKUPS_NEEDLE, tumorMarkups_Needle.GetID())

    hydromarkMarkup_Needle = parameterNode.GetNodeReference(self.HYDROMARK_MARKUP_NEEDLE)
    if hydromarkMarkup_Needle is None:
      hydromarkMarkup_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.HYDROMARK_MARKUP_NEEDLE)
      hydromarkMarkup_Needle.CreateDefaultDisplayNodes()
      hydromarkMarkup_Needle.GetDisplayNode().SetTextScale(0)
      hydromarkMarkup_Needle.LockedOn()
      hydromarkMarkup_Needle.GetDisplayNode().VisibilityOff()
      parameterNode.SetNodeReferenceID(self.HYDROMARK_MARKUP_NEEDLE, hydromarkMarkup_Needle.GetID())
    hydromarkMarkup_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())
    self.addObserver(hydromarkMarkup_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.onHydromarkMarkupNodeModified)
    self.addObserver(hydromarkMarkup_Needle, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onHydromarkMarkupNodeModified)

    # Tumor model from hydromark measurements
    tumorModelHydromark = parameterNode.GetNodeReference(self.TUMOR_MODEL_HYDROMARK)
    if tumorModelHydromark is None:
      tumorModelHydromark = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL_HYDROMARK)
      tumorModelHydromark.CreateDefaultDisplayNodes()
      tumorModelHydromarkDisplay = tumorModelHydromark.GetDisplayNode()
      tumorModelHydromarkDisplay.SetColor(1, 1, 0)  # yellow
      tumorModelHydromarkDisplay.SetOpacity(0.3)
      tumorModelHydromarkDisplay.BackfaceCullingOff()
      tumorModelHydromarkDisplay.Visibility2DOn()
      tumorModelHydromarkDisplay.SetSliceIntersectionThickness(4)
      parameterNode.SetNodeReferenceID(self.TUMOR_MODEL_HYDROMARK, tumorModelHydromark.GetID())

    hydromarkToNeedle = parameterNode.GetNodeReference(self.HYDROMARK_TO_NEEDLE)
    tumorModelHydromark.SetAndObserveTransformNodeID(hydromarkToNeedle.GetID())

    RASMarkups = parameterNode.GetNodeReference(self.RAS_MARKUPS)
    if RASMarkups is None:
      RASMarkups = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.RAS_MARKUPS)
      RASMarkups.CreateDefaultDisplayNodes()
      RASMarkups.GetDisplayNode().SetTextScale(5)
      RASMarkups.GetDisplayNode().SetGlyphScale(0)
      RASMarkups.LockedOn()
      RASMarkups.SetDisplayVisibility(0)
      parameterNode.SetNodeReferenceID(self.RAS_MARKUPS, RASMarkups.GetID())
    RASMarkups.SetAndObserveTransformNodeID(needleToReference.GetID())

    sequenceLogic = slicer.modules.sequences.logic()

    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)

    if sequenceBrowserTracking is None:
      sequenceBrowserTracking = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.TRACKING_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.TRACKING_SEQUENCE_BROWSER, sequenceBrowserTracking.GetID())
    cauteryToReference = parameterNode.GetNodeReference(self.CAUTERY_TO_REFERENCE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, cauteryToReference, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, needleToReference, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, needleTipToNeedle, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, cauteryTipToCautery, sequenceBrowserTracking)
    sequenceBrowserTracking.SetRecording(sequenceNode, True)
    sequenceBrowserTracking.SetPlayback(sequenceNode, True)
    sequenceBrowserTracking.SetRecordingActive(False)

    # Ultrasound image
    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    if imageImage is None:
      imageImage = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.IMAGE_IMAGE)
      imageImage.CreateDefaultDisplayNodes()
      imageArray = np.zeros((1, 615, 525), dtype="uint8")
      slicer.util.updateVolumeFromArray(imageImage, imageArray)
      parameterNode.SetNodeReferenceID(self.IMAGE_IMAGE, imageImage.GetID())
    # Update prediction volume dimensions when image dimensions change
    self.addObserver(imageImage, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.onImageImageModified)

    imageToProbe = parameterNode.GetNodeReference(self.IMAGE_TO_PROBE)
    imageImage.SetAndObserveTransformNodeID(imageToProbe.GetID())
    self.setDepth(self.NORMAL_DEPTH_MM)

    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)

    if sequenceBrowserUltrasound is None:
      sequenceBrowserUltrasound = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.ULTRASOUND_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.ULTRASOUND_SEQUENCE_BROWSER, sequenceBrowserUltrasound.GetID())
    image_Image = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, image_Image, sequenceBrowserUltrasound)
    sequenceBrowserUltrasound.SetRecording(sequenceNode, True)
    sequenceBrowserUltrasound.SetPlayback(sequenceNode, True)
    imageToProbe = parameterNode.GetNodeReference(self.IMAGE_TO_PROBE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, imageToProbe, sequenceBrowserUltrasound)
    sequenceBrowserUltrasound.SetRecording(sequenceNode, True)
    sequenceBrowserUltrasound.SetPlayback(sequenceNode, True)
    probeToReference = parameterNode.GetNodeReference(self.PROBE_TO_REFERENCE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, probeToReference, sequenceBrowserUltrasound)
    sequenceBrowserUltrasound.SetRecording(sequenceNode, True)
    sequenceBrowserUltrasound.SetPlayback(sequenceNode, True)
    sequenceBrowserUltrasound.SetRecordingActive(False)

    # Show ultrasound in 2D view
    layoutManager = slicer.app.layoutManager()
    # Show ultrasound in red view.
    redSlice = layoutManager.sliceWidget('Red')
    controller = redSlice.sliceController()
    controller.setSliceVisible(True)
    redSliceLogic = redSlice.sliceLogic()
    image_Image = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    redSliceLogic.GetSliceCompositeNode().SetBackgroundVolumeID(image_Image.GetID())
    # Set up volume reslice driver.
    resliceLogic = slicer.modules.volumereslicedriver.logic()
    if resliceLogic:
      redNode = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
      # Typically the image is zoomed in, therefore it is faster if the original resolution is used
      # on the 3D slice (and also we can show the full image and not the shape and size of the 2D view)
      redNode.SetSliceResolutionMode(slicer.vtkMRMLSliceNode.SliceResolutionMatchVolumes)
      resliceLogic.SetDriverForSlice(image_Image.GetID(), redNode)
      resliceLogic.SetModeForSlice(6, redNode)  # Transverse mode, default for PLUS ultrasound.
      resliceLogic.SetFlipForSlice(False, redNode)
      resliceLogic.SetRotationForSlice(180, redNode)
      redSliceLogic.FitSliceToAll()
    else:
      logging.warning('Logic not found for Volume Reslice Driver')

    # Set up breach warning node
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    if breachWarningNode is None:
      breachWarningNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLBreachWarningNode', self.BREACH_WARNING)
      breachWarningNode.SetWarningColor(1, 0, 0)

      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      breachWarningNode.SetOriginalColor(tumorModel_Needle.GetDisplayNode().GetColor())
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      breachWarningNode.SetAndObserveToolTransformNodeId(cauteryTipToCautery.GetID())
      breachWarningNode.SetAndObserveWatchedModelNodeID(tumorModel_Needle.GetID())
      parameterNode.SetNodeReferenceID(self.BREACH_WARNING, breachWarningNode.GetID())

      # Prevent warning that there is no surface model (before tumor contouring)
      self.setBreachWarning(False)
      
    warningSoundEnabled = slicer.util.settingsValue(self.WARNING_SOUND_SETTING, True, converter=slicer.util.toBool)
    self.setWarningSound(warningSoundEnabled)

    # Line properties can only be set after the line is created (made visible at least once)
    breachWarningLogic = slicer.modules.breachwarning.logic()
    breachWarningLogic.SetLineToClosestPointVisibility(True, breachWarningNode)
    distanceRulerFontSize = slicer.util.settingsValue(self.RULER_FONT_SIZE, self.RULER_DISTANCE_DEFAULT_FONT_SIZE, converter=lambda x: float(x))
    breachWarningLogic.SetLineToClosestPointTextScale(distanceRulerFontSize, breachWarningNode)
    breachWarningLogic.SetLineToClosestPointColor(0, 0, 0.5, breachWarningNode)

    # Ruler display and distance text setting
    displayRulerEnabled = slicer.util.settingsValue(self.DISPLAY_RULER_SETTING, True, converter=slicer.util.toBool)
    breachWarningLogic.SetLineToClosestPointVisibility(displayRulerEnabled, breachWarningNode)
    self.setRulerDistanceFontSize(distanceRulerFontSize)
    self.addObserver(breachWarningNode, vtk.vtkCommand.ModifiedEvent, self.onBreachWarningNodeChanged)

    breachMarkups_Needle = parameterNode.GetNodeReference(self.BREACH_MARKUPS_NEEDLE)
    if breachMarkups_Needle is None:
      breachMarkups_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.BREACH_MARKUPS_NEEDLE)
      breachMarkups_Needle.CreateDefaultDisplayNodes()
      # Breach markup size setting
      breachMarkupsSize = slicer.util.settingsValue(self.BREACH_MARKUPS_SIZE_SETTING, self.BREACH_MARKUPS_SIZE_DEFAULT, converter=lambda x: float(x))
      breachMarkups_Needle.GetDisplayNode().SetGlyphScale(breachMarkupsSize)
      breachMarkups_Needle.GetDisplayNode().SetTextScale(0)
      breachMarkups_Needle.GetDisplayNode().SetColor(1, 0, 0)
      breachMarkups_Needle.LockedOn()
      # Breach markup display setting
      breachMarkupsDisplay = slicer.util.settingsValue(self.BREACH_MARKUPS_DISPLAY_SETTING, True, converter=slicer.util.toBool)
      breachMarkups_Needle.SetDisplayVisibility(breachMarkupsDisplay)
      parameterNode.SetNodeReferenceID(self.BREACH_MARKUPS_NEEDLE, breachMarkups_Needle.GetID())
    breachMarkups_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())
    parameterNode.SetParameter(self.BREACH_STATUS, "False")

    cauteryCameraToCautery = parameterNode.GetNodeReference(self.CAUTERYCAMERA_TO_CAUTERY)
    if cauteryCameraToCautery is None:
      cauteryCameraToCauteryFileWithPath = self.resourcePath(self.CAUTERYCAMERA_TO_CAUTERY + ".h5")
      try:
        logging.info("Loading cautery camera to cautery calibration from file: {}".format(cauteryCameraToCauteryFileWithPath))
        cauteryCameraToCautery = slicer.util.loadTransform(cauteryCameraToCauteryFileWithPath)
      except Exception as e:
        logging.info("Creating cautery camera to cautery calibration file, because none was found at: "
                     "{}".format(cauteryCameraToCauteryFileWithPath))
        cauteryCameraToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYCAMERA_TO_CAUTERY)
        m = self.createMatrixFromString('1 0 0 0 '
                                        '0 1 0 5 '
                                        '0 0 -1 -200 '
                                        '0 0 0 1')
        cauteryCameraToCautery.SetMatrixTransformToParent(m)
      parameterNode.SetNodeReferenceID(self.CAUTERYCAMERA_TO_CAUTERY, cauteryCameraToCautery.GetID())
    cauteryCameraToCautery.SetAndObserveTransformNodeID(cauteryTipToCautery.GetID())

    # AI Prediction
    predictionImage = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    if predictionImage is None:
      predictionImage = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.PREDICTION_VOLUME)
      predictionImage.CreateDefaultDisplayNodes()
      predictionDisplayNode = predictionImage.GetDisplayNode()
      predictionDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeBlue")
      imageArray = np.zeros((1, 615, 525), dtype="uint8")
      slicer.util.updateVolumeFromArray(predictionImage, imageArray)
      parameterNode.SetNodeReferenceID(self.PREDICTION_VOLUME, predictionImage.GetID())

    predToProbe = parameterNode.GetNodeReference(self.PREDICTION_TO_PROBE)
    predictionImage.SetAndObserveTransformNodeID(predToProbe.GetID())

    # Create model for AI tumor
    tumorModelAI = parameterNode.GetNodeReference(self.TUMOR_MODEL_AI)
    if tumorModelAI is None:
      tumorModelAI = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL_AI)
      tumorModelAI.CreateDefaultDisplayNodes()
      tumorModelAI.SetAndObserveTransformNodeID(needleToReference.GetID())
      parameterNode.SetNodeReferenceID(self.TUMOR_MODEL_AI, tumorModelAI.GetID())

    # Event recording
    eventTableNode = parameterNode.GetNodeReference(self.EVENT_TABLE_NODE)
    if eventTableNode is None:
      eventTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", self.EVENT_TABLE_NODE)
      for i in range(self.LAST_COLUMN):
        eventTableNode.AddColumn()
      eventTableNode.RenameColumn(self.TIME_COLUMN, "Time")
      eventTableNode.RenameColumn(self.SEQUENCE_TIME_COLUMN, "Sequence Index")
      eventTableNode.RenameColumn(self.EVENT_DESCRIPTION_COLUMN, "Description")
      eventTableNode.SetUseColumnTitleAsColumnHeader(True)
      parameterNode.SetNodeReferenceID(self.EVENT_TABLE_NODE, eventTableNode.GetID())

    # iKnife TIC data
    iKnifeTICNode = parameterNode.GetNodeReference(self.IKNIFE_TIC)
    if iKnifeTICNode is None:
      iKnifeTICNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.IKNIFE_TIC)
      ticArray = np.zeros(2)
      slicer.util.updateVolumeFromArray(iKnifeTICNode, ticArray)
      parameterNode.SetNodeReferenceID(self.IKNIFE_TIC, iKnifeTICNode.GetID())

    # OpenIGTLink connection
    self.setupPlusServer()

  def setupTransformHierarchy(self):
    """
    Sets up transform nodes in the scene if they don't exist yet.
    """
    parameterNode = self.getParameterNode()

    # ReferenceToRas puts everything in a rough anatomical reference (right, anterior, superior).
    # Translation is not relevant for ReferenceToRas, and rotation is fine even with +/- 30 deg error.

    referenceToRas = self.addLinearTransformToScene(self.REFERENCE_TO_RAS)
    settings = qt.QSettings()
    referenceToRasSetting = slicer.util.settingsValue(self.REFERENCE_TO_RAS_SETTING, "")
    if referenceToRasSetting:
      referenceToRasMatrix = json.loads(referenceToRasSetting)
      referenceToRasMatrix = np.array(referenceToRasMatrix)
      referenceToRasMatrix = slicer.util.vtkMatrixFromArray(referenceToRasMatrix)
      referenceToRas.SetMatrixTransformToParent(referenceToRasMatrix)
    else:
      # Create default referenceToRas transform
      m = self.createMatrixFromString('0 0 -1 0 ' 
                                      '0.258819 -0.965926 0 0 ' 
                                      '-0.965926 -0.258819 0 0 ' 
                                      '0 0 0 1')
      referenceToRas.SetMatrixTransformToParent(m)
      # Save default referenceToRas transform
      referenceToRasMatrix = slicer.util.arrayFromTransformMatrix(referenceToRas)
      referenceToRasMatrix = referenceToRasMatrix.tolist()
      referenceToRasMatrix = json.dumps(referenceToRasMatrix)
      settings.setValue(self.REFERENCE_TO_RAS_SETTING, referenceToRasMatrix)

    # Needle tracking
    needleToReference = self.addLinearTransformToScene(self.NEEDLE_TO_REFERENCE, parentTransform=referenceToRas)
    
    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    if needleTipToNeedle is None:
      needleTipToNeedleFileWithPath = self.resourcePath(self.NEEDLETIP_TO_NEEDLE + ".h5")
      try:
        logging.info("Loading needle calibration from file: {}".format(needleTipToNeedleFileWithPath))
        needleTipToNeedle = slicer.util.loadTransform(needleTipToNeedleFileWithPath)
      except Exception as e:
        logging.info("Creating needle calibration file, because none was found as: {}".format(needleTipToNeedleFileWithPath))
        needleTipToNeedle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.NEEDLETIP_TO_NEEDLE)
      parameterNode.SetNodeReferenceID(self.NEEDLETIP_TO_NEEDLE, needleTipToNeedle.GetID())
    needleTipToNeedle.SetAndObserveTransformNodeID(needleToReference.GetID())

    # Cautery tracking
    cauteryToReference = self.addLinearTransformToScene(self.CAUTERY_TO_REFERENCE, parentTransform=referenceToRas)
    self.addLinearTransformToScene(self.CAUTERY_TO_NEEDLE)  # For cautery calibration

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    if cauteryTipToCautery is None:
      cauteryTipToCauteryFileWithPath = self.resourcePath(self.CAUTERYTIP_TO_CAUTERY + ".h5")
      try:
        logging.info("Loading cautery calibration from file: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.util.loadTransform(cauteryTipToCauteryFileWithPath)
      except Exception as e:
        logging.info("Creating cautery calibration file, because none was found as: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYTIP_TO_CAUTERY)
      parameterNode.SetNodeReferenceID(self.CAUTERYTIP_TO_CAUTERY, cauteryTipToCautery.GetID())
    cauteryTipToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

    # add observer for cautery position data recording
    self.addObserver(cauteryTipToCautery, slicer.vtkMRMLLinearTransformNode.TransformModifiedEvent, self.onTrackingDataModified)

    # Ultrasound image tracking
    probeToReference = self.addLinearTransformToScene(self.PROBE_TO_REFERENCE, parentTransform=referenceToRas)
    imageToProbe = self.addLinearTransformToScene(self.IMAGE_TO_PROBE, parentTransform=probeToReference)

    # Transforms to display tumour reconstruction in needle coordinate system
    probeToNeedle = self.addLinearTransformToScene(self.PROBE_TO_NEEDLE)
    predToProbe = self.addLinearTransformToScene(self.PREDICTION_TO_PROBE, parentTransform=probeToNeedle)
    imageToProbeMatrix = vtk.vtkMatrix4x4()
    imageToProbe.GetMatrixTransformToParent(imageToProbeMatrix)
    predToProbe.SetMatrixTransformToParent(imageToProbeMatrix)

    # Hydromark to needle to position ellipsoid
    self.addLinearTransformToScene(self.HYDROMARK_TO_NEEDLE, parentTransform=needleToReference)

  def addLinearTransformToScene(self, transformName, parentTransform=None):
    """
    Makes sure there is a transform with specified name, and it is referenced in parameter node by its name.
    :param transformName: str, name and reference of the transform.
    :param parentTransform: vtkMRMLLinearTransformNode, optional parent tranform
    :returns: vtkMRMLLinearTransformNode, the existing or newly created transform named trasnformName
    """
    parameterNode = self.getParameterNode()
    transform = parameterNode.GetNodeReference(transformName)
    if transform is None:
      transform = slicer.mrmlScene.GetFirstNodeByName(transformName)
      if transform is None:
        transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", transformName)
      parameterNode.SetNodeReferenceID(transformName, transform.GetID())
    if parentTransform is not None:
      transform.SetAndObserveTransformNodeID(parentTransform.GetID())
    else:
      transform.SetAndObserveTransformNodeID(None)
    return transform

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
      configTextNode.SetForceCreateStorageNode(slicer.vtkMRMLTextNode.CreateStorageNodeAlways)
      parameterNode.SetNodeReferenceID(self.CONFIG_TEXT_NODE, configTextNode.GetID())
      configTextNode.SaveWithSceneOff()
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
      parameterNode.SetNodeReferenceID(self.PLUS_SERVER_LAUNCHER_NODE, plusServerLauncherNode.GetID())
      plusServerLauncherNode.SetLogLevel(4)  # DEBUG
      plusServerLauncherNode.SaveWithSceneOff()

    if plusServerLauncherNode.GetNodeReferenceID('plusServerRef') != plusServerNode.GetID():
      plusServerLauncherNode.AddAndObserveServerNode(plusServerNode)

    # Set hostname from settings
    lastHostname = slicer.util.settingsValue(self.HOSTNAME_SETTING, "")
    if lastHostname != "":
      self.setHostname(lastHostname)

    # Start client connector for prediction image
    predictionConnectorNode = parameterNode.GetNodeReference(self.PREDICTION_CONNECTOR_NODE)
    if not predictionConnectorNode:
      predictionConnectorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLIGTLConnectorNode", self.PREDICTION_CONNECTOR_NODE)
      predictionConnectorNode.SetTypeClient(self.PREDICTION_HOSTNAME, self.PREDICTION_PORT)
      parameterNode.SetNodeReferenceID(self.PREDICTION_CONNECTOR_NODE, predictionConnectorNode.GetID())
      predictionConnectorNode.SaveWithSceneOff()

    # create connector node for iKnife connection
    iKnifeConnectorNode = parameterNode.GetNodeReference(self.IKNIFE_CONNECTOR_NODE)
    if not iKnifeConnectorNode:
      iKnifeConnectorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLIGTLConnectorNode", self.IKNIFE_CONNECTOR_NODE)
      iKnifeConnectorNode.SetTypeClient(self.IKNIFE_HOSTNAME, self.IKNIFE_PORT)
      parameterNode.SetNodeReferenceID(self.IKNIFE_CONNECTOR_NODE, iKnifeConnectorNode.GetID())
      iKnifeConnectorNode.SaveWithSceneOff()

  def setTrackingSequenceBrowser(self, recording):
    parameterNode = self.getParameterNode()
    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)
    sequenceBrowserTracking.SetRecordingActive(recording)  # stop

  def onTrackingDataModified(self, caller=None, event=None):
    parameterNode = self.getParameterNode()
    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)
    if sequenceBrowserTracking.GetRecordingActive():
      numItems = sequenceBrowserTracking.GetNumberOfItems()
      currentTime = sequenceBrowserTracking.GetMasterSequenceNode().GetNthIndexValue(numItems - 1)
      if currentTime and (currentTime := float(currentTime)) > self.lastTime:
        # update gui with sequence browser time
        if self.updateRecordingTimeCallback:
          self.updateRecordingTimeCallback(str(currentTime))

        # get cautery tip position in RAS
        cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
        cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
        cauteryTipToCautery.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
        cauteryTipRAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0, 0, 0, 1])
        cauteryTipRAS = np.array(cauteryTipRAS)
        
        # get distance travelled by cautery
        cauteryTravelDistance = np.linalg.norm(cauteryTipRAS - self.lastCauteryTipRAS)
        cauterySpeed = cauteryTravelDistance / (currentTime - self.lastTime)

        # get tip position in needle coordinate
        needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
        cauteryTipToNeedleMatrix = vtk.vtkMatrix4x4()
        cauteryTipToCautery.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedleMatrix)
        cauteryTipNeedle = cauteryTipToNeedleMatrix.MultiplyFloatPoint([0, 0, 0, 1])
        cauteryTipNeedle = np.array(cauteryTipNeedle)

        # get distance to tumor
        breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
        distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()

        # get tumor center in RAS and tumor model range
        tumorModel = parameterNode.GetNodeReference(self.TUMOR_MODEL)
        polydata = tumorModel.GetPolyData()
        if polydata:
          points = polydata.GetPoints()
          numPoints = points.GetNumberOfPoints()

          # Convert points to NumPy array and change from LPS to RAS by negating the X and Y coordinates
          coords = np.array([(-points.GetPoint(i)[0], -points.GetPoint(i)[1], points.GetPoint(i)[2]) for i in range(numPoints)])
          center = np.array2string(np.mean(coords, axis=0))
          xRange = np.max(coords[:, 0]) - np.min(coords[:, 0])
          yRange = np.max(coords[:, 1]) - np.min(coords[:, 1])
          zRange = np.max(coords[:, 2]) - np.min(coords[:, 2])
          tumorRange = np.array2string(np.array([xRange, yRange, zRange]))
        else:
          center = ""
          tumorRange = ""

        # add iknife data if it exists
        iKnifeTICNode = parameterNode.GetNodeReference(self.IKNIFE_TIC)
        iKnifeTICArray = slicer.util.arrayFromVolume(iKnifeTICNode)
        if not np.any(iKnifeTICArray):  # no scan number or tic
          scanNumber = ""
          tic = ""
        else:
          scanNumber = str(int(iKnifeTICArray[0]))
          tic = str(int(iKnifeTICArray[1]))

        # add data to list
        currentData = [[currentTime], [scanNumber], [np.array2string(cauteryTipNeedle[:3])], 
                       [distanceToTumor], [cauterySpeed], [center], [tumorRange], [tic]]
        self.positionMatrix = np.append(self.positionMatrix, currentData, axis=1)
        self.lastTime = currentTime
        self.lastCauteryTipRAS = cauteryTipRAS

  def exportTrackingDataToCsv(self, csvFilePath):
    df = pd.DataFrame(
      self.positionMatrix, 
      ["Time (s)", "Scan Number", "Cautery Tip Needle", "Distance To Tumour (mm)", 
       "Cautery Speed (mm/s)", "Tumor Center", "Tumor Dimensions", "TIC"]
    ).T
    df.to_csv(csvFilePath, index=False)

  def onUltrasoundSequenceBrowserClicked(self, toggled):
    self.setUltrasoundSequenceBrowser(toggled)
    self.setLivePrediction(toggled)

  def setLivePrediction(self, toggled):
    logging.info(f"setLivePrediction({toggled})")
    parameterNode = self.getParameterNode()

    if toggled:
      predictionConnectorNode = parameterNode.GetNodeReference(self.PREDICTION_CONNECTOR_NODE)
      if predictionConnectorNode and predictionConnectorNode.GetState() == predictionConnectorNode.StateConnected:
        logging.info("Starting volume reconstruction")
        self.predictionStarted = True
        self.setRegionOfInterestNode()
        reconstructionNode = self.setVolumeReconstructionNode()
        self.reconstructionLogic.StartLiveVolumeReconstruction(reconstructionNode)

    else:
      if self.predictionStarted == True:
        logging.info("Stopping volume reconstruction")
        reconstructionNode = parameterNode.GetNodeReference(self.RECONSTRUCTION_NODE)
        self.reconstructionLogic.StopLiveVolumeReconstruction(reconstructionNode)
        # Convert to convex hull
        self.createConvexHullFromVolume()
        self.predictionStarted = False

  def setUltrasoundSequenceBrowser(self, isRecording):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    connectorNode = plusServerNode.GetNodeReference("plusServerConnectorNodeRef")
    if connectorNode:
      if isRecording:
        commandXML = f"""
          <Command Name=\"StartRecording\" CaptureDeviceId=\"CaptureDevice\">
          </Command>
        """
        command = slicer.vtkSlicerOpenIGTLinkCommand()
        command.SetName("StartRecording")
        command.SetCommandContent(commandXML)
        connectorNode.SendCommand(command)
      else:
        commandXML = f"""
          <Command Name=\"StopRecording\" CaptureDeviceId=\"CaptureDevice\">
          </Command>
        """
        command = slicer.vtkSlicerOpenIGTLinkCommand()
        command.SetName("StopRecording")
        command.SetCommandContent(commandXML)
        connectorNode.SendCommand(command)

    # sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)
    # sequenceBrowserUltrasound.SetRecordingActive(isRecording)
  
  def setContourVisibility(self, toggled):
    parameterNode = self.getParameterNode()
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.GetDisplayNode().SetVisibility2D(toggled)
    tumorModel_Needle.GetDisplayNode().SetVisibility3D(toggled)
  
  def setHydromarkVisibility(self, toggled, inContouringTab):
    parameterNode = self.getParameterNode()
    hydromarkMarkup_Needle = parameterNode.GetNodeReference(self.HYDROMARK_MARKUP_NEEDLE)
    tumorModelHydromark = parameterNode.GetNodeReference(self.TUMOR_MODEL_HYDROMARK)
    if inContouringTab:
      hydromarkMarkup_Needle.GetDisplayNode().SetVisibility(toggled)
    tumorModelHydromark.GetDisplayNode().SetVisibility2D(toggled)
    tumorModelHydromark.GetDisplayNode().SetVisibility3D(toggled)

  def setSegmentationVisibility(self, toggled):
    parameterNode = self.getParameterNode()
    parameterNode.SetParameter(self.AI_VISIBLE, str(toggled))
    predictionVolume = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    tumorModelAI = parameterNode.GetNodeReference(self.TUMOR_MODEL_AI)
    if tumorModelAI:
      displayNode = tumorModelAI.GetDisplayNode()
      displayNode.SetVisibility2D(toggled)
      displayNode.SetVisibility3D(toggled)
    if toggled:
      slicer.util.setSliceViewerLayers(foreground=predictionVolume, foregroundOpacity=0.5)
    else:
      slicer.util.setSliceViewerLayers(foreground=None)

  def setRegionOfInterestNode(self):
    parameterNode = self.getParameterNode()
    roiNode = parameterNode.GetNodeReference(self.ROI_NODE)
    if roiNode is None:
      # Create new ROI node
      roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", self.ROI_NODE)
      roiNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.ROI_NODE, roiNode.GetID())
      roiNode.SetDisplayVisibility(False)

      # Set center of ROI to be center of current image
      prediction = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
      bounds = [0, 0, 0, 0, 0, 0]
      prediction.GetSliceBounds(bounds, vtk.vtkMatrix4x4())
      sliceCenter = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2]
      roiNode.SetXYZ(sliceCenter)
      roiNode.SetRadiusXYZ(100, 100, 100)
      logging.info(f"Added a 10x10x10cm ROI at position: {sliceCenter}")

  def setVolumeReconstructionNode(self):
    parameterNode = self.getParameterNode()

    # Create volume reconstruction node if it doesn't exist
    reconstructionNode = parameterNode.GetNodeReference(self.RECONSTRUCTION_NODE)
    if reconstructionNode is None:
      reconstructionNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLVolumeReconstructionNode", self.RECONSTRUCTION_NODE)
      parameterNode.SetNodeReferenceID(self.RECONSTRUCTION_NODE, reconstructionNode.GetID())
      reconstructionNode.SetLiveVolumeReconstruction(True)
      reconstructionNode.SetInterpolationMode(1)  # linear interpolation
      reconstructionNode.SetAndObserveInputVolumeNode(parameterNode.GetNodeReference(self.PREDICTION_VOLUME))
      reconstructionNode.SetAndObserveInputROINode(parameterNode.GetNodeReference(self.ROI_NODE))

    # Create volume node for reconstruction output
    reconstructionVolume = parameterNode.GetNodeReference(self.RECONSTRUCTION_VOLUME)
    if reconstructionVolume is None:
      reconstructionVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.RECONSTRUCTION_VOLUME)
      reconstructionVolume.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.RECONSTRUCTION_VOLUME, reconstructionVolume.GetID())

      reconstructionVolume.SetAndObserveTransformNodeID(None)
      reconstructionNode.SetAndObserveOutputVolumeNode(reconstructionVolume)

      volRenLogic = slicer.modules.volumerendering.logic()
      volRenDisplayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(reconstructionVolume)
      volRenDisplayNode.SetAndObserveROINodeID(parameterNode.GetNodeReference(self.ROI_NODE).GetID())
      reconstructionVolume.SetDisplayVisibility(False)

    return reconstructionNode
  
  def createConvexHullFromVolume(self):
    logging.info("Creating surface model from volume")

    parameterNode = self.getParameterNode()
    reconstructionVolume = parameterNode.GetNodeReference(self.RECONSTRUCTION_VOLUME)
    tumorModelAI = parameterNode.GetNodeReference(self.TUMOR_MODEL_AI)
    
    # Display properties
    visibleAI = parameterNode.GetParameter(self.AI_VISIBLE)
    displayNode = tumorModelAI.GetDisplayNode()
    displayNode.SetVisibility2D(True if visibleAI == "True" else False)
    displayNode.SetVisibility3D(True if visibleAI == "True" else False)
    displayNode.SetColor(0, 0, 1)  # blue
    displayNode.SetOpacity(0.3)
    displayNode.BackfaceCullingOff()
    displayNode.SetSliceIntersectionThickness(4)

    # Set up grayscale model maker CLI node
    parameters = {
        "InputVolume": reconstructionVolume.GetID(),
        "OutputGeometry": tumorModelAI.GetID(),
        "Threshold": float(parameterNode.GetParameter(self.AI_THRESHOLD)),
        "Smooth": self.DEFAULT_SMOOTH,
        "Decimate": self.DEFAULT_DECIMATE,
        "SplitNormals": True,
        "PointNormals": True
    }
    modelMaker = slicer.modules.grayscalemodelmaker

    # Run the CLI
    cliNode = slicer.cli.runSync(modelMaker, None, parameters)

    # Process results
    if cliNode.GetStatus() & cliNode.ErrorsMask:
        # error
        errorText = cliNode.GetErrorText()
        slicer.mrmlScene.RemoveNode(cliNode)
        raise ValueError("CLI execution failed: " + errorText)
    # success
    slicer.mrmlScene.RemoveNode(cliNode)

    # Extract largest portion
    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    connectivityFilter.SetInputData(tumorModelAI.GetPolyData())
    connectivityFilter.SetExtractionModeToLargestRegion()

    # Clean up model
    cleanFilter = vtk.vtkCleanPolyData()
    cleanFilter.SetInputConnection(connectivityFilter.GetOutputPort())

    # Convert to convex hull
    convexHull = vtk.vtkDelaunay3D()
    convexHull.SetInputConnection(cleanFilter.GetOutputPort())
    outerSurface = vtk.vtkGeometryFilter()
    outerSurface.SetInputConnection(convexHull.GetOutputPort())
    outerSurface.Update()
    tumorModelAI.SetAndObservePolyData(outerSurface.GetOutput())

  def setDeleteLastFiducialClicked(self, numberOfPoints):
    deleted_coord = [0.0, 0.0, 0.0]
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints - 1,deleted_coord)
    tumorMarkups_Needle.RemoveNthControlPoint(numberOfPoints - 1)
    logging.info("Deleted last fiducial at %s", deleted_coord)
    if numberOfPoints <= 1:
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      parameterNode = self.getParameterNode()
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      tumorModel_Needle.Modified()

  def setDeleteAllFiducialsClicked(self):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.RemoveAllControlPoints()
    logging.info("Deleted all fiducials")

    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(0.001)
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
    tumorModel_Needle.Modified()

  def setMarkPointCauteryTipClicked(self):
    parameterNode = self.getParameterNode()
    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    cauteryTipToNeedle = vtk.vtkMatrix4x4()
    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    cauteryTipToCautery.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedle)
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.AddControlPoint(
      cauteryTipToNeedle.GetElement(0, 3),
      cauteryTipToNeedle.GetElement(1, 3),
      cauteryTipToNeedle.GetElement(2, 3)
    )
    logging.info(
      "Tumor point placed at cautery tip, (%s, %s, %s)",
      cauteryTipToNeedle.GetElement(0, 3),
      cauteryTipToNeedle.GetElement(1, 3),
      cauteryTipToNeedle.GetElement(2, 3)
    )

  def setFreezeUltrasoundClicked(self, toggled):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    plusServerConnectorNode = plusServerNode.GetNodeReference("plusServerConnectorNodeRef")
    if plusServerConnectorNode:
      if toggled:
        plusServerConnectorNode.Stop()
      else:
        plusServerConnectorNode.Start()

  def applyDilation(self, model, dilationValue):
    parameterNode = self.getParameterNode()
    segmentationLogic = slicer.modules.segmentations.logic()
    modelNode = parameterNode.GetNodeReference(model)
    modelNode.SetAndObserveTransformNodeID(None)  # move out of transform

    # convert model to labelmap
    modelSegmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationLogic.ImportModelToSegmentationNode(modelNode, modelSegmentation)
    modelLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    segmentationLogic.ExportAllSegmentsToLabelmapNode(modelSegmentation, modelLabelmap, slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)

    import vtkITK

    modelImageData = modelLabelmap.GetImageData()
    margin = vtkITK.vtkITKImageMargin()
    margin.SetInputData(modelImageData)
    margin.CalculateMarginInMMOn()
    margin.SetOuterMarginMM(abs(dilationValue))
    margin.Update()
    modelImageData.ShallowCopy(margin.GetOutput())

    # convert to segmentation node
    segmentationLogic.ImportLabelmapToSegmentationNode(modelLabelmap, modelSegmentation)
    modelSegment = modelSegmentation.GetSegmentation().GetNthSegment(1)
    modelName = f"TumorModelDilate{dilationValue}mm"
    modelSegment.SetName(modelName)
    segmentationLogic.ExportVisibleSegmentsToModels(modelSegmentation, 3)
    dilatedModelNode = slicer.mrmlScene.GetFirstNodeByName(modelName)

    # move both tumor models back to NeedleToReference
    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    modelNode.SetAndObserveTransformNodeID(needleToReference.GetID())
    dilatedModelNode.SetAndObserveTransformNodeID(needleToReference.GetID())

    # fix opacity and color models
    modelNode.GetDisplayNode().SetOpacity(0.3)
    dilatedModelDisplayNode = dilatedModelNode.GetDisplayNode()
    dilatedModelDisplayNode.SetOpacity(0.15)
    dilatedModelDisplayNode.SetColor(0, 1, 0)  # green
    dilatedModelDisplayNode.SliceIntersectionVisibilityOn()
    dilatedModelDisplayNode.SetSliceIntersectionThickness(4)

    # cleanup temporary nodes
    slicer.mrmlScene.RemoveNode(modelLabelmap.GetDisplayNode().GetColorNode())
    slicer.mrmlScene.RemoveNode(modelLabelmap)
    slicer.mrmlScene.RemoveNode(modelSegmentation.GetDisplayNode().GetColorNode())
    slicer.mrmlScene.RemoveNode(modelSegmentation)

  def setPlusServerClicked(self, toggled):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    predictionConnectorNode = parameterNode.GetNodeReference(self.PREDICTION_CONNECTOR_NODE)
    iKnifeConnectorNode = parameterNode.GetNodeReference(self.IKNIFE_CONNECTOR_NODE)
    if plusServerNode:
      if toggled:
        plusServerNode.StartServer()
        predictionConnectorNode.Start()
        iKnifeConnectorNode.Start()
        self.removeObservers(self.onNodeAdded)
        self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)
      else:
        plusServerNode.StopServer()
        predictionConnectorNode.Stop()
        iKnifeConnectorNode.Stop()

  def setPlusConfigFile(self, configFilepath):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    configTextNode = parameterNode.GetNodeReference(self.CONFIG_TEXT_NODE)
    configTextStorageNode = configTextNode.GetStorageNode()
    configTextStorageNode.SetFileName(configFilepath)
    configTextStorageNode.ReadData(configTextNode)
    plusServerNode.SetAndObserveConfigNode(configTextNode)

  def setHostname(self, hostname):
    parameterNode = self.getParameterNode()
    plusServerLauncherNode = parameterNode.GetNodeReference(self.PLUS_SERVER_LAUNCHER_NODE)
    if plusServerLauncherNode:
      plusServerLauncherNode.SetHostname(hostname)

  def onNodeAdded(self, caller=None, event=None):
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    plusServerConnectorNode = plusServerNode.GetNodeReference("plusServerConnectorNodeRef")
    if plusServerConnectorNode and plusServerConnectorNode != self._connectorNode:
      self._connectorNode = plusServerConnectorNode
      self.updateUltrasoundParameters()

  def updateUltrasoundParameters(self, caller=None, event=None):
    if self._connectorNode and self._connectorNode.GetState() == slicer.vtkMRMLIGTLConnectorNode.StateConnected:
      self._connectorNode.SendCommand(self._setDepthCommand)
      self._connectorNode.SendCommand(self._setFocusDepthCommand)
      self._connectorNode.SendCommand(self._setFrequencyCommand)

  def setToolModelClicked(self, toggled):
    logging.info("setToolModelClicked")
    settings = qt.QSettings()
    settings.setValue(self.CAUTERY_MODEL_SELECTED, "True" if toggled else "False")
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    isCauteryVisible = slicer.util.settingsValue(self.CAUTERY_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    if isCauteryVisible:  # Only toggle if cautery visibility is enabled
      if cauteryModel is not None and stickModel is not None:
        if toggled:
          cauteryModel.SetDisplayVisibility(True)
          stickModel.SetDisplayVisibility(False)
        else:
          cauteryModel.SetDisplayVisibility(False)
          stickModel.SetDisplayVisibility(True)

  def setBreachWarning(self, active):
    """
    Turns breach warning on or off
    """
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    if active == True:
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      breachWarningNode.SetAndObserveToolTransformNodeId(cauteryTipToCautery.GetID())
    else:
      breachWarningNode.SetAndObserveToolTransformNodeId(None)

  def setRulerVisibility(self, toggled):
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    breachWarningLogic = slicer.modules.breachwarning.logic()
    if toggled:
      breachWarningLogic.SetLineToClosestPointVisibility(True, breachWarningNode)
    else:
      breachWarningLogic.SetLineToClosestPointVisibility(False, breachWarningNode)

  def setRulerDistanceFontSize(self, fontSize):
    parameterNode = self.getParameterNode()

    # ruler
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    breachWarningLogic = slicer.modules.breachwarning.logic()
    if slicer.util.settingsValue(self.DISPLAY_DISTANCE_SETTING, True, converter=slicer.util.toBool):
      breachWarningLogic.SetLineToClosestPointTextScale(fontSize, breachWarningNode)
    else:
      breachWarningLogic.SetLineToClosestPointTextScale(0, breachWarningNode)

    # corner annotation
    for i in range(slicer.app.layoutManager().threeDViewCount):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      view.cornerAnnotation().SetLinearFontScaleFactor(fontSize)
      view.forceRender()

  def setBrightness(self, maxLevel):
    self.setImageMinMaxLevel(0, maxLevel)

  def setImageMinMaxLevel(self, minLevel, maxLevel):
    parameterNode = self.getParameterNode()
    liveUSNode = parameterNode.GetNodeReference(self.IMAGE_IMAGE).GetDisplayNode()
    liveUSNode.SetAutoWindowLevel(0)
    liveUSNode.SetWindowLevelMinMax(minLevel, maxLevel)

  def setDepth(self, depth):
    if depth == self.NORMAL_DEPTH_MM:
      imageToProbePath = self.resourcePath(self.IMAGE_TO_PROBE_NORMAL_PATH)
      focusDepthPercent = self.NORMAL_FOCUS_DEPTH_PERCENT
      frequency = self.NORMAL_FREQUENCY
    else:
      imageToProbePath = self.resourcePath(self.IMAGE_TO_PROBE_DEEP_PATH)
      focusDepthPercent = self.DEEP_FOCUS_DEPTH_PERCENT
      frequency = self.DEEP_FREQUENCY

    # Update ultrasound settings using PLUS
    self._setDepthCommand = self.getSetUSParameterCommand("DepthMm", depth)
    self._setFocusDepthCommand = self.getSetUSParameterCommand("FocusDepthPercent", focusDepthPercent)
    self._setFrequencyCommand = self.getSetUSParameterCommand("FrequencyMhz", frequency)
    self.updateUltrasoundParameters()

    # Set ImageToProbe from file
    parameterNode = self.getParameterNode()
    tempNode = slicer.util.loadTransform(imageToProbePath)
    imageToProbe = parameterNode.GetNodeReference(self.IMAGE_TO_PROBE)
    imageToProbeMatrix = vtk.vtkMatrix4x4()
    tempNode.GetMatrixTransformToParent(imageToProbeMatrix)
    imageToProbe.SetMatrixTransformToParent(imageToProbeMatrix)
    slicer.mrmlScene.RemoveNode(tempNode)

  def getSetUSParameterCommand(self, parameterName, value):
    setUSParameterXML = f"""
      <Command Name=\"SetUsParameter\" UsDeviceId=\"{self.US_DEVICE_ID}\">
        <Parameter Name=\"{parameterName}\" Value=\"{value}\" />
      </Command>
    """
    cmdSetParameter = slicer.vtkSlicerOpenIGTLinkCommand()
    cmdSetParameter.SetName("SetUsParameter")
    cmdSetParameter.SetTimeoutSec(5.0)
    cmdSetParameter.SetBlocking(False)
    cmdSetParameter.SetCommandContent(setUSParameterXML)
    cmdSetParameter.ClearResponseMetaData()
    return cmdSetParameter

  def onTumorMarkupsNodeModified(self, observer, eventid):
    logging.debug("onTumorMarkupsNodeModified")
    self.createTumorFromMarkups()
    parameterNode = self.getParameterNode()
    parameterNode.Modified()

  def createTumorFromMarkups(self):
    logging.debug('createTumorFromMarkups')
    # Create polydata point set from markup points
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if numberOfPoints < 1:
      # sphereSource = vtk.vtkSphereSource()
      # # sphereSource.SetRadius(0.001)
      # tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      # tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      # tumorModel_Needle.Modified()
      return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]
    for i in range(numberOfPoints):
      tumorMarkups_Needle.GetNthControlPointPosition(i, new_coord)
      points.SetPoint(i, new_coord)

    tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints - 1, new_coord)
    logging.info("Placed point at position: %s", new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)
    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)

    delaunay = vtk.vtkDelaunay3D()

    logging.debug("use glyphs")
    sphere = vtk.vtkCubeSource()
    glyph = vtk.vtkGlyph3D()
    glyph.SetInputData(pointPolyData)
    glyph.SetSourceConnection(sphere.GetOutputPort())
    delaunay.SetInputConnection(glyph.GetOutputPort())

    delaunay.Update()
    surfaceFilter = vtk.vtkDataSetSurfaceFilter()
    surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

    smoother = vtk.vtkButterflySubdivisionFilter()
    smoother.SetInputConnection(surfaceFilter.GetOutputPort())
    smoother.SetNumberOfSubdivisions(3)
    smoother.Update()

    delaunaySmooth = vtk.vtkDelaunay3D()
    delaunaySmooth.SetInputData(smoother.GetOutput())
    delaunaySmooth.Update()

    smoothSurfaceFilter = vtk.vtkDataSetSurfaceFilter()
    smoothSurfaceFilter.SetInputConnection(delaunaySmooth.GetOutputPort())

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(smoothSurfaceFilter.GetOutputPort())
    normals.SetFeatureAngle(100.0)

    normals.Update()
    parameterNode = self.getParameterNode()
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.SetAndObservePolyData(normals.GetOutput())

  def setMarkPoints(self, toggled):
    parameterNode = self.getParameterNode()
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      parameterNode.SetParameter(self.POINTS_STATUS, self.POINTS_ADDING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      parameterNode.SetParameter(self.POINTS_STATUS, self.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def setErasePoints(self, toggled):
    parameterNode = self.getParameterNode()
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      parameterNode.SetParameter(self.POINTS_STATUS, self.POINTS_ERASING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      parameterNode.SetParameter(self.POINTS_STATUS, self.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def modifyPoints(self, observer, eventID):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if parameterNode.GetParameter(self.POINTS_STATUS) == self.POINTS_ERASING:
      numberOfPoints = tumorMarkups_Needle.GetNumberOfControlPoints()
      mostRecentPoint = [0.0, 0.0, 0.0]
      tumorMarkups_Needle.GetNthControlPointPosition(numberOfPoints - 1, mostRecentPoint)
      closestPoint, closestPointPosition = self.returnClosestPoint(tumorMarkups_Needle, mostRecentPoint)
      tumorMarkups_Needle.RemoveNthControlPoint(closestPoint)
      tumorMarkups_Needle.RemoveNthControlPoint(tumorMarkups_Needle.GetNumberOfControlPoints() - 1)
      logging.info("Used eraser to remove point at %s", closestPointPosition)
      self.createTumorFromMarkups()

  def returnClosestPoint(self, fiducialNode, erasePoint):
    # Returns closest marked point to where eraser fiducial was placed
    closestIndex = 0
    distanceToClosest = np.inf
    fiducialPosition = [0.0, 0.0, 0.0]
    numberOfPoints = fiducialNode.GetNumberOfControlPoints()
    for fiducialIndex in range(numberOfPoints - 1):
      fiducialNode.GetNthControlPointPosition(fiducialIndex, fiducialPosition)
      distanceToPoint = self.calculateDistance(fiducialPosition, erasePoint)
      if distanceToPoint < distanceToClosest:
        closestIndex = fiducialIndex
        distanceToClosest = distanceToPoint
    fiducialNode.GetNthControlPointPosition(closestIndex, fiducialPosition)
    return closestIndex, fiducialPosition

  def setPlaceHydromark(self, toggled):
    parameterNode = self.getParameterNode()
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      hydromarkMarkup_Needle = parameterNode.GetNodeReference(self.HYDROMARK_MARKUP_NEEDLE)
      hydromarkMarkup_Needle.GetDisplayNode().VisibilityOn()
      selectionNode.SetActivePlaceNodeID(hydromarkMarkup_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    
  def deleteHydromarkMarkup(self):
    parameterNode = self.getParameterNode()
    hydromarkMarkup_Needle = parameterNode.GetNodeReference(self.HYDROMARK_MARKUP_NEEDLE)
    hydromarkMarkup_Needle.RemoveAllControlPoints()

    # Reset model
    tumorModelHydromark = parameterNode.GetNodeReference(self.TUMOR_MODEL_HYDROMARK)
    if tumorModelHydromark and (tumorPolyData := tumorModelHydromark.GetPolyData):
      tumorPolyData.Reset()

  def onHydromarkMarkupNodeModified(self, observer, eventid):
    self.createTumorFromHydromark()
    self.getParameterNode().Modified()
  
  def createTumorFromHydromark(self):
    parameterNode = self.getParameterNode()
    anteriorDistToMargin = parameterNode.GetParameter(self.ANTERIOR_DIST_TO_MARGIN)
    posteriorDistToMargin = parameterNode.GetParameter(self.POSTERIOR_DIST_TO_MARGIN)
    leftDistToMargin = parameterNode.GetParameter(self.LEFT_DIST_TO_MARGIN)
    rightDistToMargin = parameterNode.GetParameter(self.RIGHT_DIST_TO_MARGIN)
    superiorDistToMargin = parameterNode.GetParameter(self.SUPERIOR_DIST_TO_MARGIN)
    inferiorDistToMargin = parameterNode.GetParameter(self.INFERIOR_DIST_TO_MARGIN)
    hydromarkMarkup_Needle = parameterNode.GetNodeReference(self.HYDROMARK_MARKUP_NEEDLE)

    # Update HydromarkToNeedle using translation defined by control point
    if hydromarkMarkup_Needle.GetNumberOfControlPoints() == 1:
      hydromarkToNeedle = parameterNode.GetNodeReference(self.HYDROMARK_TO_NEEDLE)
      hydromarkPosition = hydromarkMarkup_Needle.GetNthControlPointPosition(0)
      hydromarkToNeedleTransform = vtk.vtkTransform()
      hydromarkToNeedleTransform.Translate(hydromarkPosition)
      hydromarkToNeedleMatrix = hydromarkToNeedleTransform.GetMatrix()
      hydromarkToNeedle.SetMatrixTransformToParent(hydromarkToNeedleMatrix)

      if (anteriorDistToMargin and posteriorDistToMargin and leftDistToMargin 
          and rightDistToMargin and superiorDistToMargin and inferiorDistToMargin):
        aToP = float(anteriorDistToMargin) + float(posteriorDistToMargin)
        lToR = float(leftDistToMargin) + float(rightDistToMargin)
        sToI = float(superiorDistToMargin) + float(inferiorDistToMargin)

        ellipsoid = vtk.vtkParametricEllipsoid()
        ellipsoid.SetXRadius(lToR / 2)
        ellipsoid.SetYRadius(aToP / 2)
        ellipsoid.SetZRadius(sToI / 2)

        funcSource = vtk.vtkParametricFunctionSource()
        funcSource.SetParametricFunction(ellipsoid)
        funcSource.SetUResolution(24)
        funcSource.SetVResolution(24)
        funcSource.SetWResolution(24)
        funcSource.Update()

        # First move tumor model to RAS to create ellipsoid
        tumorModelHydromark = parameterNode.GetNodeReference(self.TUMOR_MODEL_HYDROMARK)
        tumorModelHydromark.SetAndObserveTransformNodeID(None)
        tumorModelHydromark.SetAndObservePolyData(funcSource.GetOutput())

        # Compute rotation of needle coordinate system
        needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
        rasToNeedleMatrix = vtk.vtkMatrix4x4()
        needleToReference.GetMatrixTransformToWorld(rasToNeedleMatrix)
        rasToNeedleMatrix.Invert()
        rasToNeedleArr = slicer.util.arrayFromVTKMatrix(rasToNeedleMatrix)
        # Create 4x4 matrix from rotation 3x3 matrix
        rasToNeedleRotArr = np.vstack((np.hstack((rasToNeedleArr[:3, :3], np.array([0, 0, 0])[:, None])), [0, 0, 0, 1]))
        rasToNeedleRotMatrix = slicer.util.vtkMatrixFromArray(rasToNeedleRotArr)
        tumorModelHydromark.ApplyTransformMatrix(rasToNeedleRotMatrix)

        # Move tumor model to HydromarkToNeedle
        tumorModelHydromark.SetAndObserveTransformNodeID(hydromarkToNeedle.GetID())

        # Set visibility
        hydromarkVisible = slicer.util.settingsValue(self.HYDROMARK_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
        tumorModelHydromark.GetDisplayNode().SetVisibility2D(hydromarkVisible)
        tumorModelHydromark.GetDisplayNode().SetVisibility3D(hydromarkVisible)

  def setRASMarkups(self, observer, eventid):
    parameterNode = self.getParameterNode()
    tumorModel = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    if tumorModel is not None:
      centerOfMassFilter = vtk.vtkCenterOfMass()
      centerOfMassFilter.SetInputData(tumorModel.GetPolyData())
      centerOfMassFilter.SetUseScalarsAsWeights(False)
      centerOfMassFilter.Update()
      center = centerOfMassFilter.GetCenter()
      needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
      needleToRASMatrix = vtk.vtkMatrix4x4()
      needleToReference.GetMatrixTransformToWorld(needleToRASMatrix)
      centerWorld = needleToRASMatrix.MultiplyFloatPoint(np.append(center, 1))

      # Calculate how far from center to put markups
      bounds = [0, 0, 0, 0, 0, 0]
      tumorModel.GetBounds(bounds)
      boundDist = [(bounds[1] - bounds[0]), (bounds[3] - bounds[2]), (bounds[5] - bounds[4])]
      distanceFromCenter = max(boundDist) / 2

      # Update RAS markup points
      RASMarkups = parameterNode.GetNodeReference(self.RAS_MARKUPS)
      RASMarkups.RemoveAllControlPoints()
      RASMarkups.AddControlPointWorld(centerWorld[0] + distanceFromCenter, centerWorld[1], centerWorld[2], "R")
      RASMarkups.AddControlPointWorld(centerWorld[0], centerWorld[1] + distanceFromCenter, centerWorld[2], "A")
      RASMarkups.AddControlPointWorld(centerWorld[0], centerWorld[1], centerWorld[2] + distanceFromCenter, "S")
      RASMarkups.AddControlPointWorld(centerWorld[0] - distanceFromCenter, centerWorld[1], centerWorld[2], "L")
      RASMarkups.AddControlPointWorld(centerWorld[0], centerWorld[1] - distanceFromCenter, centerWorld[2], "P")
      RASMarkups.AddControlPointWorld(centerWorld[0], centerWorld[1], centerWorld[2] - distanceFromCenter, "I")

  def onBreachWarningNodeChanged(self, observer, eventid):
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    distance = breachWarningNode.GetClosestDistanceToModelFromToolTip()

    # Display breach warning text in corner of view
    for i in range(slicer.app.layoutManager().threeDViewCount):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      distanceText = distance if distance >= 0 else 0
      view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperLeft, f"{distanceText:.0f}mm")
      textProperty = view.cornerAnnotation().GetTextProperty()
      textProperty.SetColor(0, 0, 0.5)  # blue
      view.forceRender()
    
    if breachWarningNode.GetClosestDistanceToModelFromToolTip() < 0:
      for i in range(slicer.app.layoutManager().threeDViewCount):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "BREACH!")
        textProperty = view.cornerAnnotation().GetTextProperty()
        textProperty.SetColor(1, 0, 0)  # red
        view.forceRender()

      # Add breach event to event table
      if parameterNode.GetParameter(self.BREACH_STATUS) == "False":
        self.addEvent(description="Tumor margin breach")
        parameterNode.SetParameter(self.BREACH_STATUS, "True")

      # Get coordinate of cautery tip in needle coordinate system
      needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
      cauteryTipToNeedle = vtk.vtkMatrix4x4()
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      cauteryTipToCautery.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedle)
      cauteryTip_needleTip = cauteryTipToNeedle.MultiplyFloatPoint([0, 0, 0, 1])

      # Check if another fiducial already exists within threshold distance from cautery tip
      breachMarkupsProximityThreshold = slicer.util.settingsValue(self.BREACH_MARKUPS_PROXIMITY_THRESHOLD, 1, converter=lambda x: int(x))
      breachMarkups_Needle = parameterNode.GetNodeReference(self.BREACH_MARKUPS_NEEDLE)
      if not self.hasFiducialWithinDistance(breachMarkups_Needle, cauteryTip_needleTip[0:3], breachMarkupsProximityThreshold):
        breachMarkups_Needle.AddControlPoint(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2], "")
        logging.info(f"Added breach warning fiducial at position {cauteryTip_needleTip[0:3]}")

    else:
      # Remove corner annotation
      for i in range(slicer.app.layoutManager().threeDViewCount):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "")
        view.forceRender()
      parameterNode.SetParameter(self.BREACH_STATUS, "False")

  def hasFiducialWithinDistance(self, markupsNode, point, threshold):
    numberOfPoints = markupsNode.GetNumberOfControlPoints()
    for fiducialIndex in range(numberOfPoints):
      fiducialPosition = markupsNode.GetNthControlPointPosition(fiducialIndex)
      distance = self.calculateDistance(point, fiducialPosition)
      if distance <= threshold:
        return True
    else:
      return False

  def setBreachFiducialSize(self, value):
    parameterNode = self.getParameterNode()
    breachMarkups_Needle = parameterNode.GetNodeReference(self.BREACH_MARKUPS_NEEDLE)
    if breachMarkups_Needle is not None:
      breachMarkups_Needle.GetDisplayNode().SetGlyphScale(value)

  def setBreachWarningModel(self, modelNode):
    if modelNode == None:
      return
    modelColor = modelNode.GetDisplayNode().GetColor()
    parameterNode = self.getParameterNode()
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)
    breachWarningNode.SetAndObserveWatchedModelNodeID(modelNode.GetID())
    breachWarningNode.SetOriginalColor(modelColor)
    logging.info(f"Set breach warning watched model to {modelNode.GetName()}")

    # Update autocenter
    for i in range(slicer.app.layoutManager().threeDViewCount):
      viewNode = slicer.app.layoutManager().threeDWidget(i).mrmlViewNode()
      if not self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter():
        self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetModelNode(modelNode)

  def onImageImageModified(self, observer, eventid):
    self.updatePredictionImageDimensions()

  def updatePredictionImageDimensions(self):
    parameterNode = self.getParameterNode()
    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    imageDimensions = imageImage.GetImageData().GetDimensions()
    predictionImage = parameterNode.GetNodeReference(self.PREDICTION_VOLUME)
    predictionData = predictionImage.GetImageData()
    if predictionData.GetDimensions() != imageDimensions:
      predictionData.SetDimensions(imageDimensions)

  def setDisplayCauteryStateClicked(self, pressed):
    import CauteryClassification
    cauteryClassificationLogic = CauteryClassification.CauteryClassificationLogic()
    #cauteryClassificationLogic.init()
    cauteryClassificationLogic.setup()
    cauteryClassificationLogic.setUseModelClicked(pressed)

  def addEvent(self, description=None):
    parameterNode = self.getParameterNode()
    eventTableNode = parameterNode.GetNodeReference(self.EVENT_TABLE_NODE)
    lastRowIndex = eventTableNode.AddEmptyRow()
    sequenceBrowserNode = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)
    lastItem = sequenceBrowserNode.SelectLastItem()
    if lastItem == -1:
      sequenceIndex = ""
    else:
      sequenceIndex = sequenceBrowserNode.GetMasterSequenceNode().GetNthIndexValue(sequenceBrowserNode.SelectLastItem())
    
    eventTableNode.SetCellText(lastRowIndex, self.TIME_COLUMN, datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    eventTableNode.SetCellText(lastRowIndex, self.SEQUENCE_TIME_COLUMN, sequenceIndex)
    eventTableNode.SetCellText(lastRowIndex, self.EVENT_DESCRIPTION_COLUMN, description)

  def deleteEvent(self, row):
    parameterNode = self.getParameterNode()
    eventTableNode = parameterNode.GetNodeReference(self.EVENT_TABLE_NODE)
    eventTableNode.RemoveRow(row)

  @staticmethod
  def calculateDistance(point1, point2):
    tumorFiducialPoint = np.array(point1)
    eraserPoint = np.array(point2)
    distance = np.linalg.norm(tumorFiducialPoint - eraserPoint)
    return distance

  @staticmethod
  def createMatrixFromString(transformMatrixString):
    transformMatrix = vtk.vtkMatrix4x4()
    transformMatrixArray = list(map(float, transformMatrixString.split(' ')))
    for r in range(4):
      for c in range(4):
        transformMatrix.SetElement(r, c, transformMatrixArray[r*4+c])
    return transformMatrix


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


    self.delayDisplay('Test passed')

