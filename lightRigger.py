from Qt import QtWidgets, QtCore, QtGui
from maya import cmds as cmd
from maya import OpenMayaUI as omui
from shiboken2 import wrapInstance


def getMayaMainWindow():
    win = omui.MQtUtil_mainWindow()
    ptr = wrapInstance(long(win), QtWidgets.QMainWindow)
    return ptr


def getDock(name='LightRiggerDock'):
    deleteDock(name)
    ctrl = cmd.workspaceControl(name, dockToMainWindow=('right', 1), label='Light Rigger')
    qtCtrl = omui.MQtUtil_findControl(ctrl)
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)
    return ptr

def deleteDock(name='LightRiggerDock'):
    if cmd.workspaceControl(name, query=True, exists=True):
        cmd.deleteUI(name)


class LightRigger(QtWidgets.QWidget):
    lightTypes = ['pointLight', 'spotLight', 'directionalLight', 'areaLight', 'volumeLight']
    distanceLocators = ['lightRigLocator_A', 'lightRigLocator_B']

    def __init__(self, dock=True):
        if dock:
            parent = getDock()
        else:
            deleteDock()
            if cmd.window('lightRigger', query=True, exists=True):
                cmd.deleteUI('lightRigger')

            parent = QtWidgets.QDialog(parent=getMayaMainWindow())
            parent.setObjectName('lightRigger')
            parent.setWindowTitle('Light Rigger')
            layout = QtWidgets.QVBoxLayout(parent)

        super(LightRigger, self).__init__(parent=parent)

        self.buildUI()
        self.populate()
        self.parent().layout().addWidget(self)
        if not dock:
            parent.show()

    def buildUI(self):

        mainLayout = QtWidgets.QGridLayout(self)

        #RigName
        nameLabel = QtWidgets.QLabel()
        nameLabel.setText('Rig Name')
        mainLayout.addWidget(nameLabel, 0, 0)
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText('inner_house')
        mainLayout.addWidget(self.name, 0, 1, 1, 2)

        #No.Lights
        nLightsLabel = QtWidgets.QLabel()
        nLightsLabel.setText('Number of Lights')
        mainLayout.addWidget(nLightsLabel, 1, 0)
        self.nLights = QtWidgets.QLineEdit()
        self.nLights.setText('5')
        validator = QtGui.QIntValidator(1,999, self)
        self.nLights.setValidator(validator)
        self.nLights.textChanged.connect(self.nLightsSliderMod)
        self.nLights.setMinimumSize(80,10)
        self.nLights.setMaximumSize(80, 20)
        mainLayout.addWidget(self.nLights, 1, 1, 1, 1)
        self.nLightsSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.nLightsSlider.setMaximum(10)
        self.nLightsSlider.setMinimum(1)
        self.nLightsSlider.setValue(5)
        self.nLightsSlider.valueChanged.connect(self.nLightsMod)
        mainLayout.addWidget(self.nLightsSlider, 1, 2, 1, 2)

        #Placement Method
        placementLabel = QtWidgets.QLabel()
        placementLabel.setText('Placement')
        mainLayout.addWidget(placementLabel, 2, 0)
        self.placement = QtWidgets.QComboBox()
        self.placement.addItems(['Stick to Selected', 'Distance'])
        self.placement.currentIndexChanged.connect(self.position)
        self.placement.setToolTip('Two locators are created, position them to get the desired distance')
        mainLayout.addWidget(self.placement, 2, 1 )

        #LightType
        lightTypeLabel = QtWidgets.QLabel()
        lightTypeLabel.setText('Light Type')
        mainLayout.addWidget(lightTypeLabel, 2, 2)
        self.lightType = QtWidgets.QComboBox()
        for lightype in self.lightTypes:
            self.lightType.addItem(lightype)
        mainLayout.addWidget(self.lightType, 2, 3)

        #Create Rig Button
        createBtn = QtWidgets.QPushButton('Create Rig')
        createBtn.clicked.connect(self.createRig)
        mainLayout.addWidget(createBtn, 3, 0, 1, 2)

        #Create Rig from existing Lights
        createExistingBtn = QtWidgets.QPushButton('Create rig from selection')
        createExistingBtn.clicked.connect(self.createRigFromSelected)
        mainLayout.addWidget(createExistingBtn, 3, 2, 1, 2)

        #CreateRigSpace
        rigSpace = QtWidgets.QWidget()
        rigSpace.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self.scrollLayout = QtWidgets.QVBoxLayout(rigSpace)
        rigArea = QtWidgets.QScrollArea()
        rigArea.setWidgetResizable(True)
        rigArea.setWidget(rigSpace)
        mainLayout.addWidget(rigArea, 4, 0, 1, 4)

        #Refresh Button
        refreshBtn = QtWidgets.QPushButton('Refresh')
        refreshBtn.clicked.connect(self.populate)
        mainLayout.addWidget(refreshBtn)


    def position(self):
        '''
        Sets the parameters to position each light of the rig,
        Distance: Creates two position Locators and measures the distance between them,
            the lights are positioned at a stepped distance aiming the locator 'B'
        Stick to Selected: Checks the objects selected and place the lights close to the objects
        '''

        #Creates locators and set the Z position of 'B' 5 units
        if self.placement.currentText() == 'Distance':
            cmd.confirmDialog(t='lightRiggerDistance', m='Two locators were created, position them to get the desired distance', b='OK')
            if not cmd.objExists(self.distanceLocators[0]):
                locA = cmd.spaceLocator(p=[0, 0, 0], n=self.distanceLocators[0])
            if not cmd.objExists(self.distanceLocators[1]):
                locB = cmd.spaceLocator(p=[0, 0, 0], n=self.distanceLocators[1])
                cmd.setAttr('%s.translateZ' % locB[0], 5)
            cmd.select([x for x in self.distanceLocators])

        #Deletes the locators if changed to 'Stick to Selected'
        else:
            if cmd.objExists(self.distanceLocators[0]) and cmd.objExists(self.distanceLocators[1]):
                cmd.delete(self.distanceLocators[0], self.distanceLocators[1])


    def createRig(self):
        '''
        Creates N number of lights with the rig name using the placement method
        Creates a widget to control the lights in the UI
        '''

        lightType = self.lightType.currentText()
        nLights = self.nLights.text()
        rigName = self.name.text()
        placement = True if self.placement.currentText() == 'Stick to Selected' else False
        if not rigName:
            cmd.warning('No name given')
            return
        elif cmd.objExists('%s_lgtRig' % rigName):
            cmd.warning('Name already exists')
            return

        #If the placement method is 'Stick to Selected', grabs the selected objects and returns and error if not the same as N of lights
        selectedObjs = []
        if placement:
            selectedObjs = cmd.ls(sl=True, type='transform')
            if int(nLights) > len(selectedObjs):
                cmd.warning('Not enough objects selected')
                return
        #Else, it will be selected to 'Distance', looks for the locators, return an error if there are none
        else:
            if not cmd.objExists(self.distanceLocators[0]) or not cmd.objExists(self.distanceLocators[1]):
                cmd.warning('Locators no longer exists')
                return

        attrs = []
        for i in ['translate', 'rotate']:
            for x in ['X', 'Y', 'Z']:
                attrs.append(i+x)

        #Creates N of lights, id: shape and transform nodes of each ligth and passes it down to the widget. idn: id number
        id = {}
        idn = 0
        def lightNode(shadingNode, lightType, name):
            if shadingNode:
                node = eval("cmd.shadingNode('%s', asLight=True)" % lightType)
                node = cmd.listRelatives(cmd.rename(node, name), type=['areaLight', 'volumeLight'])[0]
            else:
                node = eval("cmd.%s(n='%s')" % (lightType, name))
            return node

        shadingNode = True if lightType == 'areaLight' or lightType == 'volumeLight' else False
        for i in range(int(nLights)):
            name = rigName+str(idn)
            node = lightNode(shadingNode, lightType, name)
            id[node] = name
            idn += 1

        #Sets the position of each light depending the placement method
        if placement:
            lightNo = 0
            for light in id.values():
                cmd.parent(light,selectedObjs[lightNo])
                lightNo += 1
                for attr in attrs:
                    val = 0 if not attr.endswith('Z') else -.5
                    cmd.setAttr('%s.%s' % (light, attr), val)

                cmd.parent(light, w=True)
        else:
            locAPos = [x for x in cmd.getAttr('%s.translate' % self.distanceLocators[0])[0]]
            locBPos = [x for x in cmd.getAttr('%s.translate' % self.distanceLocators[1])[0]]
            distanceTool = cmd.distanceDimension(sp=locAPos, ep=locBPos)
            distLocA, distLocB = cmd.listConnections(distanceTool)
            distance = cmd.getAttr('%s.distance' % distanceTool)
            distanceGroup = cmd.group(id.values(), n='lightRiggerDistGroup')
            x,y, z = locAPos
            cmd.setAttr('%s.translate' % distanceGroup, x, y, z)
            cmd.aimConstraint(self.distanceLocators[1], distanceGroup)
            inicial = 0
            for light in id.values():
                cmd.setAttr('%s.translateX' % light, inicial)
                inicial += distance
            cmd.parent(id.values(), w=True)
            cmd.delete(distanceGroup, distanceTool)

        #Enclose the lights in a group and creates the widget
        cmd.group(id.keys(), n='%s_lgtRig' % rigName)
        rigWidget = RigWidget(rigName, id)
        self.scrollLayout.addWidget(rigWidget)

    def createRigFromSelected(self):
        '''
        Takes the rig name and enclosures selected lights in a group, creates a widget to control within the UI
        '''
        rigName = self.name.text()
        if not rigName:
            cmd.warning('No name given')
            return
        elif cmd.objExists('%s_lgtRig' % rigName):
            cmd.warning('Name already exists')
            return

        id = {}
        selectedLights = cmd.ls(sl=True)
        lightShapes = cmd.listRelatives(selectedLights, type=self.lightTypes)
        lights = cmd.listRelatives(lightShapes, p=True)
        for i in lights:
            id[lightShapes[lights.index(i)]] = i

        cmd.parent(id.values(), w=True)
        cmd.group(id.keys(), n='%s_lgtRig' % rigName)
        widget = RigWidget(rigName, id)
        self.scrollLayout.addWidget(widget)

    def nLightsSliderMod(self, value):
        #Slider line edit Combo
        value = 1 if not value else value
        if int(value) > self.nLightsSlider.maximum():
            self.nLightsSlider.setMaximum(int(value))

        self.nLightsSlider.setValue(int(value))

    def nLightsMod(self, value):
        # Slider line edit Combo
        self.nLights.setText(str(value))

    def populate(self):
        '''
        Looks for existing rigs, gets the shape and the transform node and creates the widgets
        '''
        for i in reversed(range(self.scrollLayout.count())):
            widget = self.scrollLayout.takeAt(i).widget()
            widget.deleteLater()
            widget.setParent(None)

        rigs = [x for x in cmd.ls(type='transform') if '_lgtRig' in x]
        if len(rigs) != 0:
            for rig in rigs:
                lights = cmd.listRelatives(rigs[rigs.index(rig)])
                if lights:
                    lightShapes = cmd.listRelatives(lights, type=self.lightTypes)
                    id = {}
                    for light in lights:
                        id[lightShapes[lights.index(light)]] = light
                    rigWidget = RigWidget(rig.split('_')[:-1][0], id)
                    self.scrollLayout.addWidget(rigWidget)

