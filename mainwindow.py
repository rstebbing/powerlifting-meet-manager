# mainwindow

# Imports
from PyQt4 import QtCore, QtGui
import StringIO, traceback, sys

from lifter import Lifter, LifterCollection
from table import TableModel, TableView

import os

# Setup logger
import log
logger = log.getLogger('qt')

# Constants
TOP_LIFTERS = 6

# AddLifterDialog
class AddLifterDialog(QtGui.QDialog):
    TRANSLATE_ATTRIBUTE = [
        ('name', '&Name', '', None),
        ('gender', '&Gender', 'M', None),
        ('weight', '&Weight', '', 'toDouble'),
        ('team', '&Team', '', None),
        ('squat_0', '&Squat 1', '', 'toDouble'),
        ('bench_0', '&Bench 1', '', 'toDouble'),
        ('deadlift_0', '&Deadlift 1', '', 'toDouble'),
        ('flight', '&Flight', '0', 'toInt'),
    ]

    def __init__(self, parent=None, flags=QtCore.Qt.Dialog):
        QtGui.QDialog.__init__(self, parent, flags)

        self.setup_ui()

        self.lifter_ = None

    def setup_ui(self):
        # Construct input layout
        input_layout = QtGui.QGridLayout()

        for i, ti in enumerate(self.TRANSLATE_ATTRIBUTE):
            label = QtGui.QLabel(ti[1])
            edit = QtGui.QLineEdit(ti[2])
            label.setBuddy(edit)

            input_layout.addWidget(label, i, 0)
            input_layout.addWidget(edit, i, 1)

            setattr(self, ti[0] + '_edit', edit)

        # Construct button layout
        self.add_pb = QtGui.QPushButton('&Add')

        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.add_pb)
        button_layout.addStretch(1)

        # Set add connections
        self.add_pb.clicked.connect(self.add_lifter)

        # Construct main layout
        main_layout = QtGui.QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # Title
        self.setWindowTitle('Add Lifter')

    def lifter(self):
        return self.lifter_

    def add_lifter(self):
        # Construct initialisation dictionary
        d = {}
        for ti in self.TRANSLATE_ATTRIBUTE:
            # Get line edit
            edit = getattr(self, ti[0] + '_edit')

            # Check text
            text = edit.text()
            if text.isEmpty():
                return False

            # Get value
            if ti[3] is None:
                val = str(text)
            else:
                val, ok = getattr(text, ti[3])()
                if not ok:
                    logger.error(
                        "Failure in conversion '%s' with field '%s' <%s>",
                        ti[3], ti[1].replace('&',''), ti[0]
                    )
                    return

            d[ti[0]] = val

        # Construct lifter
        try:
            self.lifter_ = Lifter(**d)
        except ValueError, ex:
            logger.error(
                "Failure in initialising lifter:\n%s",
                ex.message
            )
            return

        self.accept()
        return

