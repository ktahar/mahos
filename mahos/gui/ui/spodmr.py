# Form implementation generated from reading ui file 'spodmr.ui'
#
# Created by: PyQt6 UI code generator 6.7.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_SPODMR(object):
    def setupUi(self, SPODMR):
        SPODMR.setObjectName("SPODMR")
        SPODMR.resize(1464, 755)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(SPODMR)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(4)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.startButton = QtWidgets.QPushButton(parent=SPODMR)
        self.startButton.setObjectName("startButton")
        self.horizontalLayout.addWidget(self.startButton)
        self.stopButton = QtWidgets.QPushButton(parent=SPODMR)
        self.stopButton.setObjectName("stopButton")
        self.horizontalLayout.addWidget(self.stopButton)
        self.saveButton = QtWidgets.QPushButton(parent=SPODMR)
        self.saveButton.setObjectName("saveButton")
        self.horizontalLayout.addWidget(self.saveButton)
        self.exportButton = QtWidgets.QPushButton(parent=SPODMR)
        self.exportButton.setObjectName("exportButton")
        self.horizontalLayout.addWidget(self.exportButton)
        self.exportaltButton = QtWidgets.QPushButton(parent=SPODMR)
        self.exportaltButton.setObjectName("exportaltButton")
        self.horizontalLayout.addWidget(self.exportaltButton)
        self.loadButton = QtWidgets.QPushButton(parent=SPODMR)
        self.loadButton.setObjectName("loadButton")
        self.horizontalLayout.addWidget(self.loadButton)
        self.quickresumeBox = QtWidgets.QCheckBox(parent=SPODMR)
        self.quickresumeBox.setObjectName("quickresumeBox")
        self.horizontalLayout.addWidget(self.quickresumeBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.tabWidget = QtWidgets.QTabWidget(parent=SPODMR)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy)
        self.tabWidget.setAccessibleName("")
        self.tabWidget.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.tabWidget.setObjectName("tabWidget")
        self.mainTab = QtWidgets.QWidget()
        self.mainTab.setObjectName("mainTab")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.mainTab)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_2 = QtWidgets.QGroupBox(parent=self.mainTab)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.pd_lbBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        self.pd_lbBox.setMinimum(-10.0)
        self.pd_lbBox.setMaximum(10.0)
        self.pd_lbBox.setProperty("value", -10.0)
        self.pd_lbBox.setObjectName("pd_lbBox")
        self.gridLayout_2.addWidget(self.pd_lbBox, 1, 3, 1, 1)
        self.freq2Box = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        self.freq2Box.setDecimals(4)
        self.freq2Box.setMaximum(3000.0)
        self.freq2Box.setSingleStep(10.0)
        self.freq2Box.setProperty("value", 2740.0)
        self.freq2Box.setObjectName("freq2Box")
        self.gridLayout_2.addWidget(self.freq2Box, 3, 1, 1, 1)
        self.freqBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.freqBox.sizePolicy().hasHeightForWidth())
        self.freqBox.setSizePolicy(sizePolicy)
        self.freqBox.setDecimals(4)
        self.freqBox.setMinimum(1.0)
        self.freqBox.setMaximum(3000.0)
        self.freqBox.setSingleStep(10.0)
        self.freqBox.setProperty("value", 2740.0)
        self.freqBox.setObjectName("freqBox")
        self.gridLayout_2.addWidget(self.freqBox, 2, 1, 1, 1)
        self.pd_ubBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        self.pd_ubBox.setMinimum(-10.0)
        self.pd_ubBox.setMaximum(10.0)
        self.pd_ubBox.setProperty("value", 10.0)
        self.pd_ubBox.setObjectName("pd_ubBox")
        self.gridLayout_2.addWidget(self.pd_ubBox, 1, 5, 1, 1)
        self.accumwindowBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        self.accumwindowBox.setDecimals(4)
        self.accumwindowBox.setObjectName("accumwindowBox")
        self.gridLayout_2.addWidget(self.accumwindowBox, 0, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label_6.setObjectName("label_6")
        self.gridLayout_2.addWidget(self.label_6, 2, 0, 1, 1)
        self.nomwBox = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.nomwBox.setObjectName("nomwBox")
        self.gridLayout_2.addWidget(self.nomwBox, 2, 5, 1, 1)
        self.powerBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.powerBox.sizePolicy().hasHeightForWidth())
        self.powerBox.setSizePolicy(sizePolicy)
        self.powerBox.setDecimals(4)
        self.powerBox.setMinimum(-65.0)
        self.powerBox.setMaximum(0.0)
        self.powerBox.setProperty("value", 0.0)
        self.powerBox.setObjectName("powerBox")
        self.gridLayout_2.addWidget(self.powerBox, 2, 3, 1, 1)
        self.label = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.pdrateBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.pdrateBox.setMinimum(1)
        self.pdrateBox.setMaximum(10000)
        self.pdrateBox.setObjectName("pdrateBox")
        self.gridLayout_2.addWidget(self.pdrateBox, 1, 1, 1, 1)
        self.methodBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        self.methodBox.setObjectName("methodBox")
        self.methodBox.addItem("")
        self.gridLayout_2.addWidget(self.methodBox, 5, 1, 1, 1)
        self.nomw2Box = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.nomw2Box.setObjectName("nomw2Box")
        self.gridLayout_2.addWidget(self.nomw2Box, 3, 5, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 0, 9, 1, 1)
        self.power2Box = QtWidgets.QDoubleSpinBox(parent=self.groupBox_2)
        self.power2Box.setDecimals(4)
        self.power2Box.setMinimum(-65.0)
        self.power2Box.setMaximum(0.0)
        self.power2Box.setObjectName("power2Box")
        self.gridLayout_2.addWidget(self.power2Box, 3, 3, 1, 1)
        self.droprepBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.droprepBox.setObjectName("droprepBox")
        self.gridLayout_2.addWidget(self.droprepBox, 0, 5, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label_3.setObjectName("label_3")
        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)
        self.accumrepBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.accumrepBox.setMinimum(1)
        self.accumrepBox.setMaximum(1000)
        self.accumrepBox.setObjectName("accumrepBox")
        self.gridLayout_2.addWidget(self.accumrepBox, 0, 3, 1, 1)
        self.partialBox = QtWidgets.QComboBox(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.partialBox.sizePolicy().hasHeightForWidth())
        self.partialBox.setSizePolicy(sizePolicy)
        self.partialBox.setObjectName("partialBox")
        self.partialBox.addItem("")
        self.partialBox.addItem("")
        self.partialBox.addItem("")
        self.partialBox.addItem("")
        self.gridLayout_2.addWidget(self.partialBox, 5, 3, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label_5.setObjectName("label_5")
        self.gridLayout_2.addWidget(self.label_5, 5, 0, 1, 1)
        self.sweepsBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.sweepsBox.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sweepsBox.sizePolicy().hasHeightForWidth())
        self.sweepsBox.setSizePolicy(sizePolicy)
        self.sweepsBox.setPrefix("")
        self.sweepsBox.setMinimum(0)
        self.sweepsBox.setMaximum(999999999)
        self.sweepsBox.setProperty("value", 0)
        self.sweepsBox.setObjectName("sweepsBox")
        self.gridLayout_2.addWidget(self.sweepsBox, 0, 8, 1, 1)
        self.lockinrepBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.lockinrepBox.setMinimum(1)
        self.lockinrepBox.setMaximum(9999)
        self.lockinrepBox.setObjectName("lockinrepBox")
        self.gridLayout_2.addWidget(self.lockinrepBox, 0, 7, 1, 1)
        self.reduceBox = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.reduceBox.setObjectName("reduceBox")
        self.gridLayout_2.addWidget(self.reduceBox, 4, 1, 1, 1)
        self.label_10 = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label_10.setObjectName("label_10")
        self.gridLayout_2.addWidget(self.label_10, 4, 0, 1, 1)
        self.pgfreqLabel = QtWidgets.QLabel(parent=self.groupBox_2)
        self.pgfreqLabel.setObjectName("pgfreqLabel")
        self.gridLayout_2.addWidget(self.pgfreqLabel, 4, 3, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.groupBox = QtWidgets.QGroupBox(parent=self.mainTab)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.mdelayBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox)
        self.mdelayBox.setDecimals(1)
        self.mdelayBox.setMaximum(999999999.0)
        self.mdelayBox.setSingleStep(0.5)
        self.mdelayBox.setProperty("value", 1000.0)
        self.mdelayBox.setObjectName("mdelayBox")
        self.gridLayout_6.addWidget(self.mdelayBox, 1, 2, 1, 1)
        self.lwidthBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox)
        self.lwidthBox.setDecimals(1)
        self.lwidthBox.setMaximum(999999999.0)
        self.lwidthBox.setSingleStep(0.5)
        self.lwidthBox.setProperty("value", 5000.0)
        self.lwidthBox.setObjectName("lwidthBox")
        self.gridLayout_6.addWidget(self.lwidthBox, 1, 1, 1, 1)
        self.ldelayBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox)
        self.ldelayBox.setDecimals(1)
        self.ldelayBox.setMaximum(999999999.0)
        self.ldelayBox.setSingleStep(0.5)
        self.ldelayBox.setProperty("value", 45.0)
        self.ldelayBox.setObjectName("ldelayBox")
        self.gridLayout_6.addWidget(self.ldelayBox, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_5 = QtWidgets.QGroupBox(parent=self.mainTab)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.NstartBox = QtWidgets.QSpinBox(parent=self.groupBox_5)
        self.NstartBox.setSuffix("")
        self.NstartBox.setMinimum(1)
        self.NstartBox.setMaximum(9999999)
        self.NstartBox.setObjectName("NstartBox")
        self.gridLayout_3.addWidget(self.NstartBox, 1, 1, 1, 1)
        self.stopLabel = QtWidgets.QLabel(parent=self.groupBox_5)
        self.stopLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.stopLabel.setObjectName("stopLabel")
        self.gridLayout_3.addWidget(self.stopLabel, 0, 2, 1, 1)
        self.logBox = QtWidgets.QCheckBox(parent=self.groupBox_5)
        self.logBox.setObjectName("logBox")
        self.gridLayout_3.addWidget(self.logBox, 0, 5, 1, 1)
        self.NstopLabel = QtWidgets.QLabel(parent=self.groupBox_5)
        self.NstopLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.NstopLabel.setObjectName("NstopLabel")
        self.gridLayout_3.addWidget(self.NstopLabel, 1, 2, 1, 1)
        self.numBox = QtWidgets.QSpinBox(parent=self.groupBox_5)
        self.numBox.setSuffix("")
        self.numBox.setMinimum(1)
        self.numBox.setMaximum(999999999)
        self.numBox.setProperty("value", 100)
        self.numBox.setObjectName("numBox")
        self.gridLayout_3.addWidget(self.numBox, 0, 3, 1, 1)
        self.startBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_5)
        self.startBox.setDecimals(1)
        self.startBox.setMaximum(100000000.0)
        self.startBox.setSingleStep(0.5)
        self.startBox.setProperty("value", 1.0)
        self.startBox.setObjectName("startBox")
        self.gridLayout_3.addWidget(self.startBox, 0, 1, 1, 1)
        self.NstepBox = QtWidgets.QSpinBox(parent=self.groupBox_5)
        self.NstepBox.setSuffix("")
        self.NstepBox.setMinimum(1)
        self.NstepBox.setMaximum(9999999)
        self.NstepBox.setProperty("value", 1)
        self.NstepBox.setObjectName("NstepBox")
        self.gridLayout_3.addWidget(self.NstepBox, 1, 4, 1, 1)
        self.stepBox = QtWidgets.QDoubleSpinBox(parent=self.groupBox_5)
        self.stepBox.setDecimals(1)
        self.stepBox.setMaximum(100000000.0)
        self.stepBox.setSingleStep(0.5)
        self.stepBox.setProperty("value", 1.0)
        self.stepBox.setObjectName("stepBox")
        self.gridLayout_3.addWidget(self.stepBox, 0, 4, 1, 1)
        self.NnumBox = QtWidgets.QSpinBox(parent=self.groupBox_5)
        self.NnumBox.setSuffix("")
        self.NnumBox.setMinimum(2)
        self.NnumBox.setMaximum(999999999)
        self.NnumBox.setProperty("value", 100)
        self.NnumBox.setObjectName("NnumBox")
        self.gridLayout_3.addWidget(self.NnumBox, 1, 3, 1, 1)
        self.label_9 = QtWidgets.QLabel(parent=self.groupBox_5)
        self.label_9.setObjectName("label_9")
        self.gridLayout_3.addWidget(self.label_9, 0, 0, 1, 1)
        self.invertsweepBox = QtWidgets.QCheckBox(parent=self.groupBox_5)
        self.invertsweepBox.setObjectName("invertsweepBox")
        self.gridLayout_3.addWidget(self.invertsweepBox, 1, 5, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=self.groupBox_5)
        self.label_4.setObjectName("label_4")
        self.gridLayout_3.addWidget(self.label_4, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_5)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=self.mainTab)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.paramTable = ParamTable(parent=self.groupBox_4)
        self.paramTable.setObjectName("paramTable")
        self.paramTable.setColumnCount(0)
        self.paramTable.setRowCount(0)
        self.verticalLayout_4.addWidget(self.paramTable)
        self.verticalLayout.addWidget(self.groupBox_4)
        self.tabWidget.addTab(self.mainTab, "")
        self.extraTab = QtWidgets.QWidget()
        self.extraTab.setObjectName("extraTab")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.extraTab)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox_3 = QtWidgets.QGroupBox(parent=self.extraTab)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout.setObjectName("gridLayout")
        self.plotenableBox = QtWidgets.QCheckBox(parent=self.groupBox_3)
        self.plotenableBox.setObjectName("plotenableBox")
        self.gridLayout.addWidget(self.plotenableBox, 0, 0, 1, 1)
        self.taumodeBox = QtWidgets.QComboBox(parent=self.groupBox_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.taumodeBox.sizePolicy().hasHeightForWidth())
        self.taumodeBox.setSizePolicy(sizePolicy)
        self.taumodeBox.setObjectName("taumodeBox")
        self.taumodeBox.addItem("")
        self.taumodeBox.addItem("")
        self.taumodeBox.addItem("")
        self.taumodeBox.addItem("")
        self.gridLayout.addWidget(self.taumodeBox, 1, 3, 1, 1)
        self.label_14 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_14.setObjectName("label_14")
        self.gridLayout.addWidget(self.label_14, 3, 0, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem2, 1, 6, 1, 1)
        self.plotmodeBox = QtWidgets.QComboBox(parent=self.groupBox_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plotmodeBox.sizePolicy().hasHeightForWidth())
        self.plotmodeBox.setSizePolicy(sizePolicy)
        self.plotmodeBox.setObjectName("plotmodeBox")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.plotmodeBox.addItem("")
        self.gridLayout.addWidget(self.plotmodeBox, 1, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 1, 0, 1, 1)
        self.logYBox = QtWidgets.QCheckBox(parent=self.groupBox_3)
        self.logYBox.setObjectName("logYBox")
        self.gridLayout.addWidget(self.logYBox, 3, 2, 1, 1)
        self.logXBox = QtWidgets.QCheckBox(parent=self.groupBox_3)
        self.logXBox.setObjectName("logXBox")
        self.gridLayout.addWidget(self.logXBox, 3, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 2, 1, 1)
        self.flipYBox = QtWidgets.QCheckBox(parent=self.groupBox_3)
        self.flipYBox.setObjectName("flipYBox")
        self.gridLayout.addWidget(self.flipYBox, 3, 3, 1, 1)
        self.normalizeBox = QtWidgets.QCheckBox(parent=self.groupBox_3)
        self.normalizeBox.setChecked(True)
        self.normalizeBox.setObjectName("normalizeBox")
        self.gridLayout.addWidget(self.normalizeBox, 2, 0, 1, 1)
        self.offsetBox = SpinBox(parent=self.groupBox_3)
        self.offsetBox.setObjectName("offsetBox")
        self.gridLayout.addWidget(self.offsetBox, 2, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 2, 2, 1, 1)
        self.complexBox = QtWidgets.QComboBox(parent=self.groupBox_3)
        self.complexBox.setObjectName("complexBox")
        self.complexBox.addItem("")
        self.complexBox.addItem("")
        self.complexBox.addItem("")
        self.complexBox.addItem("")
        self.gridLayout.addWidget(self.complexBox, 2, 3, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox_3)
        self.fgGroupBox = QtWidgets.QGroupBox(parent=self.extraTab)
        self.fgGroupBox.setEnabled(True)
        self.fgGroupBox.setObjectName("fgGroupBox")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.fgGroupBox)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.fg_disableButton = QtWidgets.QRadioButton(parent=self.fgGroupBox)
        self.fg_disableButton.setObjectName("fg_disableButton")
        self.horizontalLayout_8.addWidget(self.fg_disableButton)
        self.fg_cwButton = QtWidgets.QRadioButton(parent=self.fgGroupBox)
        self.fg_cwButton.setObjectName("fg_cwButton")
        self.horizontalLayout_8.addWidget(self.fg_cwButton)
        self.fg_gateButton = QtWidgets.QRadioButton(parent=self.fgGroupBox)
        self.fg_gateButton.setObjectName("fg_gateButton")
        self.horizontalLayout_8.addWidget(self.fg_gateButton)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem3)
        self.verticalLayout_5.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.fg_waveBox = QtWidgets.QComboBox(parent=self.fgGroupBox)
        self.fg_waveBox.setMinimumSize(QtCore.QSize(80, 0))
        self.fg_waveBox.setObjectName("fg_waveBox")
        self.fg_waveBox.addItem("")
        self.fg_waveBox.addItem("")
        self.horizontalLayout_9.addWidget(self.fg_waveBox)
        self.fg_amplBox = QtWidgets.QDoubleSpinBox(parent=self.fgGroupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fg_amplBox.sizePolicy().hasHeightForWidth())
        self.fg_amplBox.setSizePolicy(sizePolicy)
        self.fg_amplBox.setMinimumSize(QtCore.QSize(150, 0))
        self.fg_amplBox.setDecimals(4)
        self.fg_amplBox.setMinimum(0.0)
        self.fg_amplBox.setMaximum(20.0)
        self.fg_amplBox.setSingleStep(0.1)
        self.fg_amplBox.setProperty("value", 0.0)
        self.fg_amplBox.setObjectName("fg_amplBox")
        self.horizontalLayout_9.addWidget(self.fg_amplBox)
        self.fg_phaseBox = QtWidgets.QDoubleSpinBox(parent=self.fgGroupBox)
        self.fg_phaseBox.setMinimumSize(QtCore.QSize(150, 0))
        self.fg_phaseBox.setDecimals(4)
        self.fg_phaseBox.setMinimum(0.0)
        self.fg_phaseBox.setMaximum(360.0)
        self.fg_phaseBox.setSingleStep(0.1)
        self.fg_phaseBox.setProperty("value", 0.0)
        self.fg_phaseBox.setObjectName("fg_phaseBox")
        self.horizontalLayout_9.addWidget(self.fg_phaseBox)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_9.addItem(spacerItem4)
        self.verticalLayout_5.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.fg_freqBox = QtWidgets.QDoubleSpinBox(parent=self.fgGroupBox)
        self.fg_freqBox.setMinimumSize(QtCore.QSize(150, 0))
        self.fg_freqBox.setDecimals(9)
        self.fg_freqBox.setMinimum(1e-06)
        self.fg_freqBox.setMaximum(200.0)
        self.fg_freqBox.setSingleStep(1.0)
        self.fg_freqBox.setProperty("value", 1.0)
        self.fg_freqBox.setObjectName("fg_freqBox")
        self.horizontalLayout_13.addWidget(self.fg_freqBox)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem5)
        self.verticalLayout_5.addLayout(self.horizontalLayout_13)
        self.verticalLayout_2.addWidget(self.fgGroupBox)
        spacerItem6 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem6)
        self.tabWidget.addTab(self.extraTab, "")
        self.fiTab = QtWidgets.QWidget()
        self.fiTab.setObjectName("fiTab")
        self.tabWidget.addTab(self.fiTab, "")
        self.verticalLayout_3.addWidget(self.tabWidget)
        self.horizontalLayout_2.addLayout(self.verticalLayout_3)

        self.retranslateUi(SPODMR)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(SPODMR)
        SPODMR.setTabOrder(self.startButton, self.stopButton)
        SPODMR.setTabOrder(self.stopButton, self.saveButton)
        SPODMR.setTabOrder(self.saveButton, self.exportButton)
        SPODMR.setTabOrder(self.exportButton, self.exportaltButton)
        SPODMR.setTabOrder(self.exportaltButton, self.loadButton)
        SPODMR.setTabOrder(self.loadButton, self.quickresumeBox)
        SPODMR.setTabOrder(self.quickresumeBox, self.tabWidget)
        SPODMR.setTabOrder(self.tabWidget, self.accumwindowBox)
        SPODMR.setTabOrder(self.accumwindowBox, self.accumrepBox)
        SPODMR.setTabOrder(self.accumrepBox, self.droprepBox)
        SPODMR.setTabOrder(self.droprepBox, self.lockinrepBox)
        SPODMR.setTabOrder(self.lockinrepBox, self.sweepsBox)
        SPODMR.setTabOrder(self.sweepsBox, self.pdrateBox)
        SPODMR.setTabOrder(self.pdrateBox, self.pd_lbBox)
        SPODMR.setTabOrder(self.pd_lbBox, self.pd_ubBox)
        SPODMR.setTabOrder(self.pd_ubBox, self.freqBox)
        SPODMR.setTabOrder(self.freqBox, self.powerBox)
        SPODMR.setTabOrder(self.powerBox, self.nomwBox)
        SPODMR.setTabOrder(self.nomwBox, self.freq2Box)
        SPODMR.setTabOrder(self.freq2Box, self.power2Box)
        SPODMR.setTabOrder(self.power2Box, self.nomw2Box)
        SPODMR.setTabOrder(self.nomw2Box, self.reduceBox)
        SPODMR.setTabOrder(self.reduceBox, self.methodBox)
        SPODMR.setTabOrder(self.methodBox, self.partialBox)
        SPODMR.setTabOrder(self.partialBox, self.ldelayBox)
        SPODMR.setTabOrder(self.ldelayBox, self.lwidthBox)
        SPODMR.setTabOrder(self.lwidthBox, self.mdelayBox)
        SPODMR.setTabOrder(self.mdelayBox, self.startBox)
        SPODMR.setTabOrder(self.startBox, self.numBox)
        SPODMR.setTabOrder(self.numBox, self.stepBox)
        SPODMR.setTabOrder(self.stepBox, self.logBox)
        SPODMR.setTabOrder(self.logBox, self.NstartBox)
        SPODMR.setTabOrder(self.NstartBox, self.NnumBox)
        SPODMR.setTabOrder(self.NnumBox, self.NstepBox)
        SPODMR.setTabOrder(self.NstepBox, self.invertsweepBox)
        SPODMR.setTabOrder(self.invertsweepBox, self.paramTable)
        SPODMR.setTabOrder(self.paramTable, self.plotenableBox)
        SPODMR.setTabOrder(self.plotenableBox, self.plotmodeBox)
        SPODMR.setTabOrder(self.plotmodeBox, self.taumodeBox)
        SPODMR.setTabOrder(self.taumodeBox, self.normalizeBox)
        SPODMR.setTabOrder(self.normalizeBox, self.offsetBox)
        SPODMR.setTabOrder(self.offsetBox, self.complexBox)
        SPODMR.setTabOrder(self.complexBox, self.logXBox)
        SPODMR.setTabOrder(self.logXBox, self.logYBox)
        SPODMR.setTabOrder(self.logYBox, self.flipYBox)
        SPODMR.setTabOrder(self.flipYBox, self.fg_disableButton)
        SPODMR.setTabOrder(self.fg_disableButton, self.fg_cwButton)
        SPODMR.setTabOrder(self.fg_cwButton, self.fg_gateButton)
        SPODMR.setTabOrder(self.fg_gateButton, self.fg_waveBox)
        SPODMR.setTabOrder(self.fg_waveBox, self.fg_amplBox)
        SPODMR.setTabOrder(self.fg_amplBox, self.fg_phaseBox)
        SPODMR.setTabOrder(self.fg_phaseBox, self.fg_freqBox)

    def retranslateUi(self, SPODMR):
        _translate = QtCore.QCoreApplication.translate
        SPODMR.setWindowTitle(_translate("SPODMR", "Form"))
        self.startButton.setText(_translate("SPODMR", "Start"))
        self.stopButton.setText(_translate("SPODMR", "Stop"))
        self.saveButton.setText(_translate("SPODMR", "Save"))
        self.exportButton.setText(_translate("SPODMR", "Export"))
        self.exportaltButton.setText(_translate("SPODMR", "Export Alt"))
        self.loadButton.setText(_translate("SPODMR", "Load"))
        self.quickresumeBox.setText(_translate("SPODMR", "Quick resume"))
        self.groupBox_2.setTitle(_translate("SPODMR", "Fundamental"))
        self.pd_lbBox.setPrefix(_translate("SPODMR", "lower: "))
        self.pd_lbBox.setSuffix(_translate("SPODMR", " V"))
        self.freq2Box.setPrefix(_translate("SPODMR", "freq2: "))
        self.freq2Box.setSuffix(_translate("SPODMR", " MHz"))
        self.freqBox.setPrefix(_translate("SPODMR", "freq: "))
        self.freqBox.setSuffix(_translate("SPODMR", " MHz"))
        self.pd_ubBox.setPrefix(_translate("SPODMR", "upper: "))
        self.pd_ubBox.setSuffix(_translate("SPODMR", " V"))
        self.accumwindowBox.setPrefix(_translate("SPODMR", "accum window: "))
        self.accumwindowBox.setSuffix(_translate("SPODMR", " ms"))
        self.label_6.setText(_translate("SPODMR", "Micro Wave"))
        self.nomwBox.setText(_translate("SPODMR", "Do not turn on MW"))
        self.powerBox.setPrefix(_translate("SPODMR", "power: "))
        self.powerBox.setSuffix(_translate("SPODMR", " dBm"))
        self.label.setText(_translate("SPODMR", "Detection"))
        self.pdrateBox.setSuffix(_translate("SPODMR", " kHz"))
        self.pdrateBox.setPrefix(_translate("SPODMR", "rate: "))
        self.methodBox.setItemText(0, _translate("SPODMR", "rabi"))
        self.nomw2Box.setText(_translate("SPODMR", "Do not turn on MW2"))
        self.power2Box.setPrefix(_translate("SPODMR", "power2: "))
        self.power2Box.setSuffix(_translate("SPODMR", " dBm"))
        self.droprepBox.setPrefix(_translate("SPODMR", "drop rep: "))
        self.label_3.setText(_translate("SPODMR", "Analog PD"))
        self.accumrepBox.setPrefix(_translate("SPODMR", "accum rep: "))
        self.partialBox.setItemText(0, _translate("SPODMR", "Complementary"))
        self.partialBox.setItemText(1, _translate("SPODMR", "Pattern 0 only"))
        self.partialBox.setItemText(2, _translate("SPODMR", "Pattern 1 only"))
        self.partialBox.setItemText(3, _translate("SPODMR", "Lockin"))
        self.label_5.setText(_translate("SPODMR", "method"))
        self.sweepsBox.setSuffix(_translate("SPODMR", " sweeps (0 to inf)"))
        self.lockinrepBox.setPrefix(_translate("SPODMR", "lockin rep: "))
        self.reduceBox.setText(_translate("SPODMR", "reduce pg freq"))
        self.label_10.setText(_translate("SPODMR", "PG"))
        self.pgfreqLabel.setText(_translate("SPODMR", "PG freq: Unknown"))
        self.groupBox.setTitle(_translate("SPODMR", "Common Timing"))
        self.mdelayBox.setPrefix(_translate("SPODMR", "MW delay: "))
        self.mdelayBox.setSuffix(_translate("SPODMR", " ns"))
        self.lwidthBox.setPrefix(_translate("SPODMR", "Laser width: "))
        self.lwidthBox.setSuffix(_translate("SPODMR", " ns"))
        self.ldelayBox.setPrefix(_translate("SPODMR", "Laser delay: "))
        self.ldelayBox.setSuffix(_translate("SPODMR", " ns"))
        self.groupBox_5.setTitle(_translate("SPODMR", "Sweep parameter (tau or N)"))
        self.NstartBox.setPrefix(_translate("SPODMR", "start: "))
        self.stopLabel.setText(_translate("SPODMR", "stop:"))
        self.logBox.setText(_translate("SPODMR", "logspace (for tau only)"))
        self.NstopLabel.setText(_translate("SPODMR", "stop:"))
        self.numBox.setPrefix(_translate("SPODMR", "num: "))
        self.startBox.setPrefix(_translate("SPODMR", "start: "))
        self.startBox.setSuffix(_translate("SPODMR", " ns"))
        self.NstepBox.setPrefix(_translate("SPODMR", "step: "))
        self.stepBox.setPrefix(_translate("SPODMR", "step: "))
        self.stepBox.setSuffix(_translate("SPODMR", " ns"))
        self.NnumBox.setPrefix(_translate("SPODMR", "num: "))
        self.label_9.setText(_translate("SPODMR", "tau"))
        self.invertsweepBox.setText(_translate("SPODMR", "invert sweep direction"))
        self.label_4.setText(_translate("SPODMR", "N"))
        self.groupBox_4.setTitle(_translate("SPODMR", "Additional parameters"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.mainTab), _translate("SPODMR", "Main"))
        self.groupBox_3.setTitle(_translate("SPODMR", "Plot"))
        self.plotenableBox.setText(_translate("SPODMR", "enable edit"))
        self.taumodeBox.setItemText(0, _translate("SPODMR", "raw"))
        self.taumodeBox.setItemText(1, _translate("SPODMR", "total"))
        self.taumodeBox.setItemText(2, _translate("SPODMR", "freq"))
        self.taumodeBox.setItemText(3, _translate("SPODMR", "index"))
        self.label_14.setText(_translate("SPODMR", "transform"))
        self.plotmodeBox.setItemText(0, _translate("SPODMR", "data01"))
        self.plotmodeBox.setItemText(1, _translate("SPODMR", "data0"))
        self.plotmodeBox.setItemText(2, _translate("SPODMR", "data1"))
        self.plotmodeBox.setItemText(3, _translate("SPODMR", "diff"))
        self.plotmodeBox.setItemText(4, _translate("SPODMR", "average"))
        self.plotmodeBox.setItemText(5, _translate("SPODMR", "normalize-data0"))
        self.plotmodeBox.setItemText(6, _translate("SPODMR", "normalize-data1"))
        self.plotmodeBox.setItemText(7, _translate("SPODMR", "normalize"))
        self.plotmodeBox.setItemText(8, _translate("SPODMR", "normalize1"))
        self.plotmodeBox.setItemText(9, _translate("SPODMR", "concatenate"))
        self.label_8.setText(_translate("SPODMR", "mode"))
        self.logYBox.setText(_translate("SPODMR", "log Y"))
        self.logXBox.setText(_translate("SPODMR", "log X"))
        self.label_2.setText(_translate("SPODMR", "tau mode (x axis)"))
        self.flipYBox.setText(_translate("SPODMR", "flip Y"))
        self.normalizeBox.setText(_translate("SPODMR", "normalize"))
        self.offsetBox.setPrefix(_translate("SPODMR", "offset: "))
        self.label_7.setText(_translate("SPODMR", "Complex conv"))
        self.complexBox.setItemText(0, _translate("SPODMR", "real"))
        self.complexBox.setItemText(1, _translate("SPODMR", "imag"))
        self.complexBox.setItemText(2, _translate("SPODMR", "abs"))
        self.complexBox.setItemText(3, _translate("SPODMR", "angle"))
        self.fgGroupBox.setTitle(_translate("SPODMR", "Function Generator"))
        self.fg_disableButton.setText(_translate("SPODMR", "Disable"))
        self.fg_cwButton.setText(_translate("SPODMR", "CW"))
        self.fg_gateButton.setText(_translate("SPODMR", "Gate"))
        self.fg_waveBox.setItemText(0, _translate("SPODMR", "Sinusoid"))
        self.fg_waveBox.setItemText(1, _translate("SPODMR", "Square"))
        self.fg_amplBox.setPrefix(_translate("SPODMR", "amplitude: "))
        self.fg_amplBox.setSuffix(_translate("SPODMR", " Vpp"))
        self.fg_phaseBox.setPrefix(_translate("SPODMR", "phase: "))
        self.fg_phaseBox.setSuffix(_translate("SPODMR", " deg"))
        self.fg_freqBox.setPrefix(_translate("SPODMR", "freq: "))
        self.fg_freqBox.setSuffix(_translate("SPODMR", " kHz"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.extraTab), _translate("SPODMR", "Plot / FG"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.fiTab), _translate("SPODMR", "Fit"))
from mahos.gui.param import ParamTable
from pyqtgraph import SpinBox
