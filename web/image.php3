<?php
// Syntax: getdata.php3?id=<id>

if($id) 
{
    $db = mysql_connect("localhost","top5mov_www","REDACTED");
    mysql_select_db("top5mov_primary", $db);

    $query = sprintf("select Bin_data, Filetype from Image where ID_='%d'", $id);
    $result = mysql_query($query, $db);
	
	if ( $result===false )
	{

	}
	else	
	{
	    $data = mysql_result($result,0,"Bin_data");
    	$type = mysql_result($result,0,"Filetype");

	    Header( sprintf("Content-type: %s", $type) );
    	echo $data;
	}
};
?> 