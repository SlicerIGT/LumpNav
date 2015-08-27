cmake_minimum_required(VERSION 2.8.9)

project(LumpNav)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/SlicerIGT/LumpNav")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Tamas Ungi, Andras Lasso, Thomas Vaughan, Kaci Carter, Padina Pezeshki, Laszlo Kanyasi, Gabor Fichtinger (Queen's University, PerkLab), Gabrielle Gauvin, Caitlin T. Yeo, John Rudan, Jay C Engel (Department of Surgery, Queen's University), Mikael Brudfors (Universidad Carlos III de Madrid)")
set(EXTENSION_DESCRIPTION "Breast tumor resection using tracked ultrasound and cautery. See description of the system at http://perk.cs.queensu.ca/contents/navigated-breast-tumor-excision-using-electromagnetically-tracked-ultrasound-and-surgical")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/SlicerIGT/LumpNav/master/LumpNav.png")
set(EXTENSION_SCREENSHOTURLS "http://www.na-mic.org/Wiki/images/0/0d/FullScreenModule02.png http://www.na-mic.org/Wiki/images/3/32/FullScreenModule01.png http://www.na-mic.org/Wiki/images/5/5e/LumpNav-Touchscreen.png")
set(EXTENSION_DEPENDS "SlicerIGT")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(BreachWarningLight)
add_subdirectory(Viewpoint)
add_subdirectory(LumpNav)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
