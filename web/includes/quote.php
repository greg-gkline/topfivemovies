<?php
	$db 	= GetPrimaryDB();
	$query 	= 'SELECT MAX(ID_) AS qty FROM Quote';
	$result	= mysql_query($query, $db);
	
	if ( $result === false ) {
	
	}
	else if ( $row = mysql_fetch_array($result) ) {
		$max = intval($row['qty']);
		mt_srand( time() );
		$randint = mt_rand(1, $max);
		$query = sprintf("SELECT Quote.Quote FROM Quote WHERE Quote.ID_ = '%d'", $randint);
		$result	= mysql_query($query, $db);

		if ( $result === false ) {
		}
		else if ( $row = mysql_fetch_array($result) ) {
			echo $row['Quote'];
		}
	}
?>