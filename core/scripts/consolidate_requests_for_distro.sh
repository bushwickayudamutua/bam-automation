#!/bin/sh

echo '###################################################'
echo '###################################################'
echo '** Consolidating EG Citas **'
echo '###################################################'
echo '###################################################'


echo '**************************'
echo 'Clothes -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Ropa / Clothing / 服装协助' \
    -s 'Essential Goods: Clothing Requests' \
    -t 'BAM Citas 1/6' 

echo '**************************'
echo 'Pads -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾' \
    -s 'Essential Goods: Pads' \
    -t 'BAM Citas 1/6' 

echo '**************************'
echo 'Soap -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -s 'Essential Goods: Soap & Shower Products' \
    -t 'BAM Citas 1/6' 

echo '**************************'
echo 'School Supplies -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Cosas de Escuela / School Supplies / 學校用品' \
    -s 'Essential Goods: School Supplies' \
    -t 'BAM Citas 1/6' 

echo '**************************'
echo 'Baby Diapers -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' \
    -s 'Essential Goods: Baby Diapers' \
    -t 'BAM Citas 1/6' 

echo '**************************'
echo 'Adult Diapers -> EG Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人紙尿褲' \
    -s 'Essential Goods: Adult Diapers' \
    -t 'BAM Citas 1/6' 

echo '###################################################'
echo '###################################################'
echo '** Consolidating Food Citas **'
echo '###################################################'
echo '###################################################'

echo '**************************'
echo 'Clothes -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Ropa / Clothing / 服装协助' \
    -s 'Essential Goods: Clothing Requests' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '**************************'
echo 'Pads -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾' \
    -s 'Essential Goods: Pads' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '**************************'
echo 'Soap -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -s 'Essential Goods: Soap & Shower Products' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '**************************'
echo 'School Supplies -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Cosas de Escuela / School Supplies / 學校用品' \
    -s 'Essential Goods: School Supplies' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '**************************'
echo 'Baby Diapers -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' \
    -s 'Essential Goods: Baby Diapers' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '**************************'
echo 'Adult Diapers -> Food Citas'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人紙尿褲' \
    -s 'Essential Goods: Adult Diapers' \
    -t 'Food Distro- 02/03  Citas Confirmadas' 

echo '###################################################'
echo '###################################################'
echo '** Consolidation finished. Now applying timeouts **'
echo '###################################################'
echo '###################################################'


echo '**************************'
echo 'timing out Clothes'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Ropa / Clothing / 服装协助' 

echo '**************************'
echo 'timing out Pads'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾' 

echo '**************************'
echo 'timing out Soap'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' 

echo '**************************'
echo 'timing out School Supplies'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' 

echo '**************************'
echo 'timing out Baby Diapers'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' 

echo '**************************'
echo 'timing out Adult Diapers'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人紙尿褲' 
