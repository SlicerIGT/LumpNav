import os
import time

import numpy as np
import vtk, qt, ctk, slicer

import logging
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from vtk.util import numpy_support

import matplotlib.pyplot as plt

from sklearn import datasets
from sklearn import svm
from sklearn import metrics    			
from sklearn.model_selection import train_test_split
from sklearn.metrics import plot_roc_curve
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import roc_curve, auc
from mlxtend.plotting import plot_decision_regions
import pickle

#
# LumpNav2
#

#Finding where guidelet.py and ultrasound.py are stored:
#C:\Users\(_NAME_)\AppData\Roaming\NA-MIC\Extensions-28257\SlicerIGT\lib\Slicer-4.10\qt-scripted-modules\Guidelet\GuideletLib\Guidelet.py
#C:\Users\(_NAME_)\AppData\Roaming\NA-MIC\Extensions-28257\SlicerIGT\lib\Slicer-4.10\qt-scripted-modules\Guidelet\GuideletLib\UltraSound.py


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

  # Variables to store widget state

  PIVOT_CALIBRATION = 0
  SPIN_CALIBRATION = 1
  PIVOT_CALIBRATION_TIME_SEC = 5.0
  CAUTERY_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/CauteryCalibrationTresholdMm"
  CAUTERY_CALIBRATION_THRESHOLD_DEFAULT = 1.0
  NEEDLE_CALIBRATION_THRESHOLD_SETTING = "LumpNav2/NeedleCalibrationTresholdMm"
  NEEDLE_CALIBRATION_THRESHOLD_DEFAULT = 1.0


  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    slicer.mymodW = self #then in python interactor, call "self = slicer.mymod" to use
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    self._updatingGUIFromMRML = False
    self._updatingGui = False
    self.observedNeedleModel = None
    self.observedCauteryModel = None
    self.observedTrackingSeqBrNode = None
    self.observedUltrasoundSeqBrNode = None

    # Timer for pivot calibration controls

    self.pivotCalibrationLogic = slicer.modules.pivotcalibration.logic()
    self.pivotCalibrationStopTime = 0
    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION  # Default value, but it is always set when starting pivot calibration
    self.pivotCalibrationResultNode = None

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

    # Check settings and set default values if settings not found
    cauteryCalibrationThresholdMm = slicer.util.settingsValue(self.CAUTERY_CALIBRATION_THRESHOLD_SETTING, "")
    if cauteryCalibrationThresholdMm == "":
      settings = qt.QSettings()
      settings.setValue(self.CAUTERY_CALIBRATION_THRESHOLD_SETTING, str(self.CAUTERY_CALIBRATION_THRESHOLD_DEFAULT))
    needleCalibrationThresholdMm = slicer.util.settingsValue(self.NEEDLE_CALIBRATION_THRESHOLD_SETTING, "")
    if needleCalibrationThresholdMm == "":
      settings = qt.QSettings()
      settings.setValue(self.NEEDLE_CALIBRATION_THRESHOLD_SETTING, str(self.NEEDLE_CALIBRATION_THRESHOLD_DEFAULT))
    self.logic.setCauteryVisibilty(True)  # Begin with visible cautery, regardless of saved user settings

    # Set state of custom UI button
    self.setCustomStyle(not self.getSlicerInterfaceVisible())

    # Connections
    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # QT connections

    self.ui.customUiButton.connect('toggled(bool)', self.onCustomUiClicked)
    self.ui.startPlusButton.connect('toggled(bool)', self.onStartPlusClicked)
    self.ui.toolsCollapsibleButton.connect('contentsCollapsed(bool)', self.onToolsCollapsed)
    self.ui.contouringCollapsibleButton.connect('contentsCollapsed(bool)', self.onContouringCollapsed)
    self.ui.navigationCollapsibleButton.connect('contentsCollapsed(bool)', self.onNavigationCollapsed)
    self.ui.cauteryCalibrationButton.connect('clicked()', self.onCauteryCalibrationButton)
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

    self.ui.displayDistanceButton.connect('toggled(bool)', self.onDisplayDistanceClicked)
    self.ui.exitButton.connect('clicked()', self.onExitButtonClicked)
    self.ui.saveSceneButton.connect('clicked()', self.onSaveSceneClicked)

    #contouring
    self.ui.normalBrightnessButton.connect('clicked()', self.onNormalBrightnessClicked)
    self.ui.brightBrightnessButton.connect('clicked()', self.onBrightBrightnessClicked)
    self.ui.brightestBrightnessButton.connect('clicked()', self.onBrightestBrightnessClicked)
    self.ui.markPointsButton.connect('toggled(bool)', self.onMarkPointsToggled)
    self.ui.deleteLastFiducialButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.ui.deleteAllFiducialsButton.connect('clicked()', self.onDeleteAllFiducialsClicked)
    self.ui.selectPointsToEraseButton.connect('toggled(bool)', self.onErasePointsToggled)
    self.ui.markPointCauteryTipButton.connect('clicked()', self.onMarkPointCauteryTipClicked)
    self.ui.startStopRecordingButton.connect('toggled(bool)', self.onStartStopRecordingClicked)  
    self.ui.freezeUltrasoundButton.connect('toggled(bool)', self.onFreezeUltrasoundClicked)
    self.pivotSamplingTimer.connect('timeout()', self.onPivotSamplingTimeout)
    self.initializeParameterNode() # Make sure parameter node is initialized (needed for module reload)

    #navigation
    self.ui.leftBreastButton.connect('clicked()', self.onLeftBreastButtonClicked)
    self.ui.rightBreastButton.connect('clicked()', self.onRightBreastButtonClicked)
    #self.ui.bottomBullseyeCameraButton.connect('clicked()', lambda: self.onCameraButtonClicked('View3') )
    self.ui.leftAutoCenterCameraButton.connect('toggled(bool)', self.onLeftAutoCenterCameraButtonClicked)
    self.ui.rightAutoCenterCameraButton.connect('toggled(bool)', self.onRightAutoCenterCameraButtonClicked)
    self.ui.bottomAutoCenterCameraButton.connect('toggled(bool)', self.onBottomAutoCenterCameraButtonClicked)
    self.ui.increaseDistanceFontSizeButton.connect('clicked()', self.onIncreaseDistanceFontSizeClicked)
    self.ui.decreaseDistanceFontSizeButton.connect('clicked()', self.onDecreaseDistanceFontSizeClicked)
    self.ui.deleteLastFiducialNavigationButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.ui.toolModelButton.connect('toggled(bool)', self.onToolModelClicked)
    self.ui.threeDViewButton.connect('toggled(bool)', self.onThreeDViewButton)

    # Add custom layouts
    self.logic.addCustomLayouts()

    # Oscilloscope
    self.ui.displaySampleGraphButton.connect('clicked()', self.onDisplaySampleGraphButton)
    self.ui.streamGraphButton.connect('toggled(bool)', self.onStreamGraphButton)
    self.ui.collectOffButton.connect('toggled(bool)', self.onCollectOffToggled)
    self.ui.collectCutAirButton.connect('toggled(bool)', self.onCollectCutAirToggled)
    self.ui.collectCutTissueButton.connect('toggled(bool)', self.onCollectCutTissueToggled)
    self.ui.collectCoagAirButton.connect('toggled(bool)', self.onCollectCoagAirToggled)
    self.ui.collectCoagTissueButton.connect('toggled(bool)', self.onCollectCoagTissueToggled)
    self.ui.trainAndImplementModelButton.connect('clicked()', self.onTrainAndImplementModelClicked)
    self.ui.useBaseModelButton.connect('toggled(bool)', self.onUseBaseModelClicked)
    self.ui.resetModelButton.connect('clicked()', self.onResetModelClicked)

    import Viewpoint
    self.viewpointLogic = Viewpoint.ViewpointLogic()

  def onCauteryCalibrationButton(self):
    logging.info('onCauteryCalibrationButton')
    cauteryToNeedle = self._parameterNode.GetNodeReference(self.logic.CAUTERY_TO_NEEDLE)
    cauteryTipToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYTIP_TO_CAUTERY)
    self.startPivotCalibration(cauteryToNeedle, cauteryTipToCautery)

  def startPivotCalibration(self, toolToReferenceTransformNode, toolTipToToolTransformNode):
    self.pivotCalibrationMode = self.PIVOT_CALIBRATION
    self.ui.cauteryCalibrationButton.setEnabled(False)
    self.pivotCalibrationResultNode =  toolTipToToolTransformNode
    self.pivotCalibrationLogic.SetAndObserveTransformNode( toolToReferenceTransformNode );
    self.pivotCalibrationStopTime=time.time() + self.PIVOT_CALIBRATION_TIME_SEC
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()

  def onPivotSamplingTimeout(self):
    remainingTime = self.pivotCalibrationStopTime - time.time()
    self.ui.cauteryCalibrationLabel.setText("Calibrating for {0:.0f} more seconds".format(remainingTime))
    if time.time() < self.pivotCalibrationStopTime:
      self.pivotSamplingTimer.start()  # continue
    else:
      self.onStopPivotCalibration()  # calibration completed
  
  def onExitButtonClicked(self):
    mainwindow = slicer.util.mainWindow()
    mainwindow.close()

  def onSaveSceneClicked(self):#common
    #
    # save the mrml scene to a temp directory, then zip it
    #
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
    node = self.logic.getParameterNode()
    sceneSaveDirectory = node.GetParameter('SavedScenesDirectory')
    sceneSaveDirectory = sceneSaveDirectory + "/" + self.logic.moduleName + "-" + time.strftime("%Y%m%d-%H%M%S")
    logging.info("Saving scene to: {0}".format(sceneSaveDirectory))
    if not os.access(sceneSaveDirectory, os.F_OK):
      os.makedirs(sceneSaveDirectory)

    applicationLogic = slicer.app.applicationLogic()
    if applicationLogic.SaveSceneToSlicerDataBundleDirectory(sceneSaveDirectory, None):
      logging.info("Scene saved to: {0}".format(sceneSaveDirectory))
    else:
      logging.error("Scene saving failed")
    qt.QApplication.restoreOverrideCursor()
    slicer.util.showStatusMessage("Saved!", 2000)

  def onStopPivotCalibration(self):
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.ui.cauteryCalibrationButton.setEnabled(True)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      calibrationSuccess = self.pivotCalibrationLogic.ComputePivotCalibration()
    else:
      calibrationSuccess = self.pivotCalibrationLogic.ComputeSpinCalibration()

    #todo: check if this is cautery or needle calibration and use different thresholds
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
      self.ui.cauteryCalibrationLabel.setText("Success, RMSE = {:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))

    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultNode.SetMatrixTransformToParent(tooltipToToolMatrix)

    # Save calibration result so this calibration will be loaded in the next session automatically

    pivotCalibrationResultName = self.pivotCalibrationResultNode.GetName()
    pivotCalibrationFileWithPath = self.resourcePath(pivotCalibrationResultName + ".h5")
    slicer.util.saveNode(self.pivotCalibrationResultNode, pivotCalibrationFileWithPath)

    if self.pivotCalibrationMode == self.PIVOT_CALIBRATION:
      logging.info("Pivot calibration completed. Tool: {0}. RMSE = {1:.2f} mm".format(
        self.pivotCalibrationResultNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    else:
      logging.info("Spin calibration completed.")

  def confirmExit(self):
    msgBox = qt.QMessageBox()
    msgBox.setStyleSheet(slicer.util.mainWindow().styleSheet)
    msgBox.setWindowTitle("Confirm exit")
    msgBox.setText("Some data may not have been saved yet. Do you want to exit and discard the current scene?")
    #TODO: Save scene
    if self._parameterNode.GetMTime() > self.logic.saveTime.GetMTime()):
      self.onSaveSceneClicked()
    discardButton = msgBox.addButton("Exit", qt.QMessageBox.DestructiveRole)
    cancelButton = msgBox.addButton("Cancel", qt.QMessageBox.RejectRole)
    msgBox.setModal(True)
    msgBox.exec()

    if msgBox.clickedButton() == discardButton:
      return True
    else:
      return False

  def onNeedleVisibilityToggled(self, toggled):
    logging.info("onNeedleVisibilityToggled({})".format(toggled))
    self.logic.setNeedleVisibility(toggled)

  def onCauteryVisibilityToggled(self, toggled):
    logging.info("onCauteryVisibilityToggled({})".format(toggled))
    self.setCauteryVisibility(toggled)

  def setCauteryVisibility(self, visible):
    settings = qt.QSettings()
    settings.setValue(self.logic.CAUTERY_VISIBILITY_SETTING, visible)
    if self._parameterNode is not None:
      cauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
      if cauteryModel is not None:
        cauteryModel.SetDisplayVisibility(visible)

    self.updateGUIFromMRML()

  def onWarningSoundToggled(self, toggled):
    logging.info("onWarningSoundToggled({})".format(toggled))
    self.logic.setWarningSound(toggled)

  def getCauteryVisibility(self):
    return slicer.util.settingsValue(self.logic.CAUTERY_VISIBILITY_SETTING, False, converter=slicer.util.toBool)

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
      self.onThreeDViewButton(False)
      interactionNode = slicer.app.applicationLogic().GetInteractionNode()
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
      self.updateGUIFromParameterNode()

  def onThreeDViewButton(self, toggled):
    self.ui.threeDViewButton.checked = toggled
    if toggled:
      self.ui.threeDViewButton.text = "Dual 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_DUAL3D)
    else:
      self.ui.threeDViewButton.text = "Triple 3D View"
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_TRIPLE3D)

  def onStartStopRecordingClicked(self, toggled):
    if toggled:
      self.ui.startStopRecordingButton.text = "Stop Ultrasound Recording"
      self.logic.setUltrasoundSequenceBrowser(toggled)
    else:
      self.ui.startStopRecordingButton.text = "Start Ultrasound Recording"
      self.logic.setUltrasoundSequenceBrowser(toggled)

  def onFreezeUltrasoundClicked(self, toggled):
    logging.info("onFreezeUltrasoundClicked")
    plusServerNode = self._parameterNode.GetNodeReference(self.logic.PLUS_SERVER_NODE)
    if toggled:
      self.ui.freezeUltrasoundButton.text = "Un-Freeze"
      plusServerNode.StartServer()
    else:
      self.ui.freezeUltrasoundButton.text = "Freeze"
      plusServerNode.StopServer()
    #self.logic.setFreezeUltrasoundClicked()

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

  def onTrackingSequenceBrowser(self, toggled):
    logging.info("onTrackingSequenceBrowserToggled({})".format(toggled))
    self.logic.setTrackingSequenceBrowser(toggled)

  def onNormalBrightnessClicked(self):
    logging.info("onNormalBrightnessClicked")
    self.logic.setNormalBrightnessClicked()
    if toggled:
      self.logic.setRegionOfInterestNode()

  def onBrightBrightnessClicked(self):
    logging.info("onBrightBrightnessClicked")
    self.logic.setBrightBrightnessClicked()

  def onBrightestBrightnessClicked(self):
    logging.info("onBrightestBrightnessClicked")
    self.logic.setBrightestBrightnessClicked()

  def onErasePointsToggled(self, toggled):
    logging.info("onErasePointsToggled")
    if self._updatingGui == True:
      return
    self._updatingGui = True
    if self.ui.markPointsButton.isChecked() : # ensures point placed doesn't get logged twice
      self.ui.markPointsButton.click()
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ADDING)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_ERASING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    self._updatingGui = False

    '''
    # if self._updatingGui == True:
    #   return
    # self._updatingGui = True
    # if toggled:
    #   self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ERASING)
    #   self.ui.markPointsButton.setChecked(False)
    # else:
    #   self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
    # self._updatingGui = False
    # TODO: add this to function call from widget
    if self._updatingGui == True:
      return
    self._updatingGui = True
    parameterNode = self.getParmeterNode()
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if changePoints:
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ADDING)
      parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_ERASING)
    else:  # deactivate placement mode
      parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    # TODO: add those after modifyPoints function call line in widget class
    self._updatingGui = False
    '''

  def onMarkPointsToggled(self, toggled):
    if self._updatingGui == True:
      return
    self._updatingGui = True
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if toggled:  # activate placement mode
      self.ui.selectPointsToEraseButton.setChecked(False)
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_ADDING)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_ADDING)
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:  # deactivate placement mode
      self._parameterNode.SetParameter(self.logic.CONTOUR_STATUS, self.logic.CONTOUR_UNSELECTED)
      self._parameterNode.SetParameter(self.logic.POINTS_STATUS, self.logic.POINTS_UNSELECTED)
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
    self._updatingGui = False
  
  def onMarkPointCauteryTipClicked(self):
    logging.info("Mark point at cautery tip clicked")
    self.logic.setMarkPointCauteryTipClicked()
  
  def onDeleteLastFiducialClicked(self):
    logging.debug('onDeleteLastFiducialClicked')
    if self.ui.markPointsButton.isChecked() : # ensures point placed doesn't get logged twice
      self.ui.markPointsButton.click()
    self.updateGUIFromParameterNode()
    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()
    self.logic.setDeleteLastFiducialClicked(numberOfPoints)

  def onDeleteAllFiducialsClicked(self):
    logging.debug('onDeleteAllFiducialsClicked')
    self.logic.setDeleteAllFiducialsClicked()
    self.updateGUIFromParameterNode()

  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    logging.debug("getViewNode")
    viewNode = slicer.util.getFirstNodeByName(viewName)
    return viewNode

  def onLeftBreastButtonClicked(self):
    logging.debug("onLeftButtonClicked")
    self.ui.rightBreastButton.setEnabled(True)
    self.ui.rightBreastButton.setChecked(False)
    self.ui.leftBreastButton.setEnabled(False)
    # check if autocenter buttons are already clicked before activating autocenter
    if not self.ui.leftAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View1')
    if not self.ui.rightAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View2')
    if not self.ui.bottomAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View3')
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    #TODO: Don't use magic numbers
    cameraNode1.SetPosition(-242.0042709749552, 331.2026122150233, -36.6617924419265)
    cameraNode1.SetViewUp(0.802637869051714, 0.5959392355990031, -0.025077452777348814)
    cameraNode1.SetFocalPoint(0.0,0.0,0.0)
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0, 0.0, 0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode2.ResetClippingRange()
    cameraNode1.ResetClippingRange()

  def onRightBreastButtonClicked(self):
    logging.debug("onRightButtonClicked")
    self.ui.rightBreastButton.setEnabled(False)
    self.ui.leftBreastButton.setEnabled(True)
    self.ui.leftBreastButton.setChecked(False)
    if not self.ui.leftAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View1')
    if not self.ui.rightAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View2')
    if not self.ui.bottomAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View3')
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
    cameraNode1.SetPosition(275.4944476449362, 309.31555951664205, 42.169967768629164)
    cameraNode1.SetViewUp(-0.749449157051234, 0.661802245162601, -0.018540477149624528)
    cameraNode1.SetFocalPoint(0.0,0.0,0.0)
    cameraNode2.SetPosition(0.0, 500.0, 0.0)
    cameraNode2.SetViewUp(-1.0, 0.0, 0.0)
    cameraNode2.SetFocalPoint(0.0,0.0,0.0)
    cameraNode1.SetViewAngle(25.0)
    cameraNode2.SetViewAngle(25.0)
    cameraNode3.SetViewAngle(20.0)
    cameraNode2.ResetClippingRange()
    cameraNode1.ResetClippingRange()

  def onDisplayDistanceClicked(self, toggled):
    logging.info("onDisplayDistanceClicked({})".format(toggled))
    if toggled:
      for i in range(0,3):
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        parameterNode = self._parameterNode
        breachWarningNode = parameterNode.GetNodeReference(self.logic.BREACH_WARNING)
        view.setCornerAnnotationText("{0:.2f}mm".format(breachWarningNode.GetClosestDistanceToModelFromToolTip()))
        view.forceRender()
    else:
        for i in range (0,3) : # Clear all text
          view = slicer.app.layoutManager().threeDWidget(i).threeDView()
          view.cornerAnnotation().ClearAllTexts()
          view.forceRender()
        return

  #TODO: Increase font size
  def onIncreaseDistanceFontSizeClicked(self):
    logging.debug("onIncreaseDistanceFontSizeClicked")
    for i in range(0,3):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      fontSize = view.cornerAnnotation().GetMaximumFontSize() + 1
      view.cornerAnnotation().SetMaximumFontSize(fontSize)
      view.forceRender()

  def onDecreaseDistanceFontSizeClicked(self):
    logging.debug("onDecreaseDistanceFontSizeClicked")
    for i in range(0,3):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      fontSize = view.cornerAnnotation().GetMaximumFontSize() - 1
      view.cornerAnnotation().SetMaximumFontSize(fontSize)
      view.forceRender()
  
  def onToolModelClicked(self, toggled):
    logging.info('onToolModelClicked')
    if toggled:
      self.ui.toolModelButton.text = "Cautery Model"
    else:
      self.ui.toolModelButton.text = "Stick Model"
    self.logic.setToolModelClicked(toggled)

  def onDisplaySampleGraphButton(self):
    logging.info('onDisplaySampleGraphButton')
    self.logic.setDisplaySampleGraphButton()

  def onStreamGraphButton(self, toggled):
    logging.info('onStreamGraphButton')
    self.logic.setStreamGraphButton(toggled)

  def enableBullseyeInViewNode(self, viewNode):
    logging.debug("enableBullseyeInViewNode")
    if self._parameterNode is None:
      return
    self.disableViewpointInViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    cauteryCameraToCautery = self._parameterNode.GetNodeReference(self.logic.CAUTERYCAMERA_TO_CAUTERY)
    self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetTransformNode(cauteryCameraToCautery)
    self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStart()
    self.updateGUISliders(viewNode)

  def disableBullseyeInViewNode(self, viewNode):
    logging.debug("disableBullseyeInViewNode")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye()):
      self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeStop()
      self.updateGUISliders(viewNode)

  def disableBullseyeInAllViewNodes(self):
    logging.debug("disableBullseyeInAllViewNodes")
    leftViewNode = self.getViewNode('View1')
    self.disableBullseyeInViewNode(leftViewNode)
    rightViewNode = self.getViewNode('View2')
    self.disableBullseyeInViewNode(rightViewNode)
    bottomViewNode = self.getViewNode('View3')
    self.disableBullseyeInViewNode(bottomViewNode)

  def onLeftAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onLeftAutoCenterButtonClicked")
    self.ui.rightAutoCenterCameraButton.setChecked(False)
    self.ui.bottomAutoCenterCameraButton.setChecked(False)
    self.onAutoCenterButtonClicked('View1')

  def onRightAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onRightAutoCenterCameraButtomClicked")
    self.ui.leftAutoCenterCameraButton.setChecked(False)
    self.ui.bottomAutoCenterCameraButton.setChecked(False)
    self.onAutoCenterButtonClicked('View2')

  def onBottomAutoCenterCameraButtonClicked(self, pushed):
    logging.info("onBottomAutoCenterCameraButtonClicked")
    self.ui.rightAutoCenterCameraButton.setChecked(False)
    self.ui.leftAutoCenterCameraButton.setChecked(False)
    self.onAutoCenterButtonClicked('View3')

  def onAutoCenterButtonClicked(self,viewName):
    viewNode = self.getViewNode(viewName)
    logging.debug("onAutoCenterButtonClicked")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter()):
      self.disableAutoCenterInViewNode(viewNode)
    else:
      self.enableAutoCenterInViewNode(viewNode)
      logging.info("Auto center for %s enabled", viewName)
    self.updateGUIButtons()

  def disableAutoCenterInViewNode(self, viewNode):
    logging.debug("disableAutoCenterInViewNode")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeAutoCenter()):
      self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStop()
      logging.info("Auto center for %s disabled", viewNode.GetName())

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

  def onUseBaseModelClicked(self, toggled):
    logging.info('onUseBaseModelClicked')
    self.logic.setUseBaseModelClicked(toggled)

    return
  def onResetModelClicked(self):
    logging.info('onResetModelClicked')
    return

  def enableAutoCenterInViewNode(self, viewNode):
    logging.debug("enableAutoCenterInViewNode")
    self.disableViewpointInViewNode(viewNode)
    heightViewCoordLimits = 0.6
    widthViewCoordLimits = 0.9
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMinimum(-widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMaximum(widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMinimum(-heightViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMaximum(heightViewCoordLimits)
    # self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetModelNode(self.logic.tumorModel_Needle)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStart()

  def disableViewpointInViewNode(self,viewNode):
    logging.debug("disableViewpointInViewNode")
    self.disableBullseyeInViewNode(viewNode)
    self.disableAutoCenterInViewNode(viewNode)

  def updateGUIButtons(self):
    logging.debug("updateGUIButtons")

    leftViewNode = self.getViewNode('View1')

    blockSignalState = self.ui.leftAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(leftViewNode).isCurrentModeAutoCenter()):
      self.ui.leftAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.leftAutoCenterCameraButton.setChecked(False)
    self.ui.leftAutoCenterCameraButton.blockSignals(blockSignalState)

    rightViewNode = self.getViewNode('View2')

    blockSignalState = self.ui.rightAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(rightViewNode).isCurrentModeAutoCenter()):
      self.ui.rightAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.rightAutoCenterCameraButton.setChecked(False)
    self.ui.rightAutoCenterCameraButton.blockSignals(blockSignalState)

    centerViewNode = self.getViewNode('View3')

    blockSignalState = self.ui.bottomAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(centerViewNode).isCurrentModeAutoCenter()):
      self.ui.bottomAutoCenterCameraButton.setChecked(True)
    else:
      self.ui.bottomAutoCenterCameraButton.setChecked(False)
    self.ui.bottomAutoCenterCameraButton.blockSignals(blockSignalState)

    #blockSignalState = self.ui.bottomBullseyeCameraButton.blockSignals(True)
    #if (self.viewpointLogic.getViewpointForViewNode(centerViewNode).isCurrentModeBullseye()):
    #  self.ui.bottomBullseyeCameraButton.setChecked(True)
    #else:
    #  self.ui.bottomBullseyeCameraButton.setChecked(False)
    #self.ui.bottomBullseyeCameraButton.blockSignals(blockSignalState)

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

    # Choose layout based on which collapsible button is open

    if self.ui.toolsCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(self.logic.LAYOUT_2D3D)

    if self.ui.contouringCollapsibleButton.checked:
      slicer.app.layoutManager().setLayout(6)

    if self.ui.navigationCollapsibleButton.checked:
      self.onThreeDViewButton(self.ui.threeDViewButton.checked)

    self.updateGUIFromParameterNode()
    self.updateGUIFromMRML()
  
  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    logging.debug("getCamera")
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(slicer.util.getFirstNodeByName(viewName))
    return camera
  
  def onCameraButtonClicked(self, viewName):
    viewNode = self.getViewNode(viewName)
    logging.debug("onCameraButtonClicked")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye()):
      self.disableBullseyeInViewNode(viewNode)
      self.enableAutoCenterInViewNode(viewNode)
    else:
      self.disableViewpointInViewNode(viewNode) # disable any other modes that might be active
      self.enableBullseyeInViewNode(viewNode)
    self.updateGUIButtons()
  
  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    self.observedCauteryModel = None

    self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
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
    # ...

    # If new MRML nodes are referenced, update observers

    currentNeedleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if currentNeedleModel != self.observedNeedleModel:
      self.removeObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedNeedleModel = currentNeedleModel
      if self.observedNeedleModel:
        self.addObserver(self.observedNeedleModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
    
    currentCauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    if currentCauteryModel != self.observedCauteryModel:
      self.removeObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)
      self.observedCauteryModel = currentCauteryModel
      if self.observedCauteryModel:
        self.addObserver(self.observedCauteryModel, slicer.vtkMRMLDisplayableNode.DisplayModifiedEvent, self.updateGUIFromMRML)

    currentTrackingSeqBrNode = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if currentTrackingSeqBrNode != self.observedTrackingSeqBrNode:
      self.removeObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedTrackingSeqBrNode = currentTrackingSeqBrNode
      if self.observedTrackingSeqBrNode is not None:
        self.addObserver(self.observedTrackingSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    currentUltrasoundSeqBrNode = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if currentUltrasoundSeqBrNode != self.observedUltrasoundSeqBrNode:
      self.removeObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)
      self.observedUltrasoundSeqBrNode = currentUltrasoundSeqBrNode
      if self.observedUltrasoundSeqBrNode is not None:
        self.addObserver(self.observedUltrasoundSeqBrNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromMRML)

    # All the GUI updates are done

    self._updatingGUIFromParameterNode = False

    tumorMarkups_Needle = self._parameterNode.GetNodeReference(self.logic.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()
    if numberOfPoints>=1:
      self.ui.deleteLastFiducialButton.setEnabled(True)
      self.ui.deleteAllFiducialsButton.setEnabled(True)
      self.ui.deleteLastFiducialNavigationButton.setEnabled(True)
      self.ui.selectPointsToEraseButton.setEnabled(True)

    if numberOfPoints<1:

      self.ui.deleteLastFiducialButton.setEnabled(False)
      self.ui.deleteAllFiducialsButton.setEnabled(False)
      self.ui.deleteLastFiducialNavigationButton.setEnabled(False)
      self.ui.selectPointsToEraseButton.setChecked(False)
      self.ui.selectPointsToEraseButton.setEnabled(False)
    
    # interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    # if interactionNode.GetInteractionModeAsString() == "Place" and self.ui.selectPointsToEraseButton.isChecked() == False:
    #   self.ui.markPointsButton.setChecked(True)
    # else:
    #   self.ui.markPointsButton.setChecked(False)

  def updateGUIFromMRML(self, caller=None, event=None):
    """
    Updates the GUI from MRML nodes in the scene (except parameter node).
    """
    if self._updatingGUIFromMRML:
      return

    if self._parameterNode is None:
      return

    self._updatingGUIFromMRML = True

    needleModel = self._parameterNode.GetNodeReference(self.logic.NEEDLE_MODEL)
    if needleModel is not None:
      if needleModel.GetDisplayVisibility():
        self.ui.needleVisibilityButton.checked = True
        self.ui.needleVisibilityButton.text = "Hide needle model"
      else:
        self.ui.needleVisibilityButton.checked = False
        self.ui.needleVisibilityButton.text = "Show needle model"

    cauteryModel = self._parameterNode.GetNodeReference(self.logic.CAUTERY_MODEL)
    if cauteryModel is not None:
      if cauteryModel.GetDisplayVisibility():
        self.ui.cauteryVisibilityButton.checked = True
        self.ui.cauteryVisibilityButton.text = "Hide cautery model"
      else:
        self.ui.cauteryVisibilityButton.checked = False
        self.ui.cauteryVisibilityButton.text = "Show cautery model"

    trackingSqBr = self._parameterNode.GetNodeReference(self.logic.TRACKING_SEQUENCE_BROWSER)
    if trackingSqBr is not None:
      self.ui.trackingSequenceBrowserButton.checked = trackingSqBr.GetRecordingActive()

    ultrasoundSqBr = self._parameterNode.GetNodeReference(self.logic.ULTRASOUND_SEQUENCE_BROWSER)
    if ultrasoundSqBr is not None:
      self.ui.startStopRecordingButton.checked = ultrasoundSqBr.GetRecordingActive()

    self._updatingGUIFromMRML = False

  def updateGUISliders(self, viewNode):
    logging.debug("updateGUISliders")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye()):
      self.ui.fieldOfViewSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.ui.cameraXPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.ui.cameraYPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.ui.cameraZPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.ui.fieldOfViewSlider.setDisabled(False)
      self.ui.cameraXPosSlider.setDisabled(False)
      self.ui.cameraZPosSlider.setDisabled(False)
      self.ui.cameraYPosSlider.setDisabled(False)
    else:
      self.ui.fieldOfViewSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.ui.cameraXPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.ui.cameraYPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.ui.cameraZPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.ui.fieldOfViewSlider.setDisabled(True)
      self.ui.cameraXPosSlider.setDisabled(True)
      self.ui.cameraZPosSlider.setDisabled(True)
      self.ui.cameraYPosSlider.setDisabled(True)

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
  TRANSD_TO_REFERENCE = "TransdToReference"
  IMAGE_TO_TRANSD = "ImageToTransd"
  CAUTERYCAMERA_TO_CAUTERY = "CauteryCameraToCautery"
  TRANSD_TO_NEEDLE = "TransdToNeedle"


  # Ultrasound image

  IMAGE_IMAGE = "Image_Image"
  DEFAULT_US_DEPTH = 90

  # OpenIGTLink PLUS connection

  CONFIG_FILE_SETTING = "LumpNav2/PlusConfigFile"
  CONFIG_FILE_DEFAULT = "LumpNavDefault.xml"  # Default config file if the user doesn't set another.
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"
  PLUS_REMOTE_NODE = "PlusRemoteNode"

  # Model names and settings

  NEEDLE_MODEL = "NeedleModel"
  NEEDLE_VISIBILITY_SETTING = "LumpNav2/NeedleVisible"
  CAUTERY_MODEL = "CauteryModel"
  CAUTERY_VISIBILITY_SETTING = "LumpNav2/CauteryVisible"
  CAUTERY_MODEL_FILENAME = "CauteryModel.stl"
  TUMOR_MODEL = "TumorModel"
  STICK_MODEL = "StickModel"
  WARNING_SOUND_SETTING = "LumpNav2/WarningSoundEnabled"

  # Model reconstruction
  ROI_NODE = "ROI"

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

    # Telemed C5 probe geometry

    self.scaling_Intercept = 0.01663333
    self.scaling_Slope = 0.00192667

    #self.tumorMarkups_Needle = None
    self.tumorMarkupAddedObserverTag = None

    self.eraseMarkups_Needle = None
    self.eraseMarkupsAddedObserverTag = None
    self.eraseMarkupEndInteractionObserverTag = None

    self.eraserFlag = True  # Indicates if we are removing points

    self.hideDistance = False

    self.saveTime = vtk.vtkTimeStamp()

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

    parameterNode = self.getParameterNode()
    parameterNode.SetAttribute("TipToSurfaceDistanceTextScale", "3")

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
    """
    Changes the visibility of the needle model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    parameterNode = self.getParameterNode()
    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is not None:
      needleModel.SetDisplayVisibility(visible)
      settings = qt.QSettings()
      settings.setValue(self.NEEDLE_VISIBILITY_SETTING, "True" if visible else "False")

  def setWarningSound(self, enabled):
    if self.breachWarningNode is not None:
      self.breachWarningNode.SetPlayWarningSound(enabled)
      settings = qt.QSettings()
      settings.setValue(self.WARNING_SOUND_SETTING, enabled)

  def setCauteryVisibilty(self, visible):
    """
    Changes the visibility of the cautery model, and saves it as a setting
    :param bool visible: True to show model
    :returns: None
    """
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    if cauteryModel is not None:
      cauteryModel.SetDisplayVisibility(visible)
    else:
      logging.warning("setCauteryVisibilty() called but no cautery model found")

  def setup(self):
    """
    Sets up the Slicer scene. Creates nodes if they are missing.
    """
    parameterNode = self.getParameterNode()

    self.setupTransformHierarchy()

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

    # Create models

    createModelsLogic = slicer.modules.createmodels.logic()

    # Needle model

    needleModel = parameterNode.GetNodeReference(self.NEEDLE_MODEL)
    if needleModel is None:
      needleModel = createModelsLogic.CreateNeedle(60.0, 1.0, 2.0, 0)
      needleModel.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
      needleModel.SetName(self.NEEDLE_MODEL)
      needleModel.GetDisplayNode().SliceIntersectionVisibilityOn()
      parameterNode.SetNodeReferenceID(self.NEEDLE_MODEL, needleModel.GetID())

    needleVisible = slicer.util.settingsValue(self.NEEDLE_VISIBILITY_SETTING, True, converter=slicer.util.toBool)
    needleModel.SetDisplayVisibility(needleVisible)

    needleTipToNeedle = parameterNode.GetNodeReference(self.NEEDLETIP_TO_NEEDLE)
    needleModel.SetAndObserveTransformNodeID(needleTipToNeedle.GetID())

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
      stickModel = createModelsLogic.CreateNeedle(100,1.0,2.0,0)
      stickModel.GetDisplayNode().SetColor(1.0, 1.0, 0)
      stickModel.SetName(self.STICK_MODEL)
      stickModel.GetDisplayNode().VisibilityOff() #defaul is only cautery model, turn stick model off visibility
      parameterNode.SetNodeReferenceID(self.STICK_MODEL, stickModel.GetID())
    
    stickTipToStick = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    stickModel.SetAndObserveTransformNodeID(stickTipToStick.GetID())

    # Create tumor model

    #tumorModel = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL)
    #parameterNode.SetNodeReferenceID(self.TUMOR_MODEL, tumorModel.GetID())

    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    if tumorModel_Needle is None:
      tumorModel_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", self.TUMOR_MODEL)
      tumorModel_Needle.CreateDefaultDisplayNodes()
      modelDisplayNode = tumorModel_Needle.GetDisplayNode()
      modelDisplayNode.SetColor(0,1,0) # Green
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      parameterNode.SetNodeReferenceID(self.TUMOR_MODEL, tumorModel_Needle.GetID())

    needleToReference = parameterNode.GetNodeReference(self.NEEDLE_TO_REFERENCE)
    tumorModel_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())

    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if tumorMarkups_Needle is None:
      tumorMarkups_Needle = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", self.TUMOR_MARKUPS_NEEDLE)
      tumorMarkups_Needle.CreateDefaultDisplayNodes()
      tumorMarkups_Needle.GetDisplayNode().SetTextScale(0)
      tumorMarkups_Needle.LockedOn()
    tumorMarkups_Needle.SetAndObserveTransformNodeID(needleToReference.GetID())
    self.removeObservers(method=self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.modifyPoints)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointRemovedEvent, self.onTumorMarkupsNodeModified)
    self.addObserver(tumorMarkups_Needle, slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent, self.onTumorMarkupsNodeModified)

    parameterNode.SetNodeReferenceID(self.TUMOR_MARKUPS_NEEDLE, tumorMarkups_Needle.GetID())

    # OpenIGTLink connection

    self.setupPlusServer()

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
    sequenceBrowserTracking.SetRecordingActive(True) # Actually start recording

    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)
    if sequenceBrowserUltrasound is None:
      sequenceBrowserUltrasound = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.ULTRASOUND_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.ULTRASOUND_SEQUENCE_BROWSER, sequenceBrowserUltrasound.GetID())
    image_Image = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, image_Image, sequenceBrowserUltrasound)
    sequenceBrowserUltrasound.SetRecording(sequenceNode, True)
    sequenceBrowserUltrasound.SetPlayback(sequenceNode, True)
    sequenceBrowserUltrasound.SetRecordingActive(False)


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
      sequenceBrowserScopeCollectOff = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.COLLECT_OFF_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_OFF_SEQUENCE_BROWSER, sequenceBrowserScopeCollectOff.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectOff)
    sequenceBrowserScopeCollectOff.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectOff.SetRecordingActive(False)
    #TODO: why do we include sequenceNode as parameters in these lines?

    sequenceBrowserScopeCollectCutAir = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCutAir is None:
      sequenceBrowserScopeCollectCutAir = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER, sequenceBrowserScopeCollectCutAir.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCutAir)
    sequenceBrowserScopeCollectCutAir.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCutAir.SetRecordingActive(False)

    sequenceBrowserScopeCollectCutTissue = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCutTissue is None:
      sequenceBrowserScopeCollectCutTissue = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER, sequenceBrowserScopeCollectCutTissue.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCutTissue)
    sequenceBrowserScopeCollectCutTissue.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCutTissue.SetRecordingActive(False)

    sequenceBrowserScopeCollectCoagAir = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCoagAir is None:
      sequenceBrowserScopeCollectCoagAir = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER, sequenceBrowserScopeCollectCoagAir.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCoagAir)
    sequenceBrowserScopeCollectCoagAir.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCoagAir.SetRecordingActive(False)

    sequenceBrowserScopeCollectCoagTissue = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    if sequenceBrowserScopeCollectCoagTissue is None:
      sequenceBrowserScopeCollectCoagTissue = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
      parameterNode.SetNodeReferenceID(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER, sequenceBrowserScopeCollectCoagTissue.GetID())
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, signal_Signal, sequenceBrowserScopeCollectCoagTissue)
    sequenceBrowserScopeCollectCoagTissue.SetRecording(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetPlayback(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetSaveChanges(sequenceNode, True)
    sequenceBrowserScopeCollectCoagTissue.SetRecordingActive(False)

    # Set up breach warning node
    breachWarningNode = parameterNode.GetNodeReference(self.BREACH_WARNING)

    if breachWarningNode is None:
      breachWarningNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLBreachWarningNode', self.BREACH_WARNING)
      breachWarningNode.UnRegister(None) # Python variable already holds a reference to it
      breachWarningNode.SetWarningColor(1,0,0) 
      warningSoundEnabled = slicer.util.settingsValue(self.WARNING_SOUND_SETTING, True, converter=slicer.util.toBool)
      self.setWarningSound(warningSoundEnabled)

      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      breachWarningNode.SetOriginalColor(tumorModel_Needle.GetDisplayNode().GetColor())
      cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
      breachWarningNode.SetAndObserveToolTransformNodeId(cauteryTipToCautery.GetID())
      breachWarningNode.SetAndObserveWatchedModelNodeID(tumorModel_Needle.GetID())
      breachWarningNodeObserver = breachWarningNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onBreachWarningNodeChanged)
      breachWarningLogic = slicer.modules.breachwarning.logic()
      # Line properties can only be set after the line is creaed (made visible at least once)
      breachWarningLogic.SetLineToClosestPointVisibility(False, breachWarningNode)
      parameterNode.SetNodeReferenceID(self.BREACH_WARNING, breachWarningNode.GetID())

    cauteryCameraToCautery =  parameterNode.GetNodeReference(self.CAUTERYCAMERA_TO_CAUTERY)
    if cauteryCameraToCautery is None:
      try:
        cauteryCameraToCauteryFileWithPath = self.resourcePath(self.CAUTERYCAMERA_TO_CAUTERY + ".h5")
        logging.info("Loading cautery camera to cautery calibration from file: {}".format(cauteryCameraToCauteryFileWithPath))
        cauteryTipToCautery = slicer.util.loadTransform(cauteryTipToCauteryFileWithPath)
      except:
        logging.info("Creating cautery camera to cautery calibration file, because none was found as: {}".format(cauteryCameraToCauteryFileWithPath))
        cauteryCameraToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYCAMERA_TO_CAUTERY)
        m = self.createMatrixFromString('0 0 -1 0 1 0 0 0 0 -1 0 0 0 0 0 1')
        cauteryCameraToCautery.SetMatrixTransformToParent(m)
      parameterNode.SetNodeReferenceID(self.CAUTERYCAMERA_TO_CAUTERY, cauteryCameraToCautery.GetID())
    cauteryCameraToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

    self.usFrozen = False

    scopeOffVolumeA = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_A)
    if scopeOffVolumeA is None:
      scopeOffVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_OFF_VOLUME_A)
      scopeOffVolumeA.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeOffVolumeA.SetSpacing([1, 1, 1])
      scopeOffVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeOffVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_OFF_VOLUME_A, scopeOffVolumeA.GetID())

    scopeCutAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_A)
    if scopeCutAirVolumeA is None:
      scopeCutAirVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_AIR_VOLUME_A)
      scopeCutAirVolumeA.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutAirVolumeA.SetSpacing([1, 1, 1])
      scopeCutAirVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutAirVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_AIR_VOLUME_A, scopeCutAirVolumeA.GetID())

    scopeCutTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_A)
    if scopeCutTissueVolumeA is None:
      scopeCutTissueVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_TISSUE_VOLUME_A)
      scopeCutTissueVolumeA.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutTissueVolumeA.SetSpacing([1, 1, 1])
      scopeCutTissueVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutTissueVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_TISSUE_VOLUME_A, scopeCutTissueVolumeA.GetID())

    scopeCoagTissueVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_A)
    if scopeCoagTissueVolumeA is None:
      scopeCoagTissueVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_COAG_AIR_VOLUME_A)
      scopeCoagTissueVolumeA.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagTissueVolumeA.SetSpacing([1, 1, 1])
      scopeCoagTissueVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagTissueVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_AIR_VOLUME_A, scopeCoagTissueVolumeA.GetID())

    scopeCoagAirVolumeA = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_A)
    if scopeCoagAirVolumeA is None:
      scopeCoagAirVolumeA = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_COAG_TISSUE_VOLUME_A)
      scopeCoagAirVolumeA.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagAirVolumeA.SetSpacing([1, 1, 1])
      scopeCoagAirVolumeA.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagAirVolumeA.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_TISSUE_VOLUME_A, scopeCoagAirVolumeA.GetID())

    scopeOffVolumeB = parameterNode.GetNodeReference(self.SCOPE_OFF_VOLUME_B)
    if scopeOffVolumeB is None:
      scopeOffVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_OFF_VOLUME_B)
      scopeOffVolumeB.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeOffVolumeB.SetSpacing([1, 1, 1])
      scopeOffVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeOffVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_OFF_VOLUME_B, scopeOffVolumeB.GetID())

    scopeCutAirVolume_B = parameterNode.GetNodeReference(self.SCOPE_CUT_AIR_VOLUME_B)
    if scopeCutAirVolume_B is None:
      scopeCutAirVolume_B = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_AIR_VOLUME_B)
      scopeCutAirVolume_B.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutAirVolume_B.SetSpacing([1, 1, 1])
      scopeCutAirVolume_B.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutAirVolume_B.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_AIR_VOLUME_B, scopeCutAirVolume_B.GetID())

    scopeCutTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_CUT_TISSUE_VOLUME_B)
    if scopeCutTissueVolumeB is None:
      scopeCutTissueVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_CUT_TISSUE_VOLUME_B)
      scopeCutTissueVolumeB.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCutTissueVolumeB.SetSpacing([1, 1, 1])
      scopeCutTissueVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCutTissueVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_CUT_TISSUE_VOLUME_B, scopeCutTissueVolumeB.GetID())

    scopeCoagTissueVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_AIR_VOLUME_B)
    if scopeCoagTissueVolumeB is None:
      scopeCoagTissueVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_COAG_AIR_VOLUME_B)
      scopeCoagTissueVolumeB.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagTissueVolumeB.SetSpacing([1, 1, 1])
      scopeCoagTissueVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagTissueVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_AIR_VOLUME_B, scopeCoagTissueVolumeB.GetID())

    scopeCoagAirVolumeB = parameterNode.GetNodeReference(self.SCOPE_COAG_TISSUE_VOLUME_B)
    if scopeCoagAirVolumeB is None:
      scopeCoagAirVolumeB = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.SCOPE_COAG_TISSUE_VOLUME_B)
      scopeCoagAirVolumeB.SetOrigin([0,0,0])
      spacing = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
      scopeCoagAirVolumeB.SetSpacing([1, 1, 1])
      scopeCoagAirVolumeB.SetIJKToRASDirections([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
      scopeCoagAirVolumeB.CreateDefaultDisplayNodes()
      parameterNode.SetNodeReferenceID(self.SCOPE_COAG_TISSUE_VOLUME_B, scopeCoagAirVolumeB.GetID())

    


  def setupTransformHierarchy(self):
    """
    Sets up transform nodes in the scene if they don't exist yet.
    """
    parameterNode = self.getParameterNode()

    # ReferenceToRas puts everything in a rough anatomical reference (right, anterior, superior).
    # Translation is not relevant for ReferenceToRas, and rotation is fine even with +/- 30 deg error.

    referenceToRas = self.addLinearTransformToScene(self.REFERENCE_TO_RAS)

    # Needle tracking

    needleToReference = self.addLinearTransformToScene(self.NEEDLE_TO_REFERENCE, parentTransform=referenceToRas)
    self.addLinearTransformToScene(self.NEEDLETIP_TO_NEEDLE, parentTransform=needleToReference)

    # Cautery tracking

    cauteryToReference = self.addLinearTransformToScene(self.CAUTERY_TO_REFERENCE, parentTransform=referenceToRas)
    self.addLinearTransformToScene(self.CAUTERY_TO_NEEDLE)  # For cautery calibration

    cauteryTipToCautery = parameterNode.GetNodeReference(self.CAUTERYTIP_TO_CAUTERY)
    if cauteryTipToCautery is None:
      try:
        cauteryTipToCauteryFileWithPath = self.resourcePath(self.CAUTERYTIP_TO_CAUTERY + ".h5")
        logging.info("Loading cautery calibration from file: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.util.loadTransform(cauteryTipToCauteryFileWithPath)
      except:
        logging.info("Creating cautery calibration file, because none was found as: {}".format(cauteryTipToCauteryFileWithPath))
        cauteryTipToCautery = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.CAUTERYTIP_TO_CAUTERY)
      parameterNode.SetNodeReferenceID(self.CAUTERYTIP_TO_CAUTERY, cauteryTipToCautery.GetID())
    cauteryTipToCautery.SetAndObserveTransformNodeID(cauteryToReference.GetID())

    # Ultrasound image tracking

    transdToReference = self.addLinearTransformToScene(self.TRANSD_TO_REFERENCE, parentTransform=referenceToRas)
    imageToTransd = self.addLinearTransformToScene(self.IMAGE_TO_TRANSD, parentTransform=transdToReference)
    self.updateImageToTransdFromDepth(self.DEFAULT_US_DEPTH)

    imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
    if imageImage is None:
      imageImage = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", self.IMAGE_IMAGE)
      imageImage.CreateDefaultDisplayNodes()
      imageArray = np.zeros((512, 512, 1), dtype="uint8")
      slicer.util.updateVolumeFromArray(imageImage, imageArray)
      parameterNode.SetNodeReferenceID(self.IMAGE_IMAGE, imageImage.GetID())
    imageImage.SetAndObserveTransformNodeID(imageToTransd.GetID())

    # TransdToNeedle to display tumour reconstruction in needle coordinate system
    # TODO: is this the right way to update TransdToNeedle?
    transdToNeedle = self.addLinearTransformToScene(self.TRANSD_TO_NEEDLE, parentTransform=needleToReference)
    parameterNode.SetNodeReferenceID(self.TRANSD_TO_NEEDLE, transdToNeedle.GetID())
    transdToNeedle.SetAndObserveTransformNodeID(transdToReference.GetID())

  def updateImageToTransdFromDepth(self, depthMm):
    """
    Computes ImageToTransd for a specified ultrasound depth setting (millimeters), and updates the ImageToTransd
    transform node in the current MRML scene.
    """

    imageToTransdPixel = vtk.vtkTransform()
    imageToTransdPixel.Translate(-255.5, 0, 0)

    pxToMm = self.scaling_Intercept + self.scaling_Slope * depthMm

    transdPixelToTransd = vtk.vtkTransform()
    transdPixelToTransd.Scale(pxToMm, pxToMm, pxToMm)

    imageToTransd = vtk.vtkTransform()
    imageToTransd.Concatenate(transdPixelToTransd)
    imageToTransd.Concatenate(imageToTransdPixel)
    imageToTransd.Update()

    parameterNode = self.getParameterNode()
    imageToTransdNode = parameterNode.GetNodeReference(self.IMAGE_TO_TRANSD)
    imageToTransdNode.SetAndObserveTransformToParent(imageToTransd)

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

  #def sequenceBrowserSetUp(self):
  def setTrackingSequenceBrowser(self, recording):
    
    parameterNode = self.getParameterNode()
    sequenceBrowserTracking = parameterNode.GetNodeReference(self.TRACKING_SEQUENCE_BROWSER)
    sequenceBrowserTracking.SetRecordingActive(recording) #stop

  def setUltrasoundSequenceBrowser(self, recording):

    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.ULTRASOUND_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop

  # TODO: are we assuming a useful image will be given when button is pressed?
  def setRegionOfInterestNode(self):
    parameterNode = self.getParameterNode()
    roiNode = parameterNode.GetNodeReference(self.ROI_NODE)
    if not roiNode:
      roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLAnnotationROINode", self.ROI_NODE)
      parameterNode.SetNodeReferenceID(self.ROI_NODE, roiNode.GetID())
      roiNode.SetDisplayVisibility(0)
      # Get center of current slice
      imageImage = parameterNode.GetNodeReference(self.IMAGE_IMAGE)
      bounds = [0,0,0,0,0,0]
      imageImage.GetSliceBounds(bounds, vtk.vtkMatrix4x4())
      sliceCenter = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2]
      roiNode.SetXYZ(sliceCenter)
      roiNode.SetRadiusXYZ(10, 10, 10)
      logging.info(f"Added a 10x10x10cm ROI at position: {sliceCenter}")
      # TODO: do we need to orient ROI to match the image?
  
  def setAndObserveTumorMarkupsNode(self, tumorMarkups_Needle):
    logging.debug("setAndObserveTumorMarkupsNode")

  def setDeleteLastFiducialClicked(self, numberOfPoints):
    deleted_coord = [0.0, 0.0, 0.0]
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.GetNthFiducialPosition(numberOfPoints-1,deleted_coord)
    tumorMarkups_Needle.RemoveMarkup(numberOfPoints-1)
    logging.info("Deleted last fiducial at %s", deleted_coord)
    if numberOfPoints<=1:
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      parameterNode = self.getParameterNode()
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      tumorModel_Needle.Modified()

  def setDeleteAllFiducialsClicked(self):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    tumorMarkups_Needle.RemoveAllMarkups()
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
    tumorMarkups_Needle.AddFiducial(cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))
    logging.info("Tumor point placed at cautery tip, (%s, %s, %s)", cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))

  def setFreezeUltrasoundClicked(self):
    self.usFrozen = not self.usFrozen
    parameterNode = self.getParameterNode()
    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    if self.usFrozen:
      #self.guideletParent.connectorNode.Stop()
      plusServerNode.StopServer()
    else:
      #self.guideletParent.connectorNode.Start()
      plusServerNode.StartServer()

  def setToolModelClicked(self, toggled):
    logging.info("setToolModelClicked")
    parameterNode = self.getParameterNode()
    cauteryModel = parameterNode.GetNodeReference(self.CAUTERY_MODEL)
    stickModel = parameterNode.GetNodeReference(self.STICK_MODEL)
    if toggled:
      cauteryModel.SetDisplayVisibility(True) #look to function self.logic.setNeedelVisibility, do we need the QSettings lines here? Why do they exist in the function?
      stickModel.SetDisplayVisibility(False)
    else:
      cauteryModel.SetDisplayVisibility(False)
      stickModel.SetDisplayVisibility(True)
  
  def setSelectPointsToEraseClicked(self, pushed):
    logging.info('setSelectPointsToEraseClicked')
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      parameterNode = self.getParameterNode()
      eraseMarkups_Needle = parameterNode.GetNodeReference(self.ERASE_MARKUPS_NEEDLE)
      selectionNode.SetActivePlaceNodeID(eraseMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
      
  def setDisplaySampleGraphButton(self):
    #logging.info('setDisplaySampleGraphButton')
    #call scopeSignalModified
    self.scopeSignalModified(None, None)

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

  def setStreamGraphButton(toggled):
    loggin.info('setStreamGraphButton')
    #if toggled:
      #add observer

    #else:
      #remove observer

  def setNormalBrightnessClicked(self):
    logging.info("setNormalBrightnessClicked")
    self.setImageMinMaxLevel(0,300)

  def setBrightBrightnessClicked(self):
    logging.info("setBrightBrightnessClicked")
    self.setImageMinMaxLevel(0,220)

  def setBrightestBrightnessClicked(self):
    logging.info("setBrightestBrightnessClicked")
    self.setImageMinMaxLevel(0,140)

  def setImageMinMaxLevel(self, minLevel, maxLevel):
    logging.info("setImageMinMaxLevel")
    parameterNode = self.getParameterNode()
    liveUSNode = parameterNode.GetNodeReference(self.IMAGE_IMAGE).GetDisplayNode()
    liveUSNode.SetAutoWindowLevel(0)
    liveUSNode.SetWindowLevelMinMax(minLevel, maxLevel)

  def onTumorMarkupsNodeModified(self, observer, eventid):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()
    #if numberOfPoints>1:
    #  self.ui.deleteLastFiducialButton.setEnabled(True)
    #  self.ui.deleteAllFiducialsButton.setEnabled(True)
    #  self.ui.deleteLastFiducialNavigationButton.setEnabled(True)
    #  self.ui.selectPointsToEraseButton.setEnabled(True)
    logging.debug("onTumorMarkupsNodeModified")

    self.createTumorFromMarkups()
    parameterNode.Modified()

  def createTumorFromMarkups(self):
    logging.debug('createTumorFromMarkups')
    #self.tumorMarkups_Needle.SetDisplayVisibility(0)
    # Create polydata point set from markup points
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if numberOfPoints<1:
      sphereSource = vtk.vtkSphereSource()
      #sphereSource.SetRadius(0.001)
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      tumorModel_Needle.Modified()
      return
    
    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]
    for i in range(numberOfPoints):
      tumorMarkups_Needle.GetNthFiducialPosition(i,new_coord)
      points.SetPoint(i, new_coord)

    tumorMarkups_Needle.GetNthFiducialPosition(numberOfPoints-1,new_coord)
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
    #glyph.SetVectorModeToUseNormal()
    #glyph.SetScaleModeToScaleByVector()
    #glyph.SetScaleFactor(0.25)
    delaunay.SetInputConnection(glyph.GetOutputPort())
    #print("delaunay")
    #print(delaunay)
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
    #print("delaySmooth")
    #print(delaunaySmooth)
    smoothSurfaceFilter = vtk.vtkDataSetSurfaceFilter()
    smoothSurfaceFilter.SetInputConnection(delaunaySmooth.GetOutputPort())
    #print("smoothSurface")
    #print(smoothSurfaceFilter)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(smoothSurfaceFilter.GetOutputPort())
    normals.SetFeatureAngle(100.0)
    #print("normals")
    #print(normals)
    normals.Update()
    parameterNode = self.getParameterNode()
    tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
    tumorModel_Needle.SetAndObservePolyData(normals.GetOutput())

  def modifyPoints(self, observer, eventID):
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if parameterNode.GetParameter(self.POINTS_STATUS) == self.POINTS_ERASING:
      numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()
      mostRecentPoint = [0.0, 0.0, 0.0]
      tumorMarkups_Needle.GetNthFiducialPosition(numberOfPoints - 1, mostRecentPoint)
      closestPoint = self.returnClosestPoint(tumorMarkups_Needle, mostRecentPoint)
      tumorMarkups_Needle.RemoveMarkup(closestPoint)
      tumorMarkups_Needle.RemoveMarkup(0)
      self.createTumorFromMarkups()

  def setRemoveFiducialPoint(self):

    #TODO: Remove function
    parameterNode = self.getParameterNode()
    tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
    if self.eraserFlag == False :
      self.eraserFlag = True
      return
    self.eraserFlag = False

    #place point
    #locate closest point
    #erase last placed point and closest point
    numberOfPoints = tumorMarkups_Needle.GetNumberOfFiducials()
    fiducialPosition = [0.0,0.0,0.0]
    tumorMarkups_Needle.GetNthFiducialPosition(0, fiducialPosition)
    logging.info("Used eraser to remove point at %s", fiducialPosition)
    tumorMarkups_Needle.RemoveMarkup(0)


    if numberOfPoints == 1 :
      #self.deleteLastFiducialButton.setEnabled(False)
      #self.deleteAllFiducialsButton.setEnabled(False)
      #self.deleteLastFiducialNavigationButton.setEnabled(False)
      #self.selectPointsToEraseButton.setEnabled(False)
      #self.selectPointsToEraseButton.setChecked(False)
      tumorMarkups_Needle.GetNthFiducialPosition(0,fiducialPosition)
      logging.info("Used eraser to remove point at %s", fiducialPosition)
      tumorMarkups_Needle.RemoveMarkup(0)
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      tumorModel_Needle = parameterNode.GetNodeReference(self.TUMOR_MODEL)
      tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
    elif numberOfPoints > 1 : 
      numberOfErasedPoints = eraseMarkups_Needle.GetNumberOfFiducials()
      mostRecentPoint = [0.0,0.0,0.0]
      eraseMarkups_Needle.GetNthFiducialPosition(numberOfErasedPoints-1, mostRecentPoint)
      closestPoint = self.returnClosestPoint(tumorMarkups_Needle, mostRecentPoint)
      tumorMarkups_Needle = parameterNode.GetNodeReference(self.TUMOR_MARKUPS_NEEDLE)
      tumorMarkups_Needle.RemoveMarkup(closestPoint)
    tumorMarkups_Needle.Modified()
    self.createTumorFromMarkups() 

  # returns closest marked point to where eraser fiducial was placed
  def returnClosestPoint(self, fiducialNode, erasePoint) :
    closestIndex = 0
    numberOfPoints = fiducialNode.GetNumberOfFiducials()
    closestPosition = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(0, closestPosition)
    distanceToClosest = self.returnDistance(closestPosition, erasePoint)
    fiducialPosition = [0.0,0.0,0.0]
    for fiducialIndex in range(1, numberOfPoints) :
      fiducialNode.GetNthFiducialPosition(fiducialIndex, fiducialPosition)
      distanceToPoint = self.returnDistance(fiducialPosition, erasePoint)
      if distanceToPoint < distanceToClosest :
        closestIndex = fiducialIndex
        distanceToClosest = distanceToPoint
    fiducialNode.GetNthFiducialPosition(closestIndex, fiducialPosition)
    logging.info("Used eraser to remove point at %s", fiducialPosition)
    return closestIndex
  
  def createMatrixFromString(self, transformMatrixString):
    transformMatrix = vtk.vtkMatrix4x4()
    transformMatrixArray = list(map(float, transformMatrixString.split(' ')))
    for r in range(4):
      for c in range(4):
        transformMatrix.SetElement(r,c, transformMatrixArray[r*4+c])
    return transformMatrix

  def returnDistance(self, point1, point2) :
    import numpy as np
    tumorFiducialPoint = np.array(point1)
    eraserPoint = np.array(point2)
    distance = np.linalg.norm(tumorFiducialPoint-eraserPoint)
    return distance
  
  def onBreachWarningNodeChanged(self, observer, eventid) :
    self.showDistanceToTumor()
  
  def showDistanceToTumor(self) :
    return
    if self.hideDistance : 
      return
    for i in range (0,3) : # There will always be three threeD views mapped in layout when the navigation panel is toggled
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()
      print(distanceToTumor)
      if distanceToTumor > 10 : # Only show distance with 2 decimal places if the cautery is within 10mm of the tumor boundary
        view.setCornerAnnotationText("{0:.1f}mm".format(self.breachWarningNode.GetClosestDistanceToModelFromToolTip()))
      else :
        view.setCornerAnnotationText("{0:.2f}mm".format(self.breachWarningNode.GetClosestDistanceToModelFromToolTip()))
  
  def setCollectOff(self, recording):
    #logging.info("setCollectOff")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_OFF_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop
    return
    
  def setCollectCutAir(self, recording):
    #logging.info("setCollectCutAir")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop

  def setCollectCutTissue(self, recording):
    #logging.info("setCollectCutTissue")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop

  def setCollectCoagAir(self, recording):
    #logging.info("setCollectCoagAir")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop

  def setCollectCoagTissue(self, recording):
    #logging.info("setCollectCoagTissue")
    parameterNode = self.getParameterNode()
    sequenceBrowserUltrasound = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    sequenceBrowserUltrasound.SetRecordingActive(recording) #stop

  def setTrainAndImplementModel(self):
    logging.info("setTrainAndImplementModel")
    parameterNode = self.getParameterNode()
    collectOffSeqBr = parameterNode.GetNodeReference(self.COLLECT_OFF_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectOffSeqBr.GetNumberOfItems()
    collectOffSeqBr.SelectFirstItem()
    channelACollectOff = np.empty([n,3900])
    channelBCollectOff = np.empty([n,3900])
    featureCollectOff = np.empty([n,2])
    Y_CollectOff = np.full((n,1), 0)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0,1]
      ChB = oscilloscopeArray[0,2]
      channelACollectOff[i] = ChA
      channelBCollectOff[i] = ChB
      featureCollectOff[i][0] = self.lmrMean(ChA, ChB)
      featureCollectOff[i][1] = self.mMean(ChA, ChB)
      item = collectOffSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)

    collectCutAirSeqBr = parameterNode.GetNodeReference(self.COLLECT_CUT_AIR_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCutAirSeqBr.GetNumberOfItems()
    collectCutAirSeqBr.SelectFirstItem()
    channelACollectCutAir = np.empty([n,3900])
    channelBCollectCutAir = np.empty([n,3900])
    featureCollectCutAir = np.empty([n,2])
    Y_CollectCutAir = np.full((n,1), 1)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0,1]
      ChB = oscilloscopeArray[0,2]
      channelACollectCutAir[i] = ChA
      channelBCollectCutAir[i] = ChB
      featureCollectCutAir[i][0] = self.lmrMean(ChA, ChB)
      featureCollectCutAir[i][1] = self.mMean(ChA, ChB)
      collectCutAirSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)

    collectCutTissueSeqBr = parameterNode.GetNodeReference(self.COLLECT_CUT_TISSUE_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCutTissueSeqBr.GetNumberOfItems()
    collectCutTissueSeqBr.SelectFirstItem()
    channelACollectCutTissue = np.empty([n,3900])
    channelBCollectCutTissue = np.empty([n,3900])
    featureCollectCutTissue = np.empty([n,2])
    Y_CollectCutTissue = np.full((n,1), 2)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0,1]
      ChB = oscilloscopeArray[0,2]
      channelACollectCutTissue[i] = ChA
      channelBCollectCutTissue[i] = ChB
      featureCollectCutTissue[i][0] = self.lmrMean(ChA, ChB)
      featureCollectCutTissue[i][1] = self.mMean(ChA, ChB)
      collectCutTissueSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
  
    collectCoagAirSeqBr = parameterNode.GetNodeReference(self.COLLECT_COAG_AIR_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCoagAirSeqBr.GetNumberOfItems()
    collectCoagAirSeqBr.SelectFirstItem()
    channelACollectCoagAir = np.empty([n,3900])
    channelBCollectCoagAir = np.empty([n,3900])
    featureCollectCoagAir = np.empty([n,2])
    Y_CollectCoagAir = np.full((n,1), 3)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0,1]
      ChB = oscilloscopeArray[0,2]
      channelACollectCoagAir[i] = ChA
      channelBCollectCoagAir[i] = ChB
      featureCollectCoagAir[i][0] = self.lmrMean(ChA, ChB)
      featureCollectCoagAir[i][1] = self.mMean(ChA, ChB)
      collectCoagAirSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    
    collectCoagTissueSeqBr = parameterNode.GetNodeReference(self.COLLECT_COAG_TISSUE_SEQUENCE_BROWSER)
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    n = collectCoagTissueSeqBr.GetNumberOfItems()
    collectCoagTissueSeqBr.SelectFirstItem()
    channelACollectCoagTissue = np.empty([n,3900])
    channelBCollectCoagTissue = np.empty([n,3900])
    featureCollectCoagTissue = np.empty([n,2])
    Y_CollectCoagTissue = np.full((n,1), 4)
    for i in range(n):
      oscilloscopeArray = slicer.util.arrayFromVolume(signal_Signal)
      ChA = oscilloscopeArray[0,1]
      ChB = oscilloscopeArray[0,2]
      channelACollectCoagTissue[i] = ChA
      channelBCollectCoagTissue[i] = ChB
      featureCollectCoagTissue[i][0] = self.lmrMean(ChA, ChB)
      featureCollectCoagTissue[i][1] = self.mMean(ChA, ChB)
      collectCoagTissueSeqBr.SelectNextItem()
      signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)

    #append arrays, build X and Y\
    features = np.append(featureCollectOff, featureCollectCutAir, axis = 0)
    features = np.append(features, featureCollectCutTissue, axis = 0)
    features = np.append(features, featureCollectCoagAir, axis = 0)
    features = np.append(features, featureCollectCoagTissue, axis = 0)
    Y = np.append(Y_CollectOff, Y_CollectCutAir)
    Y = np.append(Y, Y_CollectCutTissue)
    Y = np.append(Y, Y_CollectCoagAir)
    Y = np.append(Y, Y_CollectCoagTissue)
    
    self.buildScopeModel(features, Y)

  def buildScopeModel(self, features, Y):

    X_training, X_test, Y_train, Y_test = train_test_split(features, Y, test_size=0.2)

    C = 1.0
    svc = svm.SVC(kernel = 'linear', C=3.0, decision_function_shape='ovo').fit(X_training, Y_train)
    lin = svm.LinearSVC().fit(X_training, Y_train)
    rbf = svm.SVC(kernel = 'rbf', gamma = 0.9, C=1.0).fit(X_training, Y_train)
    poly = svm.SVC(kernel = 'poly', degree = 3, C = 1.0).fit(X_training, Y_train)

    filename_svc = "D:\Research\Oscilloscope\cauteryModelSVM_svc.sav"
    filename_lin = "D:\Research\Oscilloscope\cauteryModelSVM_lin.sav"
    filename_rbf = "D:\Research\Oscilloscope\cauteryModelSVM_rbf.sav"
    filename_poly = "D:\Research\Oscilloscope\cauteryModelSVM_poly.sav"
    pickle.dump(svc, open(filename_svc, "wb"))
    pickle.dump(lin, open(filename_lin, "wb"))
    pickle.dump(rbf, open(filename_rbf, "wb"))
    pickle.dump(poly, open(filename_poly, "wb"))
    loaded_module_svc = pickle.load(open(filename_svc, "rb"))
    loaded_module_lin = pickle.load(open(filename_lin, "rb"))
    loaded_module_rbf = pickle.load(open(filename_rbf, "rb"))
    loaded_module_poly = pickle.load(open(filename_poly, "rb"))
    result = loaded_module_svc.score(X_test, Y_test)
    predict = loaded_module_svc.predict(X_test)
    print("----SVC------")
    print("Prediction", predict)
    print("Y test", Y_test)
    print("result", result)
    print("-----LIN------")
    result = loaded_module_lin.score(X_test, Y_test)
    predict = loaded_module_lin.predict(X_test)
    print("Prediction", predict)
    print("Y test", Y_test)
    print("result", result)
    print("-----RBF------")
    result = loaded_module_rbf.score(X_test, Y_test)
    predict = loaded_module_rbf.predict(X_test)
    print("Prediction", predict)
    print("Y test", Y_test)
    print("result", result)
    np.save("D:/Research/Oscilloscope/features.npy", features)
    np.save("D:/Research/Oscilloscope/Y.npy", Y)
    print("-----POLY------")
    result_poly = loaded_module_poly.score(X_test, Y_test)
    predict_poly = loaded_module_poly.predict(X_test)
    print("Prediction", predict_poly)
    print("Y test", Y_test)
    print("result", result_poly)
    
    # h = 0.02  # step size in the mesh
    
    # # create a mesh to plot in

    # X_train_min, X_train_max = X_training[:,0].min() - 1, X_training[:,0].max() + 1
    # Y_train_min, Y_train_max = X_training[:,1].min() - 1, X_training[:,1].max() + 1
    # X_train, yy = np.meshgrid(np.float32(np.arange(X_train_min, X_train_max, h)), np.float32(np.arange(Y_train_min, Y_train_max, h)))
    # # title for the plots
    # titles = ['SVC with linear kernel',
    #     'LinearSVC (linear kernel)',
    #       'SVC with RBF kernel',
    #       'SVC with polynomial (degree 3) kernel']

    # for i, clf in enumerate((svc, lin_svc, rbf_svc, poly_svc)):
    #   # Plot the decision boundarY_train. For that, we will assign a color to each
    #   # point in the mesh [X_train_min, X_train_max]X_train[Y_train_min, Y_train_max].
      
    #   plt.subplot(2, 2, i + 1)
    #   plt.subplots_adjust(wspace=0.4, hspace=0.4)
  
    #   Z = clf.predict(np.c_[X_train.ravel(), yy.ravel()])
      
    #   # Put the result into a color plot
    #   Z = Z.reshape(X_train.shape)
    #   plt.contourf(X_train, yy, Z, cmap=plt.cm.coolwarm, alpha=0.8)
  
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

  def setUseBaseModelClicked(self, clicked):
    parameterNode = self.getParameterNode()
    signal_Signal = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    if clicked:
      self.addObserver(signal_Signal, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.useBaseModelModified)
    else:
      self.removeObserver(signal_Signal, slicer.vtkMRMLScalarVolumeNode.ImageDataModifiedEvent, self.useBaseModelModified)

  def useBaseModelModified(self, observer, eventID):
    #TODO: how do I non-specific to my computer file paths
    filename = "D:\Research\Oscilloscope\cauteryModelSVM_svc_78accuracy.sav"
    import pickle
    cauterySVMModel = pickle.load(open(filename, "rb"))
    parameterNode = self.getParameterNode()
    oscilloscopeVolume = parameterNode.GetNodeReference(self.SIGNAL_SIGNAL)
    oscilloscopeArray = slicer.util.arrayFromVolume(oscilloscopeVolume)
    #TODO: create parameter node reference for arrays.
    time = oscilloscopeArray[0,0]
    ChA = np.transpose(oscilloscopeArray[0,1])
    ChB = np.transpose(oscilloscopeArray[0,2])
    feat = np.empty([1,2])
    lmrMeanTest = self.lmrMean(ChA, ChB)
    mMeanTest = self.mMean(ChA, ChB)
    feat[0][0] = lmrMeanTest
    feat[0][1] = mMeanTest
    predict = cauterySVMModel.predict(feat)
    print("Prediction", predict)
    
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
      lmrSum = self.absSum(channelA) - absSum(channelB)
      return lmrSum

  def lmrMean(self, channelA, channelB):
      lmrMean = (self.absMean(channelA - channelB)) * 10000
      return lmrMean

  def mMean(self, channelA, channelB):
      mMean = (self.absMean(channelA) * self.absSum(channelB)) * 100
      return mMean

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

