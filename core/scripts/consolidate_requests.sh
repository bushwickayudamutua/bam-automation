#!/bin/sh

echo '**************************'
echo 'Clothes -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Ropa / Clothing / 服装协助' \
    -s 'Essential Goods: Clothing Requests' \
    -t 'Essential Goods: Adult Diapers' 'Essential Goods: School Supplies' 'Essential Goods: Pads' 'Essential Goods: Baby Diapers' 'Essential Goods: Soap & Shower Products' \
    -d

echo '**************************'
echo 'Pads -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 卫生巾' \
    -s 'Essential Goods: Pads' \
    -t 'Essential Goods: Clothing Requests' 'Essential Goods: Soap & Shower Products' 'Essential Goods: Baby Diapers' 'Essential Goods: Adult Diapers' 'Essential Goods: School Supplies' \
    -d

echo '**************************'
echo 'Soap -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -s 'Essential Goods: Soap & Shower Products' \
    -t 'Essential Goods: Clothing Requests' 'Essential Goods: Pads' 'Essential Goods: Baby Diapers' 'Essential Goods: Adult Diapers' 'Essential Goods: School Supplies' \
    -d

echo '**************************'
echo 'School Supplies -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Cosas de Escuela / School Supplies / 学校用品' \
    -s 'Essential Goods: School Supplies' \
    -t 'Essential Goods: Clothing Requests' 'Essential Goods: Pads' 'Essential Goods: Baby Diapers' 'Essential Goods: Adult Diapers' 'Essential Goods: Soap & Shower Products' \
    -d

echo '**************************'
echo 'Baby Diapers -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' \
    -s 'Essential Goods: Baby Diapers' \
    -t 'Essential Goods: Clothing Requests' 'Essential Goods: School Supplies' 'Essential Goods: Pads'  'Essential Goods: Adult Diapers' 'Essential Goods: Soap & Shower Products' \
    -d

echo '**************************'
echo 'Adult Diapers -> EG'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人纸尿裤' \
    -s 'Essential Goods: Adult Diapers' \
    -t 'Essential Goods: Clothing Requests' 'Essential Goods: School Supplies' 'Essential Goods: Pads' 'Essential Goods: Baby Diapers' 'Essential Goods: Soap & Shower Products' \
    -d 

echo '###################################################'
echo '###################################################'
echo '** EG consolidated, now consolidating Food **'
echo '###################################################'
echo '###################################################'

echo '**************************'
echo 'Clothes -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Ropa / Clothing / 服装协助' \
    -s 'Essential Goods: Clothing Requests' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '**************************'
echo 'Pads -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 卫生巾' \
    -s 'Essential Goods: Pads' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '**************************'
echo 'Soap -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -s 'Essential Goods: Soap & Shower Products' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '**************************'
echo 'School Supplies -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Cosas de Escuela / School Supplies / 学校用品' \
    -s 'Essential Goods: School Supplies' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '**************************'
echo 'Baby Diapers -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' \
    -s 'Essential Goods: Baby Diapers' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '**************************'
echo 'Adult Diapers -> Food'
echo '**************************'

python -m bam_core.functions.consolidate_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人纸尿裤' \
    -s 'Essential Goods: Adult Diapers' \
    -t 'Food Distro- 01/06  Citas Confirmadas' \
    -d

echo '###################################################'
echo '###################################################'
echo '** Consolidation finished. Now applying timeouts **'
echo '###################################################'
echo '###################################################'


echo '**************************'
echo 'timing out Clothes'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Ropa / Clothing / 服装协助' \
    -d

echo '**************************'
echo 'timing out Pads'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Productos Femenino - Toallitas / Feminine Products - Pads / 卫生巾' \
    -d

echo '**************************'
echo 'timing out Soap'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -d

echo '**************************'
echo 'timing out School Supplies'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品' \
    -d

echo '**************************'
echo 'timing out Baby Diapers'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Pañales / Baby Diapers / 婴儿纸尿裤' \
    -d

echo '**************************'
echo 'timing out Adult Diapers'
echo '**************************'

python -m bam_core.functions.timeout_eg_requests \
    -r 'Pañales de adultos / Adult Diapers / 成人纸尿裤' \
    -d
