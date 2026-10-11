<?php

include('common.php3');
include('date_math.php');

function getGenericFile($type)	{
	$article_file = '';

	if ( $type == "movie" || $type == "dvd")
		$article_file = "review_";
	else if ( $type == "top5" )
		$article_file = "topfive_";
	else if ( $type == "other" )
		$article_file = "other_";
	else if ( $type == "chick" )
		$article_file = "chickflick_";

	return $article_file;
}

function cleanupImgTag($imgtag) {
	$imgtag = str_replace("border='0'", "", $imgtag);
	$imgtag = str_replace("border=\"0\"", "", $imgtag);
	$imgtag = str_replace("'>", "' />", $imgtag);
	$imgtag = str_replace("\">", "\" />", $imgtag);
	return $imgtag;
}

function getDateTimestamp($date) {
	if (ereg ("([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})", $date, $regs)) {
		return mktime(0, 0, 0, $regs[2], $regs[3], $regs[1]);
	}
	return false;
}

function formatDate($date) {
	$timestamp = getDateTimestamp($date);
	return date("F d, Y", $timestamp);
}

function rfcDate($date) {
	$timestamp = getDateTimestamp($date);
	return date("r", $timestamp);
}

function xmlify($string) {
	return str_replace('& ', '&amp; ', $string);
}

class article {
	var $id;
	var $title;
	var $subtitle;
	var $author_id;
	var $author;
	var $article_date;
	var $rating;
	var $image;
	var $image_fullsize;
	var $text;
	var $type;
	var $starring;
	var $caption;
	var $release_year;
	var $qa;
	
	function article($id = "") {
		$this->id = $id;
	}

	function retrieve() {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		if ( $this->id <= 0 || $this->id == "" )
		{
			return false;
		}
		
		$select	= "SELECT Article.*, Author.ID_ AS AuthorID, Author.Name ";
		$from	= "FROM Article INNER JOIN Author ON Article.Author_ID_FK = Author.ID_ ";
		$where	= "WHERE Article.ID_ = $this->id ";
		
		$result	= mysql_query($select.$from.$where, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where' -->";
		}
		else if ( $row = mysql_fetch_array($result) )
		{
			$bRC = $this->build($row);
			mysql_free_result($result);
		}
		
		return $bRC;			
	}
	
	function build($row) {
		$this->id				= $row['ID_'];
		$this->title			= xmlify($row['Title']);
		$this->subtitle			= xmlify($row['Subtitle']);
		$this->author_id		= $row['AuthorID'];
		$this->author			= $row['Name'];
		$this->article_date		= $row['Article_date'];
		$this->rating			= $row['Rating'];
		$this->image			= cleanupImgTag($row['Image']);
		$this->image_fullsize	= cleanupImgTag($row['Image_fullsize']);
		$this->text				= xmlify($row['Text']);
		$this->type				= $row['Type'];
		$this->starring			= xmlify($row['Starring']);
		$this->caption			= xmlify($row['Caption']);
		$this->release_year		= $row['Release_year'];
		$this->qa				= $row['QA'];
		
		return true;
	}
	
	function generatePreview($length) {
		$text = $this->text;
		if ( strlen($text) > $length )
		{
			$endPos = strpos($text, ".", $length - 10);
		
			if ($endPos == 0)
				$endPos = $length;
				
			$text = substr($text, 0, $endPos + 1);	
			$text = str_replace("<P>", "</p>\n<p>", $text);
		}
		
		return sprintf("%s...", $text); 
	}
	
	function getFile()	{
		return getGenericFile($this->type);
	}
	
	function getLink()	{
		$file = $this->getFile();
		$link = sprintf("%s%d.html", $file, $this->id);
		return $link;
	}
	
	function isOlderThanWeeks($weeks) {
		if ( add_time_text($this->article_date, $weeks*7, "mday") < time() )
			return true;
		else
			return false;
	}

	function collectKeywords() {
		return $this->title.', '.str_replace(' and ', ' ', $this->starring);
	}
}

