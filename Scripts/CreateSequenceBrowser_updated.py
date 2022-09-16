# Create sequence browser for simulation scene. Adds all transforms that will need to be recorded/replayed.


def createSequenceBrowser(name):
    browserNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSequenceBrowserNode", name)
    browserNode.SetPlaybackRateFps(20)
    sequenceLogic = slicer.modules.sequences.logic()
    recordedNodeNames = ["Image_Image",
                         "TransdToTracker",
                         "CauteryToNeedle",
                         "NeedleToProbe",
                         "ProbeToTracker",
                         "TransdToReference",
                         "ImageToReference",
                         "ProbeToReference",
                         "NeedleToTracker",
                         "ReferenceToTracker",
                         "CauteryToReference",
                         "CauteryToTracker",
                         "NeedleToReference"]
    for nodeName in recordedNodeNames:
        transformNode = slicer.mrmlScene.GetFirstNodeByName(nodeName)
        if transformNode is None:
            transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", nodeName)
        sequenceNode = sequenceLogic.AddSynchronizedNode(None, transformNode, browserNode)
        browserNode.SetRecording(sequenceNode, True)
        browserNode.SetPlayback(sequenceNode, True)

createSequenceBrowser("NeedlePivotCal")
createSequenceBrowser("NeedleSpinCal")
createSequenceBrowser("CauteryPivotCal")
createSequenceBrowser("CauterySpinCal")
createSequenceBrowser("TumorScans")
createSequenceBrowser("Excision")

