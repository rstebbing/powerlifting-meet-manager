# table.py

# Imports
from PyQt4 import QtCore, QtGui
from collections import namedtuple
from lifter import Lifter, LifterCollection

import wilks
import pickle_
from string import Template

# Setup logger
from log import getLogger
logger = getLogger('qt')

# Section
Section = namedtuple('Section', 'attribute heading format conversion is_lift')

# Globals
HTML_TEMPLATE = Template(
'''<style type="text/css">
table.results
{
font-family:sans-serif;
border-collapse:collapse;
}

table.results td, th
{
font-size:1.0em;
border:1px solid black;
padding:3px 7px 2px 7px;
}

table.results th
{
font-size:1.0em;
font-weight:bold;
text-align:left;
padding-top:5px;
padding-bottom:4px;
background-color:#A9BBFF;
color:black;
}

table.results tr.alt td
{
background-color:#E0E0E0;
}

h1.results
{
font-family:sans-serif;
}

</style>
<html>
<body>
${title}

<div>
<p style="font-family:sans-serif; font-weight:bold;font-size:1.2em;">Overall</p>
<p style="font-family:sans-serif;">
<span style="font-weight:bold;">Best team: </span>${best_team}<br />
<span style="font-weight:bold;">Best lifter: </span>${best_lifter}</p>
</div>

<div>
<p style="font-family:sans-serif; font-weight:bold;font-size:1.2em;">Summary</p>
<table class="results", style="table-layout:auto;">
<tbody>
${tsum}
</tbody>
</table>
</div>

<div>
<p style="font-family:sans-serif; font-weight:bold;font-size:1.2em;">Results</p>
<table class="results", style="width:100%;">
<tbody>
${tbody}
</tbody>
</table>
</div>
''')

