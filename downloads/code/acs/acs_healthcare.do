* healthcare RD 

args topicdir
if `"`topicdir'"' == "" local topicdir "`c(pwd)'"
capture mkdir "`topicdir'/outputs"

use "`topicdir'/data/acs_clean_healthcare.dta", clear

gen obs_count = 1 

collapse (mean) uhrswork incwage in_labor_force has_health_insurance has_medicare (sum) obs_count, by(age)

twoway scatter has_health_insurance age [aw=obs_count], mc(sea%60) ///
	xtitle("Age") ///
	ytitle("Has Health Insurance") 
	
gr export "`topicdir'/outputs/has_insurance.png", replace 	
	
twoway scatter has_medicare age [aw=obs_count], mc(sea%60) ///
	xtitle("Age") ///
	ytitle("Has Medicare") 

gr export "`topicdir'/outputs/has_medicare.png", replace 	
	
twoway scatter in_labor_force age [aw=obs_count], mc(sea%60) ///
    xtitle("Age") ///
    ytitle("In Labor Force") ///
    xline(61.5, lp(dash)) ///
    xline(64.5, lp(dash)) ///
    xline(66.5, lp(dash)) ///
    text( 0.78 61.5 "Early Retirement", place(e)) ///
    text(0.65 64.5 "Medicare", place(e)) ///
    text( 0.55 66.6 "Late Retirement", place(e))

gr export "`topicdir'/outputs/in_labor_force.png", replace
