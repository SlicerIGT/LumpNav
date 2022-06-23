# LumpNav
Slicer extension for ultrasound-guided breast tumor resection (lumpectomy)

# Setting up system

## Software dependencies

- Use a Slicer version built after November 2021
- Make sure SlicerIGT, OpenIGTLink, and SlicerIGSIO extensions are installed in Slicer
- Add to additional modules paths: \aigt\SlicerExtension\LiveUltrasoundAi\SegmentationUNet\SegmentationUNet.py

When you start Slicer first time with the additional modules, Slicer will install some python libraries (including TensorFlow, which will pop up to ask if you have GPU prerequisites installed). This may take a few minutes, but only needed once.

## Read hardware

Prepare PLUS config file according to the PLUS user guide: http://perk-software.cs.queensu.ca/plus/doc/nightly/user/Configuration.html
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
2. Ensre the Ascension TrakStar unit is also plugged into a power source and to the computer.
3. Connect the ultrasound transmitter box to the TrakStar unit (labeled "Transmitter").
4. Connect the ultrasound probe to the Telemed ultrasound sytem.
