
# Create sequence browser for simulation scene. Adds all transforms that will need to be recorded/replayed.

def createSequenceBrowser(name):
  browserNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", name)
  browserNode.SetPlaybackRateFps(20)
  sequenceLogic = slicer.modules.sequences.logic()
  
  imageNode = slicer.mrmlScene.GetFirstNodeByName("Image_Image")
  if imageNode is None:
    imageNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "Image_Image")
  sequenceNode = sequenceLogic.AddSynchronizedNode(None, imageNode, browserNode)
  browserNode.SetRecording(sequenceNode, True)
  browserNode.SetPlayback(sequenceNode, True)
  
  signalNode = slicer.mrmlScene.GetFirstNodeByName("Signal_Signal")
  if signalNode is None:
    signalNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "Signal_Signal")
  signalSequenceNode = sequenceLogic.AddSynchronizedNode(None, signalNode, browserNode)
  browserNode.SetRecording(signalSequenceNode, True)
  browserNode.SetPlayback(signalSequenceNode, True)
  
  recordedNodeNames = ["ProbeToTracker",
                       "ReferenceToTracker",
                       "NeedleToTracker",
                       "CauteryToTracker",
                       "TransdToReference",
                       "NeedleToProbe",
                       "CauteryToNeedle",
                       "NeedleToReference",
                       "ImageToReference",
                       "ProbeToReference",
                       "CauteryToReference"]
  
  for nodeName in recordedNodeNames:
    transformNode = slicer.mrmlScene.GetFirstNodeByName(nodeName)
    if transformNode is None:
      transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", nodeName)
    sequenceNode = sequenceLogic.AddSynchronizedNode(None, transformNode, browserNode)
    browserNode.SetRecording(sequenceNode, True)
    browserNode.SetPlayback(sequenceNode, True)



createSequenceBrowser("NeedlePivotCalibration")
createSequenceBrowser("NeedleSpineCalibration")
createSequenceBrowser("CauteryPivotCalibration")
createSequenceBrowser("CauterySpinCalibration")
createSequenceBrowser("TumorScanning")
createSequenceBrowser("Excision")