# TableModel
class TableModel(QtCore.QAbstractTableModel):
    TRANSLATE_SECTION = [
        Section('gender', 'M/F', '%s', None, False),
        Section('flight', 'Flight', '%d', 'toInt', False),
        Section('team', 'Team', '%s', None, False),
        Section('name', 'Name', '%s', None, False),
        Section('weight', 'Weight', '%.1f', None, False),
        Section('squat_0', 'Squat 1', '%.1f', 'toDouble', True),
        Section('squat_1', 'Squat 2', '%.1f', 'toDouble', True),
        Section('squat_2', 'Squat 3', '%.1f', 'toDouble', True),
        Section('bench_0', 'Bench 1', '%.1f', 'toDouble', True),
        Section('bench_1', 'Bench 2', '%.1f', 'toDouble', True),
        Section('bench_2', 'Bench 3', '%.1f', 'toDouble', True),
        Section('deadlift_0', 'Deadlift 1', '%.1f', 'toDouble', True),
        Section('deadlift_1', 'Deadlift 2', '%.1f', 'toDouble', True),
        Section('deadlift_2', 'Deadlift 3', '%.1f', 'toDouble', True),
        Section('total', 'Total', '%.1f', None, False),
        Section('points', 'Points', '%.2f', None, False)
    ]

    model_changed = QtCore.pyqtSignal()

    def __init__(self, top=3, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.flight_filter = None
        self.last_clicked = None
        self.next_sort = QtCore.Qt.AscendingOrder

        self.lifters_map = LifterCollection(top=top)
        self.sorted_by('lifter_id')

        self.reset()

    # Required Qt methods
    def headerData(self, section, orient, role):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Horizontal:
            section_info = self.TRANSLATE_SECTION[section]

            if section_info.attribute == 'flight':
                if self.flight_filter is not None:
                    return section_info.heading + ' [%d]' % self.flight_filter

            return section_info.heading

        return QtCore.QVariant()

    def index_to_lifter(self, index):
        if not index.isValid():
            return None

        lifter_index, section = index.row(), index.column()
        lifter = self.lifters[lifter_index]
        section_info = self.TRANSLATE_SECTION[section]

        return lifter, section_info

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()

        # Get active lifter and section info
        lifter, section_info = self.index_to_lifter(index)

        if role == QtCore.Qt.DisplayRole:
            # Get section info
            value = getattr(lifter, section_info.attribute)
            return section_info.format % value

        # Handle lift representation here
        elif role == QtCore.Qt.ForegroundRole:
            pass
        elif role == QtCore.Qt.BackgroundRole:
            pass
        elif role == QtCore.Qt.FontRole:
            if section_info.is_lift:
                # Translate attribute string into lift and attempt
                lift, attempt_str = section_info.attribute.split('_')
                attempt = int(attempt_str)

                # Get record
                record = lifter.get_lift(lift, attempt)[0]

                # Set font accordingly
                font = QtGui.QFont()
                if record == Lifter.GOOD_LIFT:
                    font.setBold(True)
                elif record == Lifter.FAIL_LIFT:
                    font.setStrikeOut(True)
                elif record == Lifter.PASS_LIFT:
                    font.setStrikeOut(True)
                    font.setItalic(True)
                elif record == Lifter.SET_LIFT:
                    font.setItalic(True)

                return font

        return QtCore.QVariant()

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        if role == QtCore.Qt.EditRole:
            # Resolve lifter and section
            lifter, section_info = self.index_to_lifter(index)

            # None conversion means it isn't editable
            if section_info.conversion is None:
                return False

            # Convert value
            value, ok = getattr(value, section_info.conversion)()
            if not ok:
                return False

            # Catch entry error
            try:
                setattr(lifter, section_info.attribute, value)
            except ValueError, ex:
                logger.error('Previous attempt not completed.\n%s', ex.message)
                return False

            # Emit change over the specified index
            top_left = self.index(index.row(), 0)
            bottom_right = self.index(index.row(), self.columnCount(None)-1)
            self.dataChanged.emit(top_left, bottom_right)

            # Emit change of the model
            self.model_changed.emit()

            return True

        return False

    def validate_lift(self, index, valid):
        if not index.isValid():
            return

        # Get lifter and section if valid
        lifter, section_info = self.index_to_lifter(index)

        # If section is not a lift then don't do anything
        if not section_info.is_lift:
            return

        # Translate attribute string into lift and attempt
        lift, attempt_str = section_info.attribute.split('_')
        attempt = int(attempt_str)

        # Validate the lift
        lifter.validate_lift(lift, attempt, valid)

        # Emit signals
        self.model_changed.emit()
        self.dataChanged.emit(index, index)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        # Default flags
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

        # Resolve index and check if also editable
        lifter, section_info = self.index_to_lifter(index)

        if section_info.conversion is not None:
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def rowCount(self, parent):
        return len(self.lifters)

    def columnCount(self, parent):
        return len(self.TRANSLATE_SECTION)

    def section_clicked(self, section):
        section_info = self.TRANSLATE_SECTION[section]

        # If flight
        if section_info.attribute == 'flight':
            # Get flights
            flights = self.lifters_map.flights()

            # Get next flight filter
            reset_filter = True
            try:
                index = flights.index(self.flight_filter) + 1
            except ValueError:
                pass
            else:
                reset_filter = False
                if index >= len(flights):
                    self.flight_filter = None
                else:
                    self.flight_filter = flights[index]

            if reset_filter:
                self.flight_filter = flights[0]

        # If NOT flight, sort by attribute, then weight and lifter_id
        else:
            next_sort = QtCore.Qt.AscendingOrder

            if self.last_clicked is not None and \
                self.last_clicked == section_info.attribute:

                if self.next_sort == QtCore.Qt.AscendingOrder:
                    next_sort = QtCore.Qt.DescendingOrder

            self.next_sort = next_sort

            self.last_clicked = section_info.attribute
            self.sorted_by(section_info.attribute, 'weight', 'lifter_id')

        # All paths lead to large change
        self.reset()

    def reset(self):
        # Apply flight filter and reset it if required
        reset_all = True

        if self.flight_filter is not None:
            self.lifters = [l for l in self.lifters_ if l.flight == \
                self.flight_filter]

            if len(self.lifters) > 0:
                reset_all = False

        if reset_all:
            self.lifters = self.lifters_[:]
            self.flight_filter = None

        # reset
        QtCore.QAbstractTableModel.reset(self)

    # Sort method
    def sorted_by(self, *args):
        if len(args) > 0:
            # Save args
            self.sort_args = args

        # Sort based on args
        sort_args = list(self.sort_args)

        # Only reverse first attribute as others are used to tie-break
        if self.next_sort == QtCore.Qt.DescendingOrder:
            sort_args[0] = 'REV_' + sort_args[0]

        self.lifters_ = self.lifters_map.sorted_by(*sort_args)

    # Add / remove methods
    def add(self, lifter):
        self.lifters_map.add(lifter)

        self.sorted_by()
        self.reset()

        # Emit change of model
        self.model_changed.emit()

    def remove(self, index):
        if not index.isValid():
            return

        lifter, section_info = self.index_to_lifter(index)
        self.lifters_map.remove(lifter)

        self.sorted_by()
        self.reset()

        # Emit change of model
        self.model_changed.emit()

    # Save / load / export
    def save(self, file_):
        pickle_.dump(file_, self.lifters_map)

    def load(self, file_):
        self.lifters_map = pickle_.load(file_)

        self.sorted_by()
        self.reset()

    def export(self, file_):
        # Results summary

        # Get overall info
        best_lifter, best_total, team_info = self.lifters_map.overall_info()

        # Overall
        best_team = '%s [%.2f]' % best_total
        best_lifter = '%s [%.2f]' % \
            (best_lifter.name, best_lifter.points)

        # Team summary
        tsum = ''

        # Headers
        tsum += '<tr>'
        for heading in ['Team / lifter', 'Points']:
            tsum += '<th>%s</th>' % heading
        tsum += '</tr>\n'

        # Summary
        row = 0
        for team, info in team_info.iteritems():
            # Prepare data to output
            data = [(team, info[0])]
            for lifter in info[1]:
                data.append( ('&nbsp;' * 4 + lifter.name, lifter.points) )

            # Output the data
            for perf, points in data:
                # Alternate colours of rows
                if row % 2 == 1:
                    row_str = '<tr class="alt">'
                else:
                    row_str = '<tr>'

                # Manually increment row
                row += 1

                row_str += '<td>%s</td><td>%.2f</td></tr>\n' % (perf, points)
                tsum += row_str

        # Main results
        tbody = ''

        # Headers
        tbody += '<tr>'
        for section_info in self.TRANSLATE_SECTION:
            tbody += '<th>%s</th>' % section_info.heading
        tbody += '</tr>\n'

        # Get lifters sorted by points, then weight, then id
        lifters = self.lifters_map.sorted_by(
            'REV_points', 'weight', 'lifter_id'
        )

        # Results table
        for row, lifter in enumerate(lifters):
            # Alternate colours of rows
            if row % 2 == 1:
                row_str = '<tr class="alt">'
            else:
                row_str = '<tr>'

            # Add data
            for section_info in self.TRANSLATE_SECTION:
                # Get data as string
                value = getattr(lifter, section_info.attribute)
                data = section_info.format % value

                # If a lift, set up style string
                style_str = '"'
                if section_info.is_lift:
                    # Translate attribute string into lift and attempt
                    lift, attempt_str = section_info.attribute.split('_')
                    attempt = int(attempt_str)

                    # Get record
                    record = lifter.get_lift(lift, attempt)[0]

                    # Set font accordingly
                    if record == Lifter.GOOD_LIFT:
                        style_str += 'font-weight:bold;'
                    elif record == Lifter.FAIL_LIFT:
                        style_str += 'text-decoration:line-through;'
                    elif record == Lifter.PASS_LIFT:
                        style_str += 'text-decoration:line-through;' \
                            'font-style:italic;'
                    elif record == Lifter.SET_LIFT:
                        style_str += 'font-style:italic;'

                style_str += '"'

                # If style str is added
                if len(style_str) > 2:
                    row_str += '<td style=%s>%s</td>' % (style_str, data)
                else:
                    row_str += '<td>%s</td>' % data

            row_str += '</tr>\n'
            tbody += row_str

        # XXX Set title
        title = ''

        # Save full table
        html_table = HTML_TEMPLATE.substitute(
            title=title,
            best_team=best_team,
            best_lifter=best_lifter,
            tsum=tsum,
            tbody=tbody)
        with open(file_, 'w') as fp:
            fp.write(html_table)

# TableView
class TableView(QtGui.QTableView):
    PERFORMANCE_TEXT = '&Performance'
    SUMMARY_TEXT = '&Summary'
    GOOD_LIFT = '&Good lift'
    FAIL_LIFT = '&Fail lift'
    PASS_LIFT = '&Pass lift'

    def __init__(self, model, parent=None):
        QtGui.QTableView.__init__(self, parent)

        self.setModel(model)

        self.setup_menus()
        self.setup_ui()

    def setup_menus(self):
        menu = QtGui.QMenu()
        menu.addAction(self.PERFORMANCE_TEXT)
        menu.addAction(self.SUMMARY_TEXT)
        self.general_menu = menu

        menu = QtGui.QMenu()
        menu.addAction(self.GOOD_LIFT)
        menu.addAction(self.FAIL_LIFT)
        menu.addAction(self.PASS_LIFT)
        menu.addSeparator()
        menu.addAction(self.PERFORMANCE_TEXT)
        menu.addAction(self.SUMMARY_TEXT)
        self.lift_menu = menu

    def setup_ui(self):
        self.verticalHeader().setVisible(False)

        # Default header column behaviour is to stretch
        self.horizontalHeader().setResizeMode(
            QtGui.QHeaderView.Stretch
        )

        # Otherwise resize to contents
        headings = [i.heading for i in TableModel.TRANSLATE_SECTION]
        for heading in ['M/F', 'Flight', 'Weight', 'Team', 'Name']:
            i = headings.index(heading)
            self.horizontalHeader().setResizeMode(i,
                QtGui.QHeaderView.ResizeToContents
            )

        # Set general size policy
        self.setSizePolicy(
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding
        )

        # Set click connections
        # self.setSortingEnabled(True)
        self.horizontalHeader().setClickable(True)
        self.horizontalHeader().sectionClicked.connect(
            self.model().section_clicked
        )

        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

    def contextMenuEvent(self, event):
        # Check from mouse
        if event.reason() != QtGui.QContextMenuEvent.Mouse:
            return

        # Check index
        index = self.indexAt(event.pos())
        if not index.isValid():
            return

        # From the index get the lifter and section info
        lifter, section_info = self.model().index_to_lifter(index)

        # Execute the menu
        if section_info.is_lift:
            menu = self.lift_menu
        else:
            menu = self.general_menu

        action = menu.exec_(self.mapToGlobal(event.pos()))

        # Interpret the result
        if action is None:
            return

        if action.text() == self.PERFORMANCE_TEXT:
            # Perforamnce dialog
            dialog = PerformanceDialog(self)
            dialog.set_lifter(lifter)
            dialog.exec_()
            return

        elif action.text() == self.SUMMARY_TEXT:
            # Summary dialog
            dialog = SummaryDialog(self)
            dialog.set_lifter(lifter)
            dialog.exec_()
            return

        if section_info.is_lift:
            # Determine if the lift is good, fail, or pass
            if action.text() == self.PASS_LIFT:
                valid = None
            elif action.text() == self.GOOD_LIFT:
                valid = True
            else:
                valid = False

            # Validate the lift
            self.model().validate_lift(index, valid)

# PerformanceDialog
class PerformanceDialog(QtGui.QDialog):
    def __init__(self, parent=None, flags=QtCore.Qt.Dialog):
        QtGui.QDialog.__init__(self, parent, flags)

        self.setup_ui()

    def setup_ui(self):
        self.lifter_info = QtGui.QLabel('')

        left_layout = QtGui.QGridLayout()
        attributes = Lifter.LIFTS + ['total', 'points']

        for i, attr in enumerate(attributes):
            title = attr[0].upper() + attr[1:]
            label_0 = QtGui.QLabel('%s:' % title)
            label = QtGui.QLabel('')

            left_layout.addWidget(label_0, i, 0)
            left_layout.addWidget(label, i, 1)

            setattr(self, '%s_label' % attr, label)

        offset = len(attributes)

        attributes = ['team_total', 'best_total', 'best_team', 'difference',
            'projected_points', 'projected_total']
        titles = ['Team total', 'Best total', 'Best team', 'Difference',
            'Projected points', 'Projected total']

        for i, (attr, title) in enumerate(zip(attributes, titles)):
            label_0 = QtGui.QLabel('%s:' % title)

            if i < 4:
                post = 'label'
                label = QtGui.QLabel('')
            else:
                post = 'edit'
                label = QtGui.QLineEdit('')

            left_layout.addWidget(label_0, i + offset, 0)
            left_layout.addWidget(label, i + offset, 1)

            setattr(self, '%s_%s' % (attr, post), label)

        # Connections
        self.projected_points_edit.textEdited.connect(
            self.slot_projected_points
        )

        self.projected_total_edit.textEdited.connect(
            self.slot_projected_total
        )

        # Main layout
        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(self.lifter_info)
        main_layout.addLayout(left_layout)

        self.setLayout(main_layout)

    def set_lifter(self, lifter):
        self.lifter = lifter

        self.setWindowTitle('Performance: %s' % lifter.name)

        # Set lifter information
        self.lifter_info.setText(
            '%s, %.1f, %s' % (lifter.name, lifter.weight, lifter.team)
        )

        # Set best lifts
        for lift in Lifter.LIFTS:
            value = lifter.best_lift(lift)
            label = getattr(self, '%s_label' % lift)
            label.setText('%.1f' % value)

        # Set total and points
        for attr in ['total', 'points']:
            label = getattr(self, '%s_label' % attr)
            label.setText('%.2f' % getattr(lifter, attr))

        # Get team info
        _, best_total, team_info = lifter.overall_info()
        team_total, _ = team_info[lifter.team]

        # Get difference to best_total
        difference = best_total[1] - team_total

        # Set team points
        self.team_total_label.setText('%.2f' % team_total)
        self.best_team_label.setText('%s' % best_total[0])
        self.best_total_label.setText('%.2f' % best_total[1])
        self.difference_label.setText('%.2f' % difference)

        self.projected_points_edit.setText('%.2f' % (difference + lifter.points))

        # Call slot manually (not called with programmatic change to text)
        self.slot_projected_points(self.projected_points_edit.text())

    # Slots
    def slot_projected_points(self, text):
        points, ok = text.toDouble()
        if not ok:
            return

        total = wilks.required_total(self.lifter.gender, self.lifter.weight,
            points)

        self.projected_total_edit.setText('%.2f' % total)

    def slot_projected_total(self, text):
        total, ok = text.toDouble()
        if not ok:
            return

        points = wilks.points(self.lifter.gender, self.lifter.weight,
            total)

        self.projected_points_edit.setText('%.2f' % points)

# SummaryDialog
class SummaryDialog(QtGui.QDialog):
    def __init__(self, parent=None, flags=QtCore.Qt.Dialog):
        QtGui.QDialog.__init__(self, parent, flags)

        self.setup_ui()

    def setup_ui(self):
        self.tree = QtGui.QTreeWidget(self)
        self.tree.setColumnCount(2)
        header_item = QtGui.QTreeWidgetItem(
            None,
            ['Team / lifter', 'Points']
        )
        self.tree.setHeaderItem(header_item)
        header = self.tree.header()
        header.setResizeMode(QtGui.QHeaderView.ResizeToContents)

        attributes = ['best_team', 'best_lifter']
        titles = ['Best team', 'Best lifter']

        label_layout = QtGui.QVBoxLayout()
        for attr, title in zip(attributes, titles):
            label_0 = QtGui.QLabel('%s:' % title)
            label = QtGui.QLabel('')

            line_layout = QtGui.QHBoxLayout()
            line_layout.addWidget(label_0)
            line_layout.addWidget(label)
            line_layout.addStretch(1)

            label_layout.addLayout(line_layout)

            setattr(self, '%s_label' % attr, label)

        main_layout = QtGui.QVBoxLayout()
        main_layout.addWidget(self.tree)
        main_layout.addLayout(label_layout)

        self.setLayout(main_layout)

    def set_lifter(self, lifter):
        self.lifter = lifter

        self.setWindowTitle('Summary: %s' % lifter.name)

        # Get team info as sorted by team name
        best_lifter, best_total, team_info = lifter.overall_info()
        team_info = sorted(team_info.iteritems(), key=lambda x: x[0].lower())

        # Add to the tree widget and get best team total
        best_total = (None, 0.)
        for i, (team, info) in enumerate(team_info):
            if info[0] > best_total[1]:
                best_total = (team, info[0])

            # Construct team item
            team_item = QtGui.QTreeWidgetItem(
                None,
                [team, '%.2f' % info[0]]
            )

            # Construct member items
            for lifter in info[1]:
                item = QtGui.QTreeWidgetItem(
                    None,
                    [lifter.name, '%.2f' % lifter.points]
                )
                team_item.addChild(item)


            # Save top level item
            self.tree.insertTopLevelItem(i, team_item)

        # Set best team
        self.best_team_label.setText('%s [%.2f]' % best_total)

        # Set the best lifter
        self.best_lifter_label.setText('%s [%.2f]' % \
            (best_lifter.name, best_lifter.points))