class articles {
	var $sortcol;
	var $type;
	var $author_id;
	var $article_array;
	var $count;
	
	function articles() {
		$this->article_array = array();
		$this->count = 0;
	}
	
	function get($idx) {
		if ( $idx < 0 || $idx >= $this->count )
		{
			echo "<!-- articles->get(".$idx.") - index out of range -->";
			return -1;
		}
			
		return $this->article_array[$idx];
	}
	
	function retrieve($limit = "") {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		$select	= "SELECT Article.*, Author.ID_ AS AuthorID, Author.Name ";
		$from	= "FROM Article INNER JOIN Author ON Article.Author_ID_FK = Author.ID_ ";
		$where	= "WHERE Article.QA = '1' ";
		$order	= "ORDER BY Article.ID_ DESC ";
		$slimit	= "";

		if ( isset($this->type) ) {
			$whereclause= '';
			
			if ( strpos($this->type, "|") === false ) {
				$whereclause = "Article.Type = '$this->type' ";
			}
			else {
				$typearray 	= explode("|", $this->type);
				
				for ( $i = 0; $i < count($typearray); $i++ ) {
					if ( strlen($whereclause) > 0 )
						$whereclause = $whereclause.' OR ';
						
					$whereclause = $whereclause."Article.Type = '".$typearray[$i]."'";
				}
			}
			
			$where = $where.'AND ('.$whereclause.') ';
		}
		
		if ( isset($this->author_id) ) {
			$where = $where."AND Article.Author_ID_FK = '$this->author_id' ";
		}
				
		if ( isset($this->sortcol) ) {
			if ( $this->sortcol == 'type' )
				$order = "ORDER BY Article.Type ASC ";
			else if ( $this->sortcol == 'movie' || $this->sortcol == 'title' )
				$order = "ORDER BY Article.Title ASC ";
			else if ( $this->sortcol == 'rating' )
				$order = "ORDER BY Article.Rating DESC ";
			else if ( $this->sortcol == 'author' )
				$order = "ORDER BY Author.Name ASC ";
			else if ( $this->sortcol == 'date' )
				$order = "ORDER BY Article.Article_date DESC ";
		}
		
		if ( isset($limit) && strlen($limit) > 0 ) {
			$slimit = sprintf("LIMIT %d ", $limit);
		}		
		
		$result	= mysql_query($select.$from.$where.$order.$slimit, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where$order$slimit' -->";
		}
		else 
		{
			$bRC = true;
			$this->count = 0;
			
			while ( $bRC == true && $row = mysql_fetch_array($result) )	{
				$article = new article();
				$bRC = $article->build($row);
				
				if ( $bRC )	{
					$this->article_array[$this->count++] = $article;
					
					$a = $this->article_array[$this->count - 1];
				}
			}
			
			mysql_free_result($result);		
		}

		return $bRC;			
	}
	
	function selectRandomArticle() {
		// seed the random number generator with today
		$todayarray = getdate(time());
		mt_srand( $todayarray["yday"] );

		// choose and seek to a random row elsewhere in the result set
		$randint = mt_rand(1, $this->count - 1);
		
		return $this->get($randint);
	}
	
	function collectKeywords() {
		$words = "";
		for ( $i = 0; $i < 5 && $i < $this->count; $i++ ) {
			if ( $i > 0 )
				$words = $words.', ';
			
			$article = $this->article_array[$i];
			$words = $words.$article->collectKeywords(); 
		}
		
		return $words;
	}
}

class topfive {
 	var $id;
	var $author_id;
	var $author;
	var $title;
	var $item1;
	var $item2;
	var $item3;
	var $item4;
	var $item5;
	var $article_date;
	var $intro;
	var $image;
	var $image_fullsize;
	var $caption;
	var $QA;
	var $type;
	
	function topfive($id = "") {
		$this->id = $id;
	}

