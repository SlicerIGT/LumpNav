# ---------------------------------------------------
# #Include this information for the first run
# ---------------------------------------------------

import numpy as np
from numpy import save
bn = slicer.mrmlScene.GetFirstNodeByName('LumpNavTracking_20231124_101641') #E.g. LumpNavTracking_20220329_082749
breachWarningNode = slicer.mrmlScene.GetFirstNodeByName("LumpNavBreachWarning")
#number of nodes
print(bn.GetNumberOfItems())
burning = False
burnCount = 0
PosBurn = np.array([])
item = bn.SelectNextItem() #only include if starting collection

# ---------------------------------------------------
# #Run script to get to the proper start time, or do it manually. I just do it manually.
# ---------------------------------------------------

try:
    slicer.app.pauseRender()
    #item = bn.SelectNextItem() #only include if starting collection
    while float(bn.GetMasterSequenceNode().GetNthIndexValue(item)) < START_TIME: #start time seconds
        item = bn.SelectNextItem()
finally:
    slicer.app.resumeRender()
    
# ---------------------------------------------------
# #Run script below for positive incisions
# ---------------------------------------------------

tumorNumber = 1 #optional variable for analysis in python after collection, manual setting for the "tumor incision number"
try:
    slicer.app.pauseRender() #stops Slicer rendering for analysis
    
    while float(bn.GetMasterSequenceNode().GetNthIndexValue(item)) < 1505: #END_TIME_OF_INCISION is in seconds e.g., 1581.71
        #get transforms
        cn = slicer.mrmlScene.GetFirstNodeByName('CauteryTipToCautery')
        cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
        cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
        nn = slicer.mrmlScene.GetFirstNodeByName('NeedleTipToNeedle')
        needleTipToRASMatrix = vtk.vtkMatrix4x4()
        nn.GetMatrixTransformToWorld(needleTipToRASMatrix)
        #get locations of cautery and needle tip
        cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
        needleTip_RAS = needleTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
        #get cautery tip in the needle tip coordiantes
        RASToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Invert(needleTipToRASMatrix, RASToNeedleTip)
        cauteryTipToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(RASToNeedleTip, cauteryTipToRASMatrix, cauteryTipToNeedleTip)
        cauteryTip_needleTip = cauteryTipToNeedleTip.MultiplyFloatPoint([0,0,0,1])
        #plot cautery tip in the needle tip coordinate system
        slicer.modules.markups.logic().AddControlPoint(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2])
        #set positive burn array to store RAS location, incision number, and time
        # PosBurn = np.append(PosBurn, [(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2]),tumorNumber,bn.GetMasterSequenceNode().GetNthIndexValue(item)])
        item = bn.SelectNextItem()
finally:
    slicer.app.resumeRender() #resumes renduring

# Optional saving of time and space data for incisions
save("d:/Chris/iKnife/2021-12-14_iKnife101/positive_burns.npy", PosBurn)

# ---------------------------------------------------
# #Run script below for negative incisions
# ---------------------------------------------------

#for negative burns
NEGATIVE_THRESHOLD_DISTANCE = 25
try:
    slicer.app.pauseRender()
    item = bn.SelectNextItem() #only include if starting collection
    while float(bn.GetMasterSequenceNode().GetNthIndexValue(item)) < 396:
        cn = slicer.mrmlScene.GetFirstNodeByName('CauteryTipToCautery')
        cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
        cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
        nn = slicer.mrmlScene.GetFirstNodeByName('NeedleTipToNeedle')
        needleTipToRASMatrix = vtk.vtkMatrix4x4()
        nn.GetMatrixTransformToWorld(needleTipToRASMatrix)
        cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
        needleTip_RAS = needleTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
        #distancebetweenTips = np.linalg.norm(np.array(cauteryTip_RAS) - np.array(needleTip_RAS))
        RASToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Invert(needleTipToRASMatrix, RASToNeedleTip)
        cauteryTipToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(RASToNeedleTip, cauteryTipToRASMatrix, cauteryTipToNeedleTip)
        cauteryTip_needleTip = cauteryTipToNeedleTip.MultiplyFloatPoint([0,0,0,1])
        #distance to tumor center
        #you can either do the distance between cautery tip and needle tip, or cautery tip and a manually selected point
        # distanceToTumor = np.linalg.norm(np.array(cauteryTip_needleTip)[:3] - np.array([190,172,205])) #manually selected point
        # distanceToTumor = np.linalg.norm(np.array(cauteryTip_needleTip)[:3]-0) #needle tip
        distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()  # distance to tumor boundary
        
        #checks to see distance from tumor center and plots a point within certain range
        if distanceToTumor <= NEGATIVE_THRESHOLD_DISTANCE: #e.g., 25 (this is in mm)
            burning = True
            NegBurn = np.append(NegBurn, [(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2]),burnCount,bn.GetMasterSequenceNode().GetNthIndexValue(item)])
            slicer.modules.markups.logic().AddFiducial(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2])
            
        #calculated number of incisions that happen during procedure
        if (distanceToTumor > NEGATIVE_THRESHOLD_DISTANCE) and (burning == True):
            burnCount += 1
            burning = False
            item = bn.SelectNextItem()
