# this script is used to optimmise solar power in OutBack system
# runs on Raspberry PI 

version history
-----------------------
05.08.2018 - v3 introducere statistics, split over power (3500) pe cele doua load, 
13.12.2018 - v3 line 124 - enhancement: deleted AC grid conditon-> divert active when FLOAT
13.12.2018 - v3 line 102 - bug fix: corect error then temperature is with 1 digit
13.12.2018 - v3 line 246 - enhancement: add save of json file in case of error
04.02.2019 - v3 line 125 - update string format "Float  " with 2 blank spaces - JSON changed due to firmware update on MATE3 v 3.019
20.02.2019 - v4 major ver- start stop utilitati/parter based on SOC - main block line 127,GPIO 23 used,inclued in print output and error output log , small cosmetics on print
23.03.2019 - v4 minor    - bug fix in reporting of last time pwr cut 
15.04.2019 - v5 major - adaptat cod pentru a lucra cu doua invertoare - modificat data Json line 85 si max inverter power line 128
21.04.2019 - v5 minor - line 87 modif sursa JSON file din SYN to V4, line 158,172,240 - corectie pt a citi corect noul JSON, line 64,306 - cod pentru a copia rasp_log si rasp_error in locatia web v4
07.05.2019 - v6 minor - use json from modbus folder , changed all related links
06.06.2019 - v7 minor - directories restructured - update links 
17.06.2019 - v8 major - update cod to use external *.cfg file with variables, diversion available now (load 01) when diversion relay is closed forced
                      - fix DC diversion in EQ or charged (use bat voltage)
                      - fix calculation of grid/solar usage - now is based on voltage
                      - reset usage time on specific hour 
                      - error log subroutine simplified and add log for unknown error
22.06.2019 -v0.9 major- include compensated voltage for reference - varialble name changed
30.06.2019            - include EQ in diversion subroutine - in loop diversion by state
03.07.2019            - minor design changes
12.07.2019            - change load 1 logic - to alow one more loop for the case of load 2 inactive_skip (to reevaluate the battery and divert power)
16.10.2019 -v1.0 major- first release 
                      - data, info log renamed and path changed
27.10.2019 -v1.0 minor- small design modification for info log
30.10.2019 -v1.0 minor- file name changed, paths and name of config file 
05.01.2020 -v1.0 minor- when the boiler temp file is empty, program exit with error - now is fixed
03.03.2020 - 1.0.1_202000303 - include mqtt module - not used now - preparation for future transmission
