from __main__ import vtk, qt, ctk, slicer
import logging

#
# Viewpoint
#

class Viewpoint:
  def __init__(self, parent):
    parent.title = "Viewpoint"
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

class ViewpointWidget:
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
      
    self.logic = ViewpointLogic()
    
    self.sliderTranslationDefaultMm    = 0
    self.sliderTranslationMinMm        = -200
    self.sliderTranslationMaxMm        = 200
    self.sliderViewAngleDefaultDeg     = 30
    self.cameraViewAngleMinDeg         = 5.0  # maximum magnification
    self.cameraViewAngleMaxDeg         = 150.0 # minimum magnification
    self.sliderParallelScaleDefaultDeg = 1
    self.cameraParallelScaleMinDeg     = 0.001  # maximum magnification
    self.cameraParallelScaleMaxDeg     = 1000.0 # minimum magnification
    
    self.sliderSingleStepValue = 1
    self.sliderPageStepValue   = 10
    
    self.enableViewpointButtonState = 0
    self.enableViewpointButtonTextState0 = "Enable Viewpoint Mode"
    self.enableViewpointButtonTextState1 = "Disable Viewpoint Mode"

  def setup(self):
    # TODO: The following line is strictly for debug purposes, should be removed when this module is done
    slicer.tvwidget = self

    # Collapsible buttons
    self.parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(self.parametersCollapsibleButton)

    # Layout within the collapsible button
    self.parametersFormLayout = qt.QFormLayout(self.parametersCollapsibleButton)
    
    # Transform combobox
    self.transformLabel = qt.QLabel()
    self.transformLabel.setText("toolCameraToToolTransform: ")
    self.transformSelector = slicer.qMRMLNodeComboBox()
    self.transformSelector.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.transformSelector.noneEnabled = False
    self.transformSelector.addEnabled = False
    self.transformSelector.removeEnabled = False
    self.transformSelector.setMRMLScene( slicer.mrmlScene )
    self.transformSelector.setToolTip("Pick the transform that the camera should follow, e.g. 'cauteryCameraToCauteryTransform'")
    self.parametersFormLayout.addRow(self.transformLabel, self.transformSelector)
    
    # Camera combobox
    self.cameraLabel = qt.QLabel()
    self.cameraLabel.setText("Scene Camera: ")
    self.cameraSelector = slicer.qMRMLNodeComboBox()
    self.cameraSelector.nodeTypes = ( ("vtkMRMLCameraNode"), "" )
    self.cameraSelector.noneEnabled = False
    self.cameraSelector.addEnabled = False
    self.cameraSelector.removeEnabled = False
    self.cameraSelector.setMRMLScene( slicer.mrmlScene )
    self.cameraSelector.setToolTip("Pick the camera which should be moved, e.g. 'Default Scene Camera'")
    self.parametersFormLayout.addRow(self.cameraLabel, self.cameraSelector)

    # "Camera Control" Collapsible
    self.cameraControlCollapsibleButton = ctk.ctkCollapsibleButton()
    self.cameraControlCollapsibleButton.text = "Camera Control"
    self.layout.addWidget(self.cameraControlCollapsibleButton)

    # Layout within the collapsible button
    self.cameraControlFormLayout = qt.QFormLayout(self.cameraControlCollapsibleButton)
    
    # "Degrees of Freedom" Collapsible button
    self.degreesOfFreedomCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.degreesOfFreedomCollapsibleButton.title = "Degrees of Freedom"
    self.cameraControlFormLayout.addRow(self.degreesOfFreedomCollapsibleButton)

    # Layout within the collapsible button
    self.degreesOfFreedomFormLayout = qt.QFormLayout(self.degreesOfFreedomCollapsibleButton)
    
    # A series of radio buttons for changing the degrees of freedom
    self.degreesOfFreedom3Label = qt.QLabel(qt.Qt.Horizontal,None)
    self.degreesOfFreedom3Label.setText("3DOF: ")
    self.degreesOfFreedom3RadioButton = qt.QRadioButton()
    self.degreesOfFreedom3RadioButton.setToolTip("The camera will always look at the target model (or if unselected will act like 5DOF)")
    self.degreesOfFreedomFormLayout.addRow(self.degreesOfFreedom3Label,self.degreesOfFreedom3RadioButton)
    
    self.degreesOfFreedom5Label = qt.QLabel(qt.Qt.Horizontal,None)
    self.degreesOfFreedom5Label.setText("5DOF: ")
    self.degreesOfFreedom5RadioButton = qt.QRadioButton()
    self.degreesOfFreedom5RadioButton.setToolTip("The camera will always be oriented with the selected 'up direction'")
    self.degreesOfFreedomFormLayout.addRow(self.degreesOfFreedom5Label,self.degreesOfFreedom5RadioButton)
    
    self.degreesOfFreedom6Label = qt.QLabel(qt.Qt.Horizontal,None)
    self.degreesOfFreedom6Label.setText("6DOF: ")
    self.degreesOfFreedom6RadioButton = qt.QRadioButton()
    self.degreesOfFreedom6RadioButton.setToolTip("The camera will be virtually attached to the tool, and rotate together with it")
    self.degreesOfFreedom6RadioButton.setChecked(True)
    self.degreesOfFreedomFormLayout.addRow(self.degreesOfFreedom6Label,self.degreesOfFreedom6RadioButton)
    
    # "Up Direction" Collapsible button
    self.upDirectionCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.upDirectionCollapsibleButton.title = "Up Direction"
    self.upDirectionCollapsibleButton.setVisible(False)
    self.cameraControlFormLayout.addRow(self.upDirectionCollapsibleButton)

    # Layout within the collapsible button
    self.upDirectionFormLayout = qt.QFormLayout(self.upDirectionCollapsibleButton)
    
    # Radio buttons for each of the anatomical directions
    self.upDirectionAnteriorLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionAnteriorLabel.setText("Anterior: ")
    self.upDirectionAnteriorRadioButton = qt.QRadioButton()
    self.upDirectionAnteriorRadioButton.setChecked(True)
    self.upDirectionFormLayout.addRow(self.upDirectionAnteriorLabel,self.upDirectionAnteriorRadioButton)
    
    self.upDirectionPosteriorLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionPosteriorLabel.setText("Posterior: ")
    self.upDirectionPosteriorRadioButton = qt.QRadioButton()
    self.upDirectionFormLayout.addRow(self.upDirectionPosteriorLabel,self.upDirectionPosteriorRadioButton)
    
    self.upDirectionRightLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionRightLabel.setText("Right: ")
    self.upDirectionRightRadioButton = qt.QRadioButton()
    self.upDirectionFormLayout.addRow(self.upDirectionRightLabel,self.upDirectionRightRadioButton)
    
    self.upDirectionLeftLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionLeftLabel.setText("Left: ")
    self.upDirectionLeftRadioButton = qt.QRadioButton()
    self.upDirectionFormLayout.addRow(self.upDirectionLeftLabel,self.upDirectionLeftRadioButton)
    
    self.upDirectionSuperiorLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionSuperiorLabel.setText("Superior: ")
    self.upDirectionSuperiorRadioButton = qt.QRadioButton()
    self.upDirectionFormLayout.addRow(self.upDirectionSuperiorLabel,self.upDirectionSuperiorRadioButton)
    
    self.upDirectionInferiorLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.upDirectionInferiorLabel.setText("Inferior: ")
    self.upDirectionInferiorRadioButton = qt.QRadioButton()
    self.upDirectionFormLayout.addRow(self.upDirectionInferiorLabel,self.upDirectionInferiorRadioButton)
    
    # "Target Model" Collapsible button
    self.targetModelCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.targetModelCollapsibleButton.title = "Target Model"
    self.targetModelCollapsibleButton.setVisible(False)
    self.cameraControlFormLayout.addRow(self.targetModelCollapsibleButton)

    # Layout within the collapsible button
    self.targetModelFormLayout = qt.QFormLayout(self.targetModelCollapsibleButton)
    
    # Selection of the target model
    self.targetModelLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.targetModelLabel.text = "Target model: "
    self.targetModelSelector = slicer.qMRMLNodeComboBox()
    self.targetModelSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.targetModelSelector.noneEnabled = False
    self.targetModelSelector.addEnabled = False
    self.targetModelSelector.removeEnabled = False
    self.targetModelSelector.setMRMLScene( slicer.mrmlScene )
    self.targetModelSelector.setToolTip("This model be the center of rotation using 3DOF Viewpoint (e.g. tumour)")
    self.targetModelFormLayout.addRow(self.targetModelLabel,self.targetModelSelector)
    
    # "Zoom" Collapsible button
    self.zoomCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.zoomCollapsibleButton.title = "Zoom"
    self.cameraControlFormLayout.addRow(self.zoomCollapsibleButton)

    # Layout within the collapsible button
    self.zoomFormLayout = qt.QFormLayout(self.zoomCollapsibleButton)
    
    # Camera viewing angle (perspective projection only)
    self.cameraViewAngleLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraViewAngleLabel.setText("View angle (degrees): ")
    self.cameraViewAngleSlider = slicer.qMRMLSliderWidget()
    self.cameraViewAngleSlider.minimum = self.cameraViewAngleMinDeg
    self.cameraViewAngleSlider.maximum = self.cameraViewAngleMaxDeg
    self.cameraViewAngleSlider.value = self.sliderViewAngleDefaultDeg
    self.cameraViewAngleSlider.singleStep = self.sliderSingleStepValue
    self.cameraViewAngleSlider.pageStep = self.sliderPageStepValue
    self.cameraViewAngleSlider.setToolTip("Make the current viewing target look larger/smaller.")
    self.zoomFormLayout.addRow(self.cameraViewAngleLabel,self.cameraViewAngleSlider)
    
    # Camera parallel scale (parallel projection only)
    self.cameraParallelScaleLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraParallelScaleLabel.setText("View scale: ")
    self.cameraParallelScaleLabel.setVisible(False)
    self.cameraParallelScaleSlider = slicer.qMRMLSliderWidget()
    self.cameraParallelScaleSlider.minimum = self.cameraParallelScaleMinDeg
    self.cameraParallelScaleSlider.maximum = self.cameraParallelScaleMaxDeg
    self.cameraParallelScaleSlider.value = self.sliderParallelScaleDefaultDeg
    self.cameraParallelScaleSlider.singleStep = self.sliderSingleStepValue
    self.cameraParallelScaleSlider.pageStep = self.sliderPageStepValue
    self.cameraParallelScaleSlider.setToolTip("Make the current viewing target look larger/smaller.")
    self.cameraParallelScaleSlider.setVisible(False)
    self.zoomFormLayout.addRow(self.cameraParallelScaleLabel,self.cameraParallelScaleSlider)
    
    # "Translation" Collapsible
    self.translationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.translationCollapsibleButton.title = "Translation"
    self.cameraControlFormLayout.addRow(self.translationCollapsibleButton)

    # Layout within the collapsible button
    self.translationFormLayout = qt.QFormLayout(self.translationCollapsibleButton)
    
    self.cameraXPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraXPosLabel.text = "Left/Right (mm): "
    self.cameraXPosSlider = slicer.qMRMLSliderWidget()
    self.cameraXPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraXPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraXPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraXPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraXPosSlider.pageStep = self.sliderPageStepValue
    self.translationFormLayout.addRow(self.cameraXPosLabel,self.cameraXPosSlider)
    
    self.cameraYPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraYPosLabel.setText("Down/Up (mm): ")
    self.cameraYPosSlider = slicer.qMRMLSliderWidget()
    self.cameraYPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraYPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraYPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraYPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraYPosSlider.pageStep = self.sliderPageStepValue
    self.translationFormLayout.addRow(self.cameraYPosLabel,self.cameraYPosSlider)
    
    self.cameraZPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraZPosLabel.setText("Front/Back (mm): ")
    self.cameraZPosSlider = slicer.qMRMLSliderWidget()
    self.cameraZPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraZPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraZPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraZPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraZPosSlider.pageStep = self.sliderPageStepValue
    self.translationFormLayout.addRow(self.cameraZPosLabel,self.cameraZPosSlider)
    
    # "Model Visibility" Collapsible
    self.modelVisibilityCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.modelVisibilityCollapsibleButton.title = "Model Visibility"
    self.cameraControlFormLayout.addRow(self.modelVisibilityCollapsibleButton)
    
    # Layout within the collapsible button
    self.modelVisibilityFormLayout = qt.QFormLayout(self.modelVisibilityCollapsibleButton)
    
    self.modelOnlyViewpointOnLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.modelOnlyViewpointOnLabel.text = "Model visible only for Viewpoint on: "
    self.modelOnlyViewpointOnSelector = slicer.qMRMLNodeComboBox()
    self.modelOnlyViewpointOnSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.modelOnlyViewpointOnSelector.noneEnabled = True
    self.modelOnlyViewpointOnSelector.addEnabled = False
    self.modelOnlyViewpointOnSelector.removeEnabled = False
    self.modelOnlyViewpointOnSelector.setMRMLScene( slicer.mrmlScene )
    self.modelOnlyViewpointOnSelector.setToolTip("This model be visible if Viewpoint mode is enabled, and invisible otherwise")
    self.modelVisibilityFormLayout.addRow(self.modelOnlyViewpointOnLabel,self.modelOnlyViewpointOnSelector)
    
    self.modelOnlyViewpointOffLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.modelOnlyViewpointOffLabel.text = "Model visible only for Viewpoint off: "
    self.modelOnlyViewpointOffSelector = slicer.qMRMLNodeComboBox()
    self.modelOnlyViewpointOffSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.modelOnlyViewpointOffSelector.noneEnabled = True
    self.modelOnlyViewpointOffSelector.addEnabled = False
    self.modelOnlyViewpointOffSelector.removeEnabled = False
    self.modelOnlyViewpointOffSelector.setMRMLScene( slicer.mrmlScene )
    self.modelOnlyViewpointOffSelector.setToolTip("This model be visible if Viewpoint Mode is disabled, and invisible otherwise")
    self.modelVisibilityFormLayout.addRow(self.modelOnlyViewpointOffLabel,self.modelOnlyViewpointOffSelector)
    
    # Camera parallel projection checkbox
    self.cameraParallelProjectionLabel = qt.QLabel()
    self.cameraParallelProjectionLabel.setText("Parallel Projection")
    self.cameraParallelProjectionCheckbox = qt.QCheckBox()
    self.cameraParallelProjectionCheckbox.setCheckState(0)
    self.cameraParallelProjectionCheckbox.setToolTip("If checked, render with parallel projection (box-shaped view). Otherwise render with perspective projection (cone-shaped view).")
    self.cameraControlFormLayout.addRow(self.cameraParallelProjectionLabel,self.cameraParallelProjectionCheckbox)
    
    # "Toggle Tool Point of View" button
    self.enableViewpointButton = qt.QPushButton()
    self.enableViewpointButton.setToolTip("The camera will continuously update its position so that it follows the tool.")
    self.enableViewpointButton.setText(self.enableViewpointButtonTextState0)
    self.cameraControlFormLayout.addRow(self.enableViewpointButton)
    
    #Connections
    self.enableViewpointButton.connect('clicked()', self.enableViewpointButtonPressed)
    self.cameraParallelProjectionCheckbox.connect('stateChanged(int)', self.toggleCameraParallelProjectionCheckboxPressed)
    self.cameraViewAngleSlider.connect('valueChanged(double)', self.logic.SetCameraViewAngleDeg)
    self.cameraParallelScaleSlider.connect('valueChanged(double)', self.logic.SetCameraParallelScale)
    self.cameraXPosSlider.connect('valueChanged(double)', self.logic.SetCameraXPosMm)
    self.cameraYPosSlider.connect('valueChanged(double)', self.logic.SetCameraYPosMm)
    self.cameraZPosSlider.connect('valueChanged(double)', self.logic.SetCameraZPosMm)
    self.upDirectionAnteriorRadioButton.connect('clicked()', self.changeUpToAnterior)
    self.upDirectionPosteriorRadioButton.connect('clicked()', self.changeUpToPosterior)
    self.upDirectionLeftRadioButton.connect('clicked()', self.changeUpToLeft)
    self.upDirectionRightRadioButton.connect('clicked()', self.changeUpToRight)
    self.upDirectionSuperiorRadioButton.connect('clicked()', self.changeUpToSuperior)
    self.upDirectionInferiorRadioButton.connect('clicked()', self.changeUpToInferior)
    self.degreesOfFreedom3RadioButton.connect('clicked()', self.changeInterfaceTo3DOFMode)
    self.degreesOfFreedom5RadioButton.connect('clicked()', self.changeInterfaceTo5DOFMode)
    self.degreesOfFreedom6RadioButton.connect('clicked()', self.changeInterfaceTo6DOFMode)
    
    # Add vertical spacer
    self.layout.addStretch(1)

  def enableViewpointButtonPressed(self):
    if self.enableViewpointButtonState == 0:
      self.logic.setCameraNode(self.cameraSelector.currentNode())
      self.logic.setTransformNode(self.transformSelector.currentNode())
      self.logic.setModelPOVOnNode(self.modelOnlyViewpointOnSelector.currentNode())
      self.logic.setModelPOVOffNode(self.modelOnlyViewpointOffSelector.currentNode())
      self.logic.setTargetModelNode(self.targetModelSelector.currentNode())
      self.logic.startViewpoint()
      self.disableSelectors()
      self.enableViewpointButtonState = 1
      self.enableViewpointButton.setText(self.enableViewpointButtonTextState1)
    else: # elif self.enableViewpointButtonState == 1
      self.logic.stopViewpoint()
      self.enableSelectors()
      self.enableViewpointButtonState = 0
      self.enableViewpointButton.setText(self.enableViewpointButtonTextState0)
      
  def enableSelectors(self):
      self.cameraSelector.enabled = True
      self.transformSelector.enabled = True
      self.modelOnlyViewpointOnSelector.enabled = True
      self.modelOnlyViewpointOffSelector.enabled = True
      self.targetModelSelector.enabled = True
  
  def disableSelectors(self):
      self.cameraSelector.enabled = False
      self.transformSelector.enabled = False
      self.modelOnlyViewpointOnSelector.enabled = False
      self.modelOnlyViewpointOffSelector.enabled = False
      self.targetModelSelector.enabled = False
      
  def toggleCameraParallelProjectionCheckboxPressed(self, dummyState): # dummyState is a tristate variable, we just want True/False
    state = self.cameraParallelProjectionCheckbox.isChecked()
    self.logic.SetCameraParallelProjection(state)
    if (state == False): # unchecked
      self.cameraParallelScaleLabel.setVisible(False)
      self.cameraParallelScaleSlider.setVisible(False)
      self.cameraViewAngleLabel.setVisible(True)
      self.cameraViewAngleSlider.setVisible(True)
    else: # checked
      self.cameraParallelScaleLabel.setVisible(True)
      self.cameraParallelScaleSlider.setVisible(True)
      self.cameraViewAngleLabel.setVisible(False)
      self.cameraViewAngleSlider.setVisible(False)

  def changeInterfaceTo3DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(True)
    self.targetModelCollapsibleButton.setVisible(True)
    self.logic.changeTo3DOFMode()

  def changeInterfaceTo5DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(True)
    self.targetModelCollapsibleButton.setVisible(False)
    self.logic.changeTo5DOFMode()

  def changeInterfaceTo6DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(False)
    self.targetModelCollapsibleButton.setVisible(False)
    self.logic.changeTo6DOFMode()
    
  def changeUpToAnterior(self):
    self.logic.SetUpInRAS([0,1,0])
    
  def changeUpToPosterior(self):
    self.logic.SetUpInRAS([0,-1,0])
    
  def changeUpToRight(self):
    self.logic.SetUpInRAS([1,0,0])
    
  def changeUpToLeft(self):
    self.logic.SetUpInRAS([-1,0,0])
    
  def changeUpToSuperior(self):
    self.logic.SetUpInRAS([0,0,1])
    
  def changeUpToInferior(self):
    self.logic.SetUpInRAS([0,0,-1])
    