	function retrieve() {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		if ( $this->id <= 0 || $this->id == "" ) {
			return false;
		}
			
		$select	= "SELECT Top5.*, Author.ID_ AS AuthorID, Author.Name ";
		$from	= "FROM Top5 INNER JOIN Author ON Top5.Author_ID_FK = Author.ID_ ";
		$where	= "WHERE Top5.ID_ = $this->id ";
		
		$result	= mysql_query($select.$from.$where, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where' -->";
		}
		else if ( $row = mysql_fetch_array($result) )
		{
			$bRC = $this->build($row);
			mysql_free_result($result);
		}
		
		return $bRC;			
	}
	
	function build($row) {
		$this->id				= $row['ID_'];
		$this->author_id		= $row['AuthorID'];
		$this->author			= $row['Name'];
		$this->title			= xmlify($row['Title']);
		$this->item1			= xmlify($row['Item1']);
		$this->item2			= xmlify($row['Item2']);
		$this->item3			= xmlify($row['Item3']);
		$this->item4			= xmlify($row['Item4']);
		$this->item5			= xmlify($row['Item5']);
		$this->article_date		= $row['Article_date'];
		$this->intro			= xmlify($row['Intro']);
		$this->image			= cleanupImgTag($row['Image']);
		$this->image_fullsize	= cleanupImgTag($row['Image_fullsize']);
		$this->caption			= xmlify($row['Caption']);
		$this->QA				= $row['QA'];
		$this->type				= $row['Type'];
		
		return true;
	}
	
	function getFile()	{
		return getGenericFile($this->type);
	}
	
	function getLink()	{
		$file = $this->getFile();
		$link = sprintf("%s%d.html", $file, $this->id);
		return $link;
	}

	function collectKeywords() {
		$words = $this->title.', '.$this->trimItem($this->item1).', '.$this->trimItem($this->item2).', '.$this->trimItem($this->item3).', '.$this->trimItem($this->item4).', '.$this->trimItem($this->item5);
		return str_replace("\"", '', $words);
	}
	
	function trimItem($item) {
		$pattern	= "([a-zA-Z0-9]*)(\n)*(<div.*)";
		$replace	= "\\1";
		return trim(ereg_replace($pattern, $replace, $item));
	}
	
	function generatePreview($length) {
		$text = $this->intro;
		if ( strlen($text) > $length )
		{
			$endPos = strpos($text, ".", $length - 10);
		
			if ($endPos == 0)
				$endPos = $length;
				
			$text = substr($text, 0, $endPos + 1);								
		}
		
		return sprintf("%s...", $text); 
	}
}

class topfives {
	var $sortcol;
	var $type;
	var $author_id;
	var $topfives;
	var $count;
	
	function topfives() {
		$this->topfives = array();
		$this->count = 0;
	}
	
	function get($idx) {
		if ( $idx < 0 || $idx >= $this->count )
		{
			echo "<!-- topfives->get(".$idx.") - index out of range -->";
			return -1;
		}
			
		return $this->topfives[$idx];
	}
	
	function retrieve($limit = "") {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		$select	= "SELECT Top5.*, Author.ID_ AS AuthorID, Author.Name ";
		$from	= "FROM Top5 INNER JOIN Author ON Top5.Author_ID_FK = Author.ID_ ";
		$where	= "WHERE Top5.QA = '1' ";
		$order	= "ORDER BY Top5.ID_ DESC ";
		$slimit	= "";

		if ( isset($this->type) ) {
			$where = $where."AND Top5.Type = '$this->type' ";
		}
		
		if ( isset($this->author_id) ) {
			$where = $where."AND Top5.Author_ID_FK = '$this->author_id' ";
		}
				
		if ( isset($this->sortcol) ) {
			if ( $this->sortcol == 'title' )
				$order = "ORDER BY Top5.Title ASC ";
			else if ( $this->sortcol == 'author' )
				$order = "ORDER BY Top5.Name ASC ";
			else if ( $this->sortcol == 'date' )
				$order = "ORDER BY Top5.Article_date DESC ";
		}
		
		if ( isset($limit) && strlen($limit) > 0 ) {
			$slimit = sprintf("LIMIT %d ", $limit);
		}		
		
		$result	= mysql_query($select.$from.$where.$order.$slimit, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where$order$slimit' -->";
		}
		else 
		{
			$bRC = true;
			$this->count = 0;
			
			while ( $bRC == true && $row = mysql_fetch_array($result) )	{
				$topfive = new topfive();
				$bRC = $topfive->build($row);
				
				if ( $bRC )	{
					$this->topfives[$this->count++] = $topfive;
				}
			}
			
			mysql_free_result($result);		
		}	

		return $bRC;			
	}
	
