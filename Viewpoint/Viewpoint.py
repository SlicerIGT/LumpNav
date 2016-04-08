from __main__ import vtk, qt, ctk, slicer
import logging
import time

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

    # TRACK VIEW
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
    
    self.checkStateUNCHECKED = 0
    self.checkStateCHECKED = 2
    
    self.toggleTrackViewButtonTextState0 = "Enable Track View Mode"
    self.toggleTrackViewButtonTextState1 = "Disable Track View Mode"
    
    # FOLLOW
    self.sliderMultiplier = 100.0
    self.rangeSliderMaximum = self.sliderMultiplier
    self.rangeSliderMinimum = -self.sliderMultiplier
    self.rangeSliderMaximumValueDefault = self.sliderMultiplier
    self.rangeSliderMinimumValueDefault = -self.sliderMultiplier
    
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
    
    self.toggleFollowButtonTextState0 = "Enable Follow Mode"
    self.toggleFollowButtonTextState1 = "Disable Follow Mode"

  def setup(self):
    # TODO: The following line is strictly for debug purposes, should be removed when this module is done
    slicer.tvwidget = self
    
    # Collapsible buttons
    self.viewCollapsibleButton = ctk.ctkCollapsibleButton()
    self.viewCollapsibleButton.text = "View Selection"
    self.layout.addWidget(self.viewCollapsibleButton)

    # Layout within the collapsible button
    self.viewFormLayout = qt.QFormLayout(self.viewCollapsibleButton)
    
    self.viewLabel = qt.QLabel()
    self.viewLabel.setText("Scene Camera: ")
    self.viewSelector = slicer.qMRMLNodeComboBox()
    self.viewSelector.nodeTypes = ( ("vtkMRMLViewNode"), "" )
    self.viewSelector.noneEnabled = True
    self.viewSelector.addEnabled = False
    self.viewSelector.removeEnabled = False
    self.viewSelector.setMRMLScene( slicer.mrmlScene )
    self.viewSelector.setToolTip("Pick the view which should be adjusted, e.g. 'View1'")
    self.viewFormLayout.addRow(self.viewLabel, self.viewSelector)    

    # Collapsible buttons
    self.trackViewParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.trackViewParametersCollapsibleButton.text = "Parameters for Track View"
    self.layout.addWidget(self.trackViewParametersCollapsibleButton)

    # Layout within the collapsible button
    self.trackViewParametersFormLayout = qt.QFormLayout(self.trackViewParametersCollapsibleButton)
    
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
    self.trackViewParametersFormLayout.addRow(self.transformLabel, self.transformSelector)

    # "Camera Control" Collapsible
    self.cameraControlCollapsibleButton = ctk.ctkCollapsibleButton()
    self.cameraControlCollapsibleButton.text = "Camera Control"
    self.trackViewParametersFormLayout.addWidget(self.cameraControlCollapsibleButton)

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
    self.degreesOfFreedom6RadioButton.setChecked(self.checkStateCHECKED)
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
    self.upDirectionAnteriorRadioButton.setChecked(self.checkStateCHECKED)
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
    
    # Camera parallel projection checkbox
    self.cameraParallelProjectionLabel = qt.QLabel()
    self.cameraParallelProjectionLabel.setText("Parallel Projection")
    self.cameraParallelProjectionCheckbox = qt.QCheckBox()
    self.cameraParallelProjectionCheckbox.setCheckState(self.checkStateUNCHECKED)
    self.cameraParallelProjectionCheckbox.setToolTip("If checked, render with parallel projection (box-shaped view). Otherwise render with perspective projection (cone-shaped view).")
    self.cameraControlFormLayout.addRow(self.cameraParallelProjectionLabel,self.cameraParallelProjectionCheckbox)
    
    # "Toggle Tool Point of View" button
    self.toggleTrackViewButton = qt.QPushButton()
    self.toggleTrackViewButton.setToolTip("The camera will continuously update its position so that it follows the tool.")
    self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState0)
    self.layout.addWidget(self.toggleTrackViewButton)
    
    # FOLLOW
    
    # Collapsible buttons
    self.followParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    self.followParametersCollapsibleButton.text = "Parameters for Follow"
    self.layout.addWidget(self.followParametersCollapsibleButton)

    # Layout within the collapsible button
    self.followParametersFormLayout = qt.QFormLayout(self.followParametersCollapsibleButton)
    
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
    self.followParametersFormLayout.addRow(self.modelLabel, self.modelSelector)
    
    self.safeZoneXRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneXRangeLabel.text = "Safe Zone (Viewport X percentage): "
    self.safeZoneXRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneXRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneXRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneXRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneXRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    self.followParametersFormLayout.addRow(self.safeZoneXRangeLabel,self.safeZoneXRangeSlider)
    
    self.safeZoneYRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneYRangeLabel.setText("Safe Zone (Viewport Y percentage): ")
    self.safeZoneYRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneYRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneYRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneYRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneYRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    self.followParametersFormLayout.addRow(self.safeZoneYRangeLabel,self.safeZoneYRangeSlider)
    
    self.safeZoneZRangeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.safeZoneZRangeLabel.setText("Safe Zone (Viewport Z percentage): ")
    self.safeZoneZRangeSlider = slicer.qMRMLRangeWidget()
    self.safeZoneZRangeSlider.maximum = self.rangeSliderMaximum
    self.safeZoneZRangeSlider.minimum = self.rangeSliderMinimum
    self.safeZoneZRangeSlider.maximumValue = self.rangeSliderMaximumValueDefault
    self.safeZoneZRangeSlider.minimumValue = self.rangeSliderMinimumValueDefault
    self.followParametersFormLayout.addRow(self.safeZoneZRangeLabel,self.safeZoneZRangeSlider)
    
    self.adjustXLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustXLabel.setText("Adjust Along Camera X")
    self.adjustXCheckbox = qt.QCheckBox()
    self.adjustXCheckbox.setCheckState(self.checkStateCHECKED)
    self.adjustXCheckbox.setToolTip("If checked, adjust the camera so that it aligns with the target model along the x axis.")
    self.followParametersFormLayout.addRow(self.adjustXLabel,self.adjustXCheckbox)
    
    self.adjustYLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustYLabel.setText("Adjust Along Camera Y")
    self.adjustYCheckbox = qt.QCheckBox()
    self.adjustYCheckbox.setCheckState(self.checkStateCHECKED)
    self.adjustXCheckbox.setToolTip("If checked, adjust the camera so that it aligns with the target model along the y axis.")
    self.followParametersFormLayout.addRow(self.adjustYLabel,self.adjustYCheckbox)
    
    self.adjustZLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustZLabel.setText("Adjust Along Camera Z")
    self.adjustZCheckbox = qt.QCheckBox()
    self.adjustZCheckbox.setCheckState(self.checkStateUNCHECKED)
    self.adjustXCheckbox.setToolTip("If checked, adjust the camera so that it aligns with the target model along the z axis.")
    self.followParametersFormLayout.addRow(self.adjustZLabel,self.adjustZCheckbox)
    
    self.updateRateLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.updateRateLabel.setText("Update rate (seconds): ")
    self.updateRateSlider = slicer.qMRMLSliderWidget()
    self.updateRateSlider.minimum = self.updateRateMinSeconds
    self.updateRateSlider.maximum = self.updateRateMaxSeconds
    self.updateRateSlider.value = self.updateRateDefaultSeconds
    self.updateRateSlider.singleStep = self.sliderSingleStepValue
    self.updateRateSlider.pageStep = self.sliderPageStepValue
    self.updateRateSlider.setToolTip("The rate at which the view will be checked and updated.")
    self.followParametersFormLayout.addRow(self.updateRateLabel,self.updateRateSlider)
    
    self.timeUnsafeToAdjustLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeUnsafeToAdjustLabel.setText("Time Unsafe to Adjust (seconds): ")
    self.timeUnsafeToAdjustSlider = slicer.qMRMLSliderWidget()
    self.timeUnsafeToAdjustSlider.minimum = self.timeUnsafeToAdjustMinSeconds
    self.timeUnsafeToAdjustSlider.maximum = self.timeUnsafeToAdjustMaxSeconds
    self.timeUnsafeToAdjustSlider.value = self.timeUnsafeToAdjustDefaultSeconds
    self.timeUnsafeToAdjustSlider.singleStep = self.sliderSingleStepValue
    self.timeUnsafeToAdjustSlider.pageStep = self.sliderPageStepValue
    self.timeUnsafeToAdjustSlider.setToolTip("The length of time in which the model must be in the unsafe zone before the camera is adjusted.")
    self.followParametersFormLayout.addRow(self.timeUnsafeToAdjustLabel,self.timeUnsafeToAdjustSlider)
    
    self.timeAdjustToRestLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeAdjustToRestLabel.setText("Time Adjust to Rest (seconds): ")
    self.timeAdjustToRestSlider = slicer.qMRMLSliderWidget()
    self.timeAdjustToRestSlider.minimum = self.timeAdjustToRestMinSeconds
    self.timeAdjustToRestSlider.maximum = self.timeAdjustToRestMaxSeconds
    self.timeAdjustToRestSlider.value = self.timeAdjustToRestDefaultSeconds
    self.timeAdjustToRestSlider.singleStep = self.sliderSingleStepValue
    self.timeAdjustToRestSlider.pageStep = self.sliderPageStepValue
    self.timeAdjustToRestSlider.setToolTip("The length of time an adjustment takes.")
    self.followParametersFormLayout.addRow(self.timeAdjustToRestLabel,self.timeAdjustToRestSlider)
    
    self.timeRestToSafeLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.timeRestToSafeLabel.setText("Time Rest to Safe (seconds): ")
    self.timeRestToSafeSlider = slicer.qMRMLSliderWidget()
    self.timeRestToSafeSlider.minimum = self.timeRestToSafeMinSeconds
    self.timeRestToSafeSlider.maximum = self.timeRestToSafeMaxSeconds
    self.timeRestToSafeSlider.value = self.timeRestToSafeDefaultSeconds
    self.timeRestToSafeSlider.singleStep = self.sliderSingleStepValue
    self.timeRestToSafeSlider.pageStep = self.sliderPageStepValue
    self.timeRestToSafeSlider.setToolTip("The length of time after an adjustment that the camera remains motionless.")
    self.followParametersFormLayout.addRow(self.timeRestToSafeLabel,self.timeRestToSafeSlider)
    
    self.toggleFollowButton = qt.QPushButton()
    self.toggleFollowButton.setToolTip("The camera will continuously update its position so that it follows the model.")
    self.toggleFollowButton.setText(self.toggleFollowButtonTextState0)
    self.layout.addWidget(self.toggleFollowButton)
    
    #Connections
    self.toggleTrackViewButton.connect('clicked()', self.toggleTrackViewButtonPressed)
    self.cameraParallelProjectionCheckbox.connect('stateChanged(int)', self.toggleCameraParallelProjectionCheckboxPressed)
    self.cameraViewAngleSlider.connect('valueChanged(double)', self.changeCameraViewAngleDeg)
    self.cameraParallelScaleSlider.connect('valueChanged(double)', self.changeCameraParallelScale)
    self.cameraXPosSlider.connect('valueChanged(double)', self.changeCameraXPosMm)
    self.cameraYPosSlider.connect('valueChanged(double)', self.changeCameraYPosMm)
    self.cameraZPosSlider.connect('valueChanged(double)', self.changeCameraZPosMm)
    self.upDirectionAnteriorRadioButton.connect('clicked()', self.changeUpToAnterior)
    self.upDirectionPosteriorRadioButton.connect('clicked()', self.changeUpToPosterior)
    self.upDirectionLeftRadioButton.connect('clicked()', self.changeUpToLeft)
    self.upDirectionRightRadioButton.connect('clicked()', self.changeUpToRight)
    self.upDirectionSuperiorRadioButton.connect('clicked()', self.changeUpToSuperior)
    self.upDirectionInferiorRadioButton.connect('clicked()', self.changeUpToInferior)
    self.degreesOfFreedom3RadioButton.connect('clicked()', self.changeInterfaceTo3DOFMode)
    self.degreesOfFreedom5RadioButton.connect('clicked()', self.changeInterfaceTo5DOFMode)
    self.degreesOfFreedom6RadioButton.connect('clicked()', self.changeInterfaceTo6DOFMode)
    self.toggleFollowButton.connect('clicked()', self.toggleFollowButtonPressed)
    self.viewSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.changeViewNode)
    
    # disable all parameter widgets initially, because view selector will be "none"
    self.disableFollowAllWidgets()
    self.disableTrackViewAllWidgets()
    
    # Add vertical spacer
    self.layout.addStretch(1)
    
  def changeViewNode(self):
    newViewNode = self.viewSelector.currentNode()
    if (newViewNode):
      self.logic.changeCurrentViewNode(newViewNode)
    self.updateWidgets()
      
  def updateWidgets(self):
    if (not self.logic.currentInstance):
      self.disableFollowAllWidgets()
      self.disableTrackViewAllWidgets()
      return;
    # assume all widgets are to be enabled, disable as necessary
    self.enableFollowAllWidgets()
    self.enableTrackViewAllWidgets()
    self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState0)
    self.toggleFollowButton.setText(self.toggleFollowButtonTextState0)
    
    if (self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeFOLLOW):
      self.disableFollowParameterWidgets()
      self.disableTrackViewAllWidgets()
      self.toggleFollowButton.setText(self.toggleFollowButtonTextState1)
      self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState0)
    elif (self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeTRACKVIEW):
      #self.disableTrackViewParameterWidgets()
      self.disableFollowAllWidgets()
      self.toggleFollowButton.setText(self.toggleFollowButtonTextState0)
      self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState1)
      
    # Track View parameters
    self.transformSelector.setCurrentNode(self.logic.currentInstance.trackViewTransformNode)
    self.degreesOfFreedom6RadioButton.setChecked(self.checkStateUNCHECKED)
    self.degreesOfFreedom5RadioButton.setChecked(self.checkStateUNCHECKED)
    self.degreesOfFreedom3RadioButton.setChecked(self.checkStateUNCHECKED)
    if (self.logic.currentInstance.trackViewForcedUpDirection and self.logic.currentInstance.trackViewForcedTarget):
      self.degreesOfFreedom3RadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewForcedUpDirection):
      self.degreesOfFreedom5RadioButton.setChecked(self.checkStateCHECKED)
    else:
      self.degreesOfFreedom6RadioButton.setChecked(self.checkStateCHECKED)
    self.upDirectionAnteriorRadioButton.setChecked(self.checkStateUNCHECKED)
    self.upDirectionPosteriorRadioButton.setChecked(self.checkStateUNCHECKED)
    self.upDirectionRightRadioButton.setChecked(self.checkStateUNCHECKED)
    self.upDirectionLeftRadioButton.setChecked(self.checkStateUNCHECKED)
    self.upDirectionSuperiorRadioButton.setChecked(self.checkStateUNCHECKED)
    self.upDirectionInferiorRadioButton.setChecked(self.checkStateUNCHECKED)
    if (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASAnterior)):
      self.upDirectionRightRadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASLeft)):
      self.upDirectionLeftRadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASAnterior)):
      self.upDirectionAnteriorRadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASPosterior)):
      self.upDirectionPosteriorRadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASSuperior)):
      self.upDirectionSuperiorRadioButton.setChecked(self.checkStateCHECKED)
    elif (self.logic.currentInstance.trackViewIsUpDirectionEqualTo(self.logic.currentInstance.trackViewUpDirectionRASInferior)):
      self.upDirectionInferiorRadioButton.setChecked(self.checkStateCHECKED)
    self.targetModelSelector.setCurrentNode(self.logic.currentInstance.trackViewTargetModelNode)
    self.cameraViewAngleSlider.value = self.logic.currentInstance.trackViewCameraViewAngleDeg
    self.cameraParallelScaleSlider.value = self.logic.currentInstance.trackViewCameraParallelScale
    self.cameraXPosSlider.value = self.logic.currentInstance.trackViewCameraXPosMm
    self.cameraYPosSlider.value = self.logic.currentInstance.trackViewCameraYPosMm
    self.cameraZPosSlider.value = self.logic.currentInstance.trackViewCameraZPosMm
    if (self.logic.currentInstance.trackViewCameraParallelProjection):
      self.cameraParallelProjectionCheckbox.setCheckState(self.checkStateCHECKED)
    else:
      self.cameraParallelProjectionCheckbox.setCheckState(self.checkStateUNCHECKED)
    # Follow parameters
    self.modelSelector.setCurrentNode(self.logic.currentInstance.followModelNode)
    self.safeZoneXRangeSlider.maximumValue = self.logic.currentInstance.followSafeXMaximumNormalizedViewport*self.sliderMultiplier
    self.safeZoneXRangeSlider.minimumValue = self.logic.currentInstance.followSafeXMinimumNormalizedViewport*self.sliderMultiplier
    self.safeZoneYRangeSlider.maximumValue = self.logic.currentInstance.followSafeYMaximumNormalizedViewport*self.sliderMultiplier
    self.safeZoneYRangeSlider.minimumValue = self.logic.currentInstance.followSafeYMinimumNormalizedViewport*self.sliderMultiplier
    self.safeZoneZRangeSlider.maximumValue = self.logic.currentInstance.followSafeZMaximumNormalizedViewport*self.sliderMultiplier
    self.safeZoneZRangeSlider.minimumValue = self.logic.currentInstance.followSafeZMinimumNormalizedViewport*self.sliderMultiplier
    self.updateRateSlider.value = self.logic.currentInstance.followUpdateRateSeconds
    self.timeUnsafeToAdjustSlider.value = self.logic.currentInstance.followTimeUnsafeToAdjustMaximumSeconds
    self.timeAdjustToRestSlider.value = self.logic.currentInstance.followTimeAdjustToRestMaximumSeconds
    self.timeRestToSafeSlider.value = self.logic.currentInstance.followTimeRestToSafeMaximumSeconds
    if (self.logic.currentInstance.followAdjustX):
      self.adjustXCheckbox.setCheckState(self.checkStateCHECKED)
    else:
      self.adjustXCheckbox.setCheckState(self.checkStateUNCHECKED)
    if (self.logic.currentInstance.followAdjustY):
      self.adjustYCheckbox.setCheckState(self.checkStateCHECKED)
    else:
      self.adjustYCheckbox.setCheckState(self.checkStateUNCHECKED)
    if (self.logic.currentInstance.followAdjustZ):
      self.adjustZCheckbox.setCheckState(self.checkStateCHECKED)
    else:
      self.adjustZCheckbox.setCheckState(self.checkStateUNCHECKED)

  def toggleTrackViewButtonPressed(self):
    if self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeOFF:
      self.updateTrackViewParameters();
      self.logic.currentInstance.trackViewStart()
    elif self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeTRACKVIEW:
      self.logic.currentInstance.trackViewStop()
    else:
      logging.error("Error: Unhandled case in toggleTrackViewButtonPressed. Current state is neither off nor track view.")
    self.updateWidgets()
    
  def toggleFollowButtonPressed(self):
    if self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeOFF:
      self.updateFollowLogicParameters()
      self.logic.currentInstance.followStart()
    elif self.logic.currentInstance.currentMode == self.logic.currentInstance.currentModeFOLLOW:
      self.logic.currentInstance.followStop()
    else:
      logging.error("Error: Unhandled case in toggleFollowButtonPressed. Current state is neither off nor follow.")
    self.updateWidgets()
      
  # SPECIFIC TO TRACK-VIEW
  
  def updateTrackViewParameters(self):
    if (self.viewSelector.currentNode()):
      self.logic.currentInstance.setViewNode(self.viewSelector.currentNode())
    if (self.transformSelector.currentNode()):
      self.logic.currentInstance.trackViewSetTransformNode(self.transformSelector.currentNode())
    if (self.targetModelSelector.currentNode()):
      self.logic.currentInstance.trackViewSetTargetModelNode(self.targetModelSelector.currentNode())
  
  def enableTrackViewSelectors(self):
    self.transformSelector.enabled = True
    self.targetModelSelector.enabled = True
  
  def disableTrackViewSelectors(self):
    self.transformSelector.enabled = False
    self.targetModelSelector.enabled = False
  
  def enableTrackViewParameterWidgets(self):
    self.enableTrackViewSelectors()
    self.degreesOfFreedom3RadioButton.enabled = True
    self.degreesOfFreedom5RadioButton.enabled = True
    self.degreesOfFreedom6RadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.upDirectionAnteriorRadioButton.enabled = True
    self.cameraViewAngleSlider.enabled = True
    self.cameraParallelScaleSlider.enabled = True
    self.cameraXPosSlider.enabled = True
    self.cameraYPosSlider.enabled = True
    self.cameraZPosSlider.enabled = True
    self.cameraParallelProjectionCheckbox.enabled = True
  
  def disableTrackViewParameterWidgets(self):
    self.disableTrackViewSelectors()
    self.degreesOfFreedom3RadioButton.enabled = False
    self.degreesOfFreedom5RadioButton.enabled = False
    self.degreesOfFreedom6RadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.upDirectionAnteriorRadioButton.enabled = False
    self.cameraViewAngleSlider.enabled = False
    self.cameraParallelScaleSlider.enabled = False
    self.cameraXPosSlider.enabled = False
    self.cameraYPosSlider.enabled = False
    self.cameraZPosSlider.enabled = False
    self.cameraParallelProjectionCheckbox.enabled = False
    
  def enableTrackViewAllWidgets(self):
    self.enableTrackViewParameterWidgets()
    self.toggleTrackViewButton.enabled = True
  
  def disableTrackViewAllWidgets(self):
    self.disableTrackViewParameterWidgets()
    self.toggleTrackViewButton.enabled = False
      
  def toggleCameraParallelProjectionCheckboxPressed(self, dummyState): # dummyState is a tristate variable, we just want True/False
    state = self.cameraParallelProjectionCheckbox.isChecked()
    self.logic.currentInstance.trackViewSetCameraParallelProjection(state)
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

  def changeCameraViewAngleDeg(self, val):
    self.logic.currentInstance.trackViewSetCameraViewAngleDeg(val)
    
  def changeCameraParallelScale(self, val):
    self.logic.currentInstance.trackViewSetCameraParallelScale(val)
    
  def changeCameraXPosMm(self, val):
    self.logic.currentInstance.trackViewSetCameraXPosMm(val)
    
  def changeCameraYPosMm(self, val):
    self.logic.currentInstance.trackViewSetCameraYPosMm(val)
    
  def changeCameraZPosMm(self, val):
    self.logic.currentInstance.trackViewSetCameraZPosMm(val)
    
  def changeInterfaceTo3DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(True)
    self.targetModelCollapsibleButton.setVisible(True)
    self.logic.currentInstance.trackViewChangeTo3DOFMode()

  def changeInterfaceTo5DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(True)
    self.targetModelCollapsibleButton.setVisible(False)
    self.logic.currentInstance.trackViewChangeTo5DOFMode()

  def changeInterfaceTo6DOFMode(self):
    self.upDirectionCollapsibleButton.setVisible(False)
    self.targetModelCollapsibleButton.setVisible(False)
    self.logic.currentInstance.trackViewChangeTo6DOFMode()
    
  def changeUpToAnterior(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASAnterior)
    
  def changeUpToPosterior(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASPosterior)
    
  def changeUpToRight(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASRight)
    
  def changeUpToLeft(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASLeft)
    
  def changeUpToSuperior(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASSuperior)
    
  def changeUpToInferior(self):
    self.logic.currentInstance.trackViewSetTrackViewUpDirectionRAS(self.logic.currentInstance.trackViewUpDirectionRASInferior)
    
  # SPECIFIC TO FOLLOW
  
  def updateFollowLogicParameters(self):
    self.logic.currentInstance.setFollowModelNode(self.modelSelector.currentNode())
    self.logic.currentInstance.setViewNode(self.viewSelector.currentNode())
    self.logic.currentInstance.setSafeXMaximum(self.safeZoneXRangeSlider.maximumValue/self.sliderMultiplier)
    self.logic.currentInstance.setSafeXMinimum(self.safeZoneXRangeSlider.minimumValue/self.sliderMultiplier)
    self.logic.currentInstance.setSafeYMaximum(self.safeZoneYRangeSlider.maximumValue/self.sliderMultiplier)
    self.logic.currentInstance.setSafeYMinimum(self.safeZoneYRangeSlider.minimumValue/self.sliderMultiplier)
    self.logic.currentInstance.setSafeZMaximum(self.safeZoneZRangeSlider.maximumValue/self.sliderMultiplier)
    self.logic.currentInstance.setSafeZMinimum(self.safeZoneZRangeSlider.minimumValue/self.sliderMultiplier)
    self.logic.currentInstance.setAdjustX(self.adjustXCheckbox.isChecked())
    self.logic.currentInstance.setAdjustY(self.adjustYCheckbox.isChecked())
    self.logic.currentInstance.setAdjustZ(self.adjustZCheckbox.isChecked())
    self.logic.currentInstance.setUpdateRateSeconds(self.updateRateSlider.value)
    self.logic.currentInstance.setTimeUnsafeToAdjustMaximumSeconds(self.timeUnsafeToAdjustSlider.value)
    self.logic.currentInstance.setTimeAdjustToRestMaximumSeconds(self.timeAdjustToRestSlider.value)
    self.logic.currentInstance.setTimeRestToSafeMaximumSeconds(self.timeRestToSafeSlider.value)
      
  def enableFollowParameterWidgets(self):
    self.modelSelector.enabled = True
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
  
  def disableFollowParameterWidgets(self):
    self.modelSelector.enabled = False
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
    
  def enableFollowAllWidgets(self):
    self.enableFollowParameterWidgets()
    self.toggleFollowButton.enabled = True
    
  def disableFollowAllWidgets(self):
    self.disableFollowParameterWidgets()
    self.toggleFollowButton.enabled = False
  