finally:
    slicer.app.resumeRender()

# ---------------------------------------------------
# Plot cautery trajectory for entire procedure
# ---------------------------------------------------

THRESHOLD_DISTANCE = 80
SEQUENCE_END_TIME = 1277.7
try:
    slicer.app.pauseRender()
    startItemIndex = float(bn.GetMasterSequenceNode().GetNthIndexValue(item))
    while float(bn.GetMasterSequenceNode().GetNthIndexValue(item)) < SEQUENCE_END_TIME:
        cn = slicer.mrmlScene.GetFirstNodeByName('CauteryTipToCautery')
        cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
        cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
        nn = slicer.mrmlScene.GetFirstNodeByName('NeedleTipToNeedle')
        needleTipToRASMatrix = vtk.vtkMatrix4x4()
        nn.GetMatrixTransformToWorld(needleTipToRASMatrix)
        cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0, 0, 0, 1])
        needleTip_RAS = needleTipToRASMatrix.MultiplyFloatPoint([0, 0, 0, 1])
        RASToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Invert(needleTipToRASMatrix, RASToNeedleTip)
        cauteryTipToNeedleTip = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(RASToNeedleTip, cauteryTipToRASMatrix, cauteryTipToNeedleTip)
        cauteryTip_needleTip = cauteryTipToNeedleTip.MultiplyFloatPoint([0, 0, 0, 1])
        distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()  # distance to tumor boundary

        # checks to see distance from tumor center and plots a point within certain range
        if distanceToTumor <= THRESHOLD_DISTANCE:  # e.g., 25 (this is in mm)
            # slicer.modules.markups.logic().AddFiducial(cauteryTip_needleTip[0], cauteryTip_needleTip[1],
            #                                            cauteryTip_needleTip[2])
            slicer.modules.markups.logic().AddFiducial(cauteryTip_RAS[0], cauteryTip_RAS[1],
                                                       cauteryTip_RAS[2])
        item = bn.SelectNextItem()
finally:
    slicer.app.resumeRender()

# ---------------------------------------------------
# #Test plot cautery tip
# ---------------------------------------------------

cn = slicer.mrmlScene.GetFirstNodeByName('CauteryTipToCautery')
cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
nn = slicer.mrmlScene.GetFirstNodeByName('NeedleTipToNeedle')
needleTipToRASMatrix = vtk.vtkMatrix4x4()
nn.GetMatrixTransformToWorld(needleTipToRASMatrix)
cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
needleTip_RAS = needleTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
distancebetweenTips = np.linalg.norm(np.array(cauteryTip_RAS) - np.array(needleTip_RAS))
RASToNeedleTip = vtk.vtkMatrix4x4()
vtk.vtkMatrix4x4.Invert(needleTipToRASMatrix, RASToNeedleTip)
cauteryTipToNeedleTip = vtk.vtkMatrix4x4()
vtk.vtkMatrix4x4.Multiply4x4(RASToNeedleTip, cauteryTipToRASMatrix, cauteryTipToNeedleTip)
cauteryTip_needleTip = cauteryTipToNeedleTip.MultiplyFloatPoint([0,0,0,1])
slicer.modules.markups.logic().AddFiducial(cauteryTip_needleTip[0], cauteryTip_needleTip[1], cauteryTip_needleTip[2])

# ---------------------------------------------------
# #Collecting position data during the case.
# ---------------------------------------------------

