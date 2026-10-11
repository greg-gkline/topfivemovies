<?php
/***
 *	POSSIBLE "$field" VALUES:
 * 	"seconds"	- seconds 
 * 	"minutes"	- minutes 
 * 	"hours"		- hours 
 * 	"mday"		- day of the month 
 * 	"mon"		- month, numeric 
 * 	"year"		- year, numeric 
**/
	function add_time($timestamp, $amount, $field, $preserveHMS = true)
	{
		if ( isValidField($field) )
		{		
			$timearray = getdate($timestamp);
			
			$timearray[$field] = $timearray[$field] + $amount;
			
			$newtimestamp = mktime(	$preserveHMS ? $timearray["hours"] : 0,
									$preserveHMS ? $timearray["minutes"] : 0,
									$preserveHMS ? $timearray["seconds"] : 0,
									$timearray["mon"],
									$timearray["mday"],
									$timearray["year"] );
			
			return $newtimestamp;
		}

		return $false;
	}
	
	function subtract_time($timestamp, $amount, $field)
	{
		return add_time($timestamp, $amount * -1, $field);
	}

	function add_time_text($time_as_string, $amount, $field)
	{
		$timestamp = strtotime($time_as_string);
		return add_time($timestamp, $amount, $field);
	}
	
	function subtract_time_text($time_as_string, $amount, $field)
	{
		$timestamp = strtotime($time_as_string);
		return add_time($timestamp, $amount * -1, $field);
	}
	
	function isValidField($field)
	{
		if (	$field == "seconds"	||
				$field == "minutes"	||
				$field == "hours"	||
				$field == "mday"	||
				$field == "mon"		||
				$field == "year"		)
		{
			return true;
		}
		else
			return false;				
	}
?>
