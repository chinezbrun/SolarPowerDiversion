# this scrip is used to change MATE 3 status based on wheather prediction, sesonality 
dependency : 
ChangeMateStatus.cfg
MonitorMate for info display

version history
-----------------
0.2.0 20191001     - minor - update error reporting
0.3.1 20191015     - major - introduced weather forcast module
0.3.2 20191101     - minor - introduced two levels for clouds coverage 
0.4.0 20191103     - major - introduced three levels for clouds coverage,
                       added automatic change for Schedule ACMode in Mate based on weather prediction
                       added in config file the target values for Schedule ACMode
0.4.1 20191117     - minor  - adjusted start / end time for minigrid/backup linked with clouds coverage 
0.4.2 20191226     - minor  - very small design adjustments for info/error display messages
0.4.3 20200203     - no change  - update on whetehr prediction limits
0.4.4 20200222     - delay time for Mate3 connect, overlap with other Mate3's connection should be fixed now 