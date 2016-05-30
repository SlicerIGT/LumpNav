import os
import unittest
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# BreachWarningLight
#

class BreachWarningLight(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "BreachWarningLight" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    parent.contributors = ["Kaci Carter (Queen's University, PERK Lab)"] 
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    parent.acknowledgementText = """
    Queen's University, PERK lab, Funding: NSERC CGSM
    """

#
# BreachWarningLightWidget
#

class BreachWarningLightWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """  
  
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    # Instantiate and connect widgets ...

    self.logic = BreachWarningLightLogic()
    
    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # input volume selector
    #
    self.breachWarningSelector = slicer.qMRMLNodeComboBox()
    self.breachWarningSelector.nodeTypes = ( ("vtkMRMLBreachWarningNode"), "" )
    self.breachWarningSelector.selectNodeUponCreation = True
    self.breachWarningSelector.addEnabled = False
    self.breachWarningSelector.removeEnabled = False
    self.breachWarningSelector.noneEnabled = False
    self.breachWarningSelector.showHidden = False
    self.breachWarningSelector.showChildNodeTypes = False
    self.breachWarningSelector.setMRMLScene( slicer.mrmlScene )
    self.breachWarningSelector.setToolTip( "Pick the breach warning node to observe." )
    parametersFormLayout.addRow("Breach warning node: ", self.breachWarningSelector)

    #
    # output volume selector
    #
    self.connectorSelector = slicer.qMRMLNodeComboBox()
    self.connectorSelector.nodeTypes = ( ("vtkMRMLIGTLConnectorNode"), "" )
    self.connectorSelector.selectNodeUponCreation = True
    self.connectorSelector.addEnabled = False
    self.connectorSelector.removeEnabled = False
    self.connectorSelector.noneEnabled = False
    self.connectorSelector.showHidden = False
    self.connectorSelector.showChildNodeTypes = False
    self.connectorSelector.setMRMLScene( slicer.mrmlScene )
    self.connectorSelector.setToolTip( "Pick the OpenIGTLink connector node to send light control commands to" )
    parametersFormLayout.addRow("Connector: ", self.connectorSelector)

    #
    # marginSizeMm value
    #
    self.marginSizeMmSliderWidget = ctk.ctkSliderWidget()
    self.marginSizeMmSliderWidget.singleStep = 0.1
    self.marginSizeMmSliderWidget.minimum = 0
    self.marginSizeMmSliderWidget.maximum = 10
    self.marginSizeMmSliderWidget.value = 2.0
    self.marginSizeMmSliderWidget.setToolTip("Set the desired margin size in mm. Light pattern will indicate 'good position' if the distance is smaller than this value.")
    parametersFormLayout.addRow("Margin size (mm)", self.marginSizeMmSliderWidget)
    
    #
    # check box to trigger taking screen shots for later use in tutorials
    #
    self.enableLightFeedbackFlagCheckBox = qt.QCheckBox()
    self.enableLightFeedbackFlagCheckBox.checked = 0
    self.enableLightFeedbackFlagCheckBox.setToolTip("If checked, then light pattern will be updated whenever the breach warning state is changed.")
    parametersFormLayout.addRow("Enable light feedback", self.enableLightFeedbackFlagCheckBox)

    # connections
    self.enableLightFeedbackFlagCheckBox.connect('stateChanged(int)', self.setEnableLightFeedback)
    self.marginSizeMmSliderWidget.connect('valueChanged(double)', self.setMarginChanged)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def setMarginChanged(self, dummy):
    self.logic.setMarginSizeMm(self.marginSizeMmSliderWidget.value)
    
  def setEnableLightFeedback(self, enable):
    if enable:
      self.setMarginChanged(0)
      self.logic.startLightFeedback(self.breachWarningSelector.currentNode(), self.connectorSelector.currentNode())
    else:
      self.logic.stopLightFeedback()

#
# BreachWarningLightLogic
#

class BreachWarningLightLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    
    self.breachWarningNode = None
    self.observerTags = []
    self.connectorNode = None
    self.marginSizeMm = 2
    
    self.lightSetCommand = slicer.vtkSlicerOpenIGTLinkCommand()
    self.lightSetCommand.SetCommandName('SendText')
    self.lightSetCommand.SetCommandAttribute('DeviceId','BreachWarningLight')
    self.lightSetCommand.SetCommandTimeoutSec(1.0)
    
    # If the last light set command is still in progress then we set the new command text
    # in this variable. When the command is completed then we send the command
    self.queuedLightSetCommandText = None

  def addObservers(self):
    if self.breachWarningNode:
      print "Add observer to {0}".format(self.breachWarningNode.GetName())
      self.observerTags.append([self.breachWarningNode, self.breachWarningNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onBreachWarningNodeModified)])
      self.observerTags.append([self.lightSetCommand, self.lightSetCommand.AddObserver(self.lightSetCommand.CommandCompletedEvent, self.onLightSetCommandCompleted)])

  def removeObservers(self):
    print "Remove observers"
    for nodeTagPair in self.observerTags:
      nodeTagPair[0].RemoveObserver(nodeTagPair[1])

  def startLightFeedback(self, breachWarningNode, connectorNode):
    self.removeObservers()
    self.breachWarningNode=breachWarningNode
    self.connectorNode=connectorNode    

    # Start the updates
    self.addObservers()
    self.onBreachWarningNodeModified(0,0)

  def stopLightFeedback(self):
    self.removeObservers()
    # Disable light
    rgbIntensity = '000'
    flashTimeMsec = '000'
    lightSetCommandText = rgbIntensity + flashTimeMsec
    self.queueLightSetCommand(lightSetCommandText)

  # Send the command immediately and only once (to not send the command repeatedly in case a light controller is not connected)
  def shutdownLight(self, connectorNode):
    self.connectorNode=connectorNode
    rgbIntensity = '000'
    flashTimeMsec = '000'
    lightSetCommandText = rgbIntensity + flashTimeMsec
    self.lightSetCommand.SetCommandAttribute('Text', lightSetCommandText)
    slicer.modules.openigtlinkremote.logic().SendCommand(self.lightSetCommand, self.connectorNode.GetID())
    logging.debug('shutdownLight completed')

  def setMarginSizeMm(self, marginSizeMm):
    self.marginSizeMm = marginSizeMm
    self.onBreachWarningNodeModified(0,0)
 
  def queueLightSetCommand(self, lightSetCommandText):
    if self.lightSetCommand.IsSucceeded() and self.lightSetCommand.GetCommandAttribute('Text') == lightSetCommandText:
      # The command has been already sent successfully, no need to resend
      return
    if self.lightSetCommand.IsInProgress():
      # The previous command is still in progress anymore, so we have to wait until it is completed
      self.queuedLightSetCommandText = lightSetCommandText
      return
    # Ready to send a new setting
    self.lightSetCommand.SetCommandAttribute('Text', lightSetCommandText)
    slicer.modules.openigtlinkremote.logic().SendCommand(self.lightSetCommand, self.connectorNode.GetID())
 
  def onLightSetCommandCompleted(self, observer, eventid):
    # If there was a queued command that we could not execute because a command was already in progress
    # then send it now
    if self.queuedLightSetCommandText:
      text=self.queuedLightSetCommandText
      self.queuedLightSetCommandText = None
      self.queueLightSetCommand(text)
 
  def getLightSetCommandText(self, distanceMm):
    rgbIntensity = '000' # R, G, B intensities, each between 0 and 9
    flashTimeMsec = '000' # light is on for flashTimeMsec and then off for flashTimeMsec (0 means solid on)

    if distanceMm<0:
      # inside the tumor
      rgbIntensity =  '900' # red
      flashTimeMsec = '051' # this is the fastest possible blinking
    elif distanceMm<self.marginSizeMm:
      # good
      rgbIntensity =  '090' # green
      flashTimeMsec = '000' # solid
    else:
      # too far
      rgbIntensity =  '009' # blue
      flashTimeMsec = '000' # solid
    
    lightSetCommandText = rgbIntensity + flashTimeMsec
    return lightSetCommandText
 
  def onBreachWarningNodeModified(self, observer, eventid):
  
    if not self.breachWarningNode or not self.connectorNode:
      return

    distanceMm = self.breachWarningNode.GetClosestDistanceToModelFromToolTip()
    lightSetCommandText = self.getLightSetCommandText(distanceMm)    
    
    # print the command on the console - just for testing
    # print('Light pattern: '+lightSetCommandText)

    #send the output data to the serial input of the arduino     
    self.queueLightSetCommand(lightSetCommandText)
 
class BreachWarningLightTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_BreachWarningLight1()

  def test_BreachWarningLight1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay('Test passed!')
