<?php

Include("includes/common.php3");

// this should be the last call executed by PHP3.
//	delete the CookiesEnabled cookie set by main.php3 so we're sure we always have the most
//	recent info
setcookie("CookiesEnabled");

$error = "0";
$id = -1;

if ( $submit )
{
	if ( $vote != "vote1" && $vote != "vote2" && $vote != "vote3" && $vote != "vote4" && $vote != "vote5" )
	{
		$error = sprintf("<div class='quote'>You forgot to make a selection.  Click your browser's \"Back\" button to try again.</div>\n");
	}
	else if ( $HTTP_COOKIE_VARS["CookiesEnabled"] != "yes" )
	{
		$error = sprintf("<div class='quote'>You must have cookies enabled in order to vote.</div>\n");
	}
	else
	{
		$db_poll = getPollDB(); 

		$query_poll = sprintf("SELECT * FROM poll ORDER BY Poll_date DESC LIMIT 1");
		$result_poll = mysql_query($query_poll, $db_poll);

		if ( $myrow_poll = mysql_fetch_array($result_poll) )
		{
			$poll_id = $myrow_poll["ID_"];
			$cookie = $HTTP_COOKIE_VARS["PollCookie"];
			
			if ( isset($cookie) && $cookie == $myrow_poll["ID_"] )
			{
				$error = sprintf("<div class='quote'>Sorry, you have already voted in this poll.</div>\n");
			}
			else
			{
				if ( $vote == "vote1" )
					$sql = sprintf("Votes1 = '%d'", ($myrow_poll["Votes1"] + 1) );
				else if ( $vote == "vote2" )
					$sql = sprintf("Votes2 = '%d'", ($myrow_poll["Votes2"] + 1) );
				else if ( $vote == "vote3" )
					$sql = sprintf("Votes3 = '%d'", ($myrow_poll["Votes3"] + 1) );
				else if ( $vote == "vote4" )
					$sql = sprintf("Votes4 = '%d'", ($myrow_poll["Votes4"] + 1) );
				else if ( $vote == "vote5" )
					$sql = sprintf("Votes5 = '%d'", ($myrow_poll["Votes5"] + 1) );
				
				if ( isset($sql) )
				{
					$query = sprintf("UPDATE poll SET %s WHERE ID_ = '%d'", $sql, $myrow_poll["ID_"]);
					$result = mysql_query($query, $db_poll);				

					if ( $result===false )
					{
						$error = sprintf("<div class='quote'>Failed to update database.</div>\n");
					}
					else
					{	
						setcookie("PollCookie", $myrow_poll["ID_"], time() + 12096000, "/", $HTTP_HOST, 0);
					}
				}
			}
		}
		else
		{
			$error = sprintf("<div class='quote'>Failed to load poll data.</div>\n");
		}
	}
}
else
{
	$error = sprintf("<div class='quote'>You have reached this page in error.</div>\n");
}

?>


<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
	<title>Top Five Movies -- Poll</title>
</head>

<body>

<h1>Vote Submission</h1>

<?php

if ( $error != "0" )
{
	echo $error;
}
else
{
	echo "<div class='quote'>Your vote has been counted.</div>\n";
}

if ( $poll_id > 0 )
{
	printf("\n<a href='index.html?viewpoll=%d'>Click here to view results of the poll</a>\n", $poll_id);
}
?>



</body>
</html>



