<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">

<html>
<head>
	<?php 
	Include("includes/title.inc"); 
	Include("includes/response.php3");
	Include("includes/related.php3");
	Include("includes/common.php3");
	?>
</head>

<body leftmargin='30'>


<?php

Include("includes/header.php3");

$db = getPrimaryDB();

?>
	<div class='headline'>All Responses</div>
	<P>

<?php

$query = sprintf("CREATE TEMPORARY TABLE tmp SELECT Response.*, Article.ID_ AS Article_ID, Article.Title AS Title, Article.Type AS Type FROM Article INNER JOIN Response ON Article.ID_ = Response.Article_ID_FK WHERE Article_ID_FK <> '0';");
$result = mysql_query($query, $db);

if ( $result === true )
{	
	$query = sprintf("INSERT INTO tmp SELECT Response.*, Top5.ID_ AS Article_ID, Top5.Title AS Title, Top5.Type AS Type FROM Top5 INNER JOIN Response ON Top5.ID_ = Response.Top5_ID_FK WHERE Top5_ID_FK <> '0';");
	$result = mysql_query($query, $db);
	
	if ( $result === true )
	{
		$query = sprintf("SELECT tmp.*, Author.Name from Author INNER JOIN tmp ON Author.ID_ = tmp.Author_ID_FK ORDER BY Response_date DESC;");	
		$result = mysql_query($query, $db);
		
		if ( $myrow = mysql_fetch_array($result) ) 
		{
			echo "<hr>\n";
			
			do
			{
				$article_file = " ";
				
				if ( $myrow["Type"] == "movie" || $myrow["Type"] == "dvd")
					$article_file = "reviews.php3";
				else if ( $myrow["Type"] == "top5" )
					$article_file = "top5.php3";
				else if ( $myrow["Type"] == "other" )
					$article_file = "other.php3";
			
				printf("<P><a href='%s?id=%d' class='quote'>%s</a><p>\n", $article_file, $myrow["Article_ID"], $myrow["Title"]);
				printf("<div class='authorName'>On %s, %s responded:</div>\n<div class='bodyText'>%s</div><p>\n<hr>\n", $myrow["Response_date"], $myrow["Name"], $myrow["Text"]);
			}
			while ( $myrow = mysql_fetch_array($result) );
		}
	}
	
	$query = sprintf("DROP TABLE tmp;");
	$result = mysql_query($query, $db);
}

	Include("includes/footer.inc");
?>

</body>
</html>