class RigWidget(QtWidgets.QWidget):
    '''
    Widget Combo, Label, Table
    Table: composed of 2 rows,
        1st row contains available attributes to modify.
        2nd contains the controllers to manipulate the lights

    '''


    def __init__(self, name, info):
        super(RigWidget, self).__init__()
        self.attrsOp = ['Select Attribute', 'intensity', 'color', 'aim', 'aiExposure', 'aiSamples', 'aiRadius', 'Custom']
        self.columnCount = 0
        self.attrs = {}
        self.widgets = {}
        self.name= name
        self.info = info
        self.usedAttrs = []
        self.buildUI()
        self.tableWidth = 135
        self.aimLoc = False

    def buildUI(self):
        '''
        Buidls label and table starting at one column
        '''
        rigLayout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(1)
        self.table.setRowCount(2)
        self.table.setColumnWidth(0, 125)
        self.table.setRowHeight(1, 50)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setMinimumSize(125 ,84)
        self.table.setMaximumSize(130, 85)
        rigName = QtWidgets.QLabel(self.name)
        rigLayout.addWidget(rigName)
        lightTypes = set(cmd.objectType(x) for x in self.info.keys())

        #Adds 3 more attributes if there is any spotlight within the rig
        if 'spotLight' in lightTypes:
            self.attrsOp = self.attrsOp[:3] + ['coneAngle', 'penumbraAngle', 'dropoff'] + self.attrsOp[3:]
        self.addAttr()
        rigLayout.addWidget(self.table)

    def addAttr(self):
        '''
        Sets a new comboBox in the new column, populates it with available attributes from the list
        '''
        attr = 'attr_at_'+str(self.columnCount)
        self.attrs[attr] = QtWidgets.QComboBox()
        for i in [x for x in self.attrsOp if x not in self.usedAttrs]:
            self.attrs[attr].addItem(i)
        self.table.setCellWidget(0, self.columnCount, self.attrs[attr])
        columnCount = self.columnCount
        self.attrs[attr].currentIndexChanged.connect(lambda : self.addModule(columnCount))

    def resolveItemsCB(self, column, item):
        '''
        Takes out used attributes from the rest of the comboBoxes in the table

        :param column: Current column number
        :param item: Selected attribute
        '''
        usedAttrs = [self.attrs['attr_at_' + str(x)].currentText() for x in range(self.columnCount+1)]
        previousValue = [x for x in self.usedAttrs if x not in usedAttrs]
        self.usedAttrs = usedAttrs
        for i in range(self.columnCount+1):
            if i == column:
                continue
            itemIndex = self.attrs['attr_at_'+str(i)].findText(item)
            self.attrs['attr_at_'+str(i)].removeItem(itemIndex)
            if len(previousValue) == 1 and previousValue[0] != '':
                self.attrs['attr_at_' + str(i)].insertItem(self.attrsOp.index(previousValue[0]), previousValue[0])

    def addModule(self, columnCount):
        '''
        Creates the controllers to manipulate the lights that posses given attribute.
        The widgets are stored in a dictionary(attrs), Key: Widget variable, Value: Widget
        Creates a new column if the current column is the last of the table
        :param columnCount: Current column number
        '''

        attrPos = 'attr_at_' + str(columnCount)
        widget = 'widget_at' + str(columnCount)
        subWidget = 'subWidget_at' + str(columnCount)
        attr = self.attrs[attrPos].currentText()
        self.table.removeCellWidget(1, columnCount)
        if attr == 'color':
            self.widgets[widget] = QtWidgets.QPushButton()
            self.setButtonColor(widget)
            self.widgets[widget].clicked.connect(lambda: self.setColor(widget))
            self.table.setCellWidget(1, columnCount, self.widgets[widget])

        elif attr == 'aim':
            self.widgets[widget] = QtWidgets.QPushButton('On/Off')
            self.widgets[widget].clicked.connect(self.aim)
            self.table.setCellWidget(1, columnCount, self.widgets[widget])

        elif attr == 'Select Attribute' or attr == 'Custom':
            if attr == 'Select Attribute': pass
            else:
                inWidget = QtWidgets.QWidget()
                widgetLayout = QtWidgets.QHBoxLayout(inWidget)
                self.widgets[widget] = QtWidgets.QLineEdit()
                self.widgets[widget].setMaximumSize(90, 40)
                self.widgets[widget].setPlaceholderText('aiExposure')
                widgetLayout.addWidget(self.widgets[widget])
                subWidget = QtWidgets.QPushButton('Add')
                subWidget.setMaximumSize(30,40)
                subWidget.clicked.connect(lambda: self.addCustom(self.widgets[widget].text(), attrPos))
                widgetLayout.addWidget(subWidget)
                self.table.setCellWidget(1,columnCount, inWidget)
        else:
            initialValue = self.getAttr(attr)
            inWidget = QtWidgets.QWidget()
            widgetLayout = QtWidgets.QHBoxLayout(inWidget)
            self.widgets[widget] = QtWidgets.QLineEdit()
            self.widgets[widget].setMaximumSize(40, 40)
            self.widgets[widget].setText(str(initialValue))
            max = 999.00
            maxSld = 5
            for i in self.info.keys():
                if cmd.attributeQuery(attr, node=i, exists=True, mxe=True):
                    max = int(cmd.attributeQuery(attr, node=i, max=True)[0])
                    maxSld = max
                    break
            validator = QtGui.QIntValidator(1.00, max, self)
            self.widgets[widget].setValidator(validator)
            self.widgets[widget].textChanged.connect(lambda value: self.sliderCombo(value, subWidget, attr))
            widgetLayout.addWidget(self.widgets[widget])

            self.widgets[subWidget] = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            self.widgets[subWidget].setValue(initialValue)
            self.widgets[subWidget].setMaximum(maxSld)
            self.widgets[subWidget].valueChanged.connect(lambda value: self.sliderCombo(value, widget, attr, False))
            widgetLayout.addWidget(self.widgets[subWidget])
            self.table.setCellWidget(1, columnCount, inWidget)

        if attr not in ['Select Attribute', 'Custom']:
            self.usedAttrs.append(attr)
            self.resolveItemsCB(columnCount, attr)

        if columnCount == self.columnCount and attr != 'Select Attribute':
            self.tableWidth += 125
            self.table.setMaximumSize(1000, 85)
            self.table.setMinimumSize(self.tableWidth, 84)
            self.table.insertColumn(columnCount + 1)
            self.table.setColumnWidth(columnCount + 1, 125)
            self.columnCount += 1
            self.addAttr()

    def getAttr(self, attribute):
        '''
        Gets the attribute value from the first light that has the attribute
        returns an warning if no light has the attribute
        :param attribute: string
        :return: float
        '''
        value = 0.0
        for i in self.info.keys():
                if cmd.attributeQuery(attribute, node=i, exists=True):
                    value = cmd.getAttr('%s.%s' % (i, attribute))
                    break
                else:
                    continue
        else:
            if attribute != '':
                cmd.warning('No Lights appear to have ' + attribute)

        return value


    def setAttr(self, attr, value):
        '''
        Sets the value to each light
        :param attr: string
        :param value: string/int
        '''
        for i in self.info.keys():
            if cmd.attributeQuery(attr, node=i, exists=True):
                cmd.setAttr('%s.%s' % (i, attr), int(value))
            else:
                continue

    def addCustom(self, attribute, attr):
        '''
        Gets user input and adds a new attribute to the list, if any of the lights of the rig has it
        Returns a warning if none of the light has the new attribute
        '''
        for i in self.info.keys():
                if cmd.attributeQuery(attribute, node=i, exists=True):
                    break
                else:
                    continue
        else:
            cmd.warning('%s does not exist on any light' % attribute)
            return
        self.attrsOp.append(attribute)
        self.attrs[attr].clear()
        items = [x for x in self.attrsOp if x not in self.usedAttrs]
        self.attrs[attr].addItems(items)
        self.attrs[attr].setCurrentIndex(len(items)-1)
        self.usedAttrs.append(attribute)



    def aim(self):
        '''
        Creates a locator and creates constrains for the light to aim for it.
        Deletes the locator and teh constrains if it exists
        '''
        locatorName = self.name + '_aimLoc'
        if not cmd.objExists(locatorName):
            cmd.spaceLocator(n=locatorName)
            if self.aimLoc:
                x,y,z = list(self.aimLoc[0])
                cmd.setAttr('%s.translate' % locatorName, x, y, z)
            for i in self.info.values():
                cmd.aimConstraint(locatorName, i, mo=False, o=[0, 270, 0])
        else:
            constrains = cmd.listRelatives(self.info.values(), type='aimConstraint')
            cmd.delete(constrains)
            self.aimLoc = cmd.getAttr('%s.translate' % locatorName)
            cmd.delete(locatorName)



    def setButtonColor(self, widget, color=None):
        '''
        Gets color from set color UI, assigns it to the UI button
        :param widget: string
        :param color: list
        '''
        if not color:
            color = self.getAttr('color')[0]

        assert len(color) == 3, 'Color Error'
        r, g, b = [c * 255 for c in color]
        self.widgets[widget].setStyleSheet('background-color: rgba(%s, %s, %s, 1.0)' % (r, g, b))

    def setColor(self, widget):
        '''Sets the color of all the lights in the rig'''
        lightColor = self.getAttr( 'color')[0]
        color = cmd.colorEditor(rgbValue=lightColor)
        r, g, b, a = [float(c) for c in color.split()]
        color = (r, g, b)

        for i in self.info.keys():
            cmd.setAttr('%s.color' % i, r, g, b)
        self.setButtonColor(widget, color)

    def sliderCombo(self, value, widget, attr, way=True):
        #Slider Line edit Combo
        if way:
            value = 0 if not value else value
            if int(value) > self.widgets[widget].maximum():
                self.widgets[widget].setMaximum(int(value))
            self.setAttr(attr, value)
            self.widgets[widget].setValue(int(value))
        else:
            self.widgets[widget].setText(str(value))