#
# ViewpointLogic
#

class ViewpointLogic:

  def __init__(self):
    self.nodeInstanceDictionary = {}
    self.currentInstance = None
    
  def changeCurrentViewNode(self, viewNode):
    if (viewNode == None):
      logging.error("viewNode given to Viewpoint logic is None. Aborting operation.")
      return
    if (not viewNode in self.nodeInstanceDictionary):
      self.nodeInstanceDictionary[viewNode] = ViewpointInstance()
    self.currentInstance = self.nodeInstanceDictionary[viewNode]

#
# Viewpoint Instance
# Each view is associated with its own viewpoint instance,
# this allows support of multiple views with their own
# viewpoint parameters and settings.
#

class ViewpointInstance:
  def __init__(self):
    # global
    self.viewNode = None
    
    self.currentMode = 0
    self.currentModeOFF = 0
    self.currentModeTRACKVIEW = 1
    self.currentModeFOLLOW = 2
    
    # TRACK VIEW
    self.trackViewTransformNode = None
    self.trackViewTransformNodeObserverTags = []
    self.trackViewCameraXPosMm =  0.0
    self.trackViewCameraYPosMm =  0.0
    self.trackViewCameraZPosMm =  0.0
    
    self.trackViewCameraParallelProjection = False # False = perspective, True = parallel. This is consistent with the
                                          # representation in the vtkCamera class and documentation
                                
    self.trackViewForcedUpDirection = False # False = if the user rotates the tool, then the camera rotates with it
                                   # True = the up direction is fixed according to this next variable:
    self.trackViewUpDirectionRAS = [0,1,0] # Anterior by default
    self.trackViewUpDirectionRASRight = [1,0,0]
    self.trackViewUpDirectionRASLeft = [-1,0,0]
    self.trackViewUpDirectionRASAnterior = [0,1,0]
    self.trackViewUpDirectionRASPosterior = [0,-1,0]
    self.trackViewUpDirectionRASSuperior = [0,0,1]
    self.trackViewUpDirectionRASInferior = [0,0,-1]
    
    self.trackViewForcedTarget = False # False = camera points the direction the user is pointing it
                              # True = camera always points to the target model
    self.trackViewTargetModelNode = None
    self.trackViewTargetModelMiddleInRASMm = [0,0,0]
    
    self.trackViewCameraViewAngleDeg  =  30.0
    self.trackViewCameraParallelScale = 1.0
    
    # FOLLOW
    #inputs
    self.followSafeXMinimumNormalizedViewport = -1.0
    self.followSafeXMaximumNormalizedViewport = 1.0
    self.followSafeYMinimumNormalizedViewport = -1.0
    self.followSafeYMaximumNormalizedViewport = 1.0
    self.followSafeZMinimumNormalizedViewport = -1.0
    self.followSafeZMaximumNormalizedViewport = 1.0
    
    self.followAdjustX = True
    self.followAdjustY = True
    self.followAdjustZ = False
    
    self.followModelNode = None
    
    self.followTimeUnsafeToAdjustMaximumSeconds = 1
    self.followTimeAdjustToRestMaximumSeconds = 0.2
    self.followTimeRestToSafeMaximumSeconds = 1
    
    self.followUpdateRateSeconds = 0.02
    
    # current state
    self.followSystemTimeAtLastUpdateSeconds = 0
    self.followTimeInStateSeconds = 0
    self.followState = 0 # 0 = in safe zone (initial state), 1 = in unsafe zone, 2 = adjusting, 3 = resting
    self.followStateSAFE = 0
    self.followStateUNSAFE = 1
    self.followStateADJUST = 2
    self.followStateREST = 3
    self.followBaseCameraTranslationRas = [0,0,0]
    self.followBaseCameraPositionRas = [0,0,0]
    self.followBaseCameraFocalPointRas = [0,0,0]
    self.followModelInSafeZone = True 
    
    self.followModelTargetPositionViewport = [0,0,0]
    
  def setViewNode(self, node):
    self.viewNode = node
    
  def getCurrentMode(self):
    return self.currentMode
    
  def isCurrentModeOFF(self):
    return (self.currentMode == self.currentModeOFF)
    
  def isCurrentModeTRACKVIEW(self):
    return (self.currentMode == self.currentModeTRACKVIEW)
    
  def isCurrentModeFOLLOW(self):
    return (self.currentMode == self.currentModeFOLLOW)
    
  # TRACK VIEW

  def trackViewStart(self):
    logging.debug("Start Viewpoint Mode")
    if (self.currentMode != self.currentModeOFF):
      logging.error("Cannot activate viewpoint until the current mode is set to off!")
      return
      
    if (not self.viewNode):
      logging.warning("A node is missing. Nothing will happen until the comboboxes have items selected.")
      return
      
    if (not self.trackViewTransformNode):
      logging.warning("Transform node is missing. Nothing will happen until a transform node is provided as input.")
      return
      
    if (self.trackViewForcedTarget and not self.trackViewTargetModelNode):
      logging.error("Error in trackViewSetTargetModelNode: No targetModelNode provided as input when forced target is set. Check input parameters.")
      return
  
    self.currentMode = self.currentModeTRACKVIEW
    self.trackViewAddObservers()
    self.trackViewUpdate()
  
  def trackViewStop(self):
    logging.debug("Stop Viewpoint Mode")
    if (self.currentMode != self.currentModeTRACKVIEW):
      logging.error("trackViewStop was called, but viewpoint mode is not TRACKVIEW. No action performed.")
      return
    self.currentMode = self.currentModeOFF
    self.trackViewRemoveObservers();

  def trackViewUpdate(self):
    # no logging - it slows Slicer down a *lot*
    
    # Need to set camera attributes according to the concatenated transform
    toolCameraToRASTransform = vtk.vtkGeneralTransform()
    self.trackViewTransformNode.GetTransformToWorld(toolCameraToRASTransform)
    
    cameraOriginInRASMm = self.trackViewComputeCameraOriginInRASMm(toolCameraToRASTransform)
    focalPointInRASMm = self.trackViewComputeCameraFocalPointInRASMm(toolCameraToRASTransform)
    upDirectionInRAS = self.trackViewComputeCameraUpDirectionInRAS(toolCameraToRASTransform,cameraOriginInRASMm,focalPointInRASMm)
    
    self.trackViewSetCameraParameters(cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS)
    
  def trackViewAddObservers(self): # mostly copied from PositionErrorMapping.py in PLUS
    logging.debug("Adding observers...")
    transformModifiedEvent = 15000
    transformNode = self.trackViewTransformNode
    while transformNode:
      logging.debug("Add observer to {0}".format(transformNode.GetName()))
      self.trackViewTransformNodeObserverTags.append([transformNode, transformNode.AddObserver(transformModifiedEvent, self.trackViewOnTransformModified)])
      transformNode = transformNode.GetParentTransformNode()
    logging.debug("Done adding observers")

  def trackViewRemoveObservers(self):
    logging.debug("Removing observers...")
    for nodeTagPair in self.trackViewTransformNodeObserverTags:
      nodeTagPair[0].RemoveObserver(nodeTagPair[1])
    logging.debug("Done removing observers")

  def trackViewOnTransformModified(self, observer, eventid):
    # no logging - it slows Slicer down a *lot*
    self.trackViewUpdate()
    
  def trackViewSetTransformNode(self, transformNode):
    self.trackViewTransformNode = transformNode
    
  def trackViewSetTargetModelNode(self, targetModelNode):
    if (self.trackViewForcedTarget and not targetModelNode):
      logging.error("Error in trackViewSetTargetModelNode: No targetModelNode provided as input. Check input parameters.")
      return
    self.trackViewTargetModelNode = targetModelNode
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
    self.trackViewTargetModelMiddleInRASMm = middlePointInRASMm3
    
  def trackViewChangeTo3DOFMode(self):
    self.trackViewForcedUpDirection = True
    self.trackViewForcedTarget = True
    
  def trackViewChangeTo5DOFMode(self):
    self.trackViewForcedUpDirection = True
    self.trackViewForcedTarget = False
    
  def trackViewChangeTo6DOFMode(self):
    self.trackViewForcedUpDirection = False
    self.trackViewForcedTarget = False
  
  def trackViewIsUpDirectionEqualTo(self, compareDirection):
    if (compareDirection[0]*self.trackViewUpDirectionRAS[0]+
        compareDirection[1]*self.trackViewUpDirectionRAS[1]+
        compareDirection[2]*self.trackViewUpDirectionRAS[2] > 0.9999): # dot product close to 1
      return True;
    return False;
    
  def trackViewSetCameraParallelProjection(self,newParallelProjectionState):
    logging.debug("trackViewSetCameraParallelProjection")
    self.trackViewCameraParallelProjection = newParallelProjectionState
    
  def trackViewSetCameraViewAngleDeg(self,valueDeg):
    logging.debug("trackViewSetCameraViewAngleDeg")
    self.trackViewCameraViewAngleDeg = valueDeg
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()
    
  def trackViewSetCameraParallelScale(self,newScale):
    logging.debug("trackViewSetCameraParallelScale")
    self.trackViewCameraParallelScale = newScale
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()
    
  def trackViewSetCameraXPosMm(self,valueMm):
    logging.debug("trackViewSetCameraXPosMm")
    self.trackViewCameraXPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()

  def trackViewSetCameraYPosMm(self,valueMm):
    logging.debug("trackViewSetCameraYPosMm")
    self.trackViewCameraYPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()

  def trackViewSetCameraZPosMm(self,valueMm):
    logging.debug("trackViewSetCameraZPosMm")
    self.trackViewCameraZPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()
      
  def trackViewSetTrackViewUpDirectionRAS(self,vectorInRAS):
    logging.debug("trackViewSetTrackViewUpDirectionRAS")
    self.trackViewUpDirectionRAS = vectorInRAS
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.trackViewUpdate()
        
  def trackViewComputeCameraOriginInRASMm(self, toolCameraToRASTransform):
    # Need to get camera origin and axes from camera coordinates into Slicer RAS coordinates
    cameraOriginInToolCameraMm = [self.trackViewCameraXPosMm,self.trackViewCameraYPosMm,self.trackViewCameraZPosMm]
    cameraOriginInRASMm = [0,0,0] # placeholder values
    toolCameraToRASTransform.TransformPoint(cameraOriginInToolCameraMm,cameraOriginInRASMm)
    return cameraOriginInRASMm

  def trackViewComputeCameraFocalPointInRASMm(self, toolCameraToRASTransform):
    focalPointInRASMm = [0,0,0]; # placeholder values
    if (self.trackViewForcedTarget == True):
      focalPointInRASMm = self.trackViewTargetModelMiddleInRASMm
    else:
      # camera distance depends on slider, but lies in -z (which is the direction that the camera is facing)
      focalPointInToolCameraMm = [self.trackViewCameraXPosMm,self.trackViewCameraYPosMm,self.trackViewCameraZPosMm-200] # The number 200 mm is arbitrary. TODO: Change so that this is the camera-tumor distance
      focalPointInRASMm = [0,0,0] # placeholder values    
      toolCameraToRASTransform.TransformPoint(focalPointInToolCameraMm,focalPointInRASMm)
    return focalPointInRASMm
    
  def trackViewComputeCameraProjectionDirectionInRAS(self, cameraOriginInRASMm, focalPointInRASMm):
    math = vtk.vtkMath()
    directionFromOriginToFocalPointRAS = [0,0,0] # placeholder values
    math.Subtract(focalPointInRASMm,cameraOriginInRASMm,directionFromOriginToFocalPointRAS)
    math.Normalize(directionFromOriginToFocalPointRAS)
    numberDimensions = 3;
    lengthMm = math.Norm(directionFromOriginToFocalPointRAS,numberDimensions)
    epsilon = 0.0001
    if (lengthMm < epsilon):
      logging.warning("Warning: trackViewComputeCameraProjectionDirectionInRAS() is computing a zero vector. Check target model? Using [0,0,-1] as target direction.")
      directionFromOriginToFocalPointRAS = [0,0,-1];
    return directionFromOriginToFocalPointRAS
    
  def trackViewComputeCameraUpDirectionInRAS(self, toolCameraToRASTransform, cameraOriginInRASMm, focalPointInRASMm):
    upDirectionInRAS = [0,0,0] # placeholder values
    if (self.trackViewForcedUpDirection == True):
      math = vtk.vtkMath()
      # cross product of forwardDirectionInRAS vector with upInRAS vector is the rightDirectionInRAS vector
      upInRAS = self.trackViewUpDirectionRAS
      forwardDirectionInRAS = self.trackViewComputeCameraProjectionDirectionInRAS(cameraOriginInRASMm, focalPointInRASMm)
      rightDirectionInRAS = [0,0,0] # placeholder values
      math.Cross(forwardDirectionInRAS,upInRAS,rightDirectionInRAS)
      numberDimensions = 3;
      lengthMm = math.Norm(rightDirectionInRAS,numberDimensions)
      epsilon = 0.0001
      if (lengthMm < epsilon): # must check for this case
        logging.warning("Warning: length of cross product in trackViewComputeCameraUpDirectionInRAS is zero. Workaround used")
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

  def trackViewSetCameraParameters(self,cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    camera = cameraNode.GetCamera()
    if (self.trackViewCameraParallelProjection == False):
      camera.SetViewAngle(self.trackViewCameraViewAngleDeg)
    elif (self.trackViewCameraParallelProjection == True):
      camera.SetParallelScale(self.trackViewCameraParallelScale)
    else:
      logging.error("Error in Viewpoint: cameraParallelProjection is not 0 or 1. No projection mode has been set! No updates are being performed.")
      return
    # Parallel (a.k.a. orthographic) / perspective projection mode is stored in the view node.
    # Change it in the view node instead of directly in the camera VTK object
    # (if we changed the projection mode in the camera VTK object then the next time the camera is updated from the view node
    # the rendering mode is reset to the value stored in the view node).
    viewNode = slicer.mrmlScene.GetNodeByID(cameraNode.GetActiveTag())
    viewNodeParallelProjection = (viewNode.GetRenderMode() == slicer.vtkMRMLViewNode.Orthographic)
    if viewNodeParallelProjection != self.trackViewCameraParallelProjection:
      viewNode.SetRenderMode(slicer.vtkMRMLViewNode.Orthographic if self.trackViewCameraParallelProjection else slicer.vtkMRMLViewNode.Perspective)

    camera.SetRoll(180) # appears to be the default value for a camera in Slicer
    camera.SetPosition(cameraOriginInRASMm)
    camera.SetFocalPoint(focalPointInRASMm)
    camera.SetViewUp(upDirectionInRAS)
    cameraNode.ResetClippingRange() # without this line, some objects do not appear in the 3D view

  # FOLLOW
    
  def followStart(self):
    if (self.currentMode != self.currentModeOFF):
      logging.error("Viewpoints is already active! Can't activate follow mode until the current mode is off!")
      return
    if not self.viewNode:
      logging.warning("View node not set. Will not proceed until view node is selected.")
      return
    if not self.followModelNode:
      logging.warning("Model node not set. Will not proceed until model node is selected.")
      return
    self.setModelTargetPositionViewport()
    self.followSystemTimeAtLastUpdateSeconds = time.time()
    nextUpdateTimerMilliseconds = self.followUpdateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.followUpdate)
    
    self.currentMode = self.currentModeFOLLOW
    
  def followStop(self):
    logging.debug("followStop")
    if (self.currentMode != self.currentModeFOLLOW):
      logging.error("followStop was called, but viewpoint mode is not FOLLOW. No action performed.")
      return
    self.currentMode = self.currentModeOFF
    
  def followUpdate(self):
    if (self.currentMode != self.currentModeFOLLOW):
      return
      
    deltaTimeSeconds = time.time() - self.followSystemTimeAtLastUpdateSeconds
    self.followSystemTimeAtLastUpdateSeconds = time.time()
    
    self.followTimeInStateSeconds = self.followTimeInStateSeconds + deltaTimeSeconds

    self.updateModelInSafeZone()
    self.applyStateMachine()
      
    nextUpdateTimerMilliseconds = self.followUpdateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.followUpdate)

  def applyStateMachine(self):
    if (self.followState == self.followStateUNSAFE and self.followModelInSafeZone):
      self.followState = self.followStateSAFE
      self.followTimeInStateSeconds = 0
    if (self.followState == self.followStateSAFE and not self.followModelInSafeZone):
      self.followState = self.followStateUNSAFE
      self.followTimeInStateSeconds = 0
    if (self.followState == self.followStateUNSAFE and self.followTimeInStateSeconds >= self.followTimeUnsafeToAdjustMaximumSeconds):
      self.setCameraTranslationParameters()
      self.followState = self.followStateADJUST
      self.followTimeInStateSeconds = 0
    if (self.followState == self.followStateADJUST):
      self.translateCamera()
      if (self.followTimeInStateSeconds >= self.followTimeAdjustToRestMaximumSeconds):
        self.followState = self.followStateREST
        self.followTimeInStateSeconds = 0
    if (self.followState == self.followStateREST and self.followTimeInStateSeconds >= self.followTimeRestToSafeMaximumSeconds):
      self.followState = self.followStateSAFE
      self.followTimeInStateSeconds = 0
      
  def updateModelInSafeZone(self):
    if (self.followState == self.followStateADJUST or
        self.followState == self.followStateREST):
      return
    pointsRas = self.getModelCurrentBoundingBoxPointsRas()
    # Assume we are safe, until shown otherwise
    foundSafe = True
    for pointRas in pointsRas:
      coordsNormalizedViewport = self.convertRasToViewport(pointRas)
      XNormalizedViewport = coordsNormalizedViewport[0]
      YNormalizedViewport = coordsNormalizedViewport[1]
      ZNormalizedViewport = coordsNormalizedViewport[2]
      if ( XNormalizedViewport > self.followSafeXMaximumNormalizedViewport or 
           XNormalizedViewport < self.followSafeXMinimumNormalizedViewport or
           YNormalizedViewport > self.followSafeYMaximumNormalizedViewport or 
           YNormalizedViewport < self.followSafeYMinimumNormalizedViewport or
           ZNormalizedViewport > self.followSafeZMaximumNormalizedViewport or 
           ZNormalizedViewport < self.followSafeZMinimumNormalizedViewport ):
        foundSafe = False
        break
    self.followModelInSafeZone = foundSafe

  def setModelTargetPositionViewport(self):
    self.followModelTargetPositionViewport = [(self.followSafeXMinimumNormalizedViewport + self.followSafeXMaximumNormalizedViewport)/2.0,
                                        (self.followSafeYMinimumNormalizedViewport + self.followSafeYMaximumNormalizedViewport)/2.0,
                                        (self.followSafeZMinimumNormalizedViewport + self.followSafeZMaximumNormalizedViewport)/2.0]
    
  def setCameraTranslationParameters(self):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraPosRas = [0,0,0]
    cameraNode.GetPosition(cameraPosRas)
    self.followBaseCameraPositionRas = cameraPosRas
    cameraFocRas = [0,0,0]
    cameraNode.GetFocalPoint(cameraFocRas)
    self.followBaseCameraFocalPointRas = cameraFocRas
    
    # find the translation in RAS
    modelCurrentPositionCamera = self.getModelCurrentCenterCamera()
    modelTargetPositionCamera = self.getModelTargetPositionCamera()
    cameraTranslationCamera = [0,0,0]
    if self.followAdjustX:
      cameraTranslationCamera[0] = modelCurrentPositionCamera[0] - modelTargetPositionCamera[0]
    if self.followAdjustY:
      cameraTranslationCamera[1] = modelCurrentPositionCamera[1] - modelTargetPositionCamera[1]
    if self.followAdjustZ:
      cameraTranslationCamera[2] = modelCurrentPositionCamera[2] - modelTargetPositionCamera[2]
    self.followBaseCameraTranslationRas = self.convertVectorCameraToRas(cameraTranslationCamera)
  
  def translateCamera(self):
    # linear interpolation between base and target positions, based on the timer
    weightTarget = 1 # default value
    if (self.followTimeAdjustToRestMaximumSeconds != 0):
      weightTarget = self.followTimeInStateSeconds / self.followTimeAdjustToRestMaximumSeconds
    if (weightTarget > 1):
      weightTarget = 1
    cameraNewPositionRas = [0,0,0]
    cameraNewFocalPointRas = [0,0,0]
    for i in xrange(0,3):
      translation = weightTarget * self.followBaseCameraTranslationRas[i]
      cameraNewPositionRas[i] = translation + self.followBaseCameraPositionRas[i]
      cameraNewFocalPointRas[i] = translation + self.followBaseCameraFocalPointRas[i]
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraNode.SetPosition(cameraNewPositionRas)
    cameraNode.SetFocalPoint(cameraNewFocalPointRas)
    self.resetCameraClippingRange()
    
  def getModelCurrentCenterRas(self):
    modelBoundsRas = [0,0,0,0,0,0]
    self.followModelNode.GetRASBounds(modelBoundsRas)
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
    self.followModelNode.GetRASBounds(boundsRas)
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
    return self.convertViewportToRas(self.followModelTargetPositionViewport)
    
  def getModelTargetPositionCamera(self):
    modelTargetPositionRas = self.getModelTargetPositionRas()
    modelTargetPositionCamera = self.convertPointRasToCamera(modelTargetPositionRas)
    return modelTargetPositionCamera
    
  def getCameraNode(self, viewName):
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
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.WorldToView(x,y,z)
    return [x.get(), y.get(), z.get()]
    
  def convertViewportToRas(self, positionViewport):
    x = vtk.mutable(positionViewport[0])
    y = vtk.mutable(positionViewport[1])
    z = vtk.mutable(positionViewport[2])
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ViewToWorld(x,y,z)
    return [x.get(), y.get(), z.get()]
    
  def convertPointRasToCamera(self, positionRas):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraObj = cameraNode.GetCamera()
    modelViewTransform = cameraObj.GetModelViewTransformObject()
    positionRasHomog = [positionRas[0], positionRas[1], positionRas[2], 1] # convert to homogeneous
    positionCamHomog = [0,0,0,1] # to be filled in
    modelViewTransform.MultiplyPoint(positionRasHomog, positionCamHomog)
    positionCam = [positionCamHomog[0], positionCamHomog[1], positionCamHomog[2]] # convert from homogeneous
    return positionCam

  def convertVectorCameraToRas(self, positionCam):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
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
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ResetCameraClippingRange()

  def getThreeDWidgetIndex(self):
    if (not self.viewNode):
      logging.error("Error in getThreeDWidgetIndex: No View node selected. Returning 0.");
      return 0
    layoutManager = slicer.app.layoutManager()
    for threeDViewIndex in xrange(layoutManager.threeDViewCount):
      threeDViewNode = layoutManager.threeDWidget(threeDViewIndex).threeDView().mrmlViewNode()
      if (threeDViewNode == self.viewNode):
        return threeDViewIndex
    logging.error("Error in getThreeDWidgetIndex: Can't find the index. Selected View does not exist? Returning 0.");
    return 0
    
  def setSafeXMinimum(self, val):
    self.followSafeXMinimumNormalizedViewport = val
    
  def setSafeXMaximum(self, val):
    self.followSafeXMaximumNormalizedViewport = val
    
  def setSafeYMinimum(self, val):
    self.followSafeYMinimumNormalizedViewport = val
    
  def setSafeYMaximum(self, val):
    self.followSafeYMaximumNormalizedViewport = val    

  def setSafeZMinimum(self, val):
    self.followSafeZMinimumNormalizedViewport = val
    
  def setSafeZMaximum(self, val):
    self.followSafeZMaximumNormalizedViewport = val
    
  def setAdjustX(self, val):
    self.followAdjustX = val
    
  def setAdjustY(self, val):
    self.followAdjustY = val
    
  def setAdjustZ(self, val):
    self.followAdjustZ = val
    
  def setAdjustXTrue(self):
    self.followAdjustX = True
    
  def setAdjustXFalse(self):
    self.followAdjustX = False
    
  def setAdjustYTrue(self):
    self.followAdjustY = True
    
  def setAdjustYFalse(self):
    self.followAdjustY = False
    
  def setAdjustZTrue(self):
    self.followAdjustZ = True
    
  def setAdjustZFalse(self):
    self.followAdjustZ = False
    
  def setTimeUnsafeToAdjustMaximumSeconds(self, val):
    self.followTimeUnsafeToAdjustMaximumSeconds = val
    
  def setTimeAdjustToRestMaximumSeconds(self, val):
    self.followTimeAdjustToRestMaximumSeconds = val
    
  def setTimeRestToSafeMaximumSeconds(self, val):
    self.followTimeRestToSafeMaximumSeconds = val
    
  def setUpdateRateSeconds(self, val):
    self.followUpdateRateSeconds = val
    
  def setFollowModelNode(self, node):
    self.followModelNode = node
