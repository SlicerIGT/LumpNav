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
    
    self.toggleTrackViewButtonState = 0
    self.toggleTrackViewButtonTextState0 = "Enable Track View Mode"
    self.toggleTrackViewButtonTextState1 = "Disable Track View Mode"
    
    # FOLLOW
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
    
    self.toggleFollowButtonState = 0
    self.toggleFollowButtonTextState0 = "Enable Follow Mode"
    self.toggleFollowButtonTextState1 = "Disable Follow Mode"

  def setup(self):
    # TODO: The following line is strictly for debug purposes, should be removed when this module is done
    slicer.tvwidget = self

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
    
    # Camera combobox
    self.cameraLabel = qt.QLabel()
    self.cameraLabel.setText("Scene Camera (for track view): ")
    self.cameraSelector = slicer.qMRMLNodeComboBox()
    self.cameraSelector.nodeTypes = ( ("vtkMRMLCameraNode"), "" )
    self.cameraSelector.noneEnabled = False
    self.cameraSelector.addEnabled = False
    self.cameraSelector.removeEnabled = False
    self.cameraSelector.setMRMLScene( slicer.mrmlScene )
    self.cameraSelector.setToolTip("Pick the camera which should be moved, e.g. 'Default Scene Camera'")
    self.trackViewParametersFormLayout.addRow(self.cameraLabel, self.cameraSelector)

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
    
    self.viewLabel = qt.QLabel()
    self.viewLabel.setText("Scene Camera: ")
    self.viewSelector = slicer.qMRMLNodeComboBox()
    self.viewSelector.nodeTypes = ( ("vtkMRMLViewNode"), "" )
    self.viewSelector.noneEnabled = False
    self.viewSelector.addEnabled = False
    self.viewSelector.removeEnabled = False
    self.viewSelector.setMRMLScene( slicer.mrmlScene )
    self.viewSelector.setToolTip("Pick the view which should be adjusted, e.g. 'View1'")
    self.followParametersFormLayout.addRow(self.viewLabel, self.viewSelector)
    
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
    self.adjustXCheckbox.setCheckState(2)
    self.adjustXCheckbox.setToolTip("If checked, adjust the camera so that it aligns with the target model along the x axis.")
    self.followParametersFormLayout.addRow(self.adjustXLabel,self.adjustXCheckbox)
    
    self.adjustYLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustYLabel.setText("Adjust Along Camera Y")
    self.adjustYCheckbox = qt.QCheckBox()
    self.adjustYCheckbox.setCheckState(2)
    self.adjustXCheckbox.setToolTip("If checked, adjust the camera so that it aligns with the target model along the y axis.")
    self.followParametersFormLayout.addRow(self.adjustYLabel,self.adjustYCheckbox)
    
    self.adjustZLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.adjustZLabel.setText("Adjust Along Camera Z")
    self.adjustZCheckbox = qt.QCheckBox()
    self.adjustZCheckbox.setCheckState(0)
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
    self.toggleFollowButton.connect('clicked()', self.toggleFollowButtonPressed)
    
    # Add vertical spacer
    self.layout.addStretch(1)

  def toggleTrackViewButtonPressed(self):
    if self.toggleTrackViewButtonState == 0:
      self.logic.setCameraNode(self.cameraSelector.currentNode())
      self.logic.setTransformNode(self.transformSelector.currentNode())
      self.logic.setModelPOVOnNode(self.modelOnlyViewpointOnSelector.currentNode())
      self.logic.setModelPOVOffNode(self.modelOnlyViewpointOffSelector.currentNode())
      self.logic.setTargetModelNode(self.targetModelSelector.currentNode())
      self.logic.startTrackView()
      if (self.logic.isCurrentModeTRACKVIEW()):
        self.disableTrackViewSelectors()
        self.disableFollowAllWidgets()
        self.toggleTrackViewButtonState = 1
        self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState1)
    else: # elif self.toggleTrackViewButtonState == 1
      self.logic.stopTrackView()
      if (self.logic.isCurrentModeOFF()):
        self.enableTrackViewSelectors()
        self.enableFollowAllWidgets()
        self.toggleTrackViewButtonState = 0
        self.toggleTrackViewButton.setText(self.toggleTrackViewButtonTextState0)
    
  def toggleFollowButtonPressed(self):
    if self.toggleFollowButtonState == 0:
      self.updateFollowLogicParameters()
      self.logic.startFollow()
      if (self.logic.isCurrentModeFOLLOW()):
        self.disableFollowParameterWidgets()
        self.disableTrackViewAllWidgets()
        self.toggleFollowButtonState = 1
        self.toggleFollowButton.setText(self.toggleFollowButtonTextState1)
    else:
      self.logic.stopFollow()
      if (self.logic.isCurrentModeOFF()):
        self.enableFollowParameterWidgets()
        self.enableTrackViewAllWidgets()
        self.toggleFollowButtonState = 0
        self.toggleFollowButton.setText(self.toggleFollowButtonTextState0)
      
  # SPECIFIC TO TRACK-VIEW
  
  def enableTrackViewSelectors(self):
    self.cameraSelector.enabled = True
    self.transformSelector.enabled = True
    self.modelOnlyViewpointOnSelector.enabled = True
    self.modelOnlyViewpointOffSelector.enabled = True
    self.targetModelSelector.enabled = True
  
  def disableTrackViewSelectors(self):
    self.cameraSelector.enabled = False
    self.transformSelector.enabled = False
    self.modelOnlyViewpointOnSelector.enabled = False
    self.modelOnlyViewpointOffSelector.enabled = False
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
    
  # SPECIFIC TO FOLLOW
  
  def updateFollowLogicParameters(self):
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
      
  def enableFollowParameterWidgets(self):
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
  
  def disableFollowParameterWidgets(self):
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
    # global
    self.currentMode = 0
    self.currentModeOFF = 0
    self.currentModeTRACKVIEW = 1
    self.currentModeFOLLOW = 2
    
    # TRACK VIEW
    self.transformNode = None
    self.cameraNode = None
    self.modelPOVOnNode = None
    self.modelPOVOffNode = None
    
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
    
    # FOLLOW
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
    
    self.modelTargetPositionViewport = [0,0,0]
    
  def getCurrentMode(self):
    return self.currentMode
    
  def isCurrentModeOFF(self):
    return (self.currentMode == self.currentModeOFF)
    
  def isCurrentModeTRACKVIEW(self):
    return (self.currentMode == self.currentModeTRACKVIEW)
    
  def isCurrentModeFOLLOW(self):
    return (self.currentMode == self.currentModeFOLLOW)
    
  # TRACK VIEW
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

  def startTrackView(self):
    logging.debug("Start Viewpoint Mode")
    if (self.currentMode != self.currentModeOFF):
      logging.error("Cannot activate viewpoint until the current mode is set to off!")
      return
      
    if (not self.cameraNode):
      logging.warning("A node is missing. Nothing will happen until the comboboxes have items selected.")
      return
      
    if (not self.transformNode):
      logging.warning("A node is missing. Nothing will happen until the comboboxes have items selected.")
      return
  
    self.currentMode = self.currentModeTRACKVIEW
    self.addObservers()
    self.updateViewpointCamera()
  
  def stopTrackView(self):
    logging.debug("Stop Viewpoint Mode")
    if (self.currentMode != self.currentModeTRACKVIEW):
      logging.error("StopTrackView was called, but viewpoint mode is not TRACKVIEW. No action performed.")
      return
    if (self.modelPOVOnNode):
      modelPOVOnDisplayNode = self.modelPOVOnNode.GetDisplayNode()
      modelPOVOnDisplayNode.SetVisibility(False)
    if (self.modelPOVOffNode):
      modelPOVOffDisplayNode = self.modelPOVOffNode.GetDisplayNode()
      modelPOVOffDisplayNode.SetVisibility(True)
    self.currentMode = self.currentModeOFF
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
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.updateViewpointCamera()
    
  def SetCameraParallelScale(self,newScale):
    logging.debug("SetCameraParallelScale")
    self.cameraParallelScale = newScale
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.updateViewpointCamera()
    
  def SetCameraXPosMm(self,valueMm):
    logging.debug("SetCameraXPosMm")
    self.cameraXPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.updateViewpointCamera()

  def SetCameraYPosMm(self,valueMm):
    logging.debug("SetCameraYPosMm")
    self.cameraYPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.updateViewpointCamera()

  def SetCameraZPosMm(self,valueMm):
    logging.debug("SetCameraZPosMm")
    self.cameraZPosMm = valueMm
    if (self.currentMode == self.currentModeTRACKVIEW):
      self.updateViewpointCamera()
      
  def SetUpInRAS(self,vectorInRAS):
    logging.debug("SetUpInRAS")
    self.upInRAS = vectorInRAS
    if (self.currentMode == self.currentModeTRACKVIEW):
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
    # Parallel (a.k.a. orthographic) / perspective projection mode is stored in the view node.
    # Change it in the view node instead of directly in the camera VTK object
    # (if we changed the projection mode in the camera VTK object then the next time the camera is updated from the view node
    # the rendering mode is reset to the value stored in the view node).
    viewNode = slicer.mrmlScene.GetNodeByID(self.cameraNode.GetActiveTag())
    viewNodeParallelProjection = (viewNode.GetRenderMode() == slicer.vtkMRMLViewNode.Orthographic)
    if viewNodeParallelProjection != self.cameraParallelProjection:
      viewNode.SetRenderMode(slicer.vtkMRMLViewNode.Orthographic if self.cameraParallelProjection else slicer.vtkMRMLViewNode.Perspective)

    camera.SetRoll(180) # appears to be the default value for a camera in Slicer
    camera.SetPosition(cameraOriginInRASMm)
    camera.SetFocalPoint(focalPointInRASMm)
    camera.SetViewUp(upDirectionInRAS)
    self.cameraNode.ResetClippingRange() # without this line, some objects do not appear in the 3D view

  # FOLLOW
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
    
  def startFollow(self):
    if (self.currentMode != self.currentModeOFF):
      logging.error("Viewpoints is already active! Can't activate follow mode until the current mode is off!")
      return
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
    
    self.currentMode = self.currentModeFOLLOW
    
  def stopFollow(self):
    logging.debug("stopFollow")
    if (self.currentMode != self.currentModeFOLLOW):
      logging.error("StopFollow was called, but viewpoint mode is not FOLLOW. No action performed.")
      return
    self.currentMode = self.currentModeOFF
    
  def update(self):
    if (self.currentMode != self.currentModeFOLLOW):
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
    