#
# ViewpointLogic
#

class ViewpointLogic:
  def __init__(self):
    self.transformNode = None
    self.cameraNode = None
    self.modelPOVOnNode = None
    self.modelPOVOffNode = None
    
    self.currentlyInViewpoint = False
    self.transformNodeObserverTags = []
    
    self.cameraXPosMm =  0.0
    self.cameraYPosMm =  0.0
    self.cameraZPosMm =  0.0
    
    self.cameraParallelProjection = False # False = perspective, True = parallel. This is consistent with the
                                          # representation in the vtkCamera class and documentation
                                
    self.forcedUpDirection = False # False = if the user rotates the tool, then the camera rotates with it
                                   # True = the up direction is fixed according to this next variable:
    self.upInRAS = [0,1,0] # Anterior by default
    
    self.forcedTarget = False # False = camera points the direction the user is pointing it
                              # True = camera always points to the target model
    self.targetModelNode = None
    self.targetModelMiddleInRASMm = [0,0,0]
    
    self.cameraViewAngleDeg  =  30.0
    self.cameraParallelScale = 1.0

  def addObservers(self): # mostly copied from PositionErrorMapping.py in PLUS
    logging.debug("Adding observers...")
    transformModifiedEvent = 15000
    transformNode = self.transformNode
    while transformNode:
      logging.debug("Add observer to {0}".format(transformNode.GetName()))
      self.transformNodeObserverTags.append([transformNode, transformNode.AddObserver(transformModifiedEvent, self.onTransformModified)])
      transformNode = transformNode.GetParentTransformNode()
    logging.debug("Done adding observers")

  def removeObservers(self):
    logging.debug("Removing observers...")
    for nodeTagPair in self.transformNodeObserverTags:
      nodeTagPair[0].RemoveObserver(nodeTagPair[1])
    logging.debug("Done removing observers")
    
  def setTransformNode(self, transformNode):
    self.transformNode = transformNode
    
  def setCameraNode(self, cameraNode):
    self.cameraNode = cameraNode
    
  def setModelPOVOnNode(self, modelPOVOnNode):
    self.modelPOVOnNode = modelPOVOnNode
    
  def setModelPOVOffNode(self, modelPOVOffNode):
    self.modelPOVOffNode = modelPOVOffNode
    
  def setTargetModelNode(self, targetModelNode):
    self.targetModelNode = targetModelNode
    targetModel = targetModelNode.GetPolyData()
    targetModelBoundingBox = targetModel.GetBounds()
    # find the middle of the target model
    middleXInTumorMm = ( targetModelBoundingBox[0] + targetModelBoundingBox[1]) / 2
    middleYInTumorMm = ( targetModelBoundingBox[2] + targetModelBoundingBox[3]) / 2
    middleZInTumorMm = ( targetModelBoundingBox[4] + targetModelBoundingBox[5]) / 2
    middlePInTumorMm = 1 # represent as a homogeneous point
    middlePointInTumorMm4 = [middleXInTumorMm,middleYInTumorMm,middleZInTumorMm,middlePInTumorMm]
    middlePointInRASMm4 = [0,0,0,1]; # placeholder values
    targetModelNode.TransformPointToWorld(middlePointInTumorMm4,middlePointInRASMm4)
    # reduce dimensionality back to 3
    middlePointInRASMm3 = [middlePointInRASMm4[0], middlePointInRASMm4[1], middlePointInRASMm4[2]]
    self.targetModelMiddleInRASMm = middlePointInRASMm3
    
  def changeTo3DOFMode(self):
    self.forcedUpDirection = True
    self.forcedTarget = True
    
  def changeTo5DOFMode(self):
    self.forcedUpDirection = True
    self.forcedTarget = False
    
  def changeTo6DOFMode(self):
    self.forcedUpDirection = False
    self.forcedTarget = False

  def startViewpoint(self):
    logging.debug("Start Viewpoint Mode")
    if (self.transformNode and self.cameraNode):
      self.currentlyInViewpoint = True
      self.addObservers()
      self.updateViewpointCamera()
    else:
      logging.warning("A node is missing. Nothing will happen until the comboboxes have items selected.")
  
  def stopViewpoint(self):
    logging.debug("Stop Viewpoint Mode")
    if (self.modelPOVOnNode):
      modelPOVOnDisplayNode = self.modelPOVOnNode.GetDisplayNode()
      modelPOVOnDisplayNode.SetVisibility(False)
    if (self.modelPOVOffNode):
      modelPOVOffDisplayNode = self.modelPOVOffNode.GetDisplayNode()
      modelPOVOffDisplayNode.SetVisibility(True)
    self.currentlyInViewpoint = False
    self.removeObservers();

  def onTransformModified(self, observer, eventid):
    # no logging - it slows Slicer down a *lot*
    self.updateViewpointCamera()
    
  def SetCameraParallelProjection(self,newParallelProjectionState):
    logging.debug("SetCameraParallelProjection")
    self.cameraParallelProjection = newParallelProjectionState
    
  def SetCameraViewAngleDeg(self,valueDeg):
    logging.debug("SetCameraViewAngleDeg")
    self.cameraViewAngleDeg = valueDeg
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()
    
  def SetCameraParallelScale(self,newScale):
    logging.debug("SetCameraParallelScale")
    self.cameraParallelScale = newScale
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()
    
  def SetCameraXPosMm(self,valueMm):
    logging.debug("SetCameraXPosMm")
    self.cameraXPosMm = valueMm
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()

  def SetCameraYPosMm(self,valueMm):
    logging.debug("SetCameraYPosMm")
    self.cameraYPosMm = valueMm
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()

  def SetCameraZPosMm(self,valueMm):
    logging.debug("SetCameraZPosMm")
    self.cameraZPosMm = valueMm
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()
      
  def SetUpInRAS(self,vectorInRAS):
    logging.debug("SetUpInRAS")
    self.upInRAS = vectorInRAS
    if (self.currentlyInViewpoint == True):
      self.updateViewpointCamera()

  def updateViewpointCamera(self):
    # no logging - it slows Slicer down a *lot*
    
    # Need to set camera attributes according to the concatenated transform
    toolCameraToRASTransform = vtk.vtkGeneralTransform()
    self.transformNode.GetTransformToWorld(toolCameraToRASTransform)
    
    cameraOriginInRASMm = self.computeCameraOriginInRASMm(toolCameraToRASTransform)
    focalPointInRASMm = self.computeCameraFocalPointInRASMm(toolCameraToRASTransform)
    upDirectionInRAS = self.computeCameraUpDirectionInRAS(toolCameraToRASTransform,cameraOriginInRASMm,focalPointInRASMm)
    
    self.setCameraParameters(cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS)
    
    # model visibility
    if (self.modelPOVOffNode):
      modelPOVOffDisplayNode = self.modelPOVOffNode.GetDisplayNode()
      modelPOVOffDisplayNode.SetVisibility(False)
    if (self.modelPOVOnNode):
      modelPOVOnDisplayNode = self.modelPOVOnNode.GetDisplayNode()
      modelPOVOnDisplayNode.SetVisibility(True)
        
  def computeCameraOriginInRASMm(self, toolCameraToRASTransform):
    # Need to get camera origin and axes from camera coordinates into Slicer RAS coordinates
    cameraOriginInToolCameraMm = [self.cameraXPosMm,self.cameraYPosMm,self.cameraZPosMm]
    cameraOriginInRASMm = [0,0,0] # placeholder values
    toolCameraToRASTransform.TransformPoint(cameraOriginInToolCameraMm,cameraOriginInRASMm)
    return cameraOriginInRASMm

  def computeCameraFocalPointInRASMm(self, toolCameraToRASTransform):
    focalPointInRASMm = [0,0,0]; # placeholder values
    if (self.forcedTarget == True):
      focalPointInRASMm = self.targetModelMiddleInRASMm
    else:
      # camera distance depends on slider, but lies in -z (which is the direction that the camera is facing)
      focalPointInToolCameraMm = [self.cameraXPosMm,self.cameraYPosMm,self.cameraZPosMm-200] # The number 200 mm is arbitrary. TODO: Change so that this is the camera-tumor distance
      focalPointInRASMm = [0,0,0] # placeholder values    
      toolCameraToRASTransform.TransformPoint(focalPointInToolCameraMm,focalPointInRASMm)
    return focalPointInRASMm
    
  def computeCameraProjectionDirectionInRAS(self, cameraOriginInRASMm, focalPointInRASMm):
    math = vtk.vtkMath()
    directionFromOriginToFocalPointRAS = [0,0,0] # placeholder values
    math.Subtract(focalPointInRASMm,cameraOriginInRASMm,directionFromOriginToFocalPointRAS)
    math.Normalize(directionFromOriginToFocalPointRAS)
    numberDimensions = 3;
    lengthMm = math.Norm(directionFromOriginToFocalPointRAS,numberDimensions)
    epsilon = 0.0001
    if (lengthMm < epsilon):
      logging.warning("Warning: computeCameraProjectionDirectionInRAS() is computing a zero vector. Check target model? Using [0,0,-1] as target direction.")
      directionFromOriginToFocalPointRAS = [0,0,-1];
    return directionFromOriginToFocalPointRAS
    
  def computeCameraUpDirectionInRAS(self, toolCameraToRASTransform, cameraOriginInRASMm, focalPointInRASMm):
    upDirectionInRAS = [0,0,0] # placeholder values
    if (self.forcedUpDirection == True):
      math = vtk.vtkMath()
      # cross product of forwardDirectionInRAS vector with upInRAS vector is the rightDirectionInRAS vector
      upInRAS = self.upInRAS
      forwardDirectionInRAS = self.computeCameraProjectionDirectionInRAS(cameraOriginInRASMm, focalPointInRASMm)
      rightDirectionInRAS = [0,0,0] # placeholder values
      math.Cross(forwardDirectionInRAS,upInRAS,rightDirectionInRAS)
      numberDimensions = 3;
      lengthMm = math.Norm(rightDirectionInRAS,numberDimensions)
      epsilon = 0.0001
      if (lengthMm < epsilon): # must check for this case
        logging.warning("Warning: length of cross product in computeCameraUpDirectionInRAS is zero. Workaround used")
        backupUpDirectionInRAS = [1,1,1] # if the previous cross product was zero, then this shouldn't be
        math.Normalize(backupUpDirectionInRAS)
        upInRAS = backupUpDirectionInRAS
        math.Cross(forwardDirectionInRAS,upInRAS,rightDirectionInRAS)
      math.Normalize(rightDirectionInRAS)
      # now compute the cross product between the rightDirectionInRAS and forwardDirectionInRAS directions to get a corrected up vector
      upDirectionInRAS = [0,0,0] # placeholder values
      math.Cross(rightDirectionInRAS,forwardDirectionInRAS,upDirectionInRAS)
      math.Normalize(upDirectionInRAS)
    else:
      upDirectionInToolCamera = [0,1,0] # standard up direction in OpenGL
      dummyPoint = [0,0,0] # Needed by the TransformVectorAtPoint function
      toolCameraToRASTransform.TransformVectorAtPoint(dummyPoint,upDirectionInToolCamera,upDirectionInRAS)
    return upDirectionInRAS

  def setCameraParameters(self,cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS):
    camera = self.cameraNode.GetCamera()
    if (self.cameraParallelProjection == False):
      camera.SetViewAngle(self.cameraViewAngleDeg)
    elif (self.cameraParallelProjection == True):
      camera.SetParallelScale(self.cameraParallelScale)
    else:
      logging.error("Error in Viewpoint: cameraParallelProjection is not 0 or 1. No projection mode has been set! No updates are being performed.")
      return
    camera.SetParallelProjection(self.cameraParallelProjection)
    camera.SetRoll(180) # appears to be the default value for a camera in Slicer
    camera.SetPosition(cameraOriginInRASMm)
    camera.SetFocalPoint(focalPointInRASMm)
    camera.SetViewUp(upDirectionInRAS)
    self.cameraNode.ResetClippingRange() # without this line, some objects do not appear in the 3D view
