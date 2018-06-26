import os
from __main__ import vtk, qt, ctk, slicer

from Guidelet import GuideletLoadable, GuideletLogic, GuideletTest, GuideletWidget
from Guidelet import Guidelet
import logging
import time
import math
import numpy


#
# LumpNav ###
#

class LumpNav(GuideletLoadable):
  """Uses GuideletLoadable class, available at:
  """

  def __init__(self, parent):
    GuideletLoadable.__init__(self, parent)
    self.parent.title = "Lumpectomy Navigation"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Tamas Ungi (Perk Lab)"]
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# LumpNavWidget
#

class LumpNavWidget(GuideletWidget):
  """Uses GuideletWidget base class, available at:
  """

  def __init__(self, parent = None):
    try:
      import BreachWarningLight
      self.breachWarningLightLogic = BreachWarningLight.BreachWarningLightLogic()
    except ImportError:
      self.breachWarningLightLogic = None
      logging.warning('BreachWarningLight module is not available. Light feedback is disabled.')

    GuideletWidget.__init__(self, parent)

  def setup(self):
    GuideletWidget.setup(self)

  def addLauncherWidgets(self):
    GuideletWidget.addLauncherWidgets(self)

    # BreachWarning
    self.addBreachWarningLightPreferences()

  def onConfigurationChanged(self, selectedConfigurationName):
    GuideletWidget.onConfigurationChanged(self, selectedConfigurationName)
    if self.breachWarningLightLogic:
      settings = slicer.app.userSettings()
      lightEnabled = settings.value(self.moduleName + '/Configurations/' + self.selectedConfigurationName + '/EnableBreachWarningLight')
      self.breachWarningLightCheckBox.checked = (lightEnabled == 'True')

  def addBreachWarningLightPreferences(self):
    lnNode = slicer.util.getNode(self.moduleName)

    if self.breachWarningLightLogic:

      self.breachWarningLightCheckBox = qt.QCheckBox()
      checkBoxLabel = qt.QLabel()
      hBoxCheck = qt.QHBoxLayout()
      hBoxCheck.setAlignment(0x0001)
      checkBoxLabel.setText("Use Breach Warning Light: ")
      hBoxCheck.addWidget(checkBoxLabel)
      hBoxCheck.addWidget(self.breachWarningLightCheckBox)
      hBoxCheck.setStretch(1,2)
      self.launcherFormLayout.addRow(hBoxCheck)

      if(lnNode is not None and lnNode.GetParameter('EnableBreachWarningLight')):
          # logging.debug("There is already a connector EnableBreachWarningLight parameter " + lnNode.GetParameter('EnableBreachWarningLight'))
          self.breachWarningLightCheckBox.checked = lnNode.GetParameter('EnableBreachWarningLight')
          self.breachWarningLightCheckBox.setDisabled(True)
      else:
          self.breachWarningLightCheckBox.setEnabled(True)
          settings = slicer.app.userSettings()
          lightEnabled = settings.value(self.moduleName + '/Configurations/' + self.selectedConfigurationName + '/EnableBreachWarningLight', 'True')
          self.breachWarningLightCheckBox.checked = (lightEnabled == 'True')

      self.breachWarningLightCheckBox.connect('stateChanged(int)', self.onBreachWarningLightChanged)

  def onBreachWarningLightChanged(self, state):
    lightEnabled = ''
    if self.breachWarningLightCheckBox.checked:
      lightEnabled = 'True'
    elif not self.breachWarningLightCheckBox.checked:
      lightEnabled = 'False'
    self.guideletLogic.updateSettings({'EnableBreachWarningLight' : lightEnabled}, self.selectedConfigurationName)

  def createGuideletInstance(self):
    return LumpNavGuidelet(None, self.guideletLogic, self.selectedConfigurationName)

  def createGuideletLogic(self):
    return LumpNavLogic()

#
# LumpNavLogic ###
#

class LumpNavLogic(GuideletLogic):
  """Uses GuideletLogic base class, available at:
  """ #TODO add path

  def __init__(self, parent = None):
    GuideletLogic.__init__(self, parent)

  def addValuesToDefaultConfiguration(self):
    GuideletLogic.addValuesToDefaultConfiguration(self)
    moduleDir = os.path.dirname(slicer.modules.lumpnav.path)
    defaultSavePathOfLumpNav = os.path.join(moduleDir, 'SavedScenes')
    settingList = {'StyleSheet' : moduleDir + '\Resources\StyleSheets\LumpNavStyle.qss',
                   'EnableBreachWarningLight' : 'False',
                   'BreachWarningLightMarginSizeMm' : '2.0',
                   'TipToSurfaceDistanceTextScale' : '3',
                   'TipToSurfaceDistanceTrajectory' : 'True',
                   'CauteryModelToCauteryTip' : '0.03 0.03 1.01 0.00 -0.97 -0.23 0.03 0.00 0.23 -0.98 0.02 0.00 0 0 0 1',
                   'PivotCalibrationErrorThresholdMm' :  '0.9',
                   'PivotCalibrationDurationSec' : '5',
                   'TestMode' : 'False',
                   'RecordingFilenamePrefix' : 'LumpNavRecording-',
                   'SavedScenesDirectory': defaultSavePathOfLumpNav,#overwrites the default setting param of base
                   }
    self.updateSettings(settingList, 'Default')


#
#	LumpNavTest ###
#

class LumpNavTest(GuideletTest):
  """This is the test case for your scripted module.
  """

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    GuideletTest.runTest(self)
    #self.test_LumpNav1() #add applet specific tests here

