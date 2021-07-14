# LumpNav
Slicer extension for ultrasound-guided breast tumor resection (lumpectomy)

# Setting up system for testing

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
