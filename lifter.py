##########################################
# File: lifter.py                        #
# Copyright Richard Stebbing 2014.       #
# Distributed under the MIT License.     #
# (See accompany file LICENSE or copy at #
#  http://opensource.org/licenses/MIT)   #
##########################################

# Imports
import numpy as np
import wilks
import weakref

# Setup logger
from log import getLogger
logger = getLogger('basic')

# WeightClasses
WEIGHT_CLASSES_IPF2011 = {
    'M' : np.array([59, 66, 74, 83, 93, 105, 120], dtype=float),
    'F' : np.array([47, 52, 57, 63, 72, 84], dtype=float)
}

WEIGHT_CLASSES_OLD = {
    'M' : np.array([52, 56, 60, 67.5, 75, 82.5, 90, 100, 110, 125],
        dtype=float),
    'F' : np.array([44, 48, 52, 56, 60, 67.5, 75, 82.5, 90],
        dtype=float)
}

# Lifter
class Lifter(object):
    # Set active weight classes
    WEIGHT_CLASSES = WEIGHT_CLASSES_IPF2011

    # Definitions
    GENDERS = ['M', 'F']

    BLANK_LIFT = ' '
    SET_LIFT = 'S'
    GOOD_LIFT = 'G'
    FAIL_LIFT = 'F'
    PASS_LIFT = 'P'
    COMPLETED_LIFT = [GOOD_LIFT, FAIL_LIFT, PASS_LIFT]

    LIFTS = ['squat', 'bench', 'deadlift']
    ATTRIBUTES = ['name', 'gender', 'weight', 'rack_height',
                  'team', 'flight', 'lifter_id',
                  'lifts', 'lift_record']

    def __init__(self, name, gender, weight, rack_height, team=None, flight=0,
        lifter_id=None, collection=None, **kwargs):

        # Check gender
        if gender not in self.GENDERS:
            raise ValueError, 'gender "%s" not in %s' % (gender, self.GENDERS)

        # Set base properties
        self.name = name
        self.gender = gender
        self.weight = weight
        self.rack_height = rack_height
        self.team = team
        self.lifter_id = lifter_id
        self.flight = flight

        # Set lift records
        self.lifts = np.zeros(9, dtype=float)
        self.lift_record = [self.BLANK_LIFT] * 9

        # Save reference to collection if available
        if collection is not None:
            self.collection = weakref.ref(collection)
        else:
            self.collection = None

        # Set any further keyword arguments
        for attr, val in kwargs.iteritems():
            setattr(self, attr, val)

    def __repr__(self):
        str_ = 'Lifter(%r, %r, %.1f, ' % \
            (self.name, self.gender, self.weight)

        fmts = ['%r', '%d', '%d']
        for attr_index, attr in enumerate(['team', 'flight', 'lifter_id']):
            val = getattr(self, attr)
            if val is not None:
                str_ += '%s=%s, ' % (attr, fmts[attr_index] % val)

        return str_[:-2] + ')'

    @property
    def weight_class(self):
        # Get classes for gender
        classes = self.WEIGHT_CLASSES[self.gender]
        indices = np.nonzero(self.weight <= classes)[0]

        try:
            min_index = np.amin(indices)
        except ValueError:
            # Maximum weight class
            weight_class = '%.1f+' % classes[-1]
        else:
            weight_class = '%.1f' % classes[min_index]

        return weight_class

    # Lift enter/validation/getter
    def lift_index(self, lift, attempt):
        base_index = self.LIFTS.index(lift)
        return 3*base_index + (attempt % 3)

    def enter_lift(self, lift, attempt, weight):
        # Check previous attempt is completed
        if attempt > 0:
            index = self.lift_index(lift, attempt - 1)
            if self.lift_record[index] not in self.COMPLETED_LIFT:
                raise ValueError, \
                    'lift=%s, attempt=%d: Previous attempt not completed' % \
                    (lift, attempt)

        # Get index from lift and attempt
        index = self.lift_index(lift, attempt)

        # Set lift
        self.lifts[index] = weight

        # Indicate that lift has been set
        self.lift_record[index] = self.SET_LIFT

    def validate_lift(self, lift, attempt, valid):
        index = self.lift_index(lift, attempt)

        # Check that the lift has been set
        if self.lift_record[index] == self.BLANK_LIFT:
            self.lift_record[index] == self.PASS_LIFT

        elif self.lift_record[index] != self.SET_LIFT:
            logger.warning('lift=%s, attempt=%d is not in set position. ' \
                'Set at %s for %r',
                lift, attempt, self.lift_record[index], self)

        # Set lift record
        if valid is None:       # Lift was passed
            self.lift_record[index] = self.PASS_LIFT
        elif valid == True:     # Lift was good
            self.lift_record[index] = self.GOOD_LIFT
        else:                   # Lift was failed
            self.lift_record[index] = self.FAIL_LIFT

    def get_lift(self, lift, attempt):
        # Return record and lift
        index = self.lift_index(lift, attempt)

        return self.lift_record[index], self.lifts[index]

    # Totals
    def best_lift(self, lift):
        for attempt in [2,1,0]:
            record, weight = self.get_lift(lift, attempt)
            if record == self.GOOD_LIFT:
                return weight
        else:
            return 0.

    @property
    def total(self):
        best_lifts = [self.best_lift(lift) for lift in self.LIFTS]
        return np.sum(best_lifts)

    @property
    def points(self):
        return wilks.points(self.gender, self.weight, self.total)

    # Covenience/helpers
    def required_remaining_total(self, points):
        required_total = wilks.required_total(self.gender, self.weight, points)
        return required_total - self.total()

    # Overall info
    def overall_info(self):
        if self.collection is None:
            return None

        collection = self.collection()

        if collection is None:
            return None

        return collection.overall_info()

    # Pickle
    def __getstate__(self):
        return [getattr(self, attr) for attr in self.ATTRIBUTES]

    def __setstate__(self, state):
        for i, attr in enumerate(self.ATTRIBUTES):
            setattr(self, attr, state[i])
        self.collection = None