class LumpNavGuidelet(Guidelet):
  
  LUMPNAV_PIVOT_CALIBRATION = 0
  LUMPNAV_SPIN_CALIBRATION = 1
  
  def __init__(self, parent, logic, configurationName='Default'):

    try:
      import BreachWarningLight
      self.breachWarningLightLogic = BreachWarningLight.BreachWarningLightLogic()
    except ImportError:
      self.breachWarningLightLogic = None
      
    Guidelet.__init__(self, parent, logic, configurationName)
    logging.debug('LumpNavGuidelet.__init__')
    self.logic.addValuesToDefaultConfiguration()

    moduleDirectoryPath = slicer.modules.lumpnav.path.replace('LumpNav.py', '')
    self.needleModelTipRadius = 2.0
    
    self.needleCalibrationMode = self.LUMPNAV_PIVOT_CALIBRATION

    # Set up main frame.

    self.sliceletDockWidget.setObjectName('LumpNavPanel')
    self.sliceletDockWidget.setWindowTitle('LumpNav')
    self.mainWindow.setWindowTitle('Lumpectomy navigation')
    self.mainWindow.windowIcon = qt.QIcon(moduleDirectoryPath + '/Resources/Icons/LumpNav.png')

    self.pivotCalibrationLogic=slicer.modules.pivotcalibration.logic()

    # Set needle and cautery transforms and models
    self.tumorMarkups_Needle = None
    self.tumorMarkups_NeedleObserver = None

    # Second fiducial node used to erase points
    self.eraseMarkups_Needle = slicer.vtkMRMLMarkupsFiducialNode()
    slicer.mrmlScene.AddNode(self.eraseMarkups_Needle)
    self.eraseMarkups_Needle.CreateDefaultDisplayNodes() 
    self.eraseMarkups_NeedleObserver = None
    self.setAndObserveErasedMarkupsNode(self.eraseMarkups_Needle)

    # Temporary solution to double function call problem
    self.eraserFlag = True
    self.loggingFlag = True

    self.hideDistance = True # Only show distance to tumor after button is clicked

    self.setupScene()

    self.navigationView = self.VIEW_TRIPLE_3D

    # Setting button open on startup.
    self.calibrationCollapsibleButton.setProperty('collapsed', False)

    slicer.lumpguidelet = self #TODO: Remove

  def createFeaturePanels(self):
    # Create GUI panels.

    self.calibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupCalibrationPanel()

    featurePanelList = Guidelet.createFeaturePanels(self)
    self.addTumorContouringToUltrasoundPanel()

    self.navigationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupNavigationPanel()

    featurePanelList[len(featurePanelList):] = [self.calibrationCollapsibleButton, self.navigationCollapsibleButton]

    return featurePanelList

  def __del__(self):#common
    self.cleanup()

  # Clean up when slicelet is closed
  def cleanup(self):#common
    Guidelet.cleanup(self)
    logging.debug('cleanup')
    self.breachWarningNode.UnRegister(slicer.mrmlScene)
    self.setAndObserveTumorMarkupsNode(None)
    self.setAndObserveErasedMarkupsNode(None)
    if self.breachWarningLightLogic:
      self.breachWarningLightLogic.stopLightFeedback()

  def setupConnections(self):
    logging.debug('LumpNav.setupConnections()')
    Guidelet.setupConnections(self)

    self.calibrationCollapsibleButton.connect('toggled(bool)', self.onCalibrationPanelToggled)
    self.navigationCollapsibleButton.connect('toggled(bool)', self.onNavigationPanelToggled)

    self.cauteryPivotButton.connect('clicked()', self.onCauteryPivotClicked)
    self.needlePivotButton.connect('clicked()', self.onNeedlePivotClicked)
    self.needleSpinButton.connect('clicked()', self.onNeedleSpinClicked)
    self.needleLengthSpinBox.connect('valueChanged(int)', self.onNeedleLengthModified)
    self.placeButton.connect('clicked(bool)', self.onPlaceClicked)
    self.eraseButton.connect('clicked(bool)', self.onEraseClicked)
    self.deleteLastFiducialButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteLastFiducialDuringNavigationButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteAllFiducialsButton.connect('clicked()', self.onDeleteAllFiducialsClicked)
    self.leftBreastButton.connect('clicked()', self.onLeftBreastButtonClicked)
    self.rightBreastButton.connect('clicked()', self.onRightBreastButtonClicked)
    self.displayDistanceButton.connect('clicked()', self.onDisplayDistanceClicked)
    self.distanceFontSizeSpinner.valueChanged.connect(self.onDistanceFontSizeChanged)

    self.bottomBullseyeCameraButton.connect('clicked()', lambda: self.onCameraButtonClicked('View3') )
    self.leftAutoCenterCameraButton.connect('clicked()', lambda: self.onAutoCenterButtonClicked('View1') )
    self.rightAutoCenterCameraButton.connect('clicked()', lambda: self.onAutoCenterButtonClicked('View2') )
    self.bottomAutoCenterCameraButton.connect('clicked()', lambda: self.onAutoCenterButtonClicked('View3') )

    self.dual3dButton.connect('clicked()', self.onDual3dButtonClicked)
    self.triple3dButton.connect('clicked()', self.onTriple3dButtonClicked)

    self.placeTumorPointAtCauteryTipButton.connect('clicked(bool)', self.onPlaceTumorPointAtCauteryTipClicked)

    self.pivotSamplingTimer.connect('timeout()',self.onPivotSamplingTimeout)

    import Viewpoint
    self.viewpointLogic = Viewpoint.ViewpointLogic()

  def setupScene(self): #applet specific
    logging.debug('setupScene')

    # ReferenceToRas is needed for ultrasound initialization, so we need to
    # set it up before calling Guidelet.setupScene().
    self.referenceToRas = slicer.util.getNode('ReferenceToRas')
    if not self.referenceToRas:
      self.referenceToRas=slicer.vtkMRMLLinearTransformNode()
      self.referenceToRas.SetName("ReferenceToRas")
      m = self.logic.readTransformFromSettings('ReferenceToRas', self.configurationName)
      if m is None:
        # By default ReferenceToRas is tilted 15deg around the patient LR axis as the reference
        # sensor is attached to the sternum, which is not horizontal.
        m = self.logic.createMatrixFromString('0 0 -1 0 0.258819 -0.965926 0 0 -0.965926 -0.258819 0 0 0 0 0 1')
      self.referenceToRas.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.referenceToRas)

    Guidelet.setupScene(self)

    logging.debug('Create transforms')
    # Coordinate system definitions: https://app.assembla.com/spaces/slicerigt/wiki/Coordinate_Systems

    self.cauteryTipToCautery = slicer.util.getNode('CauteryTipToCautery')
    if not self.cauteryTipToCautery:
      self.cauteryTipToCautery=slicer.vtkMRMLLinearTransformNode()
      self.cauteryTipToCautery.SetName("CauteryTipToCautery")
      m = self.logic.readTransformFromSettings('CauteryTipToCautery', self.configurationName)
      if m:
        self.cauteryTipToCautery.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryTipToCautery)

    self.cauteryModelToCauteryTip = slicer.util.getNode('CauteryModelToCauteryTip')
    if not self.cauteryModelToCauteryTip:
      self.cauteryModelToCauteryTip=slicer.vtkMRMLLinearTransformNode()
      self.cauteryModelToCauteryTip.SetName("CauteryModelToCauteryTip")
      m = self.logic.readTransformFromSettings('CauteryModelToCauteryTip', self.configurationName)
      if m:
        self.cauteryModelToCauteryTip.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryModelToCauteryTip)

    self.needleTipToNeedle = slicer.util.getNode('NeedleTipToNeedle')
    if not self.needleTipToNeedle:
      self.needleTipToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.needleTipToNeedle.SetName("NeedleTipToNeedle")
      m = self.logic.readTransformFromSettings('NeedleTipToNeedle', self.configurationName)
      if m:
        self.needleTipToNeedle.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleTipToNeedle)

    self.needleBaseToNeedle = slicer.util.getNode('NeedleBaseToNeedle')
    if not self.needleBaseToNeedle:
      self.needleBaseToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.needleBaseToNeedle.SetName("NeedleBaseToNeedle")
      m = self.logic.readTransformFromSettings('NeedleBaseToNeedle', self.configurationName)
      if m:
        self.needleBaseToNeedle.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleBaseToNeedle)

    self.cauteryCameraToCautery = slicer.util.getNode('CauteryCameraToCautery')
    if not self.cauteryCameraToCautery:
      self.cauteryCameraToCautery=slicer.vtkMRMLLinearTransformNode()
      self.cauteryCameraToCautery.SetName("CauteryCameraToCautery")
      m = self.logic.createMatrixFromString('0 0 -1 0 1 0 0 0 0 -1 0 0 0 0 0 1')
      self.cauteryCameraToCautery.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryCameraToCautery)

    self.CauteryToNeedle = slicer.util.getNode('CauteryToNeedle')
    if not self.CauteryToNeedle:
      self.CauteryToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.CauteryToNeedle.SetName("CauteryToNeedle")
      slicer.mrmlScene.AddNode(self.CauteryToNeedle)

    # Create transforms that will be updated through OpenIGTLink

    self.cauteryToReference = slicer.util.getNode('CauteryToReference')
    if not self.cauteryToReference:
      self.cauteryToReference=slicer.vtkMRMLLinearTransformNode()
      self.cauteryToReference.SetName("CauteryToReference")
      slicer.mrmlScene.AddNode(self.cauteryToReference)

    self.needleToReference = slicer.util.getNode('NeedleToReference')
    if not self.needleToReference:
      self.needleToReference=slicer.vtkMRMLLinearTransformNode()
      self.needleToReference.SetName("NeedleToReference")
      slicer.mrmlScene.AddNode(self.needleToReference)

    # Models
    logging.debug('Create models')

    self.cauteryModel_CauteryTip = slicer.util.getNode('CauteryModel')
    if not self.cauteryModel_CauteryTip:
      moduleDirectoryPath = slicer.modules.lumpnav.path.replace('LumpNav.py', '')
      modelFilePath = qt.QDir.toNativeSeparators(moduleDirectoryPath + '/Resources/CauteryModel.stl')
      [success, self.cauteryModel_CauteryTip] = slicer.util.loadModel(modelFilePath, returnNode = True)
      if success:
        logging.debug('Loaded cautery model: {0}'.format(modelFilePath))
      else:
        logging.debug('Cautery model not found ({0}), using stick model instead'.format(modelFilePath))
        self.cauteryModel_CauteryTip = slicer.modules.createmodels.logic().CreateNeedle(100,1.0,2.0,0)
      self.cauteryModel_CauteryTip.GetDisplayNode().SetColor(1.0, 1.0, 0)
      self.cauteryModel_CauteryTip.GetDisplayNode().VisibilityOff()  # stick model is the default cautery model
      self.cauteryModel_CauteryTip.SetName("CauteryModel")
    
    self.stickModel_CauteryTip = slicer.util.getNode('StickModel')
    if not self.stickModel_CauteryTip:
      slicer.modules.createmodels.logic().CreateNeedle(100,1.0,2.0,0)
      self.stickModel_CauteryTip = slicer.util.getNode(pattern="NeedleModel")
      self.stickModel_CauteryTip.GetDisplayNode().SetColor(1.0, 1.0, 0)
      self.stickModel_CauteryTip.SetName("StickModel")
         
    self.needleModel_NeedleTip = slicer.util.getNode('NeedleModel')
    if not self.needleModel_NeedleTip:
      slicer.modules.createmodels.logic().CreateNeedle(60,1.0, self.needleModelTipRadius, 0)
      self.needleModel_NeedleTip=slicer.util.getNode(pattern="NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SetColor(0.33, 1.0, 1.0)
      self.needleModel_NeedleTip.SetName("NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SliceIntersectionVisibilityOn()

    # Create surface from point set

    logging.debug('Create surface from point set')

    self.tumorModel_Needle = slicer.util.getNode('TumorModel')
    if not self.tumorModel_Needle:
      self.tumorModel_Needle = slicer.vtkMRMLModelNode()
      self.tumorModel_Needle.SetName("TumorModel")
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      slicer.mrmlScene.AddNode(self.tumorModel_Needle)
      # Add display node
      modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
      modelDisplayNode.SetColor(0,1,0) # Green
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self.tumorModel_Needle.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    tumorMarkups_Needle = slicer.util.getNode('T')
    if not tumorMarkups_Needle:
      tumorMarkups_Needle = slicer.vtkMRMLMarkupsFiducialNode()
      tumorMarkups_Needle.SetName("T")
      slicer.mrmlScene.AddNode(tumorMarkups_Needle)
      tumorMarkups_Needle.CreateDefaultDisplayNodes()
      tumorMarkups_Needle.GetDisplayNode().SetTextScale(0)
    self.setAndObserveTumorMarkupsNode(tumorMarkups_Needle)

    # Set up breach warning node
    logging.debug('Set up breach warning')
    self.breachWarningNode = slicer.util.getNode('LumpNavBreachWarning')

    if not self.breachWarningNode:
      self.breachWarningNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLBreachWarningNode')
      self.breachWarningNode.UnRegister(None) # Python variable already holds a reference to it
      self.breachWarningNode.SetName("LumpNavBreachWarning")
      slicer.mrmlScene.AddNode(self.breachWarningNode)
      self.breachWarningNode.SetPlayWarningSound(True)
      self.breachWarningNode.SetWarningColor(1,0,0)
      self.breachWarningNode.SetOriginalColor(self.tumorModel_Needle.GetDisplayNode().GetColor())
      self.breachWarningNode.SetAndObserveToolTransformNodeId(self.cauteryTipToCautery.GetID())
      self.breachWarningNode.SetAndObserveWatchedModelNodeID(self.tumorModel_Needle.GetID())
      self.breachWarningNodeObserver = self.breachWarningNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onBreachWarningNodeChanged)
      breachWarningLogic = slicer.modules.breachwarning.logic()
      # Line properties can only be set after the line is creaed (made visible at least once)
      breachWarningLogic.SetLineToClosestPointVisibility(True, self.breachWarningNode)
      distanceTextScale = self.parameterNode.GetParameter('TipToSurfaceDistanceTextScale')
      breachWarningLogic.SetLineToClosestPointTextScale( float(distanceTextScale), self.breachWarningNode)
      breachWarningLogic.SetLineToClosestPointColor(0,0,1, self.breachWarningNode)
      breachWarningLogic.SetLineToClosestPointVisibility(False, self.breachWarningNode)

    # Set up breach warning light
    if self.breachWarningLightLogic:
      logging.debug('Set up breach warning light')
      self.breachWarningLightLogic.setMarginSizeMm(float(self.parameterNode.GetParameter('BreachWarningLightMarginSizeMm')))
      if (self.parameterNode.GetParameter('EnableBreachWarningLight')=='True'):
        logging.debug("BreachWarningLight: active")
        self.breachWarningLightLogic.startLightFeedback(self.breachWarningNode, self.connectorNode)
      else:
        logging.debug("BreachWarningLight: shutdown")
        self.breachWarningLightLogic.shutdownLight(self.connectorNode)

    # Build transform tree
    logging.debug('Set up transform tree')
    self.cauteryToReference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.cauteryCameraToCautery.SetAndObserveTransformNodeID(self.cauteryToReference.GetID())
    self.cauteryTipToCautery.SetAndObserveTransformNodeID(self.cauteryToReference.GetID())
    self.cauteryModelToCauteryTip.SetAndObserveTransformNodeID(self.cauteryTipToCautery.GetID())
    self.needleToReference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.needleBaseToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.cauteryModel_CauteryTip.SetAndObserveTransformNodeID(self.cauteryModelToCauteryTip.GetID())
    self.stickModel_CauteryTip.SetAndObserveTransformNodeID(self.cauteryModelToCauteryTip.GetID())
    self.needleModel_NeedleTip.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    self.tumorModel_Needle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.tumorMarkups_Needle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.eraseMarkups_Needle.SetAndObserveTransformNodeID(self.needleToReference.GetID())

    # self.liveUltrasoundNode_Reference.SetAndObserveTransformNodeID(self.referenceToRas.GetID())

    # Hide slice view annotations (patient name, scale, color bar, etc.) as they
    # decrease reslicing performance by 20%-100%
    logging.debug('Hide slice view annotations')
    import DataProbe
    dataProbeUtil=DataProbe.DataProbeLib.DataProbeUtil()
    dataProbeParameterNode=dataProbeUtil.getParameterNode()
    dataProbeParameterNode.SetParameter('showSliceViewAnnotations', '0')

    # Update the displayed needle length based on NeedleTipToNeedle and NeedleTipToNeedleBase
    self.updateDisplayedNeedleLength()

  def disconnect(self):#TODO see connect
    logging.debug('LumpNav.disconnect()')
    Guidelet.disconnect(self)

    # Remove observer to old parameter node
    if self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
      self.tumorMarkups_NeedleObserver = None
    
    if self.eraseMarkups_Needle and self.eraseMarkups_NeedleObserver :
      self.eraseMarkups_Needle.RemoveObserver(self.eraseMarkups_NeedleObserver)
      self.eraseMarkups_NeedleObserver = None

    self.calibrationCollapsibleButton.disconnect('toggled(bool)', self.onCalibrationPanelToggled)
    self.navigationCollapsibleButton.disconnect('toggled(bool)', self.onNavigationPanelToggled)

    self.cauteryPivotButton.disconnect('clicked()', self.onCauteryPivotClicked)
    self.needlePivotButton.disconnect('clicked()', self.onNeedlePivotClicked)
    self.needleSpinButton.disconnect('clicked()', self.onNeedleSpinClicked)
    self.deleteLastFiducialButton.disconnect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteLastFiducialDuringNavigationButton.disconnect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteAllFiducialsButton.disconnect('clicked()', self.onDeleteAllFiducialsClicked)
    self.placeButton.disconnect('clicked(bool)', self.onPlaceClicked)
    self.eraseButton.disconnect('clicked(bool)', self.onEraseClicked)
    self.leftBreastButton.connect('clicked()', self.onLeftBreastButtonClicked)
    self.rightBreastButton.connect('clicked()', self.onRightBreastButtonClicked)
    self.displayDistanceButton.disconnect('clicked()', self.onDisplayDistanceClicked)

    self.bottomBullseyeCameraButton.disconnect('clicked()', lambda: self.onCameraButtonClicked('View3') )
    self.leftAutoCenterCameraButton.disconnect('clicked()', lambda: self.onAutoCenterButtonClicked('View1') )
    self.rightAutoCenterCameraButton.disconnect('clicked()', lambda: self.onAutoCenterButtonClicked('View2') )
    self.bottomAutoCenterCameraButton.disconnect('clicked()', lambda: self.onAutoCenterButtonClicked('View3') )

    self.pivotSamplingTimer.disconnect('timeout()',self.onPivotSamplingTimeout)

    self.placeTumorPointAtCauteryTipButton.disconnect('clicked(bool)', self.onPlaceTumorPointAtCauteryTipClicked)

  def onPivotSamplingTimeout(self):#lumpnav
    self.countdownLabel.setText("Pivot calibrating for {0:.0f} more seconds".format(self.pivotCalibrationStopTime-time.time()))
    if(time.time()<self.pivotCalibrationStopTime):
      # continue
      self.pivotSamplingTimer.start()
    else:
      # calibration completed
      self.onStopPivotCalibration()

  def startPivotCalibration(self, toolToReferenceTransformName, toolToReferenceTransformNode, toolTipToToolTransformNode):#lumpnav
    self.needleCalibrationMode = self.LUMPNAV_PIVOT_CALIBRATION
    self.needlePivotButton.setEnabled(False)
    self.needleSpinButton.setEnabled(False)
    self.cauteryPivotButton.setEnabled(False)
    self.pivotCalibrationResultTargetNode =  toolTipToToolTransformNode
    self.pivotCalibrationResultTargetName = toolToReferenceTransformName
    self.pivotCalibrationLogic.SetAndObserveTransformNode( toolToReferenceTransformNode );
    self.pivotCalibrationStopTime=time.time()+float(self.parameterNode.GetParameter('PivotCalibrationDurationSec'))
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()

  def onStopPivotCalibration(self):#lumpnav
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.needlePivotButton.setEnabled(True)
    self.needleSpinButton.setEnabled(True)
    self.cauteryPivotButton.setEnabled(True)
    
    if self.needleCalibrationMode == self.LUMPNAV_PIVOT_CALIBRATION:
      calibrationSuccess = self.pivotCalibrationLogic.ComputePivotCalibration()
    else:
      calibrationSuccess = self.pivotCalibrationLogic.ComputeSpinCalibration()
    
    if not calibrationSuccess:
      self.countdownLabel.setText("Calibration failed: " + self.pivotCalibrationLogic.GetErrorText())
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    if(self.pivotCalibrationLogic.GetPivotRMSE() >= float(self.parameterNode.GetParameter('PivotCalibrationErrorThresholdMm'))):
      self.countdownLabel.setText("Calibration failed, error = {0:.2f} mm, please calibrate again!".format(self.pivotCalibrationLogic.GetPivotRMSE()))
      self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
      return
    
    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultTargetNode.SetMatrixTransformToParent(tooltipToToolMatrix)
    self.logic.writeTransformToSettings(self.pivotCalibrationResultTargetName, tooltipToToolMatrix, self.configurationName)
    self.countdownLabel.setText("Calibration completed, error = {0:.2f} mm".format(self.pivotCalibrationLogic.GetPivotRMSE()))
    logging.debug("Pivot calibration completed. Tool: {0}. RMSE = {1:.2f} mm".format(self.pivotCalibrationResultTargetNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    # We compute approximate needle length if we perform pivot calibration for the needle
    if self.pivotCalibrationResultTargetName == 'NeedleTipToNeedle':
      self.updateDisplayedNeedleLength()

  def onCauteryPivotClicked(self):#lumpnav
    logging.debug('onCauteryPivotClicked')
    self.startPivotCalibration('CauteryTipToCautery', self.CauteryToNeedle, self.cauteryTipToCautery)

  def onNeedlePivotClicked(self):#lumpnav
    # NeedleTipToNeedle transform can be computed in two ways:
    # A. Pivot calibration: NeedleTipToNeedle is computed by pivot calibration;
    #    needle length is computed from difference of NeedleTipToNeedle and NeedleBaseToNeedle transform
    # B. Needle length specification: NeedleTipToNeedle is computed by offsetting NeedleBaseToNeedle by the
    #    needle length the user specifies.
    # (NeedleBaseToNeedle is constant, depends on the geometry of the needle clip)
    logging.debug('onNeedlePivotClicked')
    self.startPivotCalibration('NeedleTipToNeedle', self.needleToReference, self.needleTipToNeedle)
  
  def onNeedleSpinClicked(self):#lumpnav
    logging.debug('onNeedleSpinClicked')
    self.needleCalibrationMode = self.LUMPNAV_SPIN_CALIBRATION
    self.needlePivotButton.setEnabled(False)
    self.needleSpinButton.setEnabled(False)
    self.cauteryPivotButton.setEnabled(False)
    self.pivotCalibrationResultTargetNode = self.needleTipToNeedle
    self.pivotCalibrationResultTargetName = 'NeedleTipToNeedle'
    self.pivotCalibrationLogic.SetAndObserveTransformNode( self.needleToReference )
    self.pivotCalibrationStopTime = time.time() + float(self.parameterNode.GetParameter('PivotCalibrationDurationSec'))
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()
    
  
  def onPlaceClicked(self, pushed):
    self.eraseButton.setChecked(False)
    logging.info("Mark Points clicked")
    logging.debug('onPlaceClicked')
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      selectionNode.SetActivePlaceNodeID(self.tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def onEraseClicked(self, pushed):
    self.placeButton.setChecked(False)
    logging.info("Erase Points clicked")
    logging.debug('onEraseClicked')

    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      selectionNode.SetActivePlaceNodeID(self.eraseMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def onDeleteLastFiducialClicked(self):
    if self.placeButton.isChecked() : # ensures point placed doesn't get logged twice
      self.placeButton.click()
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()
    deleted_coord = [0.0, 0.0, 0.0]
    self.tumorMarkups_Needle.GetNthFiducialPosition(numberOfPoints-1,deleted_coord)
    self.tumorMarkups_Needle.RemoveMarkup(numberOfPoints-1)
    logging.info("Deleted last fiducial at %s", deleted_coord)
    if numberOfPoints<=1:        
      self.deleteLastFiducialButton.setEnabled(False)
      self.deleteAllFiducialsButton.setEnabled(False)
      self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
      self.eraseButton.setEnabled(False)
      self.eraseButton.setChecked(False)
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      self.tumorModel_Needle.Modified()

  def onDeleteAllFiducialsClicked(self):
    self.tumorMarkups_Needle.RemoveAllMarkups()
    logging.info("Deleted all fiducials")
    self.deleteLastFiducialButton.setEnabled(False)
    self.deleteAllFiducialsButton.setEnabled(False)
    self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
    self.eraseButton.setEnabled(False)
    self.eraseButton.setChecked(False)
    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(0.001)
    self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
    self.tumorModel_Needle.Modified()

  def onPlaceTumorPointAtCauteryTipClicked(self):
    cauteryTipToNeedle = vtk.vtkMatrix4x4()
    self.cauteryTipToCautery.GetMatrixTransformToNode(self.needleToReference, cauteryTipToNeedle)
    self.tumorMarkups_Needle.AddFiducial(cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))
    logging.info("Tumor point placed at cautery tip, (%s, %s, %s)", cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))

  def setupCalibrationPanel(self):
    logging.debug('setupCalibrationPanel')

    self.calibrationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.calibrationCollapsibleButton.text = 'Tool calibration'
    self.sliceletPanelLayout.addWidget(self.calibrationCollapsibleButton)

    self.calibrationLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.calibrationLayout.setContentsMargins(12, 4, 4, 4)
    self.calibrationLayout.setSpacing(4)

    self.cauteryPivotButton = qt.QPushButton('Start cautery calibration')
    self.calibrationLayout.addRow(self.cauteryPivotButton)

    self.needleLengthLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.needleLengthSpinBox = qt.QSpinBox()
    self.needleLengthSpinBox.setMinimum(10)
    self.needleLengthSpinBox.setMaximum(200)
    self.needleLengthLayout.addRow('Needle length (mm)', self.needleLengthSpinBox)
    self.calibrationLayout.addRow(self.needleLengthLayout)

    # "Advanced needle calibration" Collapsible
    self.advancedNeedleCalibrationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.advancedNeedleCalibrationCollapsibleButton.title = "Advanced needle calibration"
    self.advancedNeedleCalibrationCollapsibleButton.collapsed=True
    self.calibrationLayout.addRow(self.advancedNeedleCalibrationCollapsibleButton)

    # Layout within the collapsible button
    self.advancedNeedleCalibrationFormLayout = qt.QFormLayout(self.advancedNeedleCalibrationCollapsibleButton)

    self.needlePivotButton = qt.QPushButton('Pivot calibration')
    self.advancedNeedleCalibrationFormLayout.addRow(self.needlePivotButton)
    
    self.needleSpinButton = qt.QPushButton('Spin calibration')
    self.advancedNeedleCalibrationFormLayout.addRow(self.needleSpinButton)
    
    self.countdownLabel = qt.QLabel()
    self.advancedNeedleCalibrationFormLayout.addRow(self.countdownLabel)

    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)

    # "New Needle Clip Calibration" Collapsible
    self.newNeedleClipCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.newNeedleClipCollapsibleButton.title = "New needle clip calibration"
    self.newNeedleClipCollapsibleButton.collapsed = True
    self.calibrationLayout.addRow(self.newNeedleClipCollapsibleButton)
  
    # Layout within the collapsible button
    newNeedleClipHBox = qt.QHBoxLayout()
    self.newNeedleClipFormLayout = qt.QFormLayout(self.newNeedleClipCollapsibleButton)
    self.calibrateNeedleClipButton = qt.QPushButton("Calibrate clip")
    self.calibrateNeedleClipButton.connect('clicked()', self.onNeedleClipClicked)
    self.needleLengthLabel = qt.QLabel('Specify needle length (mm):')
    self.needleLengthForClipCalibrationSpinBox = qt.QSpinBox()
    self.needleLengthForClipCalibrationSpinBox.setValue(50)

    newNeedleClipHBox.addWidget(self.calibrateNeedleClipButton)
    newNeedleClipHBox.addWidget(self.needleLengthLabel)
    newNeedleClipHBox.addWidget(self.needleLengthForClipCalibrationSpinBox)

    self.newNeedleClipFormLayout.addRow(newNeedleClipHBox)

  def addTumorContouringToUltrasoundPanel(self):

    self.ultrasoundCollapsibleButton.text = "Tumor contouring"

    self.placeButton = qt.QPushButton("Mark points")
    self.placeButton.setCheckable(True)
    self.placeButton.setIcon(qt.QIcon(":/Icons/MarkupsMouseModePlace.png"))

    moduleDirectoryPath = slicer.modules.lumpnav.path.replace('LumpNav.py', '') # eraser .png file saved in Icons folder
    self.eraseButton = qt.QPushButton("Erase points")
    self.eraseButton.setCheckable(True)
    self.eraseButton.setEnabled(False)
    self.eraseButton.setIcon(qt.QIcon(moduleDirectoryPath + '/Resources/Icons/Eraser.png'))
    
    markPointsHBox = qt.QHBoxLayout()
    markPointsHBox.addWidget(self.placeButton)
    markPointsHBox.addWidget(self.eraseButton)
    self.ultrasoundLayout.addRow(markPointsHBox)

    self.deleteLastFiducialButton = qt.QPushButton("Delete last")
    self.deleteLastFiducialButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.deleteLastFiducialButton.setEnabled(False)

    self.deleteAllFiducialsButton = qt.QPushButton("Delete all")
    self.deleteAllFiducialsButton.setIcon(qt.QIcon(":/Icons/MarkupsDeleteAllRows.png"))
    self.deleteAllFiducialsButton.setEnabled(False)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.deleteLastFiducialButton)
    hbox.addWidget(self.deleteAllFiducialsButton)
    self.ultrasoundLayout.addRow(hbox)

  def setupNavigationPanel(self):
    logging.debug('setupNavigationPanel')

    self.sliderTranslationDefaultMm = 0
    self.sliderTranslationMinMm     = -500
    self.sliderTranslationMaxMm     = 500
    self.sliderViewAngleDefaultDeg  = 30
    self.cameraViewAngleMinDeg      = 5.0  # maximum magnification
    self.cameraViewAngleMaxDeg      = 150.0 # minimum magnification

    self.sliderSingleStepValue = 1
    self.sliderPageStepValue   = 10

    self.navigationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.navigationCollapsibleButton.text = "Navigation"
    self.sliceletPanelLayout.addWidget(self.navigationCollapsibleButton)

    self.navigationCollapsibleLayout = qt.QFormLayout(self.navigationCollapsibleButton)
    self.navigationCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.navigationCollapsibleLayout.setSpacing(4)

    # Preset camera position options
    self.leftBreastButton = qt.QPushButton("Left Breast")
    self.leftBreastButton.setCheckable(True)

    self.rightBreastButton = qt.QPushButton("Right Breast")
    self.rightBreastButton.setCheckable(True)
 
    self.bottomBullseyeCameraButton = qt.QPushButton("Bottom camera")
    self.bottomBullseyeCameraButton.setCheckable(True)

    self.presetViewLabel = qt.QLabel("Preset Views :")
    self.navigationCollapsibleLayout.addRow(self.presetViewLabel)

    presetViewHBox = qt.QHBoxLayout()
    presetViewHBox.addWidget(self.leftBreastButton)
    presetViewHBox.addWidget(self.rightBreastButton)
    self.navigationCollapsibleLayout.addRow(presetViewHBox)

    # "Distance to Tumor" Collapsible
    self.distanceToTumorCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.distanceToTumorCollapsibleButton.title = "Distance to tumor margin"
    self.distanceToTumorCollapsibleButton.collapsed=True
    self.navigationCollapsibleLayout.addRow(self.distanceToTumorCollapsibleButton)

    # Layout within the collapsible button
    self.distanceToTumorFormLayout = qt.QFormLayout(self.distanceToTumorCollapsibleButton)

    self.displayDistanceButton = qt.QPushButton("Display Distance")
    self.distanceToTumorFormLayout.addRow(self.displayDistanceButton)

    self.distanceFontSizeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.distanceFontSizeLabel.setText("Distance to Tumor Font Size [mm]: ")
    self.distanceFontSizeSpinner = qt.QSpinBox()
    self.distanceFontSizeSpinner.setMinimum(5)
    self.distanceFontSizeSpinner.setMaximum(60)
    self.distanceFontSizeSpinner.setValue(35) # default font size
    self.distanceToTumorFormLayout.addRow(self.distanceFontSizeLabel, self.distanceFontSizeSpinner)

    # "View" Collapsible
    self.viewCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.viewCollapsibleButton.title = "View"
    self.viewCollapsibleButton.collapsed=True
    self.navigationCollapsibleLayout.addRow(self.viewCollapsibleButton)

    # Layout within the collapsible button
    self.viewFormLayout = qt.QFormLayout(self.viewCollapsibleButton)

    # Camera distance to focal point slider
    self.cameraViewAngleLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraViewAngleLabel.setText("Field of view [degrees]: ")
    self.cameraViewAngleSlider = slicer.qMRMLSliderWidget()
    self.cameraViewAngleSlider.minimum = self.cameraViewAngleMinDeg
    self.cameraViewAngleSlider.maximum = self.cameraViewAngleMaxDeg
    self.cameraViewAngleSlider.value = self.sliderViewAngleDefaultDeg
    self.cameraViewAngleSlider.singleStep = self.sliderSingleStepValue
    self.cameraViewAngleSlider.pageStep = self.sliderPageStepValue
    self.cameraViewAngleSlider.setDisabled(True)
    self.viewFormLayout.addRow(self.cameraViewAngleLabel,self.cameraViewAngleSlider)

    self.cameraXPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraXPosLabel.text = "Left/Right [mm]: "
    self.cameraXPosSlider = slicer.qMRMLSliderWidget()
    self.cameraXPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraXPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraXPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraXPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraXPosSlider.pageStep = self.sliderPageStepValue
    self.cameraXPosSlider.setDisabled(True)
    self.viewFormLayout.addRow(self.cameraXPosLabel,self.cameraXPosSlider)

    self.cameraYPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraYPosLabel.setText("Down/Up [mm]: ")
    self.cameraYPosSlider = slicer.qMRMLSliderWidget()
    self.cameraYPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraYPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraYPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraYPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraYPosSlider.pageStep = self.sliderPageStepValue
    self.cameraYPosSlider.setDisabled(True)
    self.viewFormLayout.addRow(self.cameraYPosLabel,self.cameraYPosSlider)

    self.cameraZPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraZPosLabel.setText("Front/Back [mm]: ")
    self.cameraZPosSlider = slicer.qMRMLSliderWidget()
    self.cameraZPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraZPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraZPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraZPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraZPosSlider.pageStep = self.sliderPageStepValue
    self.cameraZPosSlider.setDisabled(True)
    self.viewFormLayout.addRow(self.cameraZPosLabel,self.cameraZPosSlider)

    self.dual3dButton = qt.QPushButton("Dual 3D")
    self.triple3dButton = qt.QPushButton("Triple 3D")

    bullseyeHBox = qt.QHBoxLayout()
    bullseyeHBox.addWidget(self.dual3dButton)
    bullseyeHBox.addWidget(self.triple3dButton)
    self.viewFormLayout.addRow(bullseyeHBox)

    autoCenterLabel = qt.QLabel("Auto-center: ")

    self.leftAutoCenterCameraButton = qt.QPushButton("Left")
    self.leftAutoCenterCameraButton.setCheckable(True)

    self.rightAutoCenterCameraButton = qt.QPushButton("Right")
    self.rightAutoCenterCameraButton.setCheckable(True)

    self.bottomAutoCenterCameraButton = qt.QPushButton("Bottom")
    self.bottomAutoCenterCameraButton.setCheckable(True)

    self.viewFormLayout.addRow(self.bottomBullseyeCameraButton)

    autoCenterHBox = qt.QHBoxLayout()
    autoCenterHBox.addWidget(autoCenterLabel)
    autoCenterHBox.addWidget(self.leftAutoCenterCameraButton)
    autoCenterHBox.addWidget(self.bottomAutoCenterCameraButton)
    autoCenterHBox.addWidget(self.rightAutoCenterCameraButton)
    self.viewFormLayout.addRow(autoCenterHBox)

    # "Contour adjustment" Collapsible
    self.contourAdjustmentCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.contourAdjustmentCollapsibleButton.title = "Contour adjustment"
    self.contourAdjustmentCollapsibleButton.collapsed=True
    self.navigationCollapsibleLayout.addRow(self.contourAdjustmentCollapsibleButton)

    # Layout within the collapsible button
    self.contourAdjustmentFormLayout = qt.QFormLayout(self.contourAdjustmentCollapsibleButton)

    self.placeTumorPointAtCauteryTipButton = qt.QPushButton("Mark point at cautery tip")
    self.contourAdjustmentFormLayout.addRow(self.placeTumorPointAtCauteryTipButton)

    self.deleteLastFiducialDuringNavigationButton = qt.QPushButton("Delete last")
    self.deleteLastFiducialDuringNavigationButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
    self.contourAdjustmentFormLayout.addRow(self.deleteLastFiducialDuringNavigationButton)
    
    # "Choose Tool" Collapsible
    self.toolChoiceCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.toolChoiceCollapsibleButton.title = "Tool Choice"
    self.toolChoiceCollapsibleButton.collapsed = True
    self.navigationCollapsibleLayout.addRow(self.toolChoiceCollapsibleButton)
    

    # Layout within the collapsible button
    self.toolChoiceFormLayout = qt.QFormLayout(self.toolChoiceCollapsibleButton)
    self.toolChoiceLabel = qt.QLabel()
    self.toolChoiceLabel.setText("Select tool: ")
    
    self.SwitchToCauteryButton = qt.QPushButton("Cautery Model")
    self.SwitchToCauteryButton.toolTip = "Switching to cautery model"
    self.SwitchToCauteryButton.enabled = True
    self.SwitchToCauteryButton.connect('clicked(bool)', self.onSwitchToCauteryButton)
    self.SwitchToStickButton = qt.QPushButton("Stick Model")
    self.SwitchToStickButton.toolTip = "Switching to stick model"
    self.SwitchToStickButton.enabled = True
    self.SwitchToStickButton.connect('clicked(bool)', self.onSwitchToStickButton)
    
    self.toolChoiceHBox = qt.QHBoxLayout()
    self.toolChoiceHBox.addWidget(self.toolChoiceLabel)
    self.toolChoiceHBox.addWidget(self.SwitchToCauteryButton)
    self.toolChoiceHBox.addWidget(self.SwitchToStickButton)
    self.toolChoiceFormLayout.addRow(self.toolChoiceHBox)

  def onCalibrationPanelToggled(self, toggled):
    if toggled == False:
      return

    logging.debug('onCalibrationPanelToggled: {0}'.format(toggled))
    logging.info("Calibration Panel Toggled")

    if self.tumorMarkups_Needle:
      self.tumorMarkups_Needle.SetDisplayVisibility(0)

    self.selectView(self.VIEW_ULTRASOUND_3D)

  def onUltrasoundPanelToggled(self, toggled):
    Guidelet.onUltrasoundPanelToggled(self, toggled)

    if self.eraseButton.isChecked():
      self.onEraseClicked(toggled)    
    elif self.placeButton.isChecked():
      self.onPlaceClicked(toggled)

    if self.tumorMarkups_Needle:
        self.tumorMarkups_Needle.SetDisplayVisibility(0)

    # The user may want to freeze the image (disconnect) to make contouring easier.
    # Disable automatic ultrasound image auto-fit when the user unfreezes (connect)
    # to avoid zooming out of the image.
    self.fitUltrasoundImageToViewOnConnect = not toggled
  
  def showDistanceToTumor(self) :
    if self.hideDistance : 
      return
    for i in range (0,3) : # There will always be three threeD views mapped in layout when the navigation panel is toggled
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      view.setCornerAnnotationText("Distance: {0:.2f}mm".format(self.breachWarningNode.GetClosestDistanceToModelFromToolTip()))

  def createTumorFromMarkups(self):
    logging.debug('createTumorFromMarkups')
    #self.tumorMarkups_Needle.SetDisplayVisibility(0)
    # Create polydata point set from markup points
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()

    if numberOfPoints>0:
        self.deleteLastFiducialButton.setEnabled(True)
        self.deleteAllFiducialsButton.setEnabled(True)
        self.deleteLastFiducialDuringNavigationButton.setEnabled(True)
        self.eraseButton.setEnabled(True)

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if numberOfPoints<1:
      return
    
    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]
    for i in range(numberOfPoints):
      self.tumorMarkups_Needle.GetNthFiducialPosition(i,new_coord)
      points.SetPoint(i, new_coord)

    if self.placeButton.isChecked() :
      if self.loggingFlag == False : 
        self.loggingFlag = True
      else :
        self.loggingFlag = False
        self.tumorMarkups_Needle.GetNthFiducialPosition(numberOfPoints-1,new_coord)
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

    self.tumorModel_Needle.SetPolyDataConnection(normals.GetOutputPort())

    self.tumorModel_Needle.Modified()
 
  def removeFiducialPoint(self) : 
    self.eraseMarkups_Needle.SetDisplayVisibility(0)
    if self.eraserFlag == False :
      self.eraserFlag = True
      return
    self.eraserFlag = False
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()
    fiducialPosition = [0.0,0.0,0.0]
    if numberOfPoints == 1 :
      self.deleteLastFiducialButton.setEnabled(False)
      self.deleteAllFiducialsButton.setEnabled(False)
      self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
      self.eraseButton.setEnabled(False)
      self.eraseButton.setChecked(False)
      self.tumorMarkups_Needle.GetNthFiducialPosition(0,fiducialPosition)
      logging.info("Used eraser to remove point at %s", fiducialPosition)
      self.tumorMarkups_Needle.RemoveMarkup(0)
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())
      self.tumorModel_Needle.Modified()
    elif numberOfPoints > 1 : 
      numberOfErasedPoints = self.eraseMarkups_Needle.GetNumberOfFiducials()
      mostRecentPoint = [0.0,0.0,0.0]
      self.eraseMarkups_Needle.GetNthFiducialPosition(numberOfErasedPoints-1, mostRecentPoint)
      closestPoint = self.returnClosestPoint(self.tumorMarkups_Needle, mostRecentPoint)
      self.tumorMarkups_Needle.RemoveMarkup(closestPoint)
      self.tumorModel_Needle.Modified()

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
  
  def returnDistance(self, point1, point2) :
    import numpy as np
    tumorFiducialPoint = np.array(point1)
    eraserPoint = np.array(point2)
    distance = np.linalg.norm(tumorFiducialPoint-eraserPoint)
    return distance

  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    logging.debug("getCamera")
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(slicer.util.getNode(viewName))
    return camera

  def getViewNode(self, viewName):
    """
    Get the view node for the selected 3D view
    """
    logging.debug("getViewNode")
    viewNode = slicer.util.getNode(viewName)
    return viewNode

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

  # Preset View Radio Buttons
  def onLeftBreastButtonClicked(self) :
    logging.info("Left breast button clicked")
    logging.debug("onLeftBreastButtonClicked")
    self.rightBreastButton.setEnabled(True)
    self.rightBreastButton.setChecked(False)
    self.leftBreastButton.setEnabled(False)
    # check if autocenter buttons are already clicked before activating autocenter
    if not self.leftAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View1')
    if not self.rightAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View2')
    if not self.bottomAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View3')
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode3 = self.getCamera('View3')
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

  def onRightBreastButtonClicked(self) :
    logging.debug("onRightBreastButtonClicked")
    logging.info("Right breast button clicked")
    self.rightBreastButton.setEnabled(False)
    self.leftBreastButton.setEnabled(True)
    self.leftBreastButton.setChecked(False)
    if not self.leftAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View1')
    if not self.rightAutoCenterCameraButton.isChecked() :
      self.onAutoCenterButtonClicked('View2')
    if not self.bottomAutoCenterCameraButton.isChecked() :
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
  
  def onDisplayDistanceClicked(self) :
    logging.debug("onDisplayDistanceClicked")
    logging.info("Distance to Tumor button clicked")
    if self.hideDistance == False :
      self.hideDistance = True
      for i in range (0,3) : # Clear all text
        view = slicer.app.layoutManager().threeDWidget(i).threeDView()
        view.cornerAnnotation().ClearAllTexts()
      return
    self.hideDistance = False
    for i in range(0,3):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      view.cornerAnnotation().UpperLeft
      view.cornerAnnotation().SetNonlinearFontScaleFactor(0.9)
      view.cornerAnnotation().SetMaximumFontSize(self.distanceFontSizeSpinner.value)

  def enableBullseyeInViewNode(self, viewNode):
    logging.debug("enableBullseyeInViewNode")
    self.disableViewpointInViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetTransformNode(self.cauteryCameraToCautery)
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

  def updateGUISliders(self, viewNode):
    logging.debug("updateGUISliders")
    if (self.viewpointLogic.getViewpointForViewNode(viewNode).isCurrentModeBullseye()):
      self.cameraViewAngleSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.cameraXPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.cameraYPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.cameraZPosSlider.connect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.cameraViewAngleSlider.setDisabled(False)
      self.cameraXPosSlider.setDisabled(False)
      self.cameraZPosSlider.setDisabled(False)
      self.cameraYPosSlider.setDisabled(False)
    else:
      self.cameraViewAngleSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraViewAngleDeg)
      self.cameraXPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraXPosMm)
      self.cameraYPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraYPosMm)
      self.cameraZPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.getViewpointForViewNode(viewNode).bullseyeSetCameraZPosMm)
      self.cameraViewAngleSlider.setDisabled(True)
      self.cameraXPosSlider.setDisabled(True)
      self.cameraZPosSlider.setDisabled(True)
      self.cameraYPosSlider.setDisabled(True)

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

  def enableAutoCenterInViewNode(self, viewNode):
    logging.debug("enableAutoCenterInViewNode")
    self.disableViewpointInViewNode(viewNode)
    heightViewCoordLimits = 0.6;
    widthViewCoordLimits = 0.9;
    self.viewpointLogic.getViewpointForViewNode(viewNode).setViewNode(viewNode)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMinimum(-widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeXMaximum(widthViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMinimum(-heightViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetSafeYMaximum(heightViewCoordLimits)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterSetModelNode(self.tumorModel_Needle)
    self.viewpointLogic.getViewpointForViewNode(viewNode).autoCenterStart()

  def disableViewpointInViewNode(self,viewNode):
    logging.debug("disableViewpointInViewNode")
    self.disableBullseyeInViewNode(viewNode)
    self.disableAutoCenterInViewNode(viewNode)

  def updateGUIButtons(self):
    logging.debug("updateGUIButtons")

    leftViewNode = self.getViewNode('View1')

    blockSignalState = self.leftAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(leftViewNode).isCurrentModeAutoCenter()):
      self.leftAutoCenterCameraButton.setChecked(True)
    else:
      self.leftAutoCenterCameraButton.setChecked(False)
    self.leftAutoCenterCameraButton.blockSignals(blockSignalState)

    rightViewNode = self.getViewNode('View2')

    blockSignalState = self.rightAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(rightViewNode).isCurrentModeAutoCenter()):
      self.rightAutoCenterCameraButton.setChecked(True)
    else:
      self.rightAutoCenterCameraButton.setChecked(False)
    self.rightAutoCenterCameraButton.blockSignals(blockSignalState)

    centerViewNode = self.getViewNode('View3')

    blockSignalState = self.bottomAutoCenterCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(centerViewNode).isCurrentModeAutoCenter()):
      self.bottomAutoCenterCameraButton.setChecked(True)
    else:
      self.bottomAutoCenterCameraButton.setChecked(False)
    self.bottomAutoCenterCameraButton.blockSignals(blockSignalState)

    blockSignalState = self.bottomBullseyeCameraButton.blockSignals(True)
    if (self.viewpointLogic.getViewpointForViewNode(centerViewNode).isCurrentModeBullseye()):
      self.bottomBullseyeCameraButton.setChecked(True)
    else:
      self.bottomBullseyeCameraButton.setChecked(False)
    self.bottomBullseyeCameraButton.blockSignals(blockSignalState)

  def onDual3dButtonClicked(self):
    logging.info("Dual 3D button clicked")
    logging.debug("onDual3dButtonClicked")
    self.navigationView = self.VIEW_DUAL_3D
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode1.SetViewAngle(45.0)
    cameraNode2.SetViewAngle(45.0)
    self.updateNavigationView()

  def onTriple3dButtonClicked(self):
    logging.info("Triple 3D button clicked")
    logging.debug("onDual3dButtonClicked")
    self.navigationView = self.VIEW_TRIPLE_3D
    cameraNode1 = self.getCamera('View1')
    cameraNode2 = self.getCamera('View2')
    cameraNode1.SetViewAngle(25.0)
    cameraNode2.SetViewAngle(25.0)
    self.updateNavigationView()

  def updateNavigationView(self):
    logging.debug("updateNavigationView")
    self.selectView(self.navigationView)

    # Reset orientation marker
    if hasattr(slicer.vtkMRMLViewNode(),'SetOrientationMarkerType'): # orientation marker is not available in older Slicer versions
      v1=slicer.util.getNode('View1')
      v1v2OrientationMarkerSize = v1.OrientationMarkerSizeMedium if self.navigationView == self.VIEW_TRIPLE_3D else v1.OrientationMarkerSizeSmall
      v1.SetOrientationMarkerType(v1.OrientationMarkerTypeHuman)
      v1.SetOrientationMarkerSize(v1v2OrientationMarkerSize)
      v1.SetBoxVisible(False)
      v1.SetAxisLabelsVisible(False)
      v2=slicer.util.getNode('View2')
      v2.SetOrientationMarkerType(v2.OrientationMarkerTypeHuman)
      v2.SetOrientationMarkerSize(v1v2OrientationMarkerSize)
      v2.SetBoxVisible(False)
      v2.SetAxisLabelsVisible(False)
      v3=slicer.util.getNode('View3')
      if v3: # only available in triple view
        v3.SetOrientationMarkerType(v1.OrientationMarkerTypeHuman)
        v3.SetOrientationMarkerSize(v1.OrientationMarkerSizeLarge)
        v3.SetBoxVisible(False)
        v3.SetAxisLabelsVisible(False)

    # Reset the third view to show the patient from a standard direction (from feet)
    depthViewCamera = self.getCamera('View3')
    if depthViewCamera: # only available in triple view
      depthViewCamera.RotateTo(depthViewCamera.Inferior)

  def onNavigationPanelToggled(self, toggled):
    breachWarningLogic = slicer.modules.breachwarning.logic()
    showTrajectoryToClosestPoint = toggled and (self.parameterNode.GetParameter('TipToSurfaceDistanceTrajectory')=='True')
    breachWarningLogic.SetLineToClosestPointVisibility(showTrajectoryToClosestPoint, self.breachWarningNode)

    if toggled == False:
      return
    logging.info("Navigation panel toggled")
    logging.debug('onNavigationPanelToggled')
    self.updateNavigationView()
    if self.tumorMarkups_Needle:
      self.tumorMarkups_Needle.SetDisplayVisibility(0)

    ## Stop live ultrasound.
    #if self.connectorNode != None:
    #  self.connectorNode.Stop()

  def onTumorMarkupsNodeModified(self, observer, eventid):
    logging.debug("onTumorMarkupsNodeModified")
    self.createTumorFromMarkups()

  def onEraserClicked(self, observer, eventid) :
    logging.debug("onEraserClicked")
    self.removeFiducialPoint()

  def onBreachWarningNodeChanged(self, observer, eventid) :
    self.showDistanceToTumor()
    
  def setAndObserveErasedMarkupsNode(self, eraseMarkups_Needle):
    logging.debug("setAndObserveErasedMarkupsNode")
    if eraseMarkups_Needle == self.eraseMarkups_Needle and self.eraseMarkups_NeedleObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.eraseMarkups_Needle and self.eraseMarkups_NeedleObserver:
      self.eraseMarkups_Needle.RemoveObserver(self.eraseMarkups_NeedleObserver)
      self.eraseMarkups_NeedleObserver = None
    # Set and observe new parameter node
    self.eraseMarkups_Needle = eraseMarkups_Needle
    if self.eraseMarkups_Needle:
      self.eraseMarkups_NeedleObserver = self.eraseMarkups_Needle.AddObserver(vtk.vtkCommand.ModifiedEvent , self.onEraserClicked)

  def setAndObserveTumorMarkupsNode(self, tumorMarkups_Needle):
    logging.debug("setAndObserveTumorMarkupsNode")
    if tumorMarkups_Needle == self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
      self.tumorMarkups_NeedleObserver = None
    # Set and observe new parameter node
    self.tumorMarkups_Needle = tumorMarkups_Needle
    if self.tumorMarkups_Needle:
      self.tumorMarkups_NeedleObserver = self.tumorMarkups_Needle.AddObserver(vtk.vtkCommand.ModifiedEvent , self.onTumorMarkupsNodeModified)

  # Called when the user changes the needle length
  def onNeedleLengthModified(self, newLength):
    logging.debug('onNeedleLengthModified {0}'.format(newLength))
    needleBaseToNeedleMatrix = self.needleBaseToNeedle.GetMatrixTransformToParent()
    
    needleTipToNeedleBaseTransform = vtk.vtkTransform()
    needleTipToNeedleBaseTransform.Translate(0, 0, newLength)
    
    needleTipToNeedleTransform = vtk.vtkTransform()
    needleTipToNeedleTransform.Concatenate(self.needleBaseToNeedle.GetTransformToParent())
    needleTipToNeedleTransform.Concatenate(needleTipToNeedleBaseTransform)
    
    self.needleTipToNeedle.SetAndObserveTransformToParent(needleTipToNeedleTransform)
    self.logic.writeTransformToSettings('NeedleTipToNeedle', self.needleTipToNeedle.GetMatrixTransformToParent(), self.configurationName)
    
    slicer.modules.createmodels.logic().CreateNeedle(newLength,1.0, self.needleModelTipRadius, False, self.needleModel_NeedleTip)

  # Called after a successful pivot calibration
  def updateDisplayedNeedleLength(self):
    logging.debug("updateDisplayedNeedleLength")
    needleTipToNeedleBaseTransform = vtk.vtkMatrix4x4()
    self.needleTipToNeedle.GetMatrixTransformToNode(self.needleBaseToNeedle, needleTipToNeedleBaseTransform)
    needleLength = math.sqrt(needleTipToNeedleBaseTransform.GetElement(0,3)**2+needleTipToNeedleBaseTransform.GetElement(1,3)**2+needleTipToNeedleBaseTransform.GetElement(2,3)**2)
    wasBlocked = self.needleLengthSpinBox.blockSignals(True)
    self.needleLengthSpinBox.setValue(needleLength)
    self.needleLengthSpinBox.blockSignals(wasBlocked)
    # Update the needle model
    slicer.modules.createmodels.logic().CreateNeedle(needleLength,1.0, self.needleModelTipRadius, False, self.needleModel_NeedleTip)

  # Called when the user change the distance font size displayed
  def onDistanceFontSizeChanged(self):
    logging.debug("onDistanceFontSizeChanged")
    for i in range(0,3):
      view = slicer.app.layoutManager().threeDWidget(i).threeDView()
      view.cornerAnnotation().SetMaximumFontSize(self.distanceFontSizeSpinner.value)

  def onNeedleClipClicked(self) :
    logging.debug("onNewNeedleClipClicked")
    
    length = self.needleLengthForClipCalibrationSpinBox.value
    needleBaseToNeedleTipTransform = vtk.vtkTransform()
    needleBaseToNeedleTipTransform.Translate(0, 0, - length)
    
    needleTipToNeedleTransform = self.needleTipToNeedle.GetMatrixTransformToParent()
    
    needleBaseToNeedleTransform = vtk.vtkTransform()
    needleBaseToNeedleTransform.Concatenate(needleTipToNeedleTransform)
    needleBaseToNeedleTransform.Concatenate(needleBaseToNeedleTipTransform)
    
    self.needleBaseToNeedle.SetAndObserveTransformToParent(needleBaseToNeedleTransform)
    self.logic.writeTransformToSettings('NeedleBaseToNeedle', needleBaseToNeedleTransform.GetMatrix(), self.configurationName)
    self.needleLengthSpinBox.setValue(length)


  def onSwitchToCauteryButton(self):
    logging.info("Switched to cautery model")
    self.cauteryModel_CauteryTip.GetDisplayNode().VisibilityOn()
    self.stickModel_CauteryTip.GetDisplayNode().VisibilityOff()
  
  def onSwitchToStickButton(self):
    logging.info("Switched to stick model")
    self.cauteryModel_CauteryTip.GetDisplayNode().VisibilityOff()
    self.stickModel_CauteryTip.GetDisplayNode().VisibilityOn()