# MainWindow
class MainWindow(QtGui.QMainWindow):
    TEMP_FILENAME = '.powerlifting_temp.dat'
    AUTO_INTERVAL = 600000   # 10 minutes

    def __init__(self, parent=None, flags=QtCore.Qt.Window):
        QtGui.QMainWindow.__init__(self, parent, flags)

        self.setup_ui()

        self.last_dir = '.'

        # Install global exception handler
        sys.excepthook = self.global_exception_handler

        # Initialise autosave
        self.setup_autosave()

        # Set this as the Qt log parent
        log.set_qt_parent(self)

    def setup_ui(self):
        # Set title
        self.setWindowTitle('Powerlifting Meet Manager')

        # Setup table model
        self.table_model = TableModel(top=TOP_LIFTERS)

        # Setup the table view
        self.table_view = TableView(self.table_model)

        # Setup the lifter group
        self.pb_lifter_add = QtGui.QPushButton('&Add')
        self.pb_lifter_remove = QtGui.QPushButton('&Remove')

        layout_lifter = QtGui.QHBoxLayout()
        layout_lifter.addWidget(self.pb_lifter_add)
        layout_lifter.addWidget(self.pb_lifter_remove)

        grp_lifter = QtGui.QGroupBox('Lifter')
        grp_lifter.setLayout(layout_lifter)

        # Setup the lifter group signals
        self.pb_lifter_add.clicked.connect(self.add_lifter)
        self.pb_lifter_remove.clicked.connect(self.remove_lifter)

        # Setup the control group
        self.pb_save_results = QtGui.QPushButton('&Save')
        self.pb_load_results = QtGui.QPushButton('&Load')
        self.pb_export_results = QtGui.QPushButton('&Export')

        layout_control = QtGui.QHBoxLayout()
        layout_control.addWidget(self.pb_save_results)
        layout_control.addWidget(self.pb_load_results)
        layout_control.addWidget(self.pb_export_results)

        grp_control = QtGui.QGroupBox('Control')
        grp_control.setLayout(layout_control)

        # Setup the control group signals
        self.pb_load_results.clicked.connect(self.load)
        self.pb_save_results.clicked.connect(self.save)
        self.pb_export_results.clicked.connect(self.export)

        # Set the header layout
        layout_header = QtGui.QHBoxLayout()
        layout_header.addWidget(grp_lifter)
        layout_header.addStretch(1)
        layout_header.addWidget(grp_control)

        # Results group
        grp_results = QtGui.QGroupBox('Results')
        layout_results = QtGui.QHBoxLayout()
        layout_results.addWidget(self.table_view)
        grp_results.setLayout(layout_results)

        # Main layout
        main_layout = QtGui.QVBoxLayout()
        main_layout.addLayout(layout_header)
        main_layout.addWidget(grp_results)

        main_widget = QtGui.QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    # Autosave
    def setup_autosave(self):
        # Initialise mutex
        self.auto_mutex = QtCore.QMutex()

        # Set automatic timer
        self.auto_timer = QtCore.QTimer()
        self.auto_timer.timeout.connect(self.autosave)

        self.auto_timer.setSingleShot(False)
        self.auto_timer.setInterval(self.AUTO_INTERVAL)

        # Enable autosave
        self.set_autosave(True)

    def set_autosave(self, enable):
        if enable:
            # Save on changes to model
            self.table_model.model_changed.connect(self.autosave)

            # Start timer
            self.auto_timer.start()
        else:
            # Lock mutex
            self.auto_mutex.lock()

            # Stop timer
            self.auto_timer.stop()

            # Disconnect on changes to model
            self.table_model.model_changed.disconnect(self.autosave)

            # Unlock mutex
            self.auto_mutex.unlock()

    def autosave(self):
        # Lock mutex
        self.auto_mutex.lock()

        # Save the model to the temp filename
        self.table_model.save(self.TEMP_FILENAME)

        # Unlock mutex
        self.auto_mutex.unlock()

    # Close
    def closeEvent(self, event):
        result = QtGui.QMessageBox.question(self,
            'Exit',
            'Are you sure you want to exit?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No ,
            QtGui.QMessageBox.No
        )

        if result != QtGui.QMessageBox.Yes:
            event.ignore()
        else:
            # Disable autosave
            self.set_autosave(False)

            # Unregister exception hook
            sys.excepthook = sys.__excepthook__
            event.accept()

        return

    # Lifter addition/removal slots
    def add_lifter(self):
        # Show a new lifter dialog
        dlg = AddLifterDialog(self)
        dlg.exec_()

        if dlg.result():
            # Get lifter
            lifter = dlg.lifter()
            self.table_model.add(lifter)

    def remove_lifter(self):
        # Get active lifter
        index = self.table_view.currentIndex()

        lifter_info = self.table_model.index_to_lifter(index)
        if lifter_info is None:
            return

        lifter = lifter_info[0]

        # Check to remove lifter
        result = QtGui.QMessageBox.question(self,
            'Remove Lifter',
            "Remove lifter '%s'?" % lifter.name,
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No ,
            QtGui.QMessageBox.No
        )

        if result != QtGui.QMessageBox.Yes:
            return

        # Remove the lifter at index
        self.table_model.remove(index)

    # Control button slots
    def save(self):
        full_path = QtGui.QFileDialog.getSaveFileName(
            self, 'Save', self.last_dir, '*.dat'
        )

        if full_path.isEmpty():
            return

        # Decompose full path (e.g. for checks)
        dir_, filename = os.path.split(str(full_path))
        self.last_dir = dir_

        root, ext = os.path.splitext(filename)

        # Put back together
        full_path = os.path.join(dir_, root + '.dat')

        self.table_model.save(full_path)

    def load(self):
        full_path = QtGui.QFileDialog.getOpenFileName(
            self, 'Load', self.last_dir, '*.dat'
        )

        if full_path.isEmpty():
            return

        # Decompose full path
        full_path = str(full_path)
        dir_, filename = os.path.split(full_path)
        self.last_dir = dir_

        self.table_model.load(full_path)

    def export(self):
        full_path = QtGui.QFileDialog.getSaveFileName(
            self, 'Export', self.last_dir, '*.html'
        )

        if full_path.isEmpty():
            return

        # Decompose full path (e.g. for checks)
        dir_, filename = os.path.split(str(full_path))
        self.last_dir = dir_

        root, ext = os.path.splitext(filename)

        full_path = os.path.join(dir_, root + '.html')

        self.table_model.export(full_path)

    @classmethod
    def global_exception_handler(cls, type_, exception, tb):
        string_buffer = StringIO.StringIO()
        traceback.print_tb(tb, None, string_buffer)

        logger.error(
            'Unhandled Exception\n%s, "%s"\n:: %s',
            type_.__name__,
            exception.message,
            string_buffer.getvalue()
        )

        string_buffer.close()

