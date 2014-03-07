powerlifting-meet-manager
=========================

Powerlifting Meet Manager

Simple program to manage a powerlifting competition with three squats, three bench presses, three deadlifts.
Wilks calculator and team summaries can be done, and the performance of each lifter can be inspected.

Dependencies
------------

Tested on Python 2.7.3, Numpy >= 1.5, PyQt4 >= 4.7.2

Quick Start
-----------

To launch:

    python main.py

Use `Add` to add a lifter.
Each flight can be selected by clicking on the `Flight` heading under `Results`.
All numerical fields under `Results` can then be used to sort the lifters.
For example, to sort by `Squat 1` just click the heading.

All tentative lifts are in italics.
To confirm a lift (attempt), right-click on it and set it to either `Good`, `Fail`, or `Pass`.
The attempt can be completely reset by re-entering in the weight.
Subsequent attempts can only be entered once initial attempts have been confirmed.

To inspect an individual lifter, right-click and select `Performance`.

The table can be saved (pickled) using `Save` and `Load`.
The final results can also be exported to a simple HTML output.

TODO
----

- Correct scoring when a lifter "bombs out".
- Add rack height as a lifter field.
- Add options dialog to control team scoring.
- Dynamic fields.

NOTE
----

This was written up over a couple of days when I was first starting Python. Go easy ...
