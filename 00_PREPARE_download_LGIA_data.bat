@ECHO OFF

CALL 00_config.bat

ECHO Download LAS files
REM python3  00_PREPARE_download_LGIA_las.py  -o LAS %POLYGON%
ECHO LAS downloads Done

ECHO Download Ortofoto files
python3 00_PREPARE_download_LGIA_orto.py -o ORTO https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/ortofoto_rgb_v6/ %POLYGON%
ECHO Ortofoto downloads Done

::ECHO Download CIR files
::python3 00_PREPARE_download_LGIA_orto.py -o CIR https://s3.storage.pub.lvdc.gov.lv/lgia-opendata/ortofoto_cir_v6/ %POLYGON%
::ECHO CIR downloads Done