	function collectKeywords() {
		$words = "";
		for ( $i = 0; $i < $this->count; $i++ ) {
			if ( $i > 0 )
				$words = $words.',';
			
			$topfive = $this->topfives[$i];
			$words = $words.$topfive->collectKeywords();
		}
		
		return $words;
	}
}

class response {
	var $id;
	var $author;
	var $author_img;
	var $text;
	var $response_date;
	var $author_id;
	var	$article_id;
	var	$top5_id;
	
	function response($id="") {
		$this->id = $id;
	}

	function retrieve() {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		if ( $this->id <= 0 || $this->id == "" ) {
			return false;
		}
			
		$select	= "SELECT Response.*, Author.Name, Author.Image ";
		$from	= "FROM Response INNER JOIN Author ON Response.Author_ID_FK = Author.ID_ ";
		$where	= "WHERE Response.ID_ = '$this->id' ";
		
		$result	= mysql_query($select.$from.$where, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where' -->";
		}
		else if ( $row = mysql_fetch_array($result) )
		{
			$bRC = $this->build($row);
			mysql_free_result($result);
		}
		
		return $bRC;			
	}
	
	function build($row) {
		$this->id				= $row['ID_'];
		$this->author			= $row['Name'];
		$this->author_img		= $row['Image'];
		$this->author_id		= $row['AUTHOR_ID_FK'];
		$this->article_id		= $row['ARTICLE_ID_FK'];
		$this->top5_id			= $row['TOP5_ID_FK'];
		$this->text				= $row['Text'];
		$this->response_date	= $row['Response_date'];
		
		return true;
	}

	function outputResponse() {
		echo "\n<div class='response'>";
		printf("\n<div class='response_img'><img src='/images/%s' alt='%s says:' title='%s says:' /></div>", $this->author_img, $this->author, $this->author);
		printf("\n<div class='response_bubble_container'><div class='response_bubble'><div class='response_text'>%s</div></div></div>", $this->text);
		echo "\n</div>";
	}
	
	function insert() {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		$insert = sprintf("INSERT INTO Response ( Response_date, AUTHOR_ID_FK, ARTICLE_ID_FK, TOP5_ID_FK, Text ) VALUES ( '%s', '%d', '%d', '%d', '%s' )",
					date("Y-m-d"), $this->author_id, $this->article_id, $this->top5_id, $this->text);
		$result	= mysql_query($insert, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$insert' -->";
		}
		else
		{
			$bRC = true;
		}
		
		return $bRC;
	} 
}

class responses {
	var $count;
	var $responses;
	
	function responses() {
		$this->responses = array();
		$this->count = 0;
	}

	function get($idx) {
		if ( $idx < 0 || $idx >= $this->count )	{
			return -1;
		}
		return $this->responses[$idx];
	}
	
	function retrieve($item_type, $item_id) {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		$select	= "SELECT Response.*, Author.Name, Author.Image ";
		$from	= "FROM Response INNER JOIN Author ON Response.Author_ID_FK = Author.ID_ ";
		$where	= "";
		$order	= "ORDER BY Response.ID_ ASC ";

		if ( $item_type == 'top5' )
			$where = "WHERE Response.TOP5_ID_FK = '$item_id' ";
		else
			$where = "WHERE Response.ARTICLE_ID_FK = '$item_id' ";
		
		$result	= mysql_query($select.$from.$where.$order, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where$order' -->";
		}
		else 
		{
			$bRC = true;
			$this->count = 0;

			while ( $bRC == true && $row = mysql_fetch_array($result) )	{
				$response = new response();
				$bRC = $response->build($row);
				
				if ( $bRC )	{
					$this->responses[$this->count++] = $response;
				}
			}
			
			mysql_free_result($result);		
		}
		
		return $bRC;	
	}
	
