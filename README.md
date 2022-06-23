# LumpNav
Slicer extension for ultrasound-guided breast tumor resection (lumpectomy).

# Setting up system

## Software dependencies

- Use a Slicer version built after November 2021
- Make sure SlicerIGT, OpenIGTLink, and SlicerIGSIO extensions are installed in Slicer
- Add to additional modules paths: \aigt\SlicerExtension\LiveUltrasoundAi\SegmentationUNet\SegmentationUNet.py

When you start Slicer first time with the additional modules, Slicer will install some python libraries (including TensorFlow, which will pop up to ask if you have GPU prerequisites installed). This may take a few minutes, but only needed once.

## Read hardware

Prepare PLUS config file according to the [PLUS user guide](http://perk-software.cs.queensu.ca/plus/doc/nightly/user/Configuration.html). 
Transforms to be sent from the PLUS server to Slicer (via OpenIGTLink) are:
- Image_Image
- TransducerToReference
- CauteryToReference
- NeedleToReference
- CauteryToNeedle
- TransducerToTracker
- CauteryToTracker
- NeedleToTracker
- ReferenceToTracker

ImageToTransducer should be computed by LumpNav.

## Setting up the hardware

1. Ensure the Telemed MicrUs EXT-1H ultrasound system is connected to a power source and to the computer via USB.
2. Ensure the Ascension trakStar unit is also plugged into a power source and to the computer.
3. Connect the ultrasound transmitter box to the trakStar unit (labeled "Transmitter").
4. Connect the ultrasound probe to the Telemed ultrasound system.
5. Connect sensor cables to all 4 slots on the trakStar unit (labeled "Sensors"):
   1. Slot 1: ultrasound probe
   2. Slot 2: reference sensor
   3. Slot 3: needle
   4. Slot 4: cautery
6. Connect the sensors to the respective tools using the 3D-printed clips.

## Launching the Plus server

1. Start the [Plus Server Launcher](http://perk-software.cs.queensu.ca/plus/doc/nightly/user/ApplicationPlusServerLauncher.html) on the computer.
2. In the "Device set configuration directory" box, navigate to the *LumpNav/LumpNav2/Resources* directory.
3. For "Device set", choose "LumpNav2 Demo" (or any other Plus config file).
4. Click on the "Launch server" button to start.
5. "Connection successful!" text should appear in the dialog box once the server is ready.

## Connecting to 3D Slicer

1. Go to the OpenIGTLinkIF module in 3D Slicer (under the IGT section).
2. Create a new connector by clicking on the "+" button.
3. Check the "Active" box under "Status" to start receiving data.
