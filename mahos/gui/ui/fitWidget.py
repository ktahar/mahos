# Form implementation generated from reading ui file 'fitWidget.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_FitWidget(object):
    def setupUi(self, FitWidget):
        FitWidget.setObjectName("FitWidget")
        FitWidget.resize(1344, 953)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(FitWidget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.splitter_2 = QtWidgets.QSplitter(parent=FitWidget)
        self.splitter_2.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.verticalLayoutWidget = QtWidgets.QWidget(parent=self.splitter_2)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.indexBox = QtWidgets.QSpinBox(parent=self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.indexBox.sizePolicy().hasHeightForWidth())
        self.indexBox.setSizePolicy(sizePolicy)
        self.indexBox.setMinimumSize(QtCore.QSize(0, 0))
        self.indexBox.setMaximumSize(QtCore.QSize(160, 16777215))
        self.indexBox.setBaseSize(QtCore.QSize(0, 0))
        self.indexBox.setMinimum(-1)
        self.indexBox.setMaximum(999)
        self.indexBox.setProperty("value", -1)
        self.indexBox.setObjectName("indexBox")
        self.horizontalLayout.addWidget(self.indexBox)
        self.loadButton = QtWidgets.QPushButton(parent=self.verticalLayoutWidget)
        self.loadButton.setObjectName("loadButton")
        self.horizontalLayout.addWidget(self.loadButton)
        self.popbufButton = QtWidgets.QPushButton(parent=self.verticalLayoutWidget)
        self.popbufButton.setObjectName("popbufButton")
        self.horizontalLayout.addWidget(self.popbufButton)
        self.clearbufButton = QtWidgets.QPushButton(parent=self.verticalLayoutWidget)
        self.clearbufButton.setObjectName("clearbufButton")
        self.horizontalLayout.addWidget(self.clearbufButton)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.splitter = QtWidgets.QSplitter(parent=self.verticalLayoutWidget)
        self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.splitter.setObjectName("splitter")
        self.bufferTable = QtWidgets.QTableWidget(parent=self.splitter)
        self.bufferTable.setObjectName("bufferTable")
        self.bufferTable.setColumnCount(0)
        self.bufferTable.setRowCount(0)
        self.resultEdit = QtWidgets.QTextEdit(parent=self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.resultEdit.sizePolicy().hasHeightForWidth())
        self.resultEdit.setSizePolicy(sizePolicy)
        self.resultEdit.setReadOnly(True)
        self.resultEdit.setObjectName("resultEdit")
        self.verticalLayout.addWidget(self.splitter)
        self.layoutWidget = QtWidgets.QWidget(parent=self.splitter_2)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.fitButton = QtWidgets.QPushButton(parent=self.layoutWidget)
        self.fitButton.setObjectName("fitButton")
        self.horizontalLayout_3.addWidget(self.fitButton)
        self.clearfitButton = QtWidgets.QPushButton(parent=self.layoutWidget)
        self.clearfitButton.setObjectName("clearfitButton")
        self.horizontalLayout_3.addWidget(self.clearfitButton)
        self.methodBox = QtWidgets.QComboBox(parent=self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.methodBox.sizePolicy().hasHeightForWidth())
        self.methodBox.setSizePolicy(sizePolicy)
        self.methodBox.setObjectName("methodBox")
        self.horizontalLayout_3.addWidget(self.methodBox)
        self.applyloadBox = QtWidgets.QCheckBox(parent=self.layoutWidget)
        self.applyloadBox.setChecked(True)
        self.applyloadBox.setObjectName("applyloadBox")
        self.horizontalLayout_3.addWidget(self.applyloadBox)
        self.applyresultBox = QtWidgets.QCheckBox(parent=self.layoutWidget)
        self.applyresultBox.setChecked(True)
        self.applyresultBox.setObjectName("applyresultBox")
        self.horizontalLayout_3.addWidget(self.applyresultBox)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.paramTable = ParamTable(parent=self.layoutWidget)
        self.paramTable.setObjectName("paramTable")
        self.paramTable.setColumnCount(0)
        self.paramTable.setRowCount(0)
        self.verticalLayout_2.addWidget(self.paramTable)
        self.verticalLayout_3.addWidget(self.splitter_2)

        self.retranslateUi(FitWidget)
        QtCore.QMetaObject.connectSlotsByName(FitWidget)
        FitWidget.setTabOrder(self.loadButton, self.bufferTable)

    def retranslateUi(self, FitWidget):
        _translate = QtCore.QCoreApplication.translate
        FitWidget.setWindowTitle(_translate("FitWidget", "Form"))
        self.indexBox.setPrefix(_translate("FitWidget", "index: "))
        self.loadButton.setText(_translate("FitWidget", "Load"))
        self.popbufButton.setText(_translate("FitWidget", "Pop"))
        self.clearbufButton.setText(_translate("FitWidget", "Clear Buffer"))
        self.fitButton.setText(_translate("FitWidget", "Fit"))
        self.clearfitButton.setText(_translate("FitWidget", "Clear Fit"))
        self.applyloadBox.setText(_translate("FitWidget", "apply loaded"))
        self.applyresultBox.setText(_translate("FitWidget", "apply result"))
from mahos.gui.param import ParamTable
