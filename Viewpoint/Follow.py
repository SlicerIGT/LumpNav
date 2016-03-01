from __main__ import vtk, qt, ctk, slicer
import logging
import time

#
# Follow
#

class Follow:
  def __init__(self, parent):
    parent.title = "Follow"
    parent.categories = ["IGT"]
    parent.dependencies = []
    parent.contributors = ["Thomas Vaughan (Queen's)",
                           "Andras Lasso (Queen's)",
                           "Tamas Ungi (Queen's)",
                           "Gabor Fichtinger (Queen's)"]
    parent.helpText = """
    Set an observed transform which will guide the camera.
    """
    parent.acknowledgementText = """
    This work is part of the Breast NaviKnife project within the Laboratory for Percutaneous Surgery, Queen's University, Kingston, Ontario. Thomas Vaughan is funded by an NSERC Postgraduate award. Gabor Fichtinger is funded as a Cancer Care Ontario (CCO) Chair.
    """ # replace with organization, grant and thanks.
    self.parent = parent

#
# ViewpointWidget
#

class FollowWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
      self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
      
    self.logic = FollowLogic()
    
    self.rangeSliderMaximum = 100
    self.rangeSliderMinimum = -100
    self.rangeSliderMaximumValueDefault = 100
    self.rangeSliderMinimumValueDefault = -100
    
    self.sliderSingleStepValue = 0.01
    self.sliderPageStepValue   = 0.1
    
    self.updateRateMinSeconds = 0
    self.updateRateMaxSeconds = 1
    self.updateRateDefaultSeconds = 0.1
    
    self.timeUnsafeToAdjustMinSeconds = 0
    self.timeUnsafeToAdjustMaxSeconds = 5
    self.timeUnsafeToAdjustDefaultSeconds = 1
    
    self.timeAdjustToRestMinSeconds = 0
    self.timeAdjustToRestMaxSeconds = 5
    self.timeAdjustToRestDefaultSeconds = 1
    
    self.timeRestToSafeMinSeconds = 0
    self.timeRestToSafeMaxSeconds = 5
    self.timeRestToSafeDefaultSeconds = 1
    
    self.enableFollowButtonState = 0
    self.enableFollowButtonTextState0 = "Enable Viewpoint Mode"
    self.enableFollowButtonTextState1 = "Disable Viewpoint Mode"
    
  def setup(self):
    # TODO: The following line is strictly for debug purposes, should be removed when this module is done
    slicer.fwwidget = self
    
    # Collapsible buttons
    self.parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(self.parametersCollapsibleButton)

    # Layout within the collapsible button
    self.parametersFormLayout = qt.QFormLayout(self.parametersCollapsibleButton)
    
    # Transform combobox
    self.modelLabel = qt.QLabel()
    self.modelLabel.setText("toolCameraToToolTransform: ")
    self.modelSelector = slicer.qMRMLNodeComboBox()
    self.modelSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.modelSelector.noneEnabled = False
    self.modelSelector.addEnabled = False
    self.modelSelector.removeEnabled = False
    self.modelSelector.setMRMLScene( slicer.mrmlScene )
    self.modelSelector.setToolTip("Pick the model that the camera should follow, e.g. 'tumorModel'")
    self.parametersFormLayout.addRow(self.modelLabel, self.modelSelector)
    
    self.viewLabel = qt.QLabel()
    self.viewLabel.setText("Scene Camera: ")
    self.viewSelector = slicer.qMRMLNodeComboBox()
    self.viewSelector.nodeTypes = ( ("vtkMRMLViewNode"), "" )
    self.viewSelector.noneEnabled = False
    self.viewSelector.addEnabled = False
    self.viewSelector.removeEnabled = False
    self.viewSelector.setMRMLScene( slicer.mrmlScene )
    self.viewSelector.setToolTip("Pick the view which should be adjusted, e.g. 'View1'")
    self.parametersFormLayout.addRow(self.viewLabel, self.viewSelector)
    
    self.safeZoneXRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneXRangeLabel.text = "Safe Zone (Viewport X percentage): "
    self.safeZoneXRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneXRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneXRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneXRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneXRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    #self.safeZoneXRangeSlider.singleStep = self.sliderSingleStepValue
    #self.safeZoneXRangeSlider.pageStep = self.sliderPageStepValue
    self.parametersFormLayout.addRow(self.safeZoneXRangeLabel,self.safeZoneXRangeSlider)
    
    self.safeZoneYRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneYRangeLabel.setText("Safe Zone (Viewport Y percentage): ")
    self.safeZoneYRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneYRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneYRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneYRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneYRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    #self.safeZoneYRangeSlider.singleStep = self.sliderSingleStepValue
    #self.safeZoneYRangeSlider.pageStep = self.sliderPageStepValue
    self.parametersFormLayout.addRow(self.safeZoneYRangeLabel,self.safeZoneYRangeSlider)
    
    self.safeZoneZRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneZRangeLabel.setText("Safe Zone (Viewport Z percentage): ")
    self.safeZoneZRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneZRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneZRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneZRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneZRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    #self.safeZoneZRangeSlider.singleStep = self.sliderSingleStepValue
    #self.safeZoneZRangeSlider.pageStep = self.sliderPageStepValue
    self.parametersFormLayout.addRow(self.safeZoneZRangeLabel,self.safeZoneZRangeSlider)
    
    self.adjustXLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustXLabel.setText("Adjust X")
    self.adjustXCheckbox = qt.QCheckBox()
    self.adjustXCheckbox.setCheckState(1)
    self.adjustXCheckbox.setToolTip("If checked, render with parallel projection (box-shaped view). Otherwise render with perspective projection (cone-shaped view).")
    self.parametersFormLayout.addRow(self.adjustXLabel,self.adjustXCheckbox)
    
    self.adjustYLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustYLabel.setText("Adjust Y")
    self.adjustYCheckbox = qt.QCheckBox()
    self.adjustYCheckbox.setCheckState(1)
    self.adjustYCheckbox.setToolTip("If checked, render with parallel projection (box-shaped view). Otherwise render with perspective projection (cone-shaped view).")
    self.parametersFormLayout.addRow(self.adjustYLabel,self.adjustYCheckbox)
    
    self.adjustZLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustZLabel.setText("Adjust Z")
    self.adjustZCheckbox = qt.QCheckBox()
    self.adjustZCheckbox.setCheckState(1)
    self.adjustZCheckbox.setToolTip("If checked, render with parallel projection (box-shaped view). Otherwise render with perspective projection (cone-shaped view).")
    self.parametersFormLayout.addRow(self.adjustZLabel,self.adjustZCheckbox)
    
    self.updateRateLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.updateRateLabel.setText("Update rate (seconds): ")
    self.updateRateSlider = slicer.qMRMLSliderWidget()
    self.updateRateSlider.minimum = self.updateRateMinSeconds
    self.updateRateSlider.maximum = self.updateRateMaxSeconds
    self.updateRateSlider.value = self.updateRateDefaultSeconds
    self.updateRateSlider.singleStep = self.sliderSingleStepValue
    self.updateRateSlider.pageStep = self.sliderPageStepValue
    self.updateRateSlider.setToolTip("The rate at which the view will be checked and updated.")
    self.parametersFormLayout.addRow(self.updateRateLabel,self.updateRateSlider)
    
    self.timeUnsafeToAdjustLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeUnsafeToAdjustLabel.setText("Time Unsafe to Adjust (seconds): ")
    self.timeUnsafeToAdjustSlider = slicer.qMRMLSliderWidget()
    self.timeUnsafeToAdjustSlider.minimum = self.timeUnsafeToAdjustMinSeconds
    self.timeUnsafeToAdjustSlider.maximum = self.timeUnsafeToAdjustMaxSeconds
    self.timeUnsafeToAdjustSlider.value = self.timeUnsafeToAdjustDefaultSeconds
    self.timeUnsafeToAdjustSlider.singleStep = self.sliderSingleStepValue
    self.timeUnsafeToAdjustSlider.pageStep = self.sliderPageStepValue
    self.timeUnsafeToAdjustSlider.setToolTip("The length of time in which the model must be in the unsafe zone before the camera is adjusted.")
    self.parametersFormLayout.addRow(self.timeUnsafeToAdjustLabel,self.timeUnsafeToAdjustSlider)
    
    self.timeAdjustToRestLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeAdjustToRestLabel.setText("Time Adjust to Rest (seconds): ")
    self.timeAdjustToRestSlider = slicer.qMRMLSliderWidget()
    self.timeAdjustToRestSlider.minimum = self.timeAdjustToRestMinSeconds
    self.timeAdjustToRestSlider.maximum = self.timeAdjustToRestMaxSeconds
    self.timeAdjustToRestSlider.value = self.timeAdjustToRestDefaultSeconds
    self.timeAdjustToRestSlider.singleStep = self.sliderSingleStepValue
    self.timeAdjustToRestSlider.pageStep = self.sliderPageStepValue
    self.timeAdjustToRestSlider.setToolTip("The length of time an adjustment takes.")
    self.parametersFormLayout.addRow(self.timeAdjustToRestLabel,self.timeAdjustToRestSlider)
    
    self.timeRestToSafeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeRestToSafeLabel.setText("Time Rest to Safe (seconds): ")
    self.timeRestToSafeSlider = slicer.qMRMLSliderWidget()
    self.timeRestToSafeSlider.minimum = self.timeRestToSafeMinSeconds
    self.timeRestToSafeSlider.maximum = self.timeRestToSafeMaxSeconds
    self.timeRestToSafeSlider.value = self.timeRestToSafeDefaultSeconds
    self.timeRestToSafeSlider.singleStep = self.sliderSingleStepValue
    self.timeRestToSafeSlider.pageStep = self.sliderPageStepValue
    self.timeRestToSafeSlider.setToolTip("The length of time after an adjustment that the camera remains motionless.")
    self.parametersFormLayout.addRow(self.timeRestToSafeLabel,self.timeRestToSafeSlider)
    
    self.enableFollowButton = qt.QPushButton()
    self.enableFollowButton.setToolTip("The camera will continuously update its position so that it follows the model.")
    self.enableFollowButton.setText(self.enableFollowButtonTextState0)
    self.enableFollowButton.connect('clicked()', self.enableFollowButtonPressed)
    self.parametersFormLayout.addRow(self.enableFollowButton)
    
  def enableFollowButtonPressed(self):
    if self.enableFollowButtonState == 0:
      self.updateLogicParameters()
      self.logic.startFollow()
      if (self.logic.getActive()):
        self.disableWidgets()
        self.enableFollowButtonState = 1
        self.enableFollowButton.setText(self.enableFollowButtonTextState1)
    else:
      self.logic.stopFollow()
      if (not self.logic.getActive()):
        self.enableWidgets()
        self.enableFollowButtonState = 0
        self.enableFollowButton.setText(self.enableFollowButtonTextState0)
  
  def updateLogicParameters(self):
    self.logic.setModelNode(self.modelSelector.currentNode())
    self.logic.setViewNode(self.viewSelector.currentNode())
    self.logic.setSafeXMaximum(self.safeZoneXRangeSlider.maximumValue/100.0)
    self.logic.setSafeXMinimum(self.safeZoneXRangeSlider.minimumValue/100.0)
    self.logic.setSafeYMaximum(self.safeZoneYRangeSlider.maximumValue/100.0)
    self.logic.setSafeYMinimum(self.safeZoneYRangeSlider.minimumValue/100.0)
    self.logic.setSafeZMaximum(self.safeZoneZRangeSlider.maximumValue/100.0)
    self.logic.setSafeZMinimum(self.safeZoneZRangeSlider.minimumValue/100.0)
    self.logic.setAdjustX(self.adjustXCheckbox.isChecked())
    self.logic.setAdjustY(self.adjustYCheckbox.isChecked())
    self.logic.setAdjustZ(self.adjustZCheckbox.isChecked())
    self.logic.setUpdateRateSeconds(self.updateRateSlider.value)
    self.logic.setTimeUnsafeToAdjustMaximumSeconds(self.timeUnsafeToAdjustSlider.value)
    self.logic.setTimeAdjustToRestMaximumSeconds(self.timeAdjustToRestSlider.value)
    self.logic.setTimeRestToSafeMaximumSeconds(self.timeRestToSafeSlider.value)
      
  def enableWidgets(self):
    self.modelSelector.enabled = True
    self.viewSelector.enabled = True
    self.safeZoneXRangeSlider.enabled = True
    self.safeZoneYRangeSlider.enabled = True
    self.safeZoneZRangeSlider.enabled = True
    self.adjustXCheckbox.enabled = True
    self.adjustYCheckbox.enabled = True
    self.adjustZCheckbox.enabled = True
    self.updateRateSlider.enabled = True
    self.timeUnsafeToAdjustSlider.enabled = True
    self.timeAdjustToRestSlider.enabled = True
    self.timeRestToSafeSlider.enabled = True
  
  def disableWidgets(self):
    self.modelSelector.enabled = False
    self.viewSelector.enabled = False
    self.safeZoneXRangeSlider.enabled = False
    self.safeZoneYRangeSlider.enabled = False
    self.safeZoneZRangeSlider.enabled = False
    self.adjustXCheckbox.enabled = False
    self.adjustYCheckbox.enabled = False
    self.adjustZCheckbox.enabled = False
    self.updateRateSlider.enabled = False
    self.timeUnsafeToAdjustSlider.enabled = False
    self.timeAdjustToRestSlider.enabled = False
    self.timeRestToSafeSlider.enabled = False
      
