<?php
function outputPollResults($poll_id)
{
	$db_poll 	= getPollDB();
	$query_poll = sprintf("SELECT * FROM poll WHERE ID_ = %d", $poll_id);
	$result_poll= mysql_query($query_poll, $db_poll);

	if ( $poll_row = mysql_fetch_array($result_poll) )
	{
		printf("<div id=\"polldescription\">%s</div>\n", $poll_row["Question"]); 
		
		$choicecount = 0;
		$totalvotes = 0;
		
		// first tally all the votes
		if ( $poll_row["Text1"] != "0" )
		{
			$choicecount++;
			$totalvotes += $poll_row["Votes1"];
		}
		if ( $poll_row["Text2"] != "0" )
		{
			$choicecount++;
			$totalvotes += $poll_row["Votes2"];
		}
		if ( $poll_row["Text3"] != "0" )
		{
			$choicecount++;
			$totalvotes += $poll_row["Votes3"];
		}
		if ( $poll_row["Text4"] != "0" )
		{
			$choicecount++;
			$totalvotes += $poll_row["Votes4"];
		}
		if ( $poll_row["Text5"] != "0" )
		{
			$choicecount++;
			$totalvotes += $poll_row["Votes5"];
		}
		
		if ( $totalvotes == 0 )
		{
			printf("<div id=\"results\">No one has voted in this poll yet</div>");
		}
		else
		{
			// now display the results								
			if ( $poll_row["Text1"] != "0" )
			{
				$pct = ($poll_row["Votes1"] / $totalvotes) * 100;
				
				printf("<p>%s (%d%%)<br />\n", $poll_row["Text1"], $pct);
				printf("<img src='images/maroon_dot.jpg' height='3' width='%d%%' alt='%d votes' /></p>", $pct, $poll_row["Votes1"]);
			} 
			if ( $poll_row["Text2"] != "0" )
			{
				$pct = ($poll_row["Votes2"] / $totalvotes) * 100;
				
				printf("<p>%s (%d%%)<br />\n", $poll_row["Text2"], $pct);
				printf("<img src='images/maroon_dot.jpg' height='3' width='%d%%' alt='%d votes' /></p>", $pct, $poll_row["Votes2"]);
			}
			if ( $poll_row["Text3"] != "0" )
			{
				$pct = ($poll_row["Votes3"] / $totalvotes) * 100;
				
				printf("<p>%s (%d%%)<br />\n", $poll_row["Text3"], $pct);
				printf("<img src='images/maroon_dot.jpg' height='3' width='%d%%' alt='%d votes' /></p>", $pct, $poll_row["Votes3"]);
			}
			if ( $poll_row["Text4"] != "0" )
			{
				$pct = ($poll_row["Votes4"] / $totalvotes) * 100;
				
				printf("<p>%s (%d%%)<br />\n", $poll_row["Text4"], $pct);
				printf("<img src='images/maroon_dot.jpg' height='3' width='%d%%' alt='%d votes' /></p>", $pct, $poll_row["Votes4"]);
			}
			if ( $poll_row["Text5"] != "0" )
			{
				$pct = ($poll_row["Votes5"] / $totalvotes) * 100;
				
				printf("<p>%s (%d%%)<br />\n", $poll_row["Text5"], $pct);
				printf("<img src='images/maroon_dot.jpg' height='3' width='%d%%' alt='%d votes' /></p>", $pct, $poll_row["Votes5"]);
			}
			
			printf("<P><div class='bodyText'>Based on %d total votes</div>", $totalvotes);
		}
	}
	else
	{
		printf("<div id=\"polldescription\">No poll found matching id=%d</div>\n", $poll_id); 
	}
}

function displayPoll($viewpoll, $cookies)
{
?>
	<div id="poll">
		<div class="access"><a href="#skippoll">skip poll</a></div>
		<h2>Poll</h2>
		<div id="polltext">
			<form action="poll.php3" method="post">
<?php
		$bDone		= false;
		$cookieval	= intval($cookies['PollCookie']);
		
		printf("\n<!-- pollcookie: %d -->", $cookieval);
		
		if ( isset($viewpoll) && $viewpoll > 0 )
		{
			outputPollResults($viewpoll);
			$bDone = true;
		}
		else if ( $cookieval > 0 )
		{
			$db_poll 	= getPollDB();			
			$query		= "SELECT MAX(ID_) AS PollMax FROM poll ";
			$result		= mysql_query($query, $db_poll);
			
			if ( $myrow = mysql_fetch_array($result) ) {
				printf("\n<!-- pollmax: %d -->", intval($myrow['PollMax']));
				if ( intval($myrow['PollMax']) == $cookieval ) {
					outputPollResults($cookieval);
					$bDone = true;
				}
			}
		}

		if ( $bDone === false )
		{
			$db_poll 	= getPollDB();			
			$query_poll = sprintf("SELECT * FROM poll ORDER BY Poll_date DESC LIMIT 2");
			$result_poll = mysql_query($query_poll, $db_poll);
	
			if ( $myrow_poll = mysql_fetch_array($result_poll) )
			{
				printf("<div id=\"polldescription\">%s</div>\n", $myrow_poll["Question"]); 

				if ( $myrow_poll["Text1"] != "0" )
					printf("<p><input type='radio' name='vote' value='vote1' id='vote1' /><label for='vote1'>%s</label></p>\n", $myrow_poll["Text1"]);

				if ( $myrow_poll["Text2"] != "0" )
					printf("<p><input type='radio' name='vote' value='vote2' id='vote2' /><label for='vote2'>%s</label></p>\n", $myrow_poll["Text2"]);
				
				if ( $myrow_poll["Text3"] != "0" )
					printf("<p><input type='radio' name='vote' value='vote3' id='vote3' /><label for='vote3'>%s</label></p>\n", $myrow_poll["Text3"]);

				if ( $myrow_poll["Text4"] != "0" )
					printf("<p><input type='radio' name='vote' value='vote4' id='vote4' /><label for='vote4'>%s</label></p>\n", $myrow_poll["Text4"]);

				if ( $myrow_poll["Text5"] != "0" )
					printf("<p><input type='radio' name='vote' value='vote5' id='vote5' /><label for='vote5'>%s</label></p>\n", $myrow_poll["Text5"]);

			?>
				<p><input type="submit" name="submit" id="submit" value="Vote!" /></p>
				<div id="results"><a href="<?php printf("%s?viewpoll=%d", $_SERVER['PHP_SELF'], $myrow_poll["ID_"]); ?>">View results w/o voting</a></div>
			<?php
			}
			
			// querying for the second item
			if ( $myrow_poll = mysql_fetch_array($result_poll) )
				printf("<div id='prevpoll'><a href='%s?viewpoll=%d'>View results of previous poll</a></div>\n", $_SERVER['PHP_SELF'], $myrow_poll["ID_"]);
		}

?>
			</form>
		</div>
	</div>
	<a name="skippoll" class="access">&nbsp;</a>
<?php
}
?>
