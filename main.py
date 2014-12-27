##########################################
# File: main.py                          #
# Copyright Richard Stebbing 2014.       #
# Distributed under the MIT License.     #
# (See accompany file LICENSE or copy at #
#  http://opensource.org/licenses/MIT)   #
##########################################

# Imports
import sys
from PyQt4 import QtGui
from mainwindow import MainWindow

# main
def main():
    qapp = QtGui.QApplication(sys.argv)

    mainwindow = MainWindow()
    mainwindow.show()

    qapp.exec_()

if __name__ == '__main__':
    main()

