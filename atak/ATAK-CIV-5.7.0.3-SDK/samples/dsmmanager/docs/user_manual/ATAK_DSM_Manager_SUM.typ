
#import "@preview/polylux:0.4.0": *
#import "formatting.typ": *

#show: userguide.with(
   plugin-name: "DSM Manager",
   plugin-version: "3.4",
   platform: "ATAK",
   platform-version: "5.6.0",
)


#tak-slide[
  = Overview
#toolbox.side-by-side(columns:(.75fr, 13fr))[
#image("dsm.svg", width: 90%)  
][
The DSM Manager Plug-in allows the user to view Digital Surface Model (DSM) data within ATAK. Surface model data provides the heights of objects like buildings and trees. During normal usage, the DSM data is treated transparently like any other elevation data source. Additional details can be viewed with the Red X Tool.
]
= Loading DSM data

To load a file containing DSM data into ATAK, copy it into the atak/tools/dsm directory on the ATAK device.

= Usage
#toolbox.side-by-side(columns:(3fr, 13fr))[
#image("dsm_list.jpg", width: 90%)
][
Select *DSM Manager* from the ATAK toolbar to open DSM Manager and see a list of all loaded DSM datasets. Select the *Pan To* button by a dataset to pan / zoom the map view over its coverage area.
]
Select *Edit* to modify the data reference parameters for a dataset. Parameters include Model (surface, terrain, or terrain + surface), Units (meters or feet), and Reference (HAE or AGL). It is important to set the parameter values correctly if using a data set that does not conform to the default values (surface, meters, HAE). 

#toolbox.side-by-side(columns:(2.5fr, 10fr, 2.5fr))[
#image("dsm_edit.jpg", width: 90%)
][
When the *Red X* tool is placed at a location with DSM data, the customary information widget will contain additional lines of information detailing the terrain (ground) elevation, surface elevation (on top of the object at that point), and surface height (height of the object at that point).
][
#set align(right)
#image("dsm_red_x.jpg", width: 90%)
]
]