	function outputResponses() {
		if ( $this->count > 0 )	{
			echo "\n<h2 id='staff_responses'>Staff Responses</h2>";
			
			for ( $i = 0; $i < $this->count; $i++ )	{
				$response = $this->get($i);
				$response->outputResponse();
			}
		}	
	} 
}

class author {
	var $id;
	var $name;
	var $email;
	var $img;
	var $img_notag;
	var $bio;
	var $jobtitle;
	var $articles;
	var $topfives;
	var $userid;
	
	function author($id="") {
		$this->id = $id;
		$this->articles = new articles();
		$this->topfives = new topfives();
	}
	
	function retrieveArticles() {
		$this->articles->author_id = $this->id;
		$bRC = $this->articles->retrieve();
		
		if ( $bRC ) {
			$this->topfives->author_id = $this->id;
			$bRC = $this->topfives->retrieve();
		}
		
		return $bRC;
	}
	
	function retrieve() {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		if ( $this->id <= 0 || $this->id == "" ) {
			return false;
		}
			
		$select	= "SELECT Author.* ";
		$from	= "FROM Author ";
		$where	= "WHERE Author.ID_ = '$this->id' ";
		
		$result	= mysql_query($select.$from.$where, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where' -->";
		}
		else if ( $row = mysql_fetch_array($result) )
		{
			$bRC = $this->build($row);
			mysql_free_result($result);
		}
		
		return $bRC;			
	}
	
	function build($row) {
		$this->id				= $row['ID_'];
		$this->name				= $row['Name'];
		$this->email			= $row['Email'];
		$this->img_notag		= $row['Image'];
		$this->img				= '<img src="images/'.$row['Image'].'" alt="'.$this->name.'" />';
		$this->bio				= $row['Bio'];
		$this->jobtitle			= $row['Jobtitle'];
		$this->userid			= $row['Userid'];
		
		$this->bio				= str_replace('<P>', '</p><p>', $this->bio);
		$this->bio				= str_replace('<BR>', '<br />', $this->bio);
		$this->bio				= str_replace('& ', '&amp; ', $this->bio);
		
		if ( strpos($this->bio, '<table') === false )
			$this->bio = '<p>'.$this->bio.'</p>';
		
		return true;
	}
}

class authors {
	var $count;
	var $authors;
	
	function authors() {
		$this->authors = array();
		$this->count = 0;
	}

	function get($idx) {
		if ( $idx < 0 || $idx >= $this->count )	{
			return -1;
		}
		return $this->authors[$idx];
	}
	
	function retrieve($userid='') {
		$bRC 	= false;
		$db		= GetPrimaryDB();
		
		$select	= "SELECT Author.* ";
		$from	= "FROM Author ";
		$where	= "";
		
		if ( isset($userid) && strlen($userid) > 0 )
			$where = "WHERE Author.Userid = '$userid' ";
		
		$order	= "ORDER BY Author.Name ASC ";

		$result	= mysql_query($select.$from.$where.$order, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "<!-- ERROR -- ".mysql_error()." -- Full SQL='$select$from$where$order' -->";
		}
		else 
		{
			$bRC = true;
			$this->count = 0;

			while ( $bRC == true && $row = mysql_fetch_array($result) )	{
				$author = new author();
				$bRC = $author->build($row);
				
				if ( $bRC )	{
					$this->authors[$this->count++] = $author;
				}
			}
			
			mysql_free_result($result);		
		}
		
		return $bRC;	
	}
}

class combinedItem {
	var $id;
	var $title;
	var $article_date;
	var $type;
	var $qa;
	var $author_id;
	var $author;
	var $text;
	
	function combinedItem($id="") {
		$this->id = $id;
	}
	
