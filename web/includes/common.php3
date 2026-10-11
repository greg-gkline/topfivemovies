<?php
$hostname = "mysql.gkline.com";
$primary_password = "REDACTED";
$poll_password = "REDACTED";

// Local dev: the devcontainer generates this file at startup with random passwords
if ( file_exists("/etc/topfive/db.php") )
	include("/etc/topfive/db.php");

function getArticleFile($type)
{
	$article_file = "";
	
	if ( $type == "movie" || $type == "dvd")
		$article_file = "reviews.php3";
	else if ( $type == "top5" )
		$article_file = "top5.php3";
	else if ( $type == "other" )
		$article_file = "other.php3";

	return $article_file;
}

function getPrimaryDB()
{
	global $hostname, $primary_password;
	
	$db = mysql_connect($hostname, "gklinec_top5prim", $primary_password);
	mysql_select_db("gklinec_top5primary", $db);
	
	if ( $db === false )
		return false;
	else
		return $db;
}

function getPollDB()
{
	global $hostname, $poll_password;
	
	$db = mysql_connect($hostname, "gklinec_poll", $poll_password);
	mysql_select_db("gklinec_poll", $db);
	
	if ( $db === false )
		return false;
	else
		return $db;
}

function formatTextForIntro($text, $length)
{
	if ( strlen($text) > $length )
	{
		$endPos = strpos($text, ".", $length - 10);
	
		if ($endPos == 0)
			$endPos = $length;
			
		$text = substr($text, 0, $endPos + 1);								
	}
	
	return sprintf("%s...", $text);
}
?>