##########################################
# File: log.py                           #
# Copyright Richard Stebbing 2014.       #
# Distributed under the MIT License.     #
# (See accompany file LICENSE or copy at #
#  http://opensource.org/licenses/MIT)   #
##########################################

# Imports
import logging, sys
from logging import getLogger, Handler
from PyQt4 import QtGui

# basic_formatter
BASIC_FMT = '<%(asctime)s> %(levelname)s::%(module)s.%(funcName)s [%(lineno)d]:: %(message)s'
BASIC_DATEFMT = '%H:%M:%S'
basic_formatter = logging.Formatter(BASIC_FMT, BASIC_DATEFMT)

# basic_logger
basic_handler = logging.StreamHandler(sys.stderr)
basic_handler.setFormatter(basic_formatter)

basic_logger = logging.getLogger('basic')
basic_logger.setLevel(logging.INFO)
basic_logger.addHandler(basic_handler)

# QtHandler
class QtHandler(Handler):
    MESSAGE_BOXES = {
        logging.DEBUG : QtGui.QMessageBox.information,
        logging.INFO : QtGui.QMessageBox.information,
        logging.WARNING : QtGui.QMessageBox.warning,
        logging.ERROR : QtGui.QMessageBox.critical,
        logging.CRITICAL : QtGui.QMessageBox.critical
    }

    def __init__(self, parent=None):
        Handler.__init__(self)
        self.parent = parent

    def emit(self, record):
        # Don't emit at levels with no message box
        try:
            msg_box = self.MESSAGE_BOXES[record.levelno]
        except KeyError:
            return

        msg_box(
            self.parent,
            record.levelname,
            self.format(record)
        )

# qt_formatter
GUI_FMT = '<%(asctime)s> %(module)s.%(funcName)s [%(lineno)d]::\n%(message)s'
GUI_DATEFMT = '%H:%M:%S'
qt_formatter = logging.Formatter(GUI_FMT, GUI_DATEFMT)

# qt_logger
qt_logger = logging.getLogger('qt')
qt_logger.setLevel(logging.INFO)

# set_qt_parent
qt_handler = None
def set_qt_parent(parent):
    # Remove and replace past qt_handler
    global qt_handler

    if qt_handler is not None:
        qt_logger.removeHandler(qt_handler)

    qt_handler = QtHandler(parent)
    qt_handler.setFormatter(qt_formatter)

    qt_logger.addHandler(qt_handler)

# qt_handler
set_qt_parent(None)