	function build($row) {
		$this->id				= $row['ID_'];
		$this->title			= xmlify($row['Title']);
		$this->article_date		= $row['Article_date'];
		$this->type				= $row['Type'];
		$this->qa				= $row['QA'];
		$this->author_id		= $row['AuthorID'];
		$this->author			= $row['Name'];
		$this->text				= xmlify($row['Text']);
		
		return true;
	}
	
	function getFile()	{
		return getGenericFile($this->type);
	}
	
	function getLink()	{
		$file = $this->getFile();
		$link = sprintf("%s%d.html", $file, $this->id);
		return $link;
	}

	function generatePreview($length) {
		$text = $this->text;
		if ( strlen($text) > $length )
		{
			$endPos = strpos($text, ".", $length - 10);
		
			if ($endPos == 0)
				$endPos = $length;
				
			$text = substr($text, 0, $endPos + 1);								
		}
		
		return sprintf("%s...", $text); 
	}
}

class combinedItems {
	var $count;
	var $items;
	var $sortcol;
	
	function combinedItems() {
		$this->count = 0;
		$this->items = array();
	}

	function get($idx) {
		if ( $idx < 0 || $idx >= $this->count )
		{
			echo "<!-- combinedItems->get(".$idx.") - index out of range -->";
			return -1;
		}
			
		return $this->items[$idx];
	}
	
	function retrieve($author_id='', $limit='') {
		$bRC 	= false;
		$db 	= GetPrimaryDB();
		
		$query 	= "CREATE TEMPORARY TABLE tmp SELECT Article.ID_, Article.Title, Article.Article_date, Article.Type, Article.QA, Article.Text, Author.ID_ AS AuthorID, Author.Name FROM Article INNER JOIN Author ON Article.Author_ID_FK = Author.ID_ ";
		if ( strlen($author_id) > 0 )
			$query = $query.sprintf("WHERE Article.Author_ID_FK = '%d' ", $author_id);
		$result = mysql_query($query, $db);
		
		if ( $result === false )
		{
			$bRC = false;
			echo "\n\n<!-- error in 1st query: ".mysql_error()." -- full sql: '$query' -->";
		}
		else
		{	
			$query 	= "INSERT INTO tmp SELECT Top5.ID_, Top5.Title, Top5.Article_date, Top5.Type, Top5.QA, Top5.Intro AS Text, Author.ID_ AS AuthorID, Author.Name FROM Top5 INNER JOIN Author ON Top5.Author_ID_FK = Author.ID_ ";
			if ( strlen($author_id) > 0 )
				$query = $query.sprintf("WHERE Top5.Author_ID_FK = '%d' ", $author_id);
			$result = mysql_query($query, $db);
			
			if ( $result === false )
			{
				$bRC = false;
				echo "\n\n<!-- error in 2nd query: ".mysql_error()." -- full sql: '$query' -->";
			}
			else
			{
				$query = sprintf("SELECT * from tmp WHERE QA = '1' ");
				
				if ( $this->sortcol == 'title' )
					$query = $query.'ORDER BY Title ASC ';
				else
					$query = $query.'ORDER BY Article_date DESC ';
					
				if ( strlen($limit) > 0 )
					$query = $query.sprintf("LIMIT %d ", $limit);
				$result = mysql_query($query, $db);
	
				if ( $result === false )
				{
					$bRC = false;
					echo "\n\n<!-- error in 3rd query: ".mysql_error()." -- full sql: '$query' -->";				
				}
				else 
				{
					$bRC = true;
					$this->count = 0;
		
					while ( $bRC == true && $row = mysql_fetch_array($result) )	{
						$item = new combinedItem();
						$bRC = $item->build($row);
						
						if ( $bRC )	{
							$this->items[$this->count++] = $item;
						}
					}
					
					mysql_free_result($result);		
				}
			}
			
			$query = sprintf("DROP TABLE tmp;");	
			$result = mysql_query($query, $db);		
		}
		
		return $bRC;
	}
}
?>