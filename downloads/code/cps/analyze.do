*************************************

* Exploration of CPS

*************************************


args topicdir
if `"`topicdir'"' == "" local topicdir "`c(pwd)'"
capture mkdir "`topicdir'/outputs"

use "`topicdir'/data/cps_aug_25.dta", clear

* Restrict to individuals >=16 with non-missing labor force values
drop if labforce == 0 
drop if age < 16

* table of labforce
tab labforce

* table of employment status 
tab empstat

* table of occupations 
tab occ if empstat == 10 | empstat==12

* Earnings analysis 
sum earnweek2
replace earnweek2=. if earnweek2==999999.99
sum earnweek2, de

hist earnweek2, fcolor(blue%40) lcolor(blue%40) title("Histogram of Weekly Earnings") frac

graph export "`topicdir'/outputs/weekly_earnings.png", replace