#
# ViewpointLogic
#

class FollowLogic:
  def __init__(self):
    #inputs
    self.safeXMinimumNormalizedViewport = -1
    self.safeXMaximumNormalizedViewport = 1
    self.safeYMinimumNormalizedViewport = -1
    self.safeYMaximumNormalizedViewport = 1
    self.safeZMinimumNormalizedViewport = -1
    self.safeZMaximumNormalizedViewport = 1
    
    self.adjustX = True
    self.adjustY = True
    self.adjustZ = True
    
    self.modelNode = None
    self.viewNode = None
    
    self.timeUnsafeToAdjustMaximumSeconds = 1
    self.timeAdjustToRestMaximumSeconds = 0.2
    self.timeRestToSafeMaximumSeconds = 1
    
    self.updateRateSeconds = 0.1
    
    # current state
    self.transformNodeObserverTags = []
    self.active = False
    self.systemTimeAtLastUpdateSeconds = 0
    self.timeInStateSeconds = 0
    self.state = 0 # 0 = in safe zone (initial state), 1 = in unsafe zone, 2 = adjusting, 3 = resting
    self.stateSAFE = 0
    self.stateUNSAFE = 1
    self.stateADJUST = 2
    self.stateREST = 3
    self.cameraPositionRelativeToModel = [0,0,0]
    self.baseCameraTranslationRas = [0,0,0]
    self.baseCameraPositionRas = [0,0,0]
    self.baseCameraFocalPointRas = [0,0,0]
    self.modelInSafeZone = True 
    
    self.threeDWidgetIndex = 0 #TODO: Determine this
    self.modelTargetPositionViewport = [0,0,0]
  
  
  # FINITE STATE MACHINE:
  #  Safe <--pos-> Unsafe
  #    ^             |
  #    |            time
  #   time           |
  #    |             V
  #  Rest --time-> Adjust
  

  def setSafeXMinimum(self, val):
    self.safeXMinimumNormalizedViewport = val
    
  def setSafeXMaximum(self, val):
    self.safeXMaximumNormalizedViewport = val
    
  def setSafeYMinimum(self, val):
    self.safeYMinimumNormalizedViewport = val
    
  def setSafeYMaximum(self, val):
    self.safeYMaximumNormalizedViewport = val    

  def setSafeZMinimum(self, val):
    self.safeZMinimumNormalizedViewport = val
    
  def setSafeZMaximum(self, val):
    self.safeZMaximumNormalizedViewport = val
    
  def setAdjustX(self, val):
    self.adjustX = val
    
  def setAdjustY(self, val):
    self.adjustY = val
    
  def setAdjustZ(self, val):
    self.adjustZ = val
    
  def setAdjustXTrue(self):
    self.adjustX = True
    
  def setAdjustXFalse(self):
    self.adjustX = False
    
  def setAdjustYTrue(self):
    self.adjustY = True
    
  def setAdjustYFalse(self):
    self.adjustY = False
    
  def setAdjustZTrue(self):
    self.adjustZ = True
    
  def setAdjustZFalse(self):
    self.adjustZ = False
    
  def setTimeUnsafeToAdjustMaximumSeconds(self, val):
    self.timeUnsafeToAdjustMaximumSeconds = val
    
  def setTimeAdjustToRestMaximumSeconds(self, val):
    self.timeAdjustToRestMaximumSeconds = val
    
  def setTimeRestToSafeMaximumSeconds(self, val):
    self.timeRestToSafeMaximumSeconds = val
    
  def setUpdateRateSeconds(self, val):
    self.updateRateSeconds = val
    
  def setViewNode(self, node):
    self.viewNode = node
    
  def setModelNode(self, node):
    self.modelNode = node
    
  def getActive(self):
    return self.active
    
  def startFollow(self):
    if not self.viewNode:
      logging.warning("View node not set. Will not proceed until view node is selected.")
      return
    if not self.modelNode:
      logging.warning("Model node not set. Will not proceed until model node is selected.")
      return
    self.setModelTargetPositionViewport()
    self.systemTimeAtLastUpdateSeconds = time.time()
    nextUpdateTimerMilliseconds = self.updateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.update)
    
    self.active = True
    
  def stopFollow(self):
    logging.debug("stopFollow")
    self.active = False
    
  def update(self):
    if (not self.active):
      return
      
    deltaTimeSeconds = time.time() - self.systemTimeAtLastUpdateSeconds
    self.systemTimeAtLastUpdateSeconds = time.time()
    
    self.timeInStateSeconds = self.timeInStateSeconds + deltaTimeSeconds

    self.updateModelInSafeZone()
    self.applyStateMachine()
      
    nextUpdateTimerMilliseconds = self.updateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.update)

  def applyStateMachine(self):
    if (self.state == self.stateUNSAFE and self.modelInSafeZone):
      self.state = self.stateSAFE
      self.timeInStateSeconds = 0
    if (self.state == self.stateSAFE and not self.modelInSafeZone):
      self.state = self.stateUNSAFE
      self.timeInStateSeconds = 0
    if (self.state == self.stateUNSAFE and self.timeInStateSeconds >= self.timeUnsafeToAdjustMaximumSeconds):
      self.setCameraTranslationParameters()
      self.state = self.stateADJUST
      self.timeInStateSeconds = 0
    if (self.state == self.stateADJUST):
      self.translateCamera()
      if (self.timeInStateSeconds >= self.timeAdjustToRestMaximumSeconds):
        self.state = self.stateREST
        self.timeInStateSeconds = 0
    if (self.state == self.stateREST and self.timeInStateSeconds >= self.timeRestToSafeMaximumSeconds):
      self.state = self.stateSAFE
      self.timeInStateSeconds = 0
      
  def updateModelInSafeZone(self):
    if (self.state == self.stateADJUST or
        self.state == self.stateREST):
      return
    pointsRas = self.getModelCurrentBoundingBoxPointsRas()
    # Assume we are safe, until shown otherwise
    foundSafe = True
    for pointRas in pointsRas:
      coordsNormalizedViewport = self.convertRasToViewport(pointRas)
      XNormalizedViewport = coordsNormalizedViewport[0]
      YNormalizedViewport = coordsNormalizedViewport[1]
      ZNormalizedViewport = coordsNormalizedViewport[2]
      if ( XNormalizedViewport > self.safeXMaximumNormalizedViewport or 
           XNormalizedViewport < self.safeXMinimumNormalizedViewport or
           YNormalizedViewport > self.safeYMaximumNormalizedViewport or 
           YNormalizedViewport < self.safeYMinimumNormalizedViewport or
           ZNormalizedViewport > self.safeZMaximumNormalizedViewport or 
           ZNormalizedViewport < self.safeZMinimumNormalizedViewport ):
        foundSafe = False
        break
    self.modelInSafeZone = foundSafe

  def setModelTargetPositionViewport(self):
    modelPosRas = self.getModelCurrentCenterRas()
    self.modelTargetPositionViewport = self.convertRasToViewport(modelPosRas)
    
  def setCameraTranslationParameters(self):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCamera(viewName)
    cameraPosRas = [0,0,0]
    cameraNode.GetPosition(cameraPosRas)
    self.baseCameraPositionRas = cameraPosRas
    cameraFocRas = [0,0,0]
    cameraNode.GetFocalPoint(cameraFocRas)
    self.baseCameraFocalPointRas = cameraFocRas
    
    # find the translation in RAS
    modelCurrentPositionCamera = self.getModelCurrentCenterCamera()
    modelTargetPositionCamera = self.getModelTargetPositionCamera()
    cameraTranslationCamera = [0,0,0]
    if self.adjustX:
      cameraTranslationCamera[0] = modelCurrentPositionCamera[0] - modelTargetPositionCamera[0]
    if self.adjustY:
      cameraTranslationCamera[1] = modelCurrentPositionCamera[1] - modelTargetPositionCamera[1]
    if self.adjustZ:
      cameraTranslationCamera[2] = modelCurrentPositionCamera[2] - modelTargetPositionCamera[2]
    self.baseCameraTranslationRas = self.convertVectorCameraToRas(cameraTranslationCamera)
  
  def translateCamera(self):
    # linear interpolation between base and target positions, based on the timer
    weightTarget = 1 # default value
    if (self.timeAdjustToRestMaximumSeconds != 0):
      weightTarget = self.timeInStateSeconds / self.timeAdjustToRestMaximumSeconds
    if (weightTarget > 1):
      weightTarget = 1
    cameraNewPositionRas = [0,0,0]
    cameraNewFocalPointRas = [0,0,0]
    for i in xrange(0,3):
      translation = weightTarget * self.baseCameraTranslationRas[i]
      cameraNewPositionRas[i] = translation + self.baseCameraPositionRas[i]
      cameraNewFocalPointRas[i] = translation + self.baseCameraFocalPointRas[i]
    viewName = self.viewNode.GetName()
    cameraNode = self.getCamera(viewName)
    cameraNode.SetPosition(cameraNewPositionRas)
    cameraNode.SetFocalPoint(cameraNewFocalPointRas)
    self.resetCameraClippingRange()
    
  def getModelCurrentCenterRas(self):
    modelBoundsRas = [0,0,0,0,0,0]
    self.modelNode.GetRASBounds(modelBoundsRas)
    modelCenterX = (modelBoundsRas[0] + modelBoundsRas[1]) / 2
    modelCenterY = (modelBoundsRas[2] + modelBoundsRas[3]) / 2
    modelCenterZ = (modelBoundsRas[4] + modelBoundsRas[5]) / 2
    modelPosRas = [modelCenterX, modelCenterY, modelCenterZ]
    return modelPosRas
    
  def getModelCurrentCenterCamera(self):
    modelCenterRas = self.getModelCurrentCenterRas()
    modelCenterCamera = self.convertPointRasToCamera(modelCenterRas)
    return modelCenterCamera
    
  def getModelCurrentBoundingBoxPointsRas(self):
    pointsRas = []
    boundsRas = [0,0,0,0,0,0]
    self.modelNode.GetRASBounds(boundsRas)
    # permute through the different combinations of x,y,z; min,max
    for x in [0,1]:
      for y in [0,1]:
        for z in [0,1]:
          pointRas = []
          pointRas.append(boundsRas[0+x])
          pointRas.append(boundsRas[2+y])
          pointRas.append(boundsRas[4+z])
          pointsRas.append(pointRas)
    return pointsRas
    
  def getModelTargetPositionRas(self):
    return self.convertViewportToRas(self.modelTargetPositionViewport)
    
  def getModelTargetPositionCamera(self):
    modelTargetPositionRas = self.getModelTargetPositionRas()
    modelTargetPositionCamera = self.convertPointRasToCamera(modelTargetPositionRas)
    return modelTargetPositionCamera
    
  def getCamera(self, viewName):
    """
    Get camera for the selected 3D view
    """
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(slicer.util.getNode(viewName))
    return camera
      
  def convertRasToViewport(self, positionRas):
    """Computes normalized view coordinates from RAS coordinates
    Normalized view coordinates origin is in bottom-left corner, range is [-1,+1]
    """
    x = vtk.mutable(positionRas[0])
    y = vtk.mutable(positionRas[1])
    z = vtk.mutable(positionRas[2])
    view = slicer.app.layoutManager().threeDWidget(self.threeDWidgetIndex).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.WorldToView(x,y,z)
    return [x.get(), y.get(), z.get()]
    
  def convertViewportToRas(self, positionViewport):
    """Computes normalized view coordinates from RAS coordinates
    Normalized view coordinates origin is in bottom-left corner, range is [-1,+1]
    """
    x = vtk.mutable(positionViewport[0])
    y = vtk.mutable(positionViewport[1])
    z = vtk.mutable(positionViewport[2])
    view = slicer.app.layoutManager().threeDWidget(self.threeDWidgetIndex).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ViewToWorld(x,y,z)
    return [x.get(), y.get(), z.get()]
    
  def convertPointRasToCamera(self, positionRas):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCamera(viewName)
    cameraObj = cameraNode.GetCamera()
    modelViewTransform = cameraObj.GetModelViewTransformObject()
    positionRasHomog = [positionRas[0], positionRas[1], positionRas[2], 1] # convert to homogeneous
    positionCamHomog = [0,0,0,1] # to be filled in
    modelViewTransform.MultiplyPoint(positionRasHomog, positionCamHomog)
    positionCam = [positionCamHomog[0], positionCamHomog[1], positionCamHomog[2]] # convert from homogeneous
    return positionCam

  def convertVectorCameraToRas(self, positionCam):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCamera(viewName)
    cameraObj = cameraNode.GetCamera()
    modelViewTransform = cameraObj.GetModelViewTransformObject()
    modelViewMatrix = modelViewTransform.GetMatrix()
    modelViewInverseMatrix = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Invert(modelViewMatrix, modelViewInverseMatrix)
    modelViewInverseTransform = vtk.vtkTransform()
    modelViewInverseTransform.DeepCopy(modelViewTransform)
    modelViewInverseTransform.SetMatrix(modelViewInverseMatrix)
    positionCamHomog = [positionCam[0], positionCam[1], positionCam[2], 0] # convert to homogeneous
    positionRasHomog = [0,0,0,0] # to be filled in
    modelViewInverseTransform.MultiplyPoint(positionCamHomog, positionRasHomog)
    positionRas = [positionRasHomog[0], positionRasHomog[1], positionRasHomog[2]] # convert from homogeneous
    return positionRas
    
  def resetCameraClippingRange(self):
    view = slicer.app.layoutManager().threeDWidget(self.threeDWidgetIndex).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ResetCameraClippingRange
