# Form implementation generated from reading ui file 'trackDialog.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_trackDialog(object):
    def setupUi(self, trackDialog):
        trackDialog.setObjectName("trackDialog")
        trackDialog.resize(850, 571)
        self.verticalLayout = QtWidgets.QVBoxLayout(trackDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.lenLabel = QtWidgets.QLabel(parent=trackDialog)
        self.lenLabel.setObjectName("lenLabel")
        self.gridLayout.addWidget(self.lenLabel, 4, 1, 1, 1)
        self.label_12 = QtWidgets.QLabel(parent=trackDialog)
        self.label_12.setObjectName("label_12")
        self.gridLayout.addWidget(self.label_12, 4, 4, 1, 1)
        self.numLabel_2 = QtWidgets.QLabel(parent=trackDialog)
        self.numLabel_2.setObjectName("numLabel_2")
        self.gridLayout.addWidget(self.numLabel_2, 8, 2, 1, 1)
        self.xyxlenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xyxlenBox.setDecimals(4)
        self.xyxlenBox.setMinimum(0.1)
        self.xyxlenBox.setProperty("value", 2.0)
        self.xyxlenBox.setObjectName("xyxlenBox")
        self.gridLayout.addWidget(self.xyxlenBox, 5, 1, 1, 1)
        self.xzzoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xzzoffsetBox.setDecimals(4)
        self.xzzoffsetBox.setMinimum(-10.0)
        self.xzzoffsetBox.setMaximum(10.0)
        self.xzzoffsetBox.setSingleStep(0.01)
        self.xzzoffsetBox.setObjectName("xzzoffsetBox")
        self.gridLayout.addWidget(self.xzzoffsetBox, 10, 4, 1, 1)
        self.yzzlenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.yzzlenBox.setDecimals(4)
        self.yzzlenBox.setMinimum(0.1)
        self.yzzlenBox.setProperty("value", 2.0)
        self.yzzlenBox.setObjectName("yzzlenBox")
        self.gridLayout.addWidget(self.yzzlenBox, 14, 1, 1, 1)
        self.xzxstepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.xzxstepLabel.setObjectName("xzxstepLabel")
        self.gridLayout.addWidget(self.xzxstepLabel, 9, 3, 1, 1)
        self.stepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.stepLabel.setObjectName("stepLabel")
        self.gridLayout.addWidget(self.stepLabel, 4, 3, 1, 1)
        self.linemodeBox = QtWidgets.QComboBox(parent=trackDialog)
        self.linemodeBox.setObjectName("linemodeBox")
        self.linemodeBox.addItem("")
        self.linemodeBox.addItem("")
        self.linemodeBox.addItem("")
        self.gridLayout.addWidget(self.linemodeBox, 1, 3, 1, 1)
        self.numLabel = QtWidgets.QLabel(parent=trackDialog)
        self.numLabel.setObjectName("numLabel")
        self.gridLayout.addWidget(self.numLabel, 4, 2, 1, 1)
        self.xzmodeBox = QtWidgets.QComboBox(parent=trackDialog)
        self.xzmodeBox.setObjectName("xzmodeBox")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.xzmodeBox.addItem("")
        self.gridLayout.addWidget(self.xzmodeBox, 8, 0, 1, 1)
        self.modeBox = QtWidgets.QComboBox(parent=trackDialog)
        self.modeBox.setObjectName("modeBox")
        self.modeBox.addItem("")
        self.gridLayout.addWidget(self.modeBox, 1, 1, 1, 1)
        self.intervalBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.intervalBox.setDecimals(1)
        self.intervalBox.setMinimum(-1.0)
        self.intervalBox.setMaximum(10000.0)
        self.intervalBox.setProperty("value", 180.0)
        self.intervalBox.setObjectName("intervalBox")
        self.gridLayout.addWidget(self.intervalBox, 0, 1, 1, 1)
        self.xyxoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xyxoffsetBox.setDecimals(4)
        self.xyxoffsetBox.setMinimum(-10.0)
        self.xyxoffsetBox.setMaximum(10.0)
        self.xyxoffsetBox.setSingleStep(0.01)
        self.xyxoffsetBox.setObjectName("xyxoffsetBox")
        self.gridLayout.addWidget(self.xyxoffsetBox, 5, 4, 1, 1)
        self.xzxoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xzxoffsetBox.setDecimals(4)
        self.xzxoffsetBox.setMinimum(-10.0)
        self.xzxoffsetBox.setMaximum(10.0)
        self.xzxoffsetBox.setSingleStep(0.01)
        self.xzxoffsetBox.setObjectName("xzxoffsetBox")
        self.gridLayout.addWidget(self.xzxoffsetBox, 9, 4, 1, 1)
        self.xLabel = QtWidgets.QLabel(parent=trackDialog)
        self.xLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.xLabel.setObjectName("xLabel")
        self.gridLayout.addWidget(self.xLabel, 5, 0, 1, 1)
        self.stepLabel_2 = QtWidgets.QLabel(parent=trackDialog)
        self.stepLabel_2.setObjectName("stepLabel_2")
        self.gridLayout.addWidget(self.stepLabel_2, 8, 3, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=trackDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 7, 0, 1, 1)
        self.dummysampleBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.dummysampleBox.setMinimum(1)
        self.dummysampleBox.setMaximum(999)
        self.dummysampleBox.setProperty("value", 10)
        self.dummysampleBox.setObjectName("dummysampleBox")
        self.gridLayout.addWidget(self.dummysampleBox, 2, 2, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=trackDialog)
        self.label_7.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 14, 0, 1, 1)
        self.label_8 = QtWidgets.QLabel(parent=trackDialog)
        self.label_8.setObjectName("label_8")
        self.gridLayout.addWidget(self.label_8, 0, 0, 1, 1)
        self.xyxstepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.xyxstepLabel.setObjectName("xyxstepLabel")
        self.gridLayout.addWidget(self.xyxstepLabel, 5, 3, 1, 1)
        self.yzyoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.yzyoffsetBox.setDecimals(4)
        self.yzyoffsetBox.setMinimum(-10.0)
        self.yzyoffsetBox.setMaximum(10.0)
        self.yzyoffsetBox.setSingleStep(0.01)
        self.yzyoffsetBox.setObjectName("yzyoffsetBox")
        self.gridLayout.addWidget(self.yzyoffsetBox, 13, 4, 1, 1)
        self.saveBox = QtWidgets.QCheckBox(parent=trackDialog)
        self.saveBox.setObjectName("saveBox")
        self.gridLayout.addWidget(self.saveBox, 0, 2, 1, 1)
        self.yzynumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.yzynumBox.setMinimum(2)
        self.yzynumBox.setMaximum(9999)
        self.yzynumBox.setProperty("value", 21)
        self.yzynumBox.setObjectName("yzynumBox")
        self.gridLayout.addWidget(self.yzynumBox, 13, 2, 1, 1)
        self.xzxnumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.xzxnumBox.setMinimum(2)
        self.xzxnumBox.setMaximum(9999)
        self.xzxnumBox.setProperty("value", 21)
        self.xzxnumBox.setObjectName("xzxnumBox")
        self.gridLayout.addWidget(self.xzxnumBox, 9, 2, 1, 1)
        self.defaultButton = QtWidgets.QPushButton(parent=trackDialog)
        self.defaultButton.setObjectName("defaultButton")
        self.gridLayout.addWidget(self.defaultButton, 0, 3, 1, 1)
        self.pollsampleBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.pollsampleBox.setSuffix("")
        self.pollsampleBox.setMinimum(1000)
        self.pollsampleBox.setMaximum(10000)
        self.pollsampleBox.setSingleStep(1000)
        self.pollsampleBox.setObjectName("pollsampleBox")
        self.gridLayout.addWidget(self.pollsampleBox, 2, 3, 1, 1)
        self.xzxlenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xzxlenBox.setDecimals(4)
        self.xzxlenBox.setMinimum(0.1)
        self.xzxlenBox.setProperty("value", 2.0)
        self.xzxlenBox.setObjectName("xzxlenBox")
        self.gridLayout.addWidget(self.xzxlenBox, 9, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=trackDialog)
        self.label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 10, 0, 1, 1)
        self.numLabel_3 = QtWidgets.QLabel(parent=trackDialog)
        self.numLabel_3.setObjectName("numLabel_3")
        self.gridLayout.addWidget(self.numLabel_3, 12, 2, 1, 1)
        self.xyynumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.xyynumBox.setMinimum(2)
        self.xyynumBox.setMaximum(9999)
        self.xyynumBox.setProperty("value", 21)
        self.xyynumBox.setObjectName("xyynumBox")
        self.gridLayout.addWidget(self.xyynumBox, 6, 2, 1, 1)
        self.label_10 = QtWidgets.QLabel(parent=trackDialog)
        self.label_10.setObjectName("label_10")
        self.gridLayout.addWidget(self.label_10, 1, 0, 1, 1)
        self.xyyoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xyyoffsetBox.setDecimals(4)
        self.xyyoffsetBox.setMinimum(-10.0)
        self.xyyoffsetBox.setMaximum(10.0)
        self.xyyoffsetBox.setSingleStep(0.01)
        self.xyyoffsetBox.setObjectName("xyyoffsetBox")
        self.gridLayout.addWidget(self.xyyoffsetBox, 6, 4, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=trackDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 11, 0, 1, 1)
        self.xyystepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.xyystepLabel.setObjectName("xyystepLabel")
        self.gridLayout.addWidget(self.xyystepLabel, 6, 3, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=trackDialog)
        self.label_6.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 13, 0, 1, 1)
        self.label_9 = QtWidgets.QLabel(parent=trackDialog)
        self.label_9.setObjectName("label_9")
        self.gridLayout.addWidget(self.label_9, 2, 0, 1, 1)
        self.yzzoffsetBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.yzzoffsetBox.setDecimals(4)
        self.yzzoffsetBox.setMinimum(-10.0)
        self.yzzoffsetBox.setMaximum(10.0)
        self.yzzoffsetBox.setSingleStep(0.01)
        self.yzzoffsetBox.setObjectName("yzzoffsetBox")
        self.gridLayout.addWidget(self.yzzoffsetBox, 14, 4, 1, 1)
        self.xzzlenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xzzlenBox.setDecimals(4)
        self.xzzlenBox.setMinimum(0.1)
        self.xzzlenBox.setProperty("value", 2.0)
        self.xzzlenBox.setObjectName("xzzlenBox")
        self.gridLayout.addWidget(self.xzzlenBox, 10, 1, 1, 1)
        self.yzylenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.yzylenBox.setDecimals(4)
        self.yzylenBox.setMinimum(0.1)
        self.yzylenBox.setProperty("value", 2.0)
        self.yzylenBox.setObjectName("yzylenBox")
        self.gridLayout.addWidget(self.yzylenBox, 13, 1, 1, 1)
        self.yzmodeBox = QtWidgets.QComboBox(parent=trackDialog)
        self.yzmodeBox.setObjectName("yzmodeBox")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.yzmodeBox.addItem("")
        self.gridLayout.addWidget(self.yzmodeBox, 12, 0, 1, 1)
        self.xyylenBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.xyylenBox.setDecimals(4)
        self.xyylenBox.setMinimum(0.1)
        self.xyylenBox.setProperty("value", 2.0)
        self.xyylenBox.setObjectName("xyylenBox")
        self.gridLayout.addWidget(self.xyylenBox, 6, 1, 1, 1)
        self.yLabel = QtWidgets.QLabel(parent=trackDialog)
        self.yLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.yLabel.setObjectName("yLabel")
        self.gridLayout.addWidget(self.yLabel, 6, 0, 1, 1)
        self.xzznumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.xzznumBox.setMinimum(2)
        self.xzznumBox.setMaximum(9999)
        self.xzznumBox.setProperty("value", 21)
        self.xzznumBox.setObjectName("xzznumBox")
        self.gridLayout.addWidget(self.xzznumBox, 10, 2, 1, 1)
        self.yzystepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.yzystepLabel.setObjectName("yzystepLabel")
        self.gridLayout.addWidget(self.yzystepLabel, 13, 3, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=trackDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)
        self.yzzstepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.yzzstepLabel.setObjectName("yzzstepLabel")
        self.gridLayout.addWidget(self.yzzstepLabel, 14, 3, 1, 1)
        self.label_11 = QtWidgets.QLabel(parent=trackDialog)
        self.label_11.setObjectName("label_11")
        self.gridLayout.addWidget(self.label_11, 1, 2, 1, 1)
        self.xyxnumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.xyxnumBox.setMinimum(2)
        self.xyxnumBox.setMaximum(9999)
        self.xyxnumBox.setProperty("value", 21)
        self.xyxnumBox.setObjectName("xyxnumBox")
        self.gridLayout.addWidget(self.xyxnumBox, 5, 2, 1, 1)
        self.delayBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.delayBox.setObjectName("delayBox")
        self.gridLayout.addWidget(self.delayBox, 2, 4, 1, 1)
        self.xymodeBox = QtWidgets.QComboBox(parent=trackDialog)
        self.xymodeBox.setObjectName("xymodeBox")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.xymodeBox.addItem("")
        self.gridLayout.addWidget(self.xymodeBox, 4, 0, 1, 1)
        self.yzznumBox = QtWidgets.QSpinBox(parent=trackDialog)
        self.yzznumBox.setMinimum(2)
        self.yzznumBox.setMaximum(9999)
        self.yzznumBox.setProperty("value", 21)
        self.yzznumBox.setObjectName("yzznumBox")
        self.gridLayout.addWidget(self.yzznumBox, 14, 2, 1, 1)
        self.label = QtWidgets.QLabel(parent=trackDialog)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 9, 0, 1, 1)
        self.stepLabel_3 = QtWidgets.QLabel(parent=trackDialog)
        self.stepLabel_3.setObjectName("stepLabel_3")
        self.gridLayout.addWidget(self.stepLabel_3, 12, 3, 1, 1)
        self.lenLabel_2 = QtWidgets.QLabel(parent=trackDialog)
        self.lenLabel_2.setObjectName("lenLabel_2")
        self.gridLayout.addWidget(self.lenLabel_2, 8, 1, 1, 1)
        self.xzzstepLabel = QtWidgets.QLabel(parent=trackDialog)
        self.xzzstepLabel.setObjectName("xzzstepLabel")
        self.gridLayout.addWidget(self.xzzstepLabel, 10, 3, 1, 1)
        self.timeBox = QtWidgets.QDoubleSpinBox(parent=trackDialog)
        self.timeBox.setMinimum(0.1)
        self.timeBox.setMaximum(1000.0)
        self.timeBox.setProperty("value", 10.0)
        self.timeBox.setObjectName("timeBox")
        self.gridLayout.addWidget(self.timeBox, 2, 1, 1, 1)
        self.lenLabel_3 = QtWidgets.QLabel(parent=trackDialog)
        self.lenLabel_3.setObjectName("lenLabel_3")
        self.gridLayout.addWidget(self.lenLabel_3, 12, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(3)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_13 = QtWidgets.QLabel(parent=trackDialog)
        self.label_13.setObjectName("label_13")
        self.verticalLayout_2.addWidget(self.label_13)
        self.upButton = QtWidgets.QPushButton(parent=trackDialog)
        self.upButton.setObjectName("upButton")
        self.verticalLayout_2.addWidget(self.upButton)
        self.downButton = QtWidgets.QPushButton(parent=trackDialog)
        self.downButton.setObjectName("downButton")
        self.verticalLayout_2.addWidget(self.downButton)
        self.horizontalLayout_9.addLayout(self.verticalLayout_2)
        self.orderList = QtWidgets.QListWidget(parent=trackDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.orderList.sizePolicy().hasHeightForWidth())
        self.orderList.setSizePolicy(sizePolicy)
        self.orderList.setMaximumSize(QtCore.QSize(16777215, 100))
        self.orderList.setObjectName("orderList")
        item = QtWidgets.QListWidgetItem()
        self.orderList.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.orderList.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.orderList.addItem(item)
        self.horizontalLayout_9.addWidget(self.orderList)
        self.verticalLayout.addLayout(self.horizontalLayout_9)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=trackDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(trackDialog)
        self.buttonBox.accepted.connect(trackDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(trackDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(trackDialog)
        trackDialog.setTabOrder(self.intervalBox, self.saveBox)
        trackDialog.setTabOrder(self.saveBox, self.defaultButton)
        trackDialog.setTabOrder(self.defaultButton, self.modeBox)
        trackDialog.setTabOrder(self.modeBox, self.linemodeBox)
        trackDialog.setTabOrder(self.linemodeBox, self.timeBox)
        trackDialog.setTabOrder(self.timeBox, self.dummysampleBox)
        trackDialog.setTabOrder(self.dummysampleBox, self.pollsampleBox)
        trackDialog.setTabOrder(self.pollsampleBox, self.delayBox)
        trackDialog.setTabOrder(self.delayBox, self.xymodeBox)
        trackDialog.setTabOrder(self.xymodeBox, self.xzmodeBox)
        trackDialog.setTabOrder(self.xzmodeBox, self.yzmodeBox)
        trackDialog.setTabOrder(self.yzmodeBox, self.xyxlenBox)
        trackDialog.setTabOrder(self.xyxlenBox, self.xyxnumBox)
        trackDialog.setTabOrder(self.xyxnumBox, self.xyxoffsetBox)
        trackDialog.setTabOrder(self.xyxoffsetBox, self.xyylenBox)
        trackDialog.setTabOrder(self.xyylenBox, self.xyynumBox)
        trackDialog.setTabOrder(self.xyynumBox, self.xyyoffsetBox)
        trackDialog.setTabOrder(self.xyyoffsetBox, self.xzxlenBox)
        trackDialog.setTabOrder(self.xzxlenBox, self.xzxnumBox)
        trackDialog.setTabOrder(self.xzxnumBox, self.xzxoffsetBox)
        trackDialog.setTabOrder(self.xzxoffsetBox, self.xzzlenBox)
        trackDialog.setTabOrder(self.xzzlenBox, self.xzznumBox)
        trackDialog.setTabOrder(self.xzznumBox, self.xzzoffsetBox)
        trackDialog.setTabOrder(self.xzzoffsetBox, self.yzylenBox)
        trackDialog.setTabOrder(self.yzylenBox, self.yzynumBox)
        trackDialog.setTabOrder(self.yzynumBox, self.yzyoffsetBox)
        trackDialog.setTabOrder(self.yzyoffsetBox, self.yzzlenBox)
        trackDialog.setTabOrder(self.yzzlenBox, self.yzznumBox)
        trackDialog.setTabOrder(self.yzznumBox, self.yzzoffsetBox)
        trackDialog.setTabOrder(self.yzzoffsetBox, self.orderList)
        trackDialog.setTabOrder(self.orderList, self.upButton)
        trackDialog.setTabOrder(self.upButton, self.downButton)

    def retranslateUi(self, trackDialog):
        _translate = QtCore.QCoreApplication.translate
        trackDialog.setWindowTitle(_translate("trackDialog", "Track scan setting"))
        self.lenLabel.setText(_translate("trackDialog", "length"))
        self.label_12.setText(_translate("trackDialog", "offset"))
        self.numLabel_2.setText(_translate("trackDialog", "num"))
        self.xzxstepLabel.setText(_translate("trackDialog", "1"))
        self.stepLabel.setText(_translate("trackDialog", "step"))
        self.linemodeBox.setItemText(0, _translate("trackDialog", "ASCEND"))
        self.linemodeBox.setItemText(1, _translate("trackDialog", "DESCEND"))
        self.linemodeBox.setItemText(2, _translate("trackDialog", "ZIGZAG"))
        self.numLabel.setText(_translate("trackDialog", "num"))
        self.xzmodeBox.setItemText(0, _translate("trackDialog", "Disable"))
        self.xzmodeBox.setItemText(1, _translate("trackDialog", "Phase Only Correlation"))
        self.xzmodeBox.setItemText(2, _translate("trackDialog", "2D Gaussian"))
        self.xzmodeBox.setItemText(3, _translate("trackDialog", "1D Gaussian (X)"))
        self.xzmodeBox.setItemText(4, _translate("trackDialog", "1D Gaussian (Z)"))
        self.xzmodeBox.setItemText(5, _translate("trackDialog", "Maximum pixel"))
        self.xzmodeBox.setItemText(6, _translate("trackDialog", "1D Maximum (X)"))
        self.xzmodeBox.setItemText(7, _translate("trackDialog", "1D Maximum (Z)"))
        self.modeBox.setItemText(0, _translate("trackDialog", "None"))
        self.intervalBox.setPrefix(_translate("trackDialog", "interval "))
        self.intervalBox.setSuffix(_translate("trackDialog", " s"))
        self.xLabel.setText(_translate("trackDialog", "X"))
        self.stepLabel_2.setText(_translate("trackDialog", "step"))
        self.label_4.setText(_translate("trackDialog", "XZ Track Type"))
        self.dummysampleBox.setPrefix(_translate("trackDialog", "dummy samples "))
        self.label_7.setText(_translate("trackDialog", "Z"))
        self.label_8.setText(_translate("trackDialog", "Set Tracking parameters"))
        self.xyxstepLabel.setText(_translate("trackDialog", "1"))
        self.saveBox.setText(_translate("trackDialog", "Save data"))
        self.defaultButton.setText(_translate("trackDialog", "set default"))
        self.pollsampleBox.setPrefix(_translate("trackDialog", "poll samples "))
        self.label_2.setText(_translate("trackDialog", "Z"))
        self.numLabel_3.setText(_translate("trackDialog", "num"))
        self.label_10.setText(_translate("trackDialog", "Scan mode"))
        self.label_5.setText(_translate("trackDialog", "YZ Track Type"))
        self.xyystepLabel.setText(_translate("trackDialog", "1"))
        self.label_6.setText(_translate("trackDialog", "Y"))
        self.label_9.setText(_translate("trackDialog", "Timing"))
        self.yzmodeBox.setItemText(0, _translate("trackDialog", "Disable"))
        self.yzmodeBox.setItemText(1, _translate("trackDialog", "Phase Only Correlation"))
        self.yzmodeBox.setItemText(2, _translate("trackDialog", "2D Gaussian"))
        self.yzmodeBox.setItemText(3, _translate("trackDialog", "1D Gaussian (Y)"))
        self.yzmodeBox.setItemText(4, _translate("trackDialog", "1D Gaussian (Z)"))
        self.yzmodeBox.setItemText(5, _translate("trackDialog", "Maximum pixel"))
        self.yzmodeBox.setItemText(6, _translate("trackDialog", "1D Maximum (Y)"))
        self.yzmodeBox.setItemText(7, _translate("trackDialog", "1D Maximum (Z)"))
        self.yLabel.setText(_translate("trackDialog", "Y"))
        self.yzystepLabel.setText(_translate("trackDialog", "1"))
        self.label_3.setText(_translate("trackDialog", "XY Track Type"))
        self.yzzstepLabel.setText(_translate("trackDialog", "1"))
        self.label_11.setText(_translate("trackDialog", "Line mode"))
        self.delayBox.setPrefix(_translate("trackDialog", "delay: "))
        self.delayBox.setSuffix(_translate("trackDialog", " ms"))
        self.xymodeBox.setItemText(0, _translate("trackDialog", "Disable"))
        self.xymodeBox.setItemText(1, _translate("trackDialog", "Phase Only Correlation"))
        self.xymodeBox.setItemText(2, _translate("trackDialog", "2D Gaussian"))
        self.xymodeBox.setItemText(3, _translate("trackDialog", "1D Gaussian (X)"))
        self.xymodeBox.setItemText(4, _translate("trackDialog", "1D Gaussian (Y)"))
        self.xymodeBox.setItemText(5, _translate("trackDialog", "Maximum pixel"))
        self.xymodeBox.setItemText(6, _translate("trackDialog", "1D Maximum (X)"))
        self.xymodeBox.setItemText(7, _translate("trackDialog", "1D Maximum (Y)"))
        self.label.setText(_translate("trackDialog", "X"))
        self.stepLabel_3.setText(_translate("trackDialog", "step"))
        self.lenLabel_2.setText(_translate("trackDialog", "length"))
        self.xzzstepLabel.setText(_translate("trackDialog", "1"))
        self.timeBox.setPrefix(_translate("trackDialog", "time window "))
        self.timeBox.setSuffix(_translate("trackDialog", " ms"))
        self.lenLabel_3.setText(_translate("trackDialog", "length"))
        self.label_13.setText(_translate("trackDialog", "Track order"))
        self.upButton.setText(_translate("trackDialog", "Up"))
        self.downButton.setText(_translate("trackDialog", "Down"))
        __sortingEnabled = self.orderList.isSortingEnabled()
        self.orderList.setSortingEnabled(False)
        item = self.orderList.item(0)
        item.setText(_translate("trackDialog", "XY"))
        item = self.orderList.item(1)
        item.setText(_translate("trackDialog", "XZ"))
        item = self.orderList.item(2)
        item.setText(_translate("trackDialog", "YZ"))
        self.orderList.setSortingEnabled(__sortingEnabled)
