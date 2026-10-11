<?php 
	include('includes/classes.php');
	
	$combined = new combinedItems();
	$combined->retrieve('', 20);

	$firstItem	= $combined->get(0);	
	$datestr	= rfcDate($firstItem->article_date);

	ob_start();
	echo '<?xml version="1.0"?>'; 
?>

<rss version="2.0">
	<channel>
		<title>Top Five Movies</title>
		<link>http://www.topfivemovies.com/</link>
		<description>The latest movie reviews and top-five lists from topfivemovies.com.  Top Five Movies is written and maintained by a bunch of regular guys, not snobby movie critics.</description>
		<language>en-us</language>
		<copyright>Copyright (c) 2001-<?php echo date("Y"); ?> topfivemovies.com, and each article's respective author.</copyright>
		<docs>http://blogs.law.harvard.edu/tech/rss</docs>
		<image>
			<url>http://topfivemovies.gkline.com/images/top5gray_small.jpg</url>
			<title>Top Five Movies</title>
			<link>http://www.topfivemovies.com/</link>
			<width>144</width>
			<height>48</height>
		</image>
		<pubDate><?php echo $datestr; ?></pubDate>
		<lastBuildDate><?php echo date("r"); ?></lastBuildDate>

<?php
	for ( $i = 0; $i < $combined->count; $i++ ) {
		$item = $combined->get($i);
		
		echo "\n\t\t<item>";
		printf("\n\t\t\t<title>%s</title>", $item->title);
		printf("\n\t\t\t<link>http://%s/%s</link>", $_SERVER['SERVER_NAME'], $item->getLink());
		printf("\n\t\t\t<guid isPermaLink=\"true\">http://%s/%s</guid>", $_SERVER['SERVER_NAME'], $item->getLink());
		printf("\n\t\t\t<description>%s</description>", strip_tags($item->generatePreview(350)));
		printf("\n\t\t\t<author>%s</author>", $item->author);
		printf("\n\t\t\t<pubDate>%s</pubDate>", rfcDate($item->article_date));
		echo "\n\t\t</item>";
	}
?>

	</channel>
</rss>

<?php
	$fullpage = ob_get_contents();
	ob_end_clean();
	
	$fp = fopen('/home/gklinec/public_html/topfivemovies/index.xml', 'w+');
	
	if ( $fp === false )
		die("open failed");
	
	fwrite($fp, $fullpage);
	fclose($fp);
?>
<h1>finished</h1>