#only include at start
import numpy as np
import pandas as pd
from numpy import save
bn = slicer.mrmlScene.GetFirstNodeByName('TrackingSequenceBrowser')
item = bn.SelectNextItem() #only include if starting collection
cn = slicer.mrmlScene.GetFirstNodeByName('CTTC')
cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
lastCauteryTip_RAS = np.array(cauteryTip_RAS)
breachWarningNode = slicer.mrmlScene.GetFirstNodeByName("LumpNavBreachWarning")
lastTime = float(bn.GetMasterSequenceNode().GetNthIndexValue(item))
item = bn.SelectNextItem() #only include if starting collection

positionMatrix = [[], [], [], [], []]
# positionMatrix = [[], [], []]
try:
    slicer.app.pauseRender()
    
    while float(bn.GetMasterSequenceNode().GetNthIndexValue(item)) < 2455.30:
        # Get cautery tip position in RAS
        cn = slicer.mrmlScene.GetFirstNodeByName('CTTC')
        cauteryTipToRASMatrix = vtk.vtkMatrix4x4()
        cn.GetMatrixTransformToWorld(cauteryTipToRASMatrix)
        cauteryTip_RAS = cauteryTipToRASMatrix.MultiplyFloatPoint([0,0,0,1])
        cauteryTip_RAS = np.array(cauteryTip_RAS)

        # Get tip position in needle coordinate
        tumorModel = slicer.mrmlScene.GetFirstNodeByName("TumorModel")
        needleToReference = tumorModel.GetParentTransformNode()
        cauteryTipToNeedleMatrix = vtk.vtkMatrix4x4()
        cn.GetMatrixTransformToNode(needleToReference, cauteryTipToNeedleMatrix)
        cauteryTip_Needle = cauteryTipToNeedleMatrix.MultiplyFloatPoint([0,0,0,1])
        cauteryTip_Needle = np.array(cauteryTip_Needle)
        cauteryTip_Needle_str = np.array2string(cauteryTip_Needle[:3])

        # Get tumor center
        centerOfMassFilter = vtk.vtkCenterOfMass()
        centerOfMassFilter.SetInputData(tumorModel.GetPolyData())
        centerOfMassFilter.SetUseScalarsAsWeights(False)
        centerOfMassFilter.Update()
        center = centerOfMassFilter.GetCenter()
        needleToReference = tumorModel.GetParentTransformNode()
        needleToRASMatrix = vtk.vtkMatrix4x4()
        needleToReference.GetMatrixTransformToWorld(needleToRASMatrix)
        tumorCenter_RAS = needleToRASMatrix.MultiplyFloatPoint(np.append(center, 1))
        tumorCenter_RAS = np.array(tumorCenter_RAS)
        tumorCenter_RAS_str = np.array2string(tumorCenter_RAS[:3])

        # Get distance to tumor and cautery speed
        distanceToTumor = breachWarningNode.GetClosestDistanceToModelFromToolTip()
        currentTime = float(bn.GetMasterSequenceNode().GetNthIndexValue(item))
        distanceCauteryTraveled = np.linalg.norm(np.array(cauteryTip_RAS) - np.array(lastCauteryTip_RAS))
        speed = distanceCauteryTraveled/(currentTime - lastTime)

        currentPosition = [[bn.GetMasterSequenceNode().GetNthIndexValue(item)], [cauteryTip_Needle_str], [distanceToTumor], [speed], [tumorCenter_RAS_str]]
        # currentPosition = [[bn.GetMasterSequenceNode().GetNthIndexValue(item)], [np.array2string(cauteryTip_Needle[:3])], [distanceToTumor]]
        positionMatrix = np.append(positionMatrix, currentPosition, axis = 1)
        lastCauteryTip_RAS = cauteryTip_RAS
        lastTime = currentTime
        item = bn.SelectNextItem()

finally:
    slicer.app.resumeRender()

df = pd.DataFrame(positionMatrix, ["Time (s)", "Cautery Tip Needle", "Distance To Tumour (mm)", "Cautery Speed (mm/s)", "Tumor Center RAS"])
# df = pd.DataFrame(positionMatrix, ["Time (s)", "CauteryTip_Needle", "Distance To Tumour (mm)"])
df = df.T
df.to_csv(r"c:\Users\Chris Yeung\Queen's University\Amoon Jamzad - Breast_navigated_iKnife\2024-07-26_FirstCase\iKnifeSyncData.csv")
