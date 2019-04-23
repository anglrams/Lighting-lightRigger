#lightRigger - Lighting tool for Maya
This tool works using the Qt.py library.

lightRigger allows to create light rigs with n number of lights and position them. 
By selecting existing lights it can create a rig(group) by clicking 'create from selected'
Once excecuted, it will populate the rigs section with existing rigs with the termination 'lgt_rig'.

Creates a table of attibutes for each rig to be modified in all of the lights within the rig. 
Once selecting the first attibute, it will add a column to select another attribute, and so on. 
There is a custom attibute whitch allows to write the name of the attribute if it is not in the list. 

To run the tool, run this in the python command line in maya:
import lightRigger
lightRigger.LightRigger()