# Lifter 'squat', 'bench', and 'deadlift' properties
for lift in Lifter.LIFTS:
    for attempt in [0,1,2]:
        # property factory required so binding of lift and attempt is correct
        def make_property(lift, attempt):
            def getter(self):
                return self.get_lift(lift, attempt)[1]

            def setter(self, value):
                self.enter_lift(lift, attempt, value)

            return property(getter, setter)

        attr = '%s_%d' % (lift, attempt)
        setattr(Lifter,attr, make_property(lift, attempt))

# LifterCollection
class LifterCollection(object):
    ATTRIBUTES = ['map_', 'id_count', 'top']

    def __init__(self, top=3):
        self.map_ = {}
        self.id_count = 0
        self.top = top

    def add(self, lifter):
        # Add lifter_id
        lifter.lifter_id = self.id_count
        self.id_count += 1

        # Set weak reference to this collection
        lifter.collection = weakref.ref(self)

        # Add lifter
        self.map_[lifter.lifter_id] = lifter

    def remove(self, lifter):
        # Remove the lifter from the map
        del self.map_[lifter.lifter_id]

    def sorted_by(self, *el):
        # Initialise list
        l = self.map_.itervalues()

        # Proceed through attributes in reverse
        # Only possible because Python sort is stable!
        for e in reversed(el):
            # Check if reverse on attribute
            reverse = False
            if e.startswith('REV_'):
                e = e.strip('REV_')
                reverse = True

            def key(i):
                return getattr(i, e)

            l = sorted(l, key=key, reverse=reverse)

        return l

    def overall_info(self):
        # Get lifters sorted by points
        # Guarantees correct order in return dictionary
        lifters = self.sorted_by('REV_points', 'weight')

        # Assemble team info dictionary
        ret = {}
        for lifter in lifters:
            try:
                l = ret[lifter.team]
            except KeyError:
                l = [0., []]
                ret[lifter.team] = l

            if len(l[1]) >= self.top:
                continue

            l[0] += lifter.points
            l[1].append(lifter)

        # Get best team
        best_total = (None, 0.)
        for team, info in ret.iteritems():
            if info[0] > best_total[1]:
                best_total = (team, info[0])

        return lifters[0], best_total, ret

    def flights(self):
        flights = []
        for lifter in self.map_.itervalues():
            if lifter.flight not in flights:
                flights.append(lifter.flight)

        return sorted(flights)

    # Convenience
    def __getitem__(self, lifter_id):
        return self.map_[lifter_id]

    # Pickle
    def __getstate__(self):
        return [getattr(self, attr) for attr in self.ATTRIBUTES]

    def __setstate__(self, state):
        for i, attr in enumerate(self.ATTRIBUTES):
            setattr(self, attr, state[i])

        # Reset weak references
        for lifter in self.map_.itervalues():
            lifter.collection = weakref.ref(self)

# Tests

# test_Lifter
def test_Lifter():
    lifter = Lifter('Lifter1','M',70,'Oxford')

    lifter.enter_lift('squat',0,130.)
    lifter.validate_lift('squat',0,True)

    lifter.enter_lift('squat',1,150.)
    lifter.validate_lift('squat',1,True)

    lifter.enter_lift('bench',0,110.)
    lifter.validate_lift('bench',0,True)

    lifter.enter_lift('deadlift',0,195.)
    lifter.validate_lift('deadlift',0,True)

    print lifter.total
    print lifter.points

# test_LifterCollection
def test_LifterCollection():
    collection = LifterCollection()
    collection.add(Lifter('Lifter1','M',70,'Oxford'))
    collection.add(Lifter('Lifter2','M',105,'Oxford'))

    print collection.sorted_by('lifter_id')
    return collection

# main
def main():
    l = test_LifterCollection()
    from pickle_ import dump, load

    dump('l', l)
    a = load('l')

# main
if __name__ == '__main__':
    main()

