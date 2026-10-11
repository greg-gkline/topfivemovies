<!-- begin footer -->
<div id="footer">
	<div id="footernav">
		<a href="/index.html">Home</a> | 
		<a href="/topfives.html">Top 5 Lists</a> | 
		<a href="/reviews.html">Reviews</a> | 
		<a href="/chickflicks.html">Chick Flicks</a> | 
		<a href="/others.html">Other Features</a> | 
		<a href="/about.html">About Us</a>
	</div>
	
	<div id="copyright">
		<div id="cclogo">
			<a href="http://creativecommons.org/licenses/by-nc-sa/2.5/" title="learn more about Creative Commons licensing"><img src="/images/somerights20.png" alt="Creative Commons" /></a>
		</div>
		<div id="cctext">
			This site design and all articles by Greg are free for non-commercial use with attribution.<br />
			All other articles contained herein are the copyright of their respective authors, unless otherwise noted. 
		</div>
	</div>

<?php
	$link = $_SERVER['SERVER_NAME'].$_SERVER['PHP_SELF'];
	if ( isset($_GET['id']) )
		$link = sprintf("%s?id=%d", $link, $_GET['id']);
?>
	<div id="intra">
		<a href="/intra/"><img src="/images/lockgray.gif" alt="" /></a>
	</div>
	
	<div id="tech">
		<a href="http://validator.w3.org/check?outline=1&amp;verbose=1&amp;uri=http%3A//<?php echo $link; ?>" 
			title="this page validates against the W3C XHTML 1.0 Transitional Specification" target="validate">xhtml 1.0</a> | 
		<a type="application/rss+xml" href="/index.xml" title="Syndicate TopFiveMovies with an RSS feed">rss 2.0</a>
	</div>
</div>

	<!-- 
	<rdf:RDF xmlns="http://web.resource.org/cc/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
		<Work rdf:about="http://topfivemovies.gkline.com/">
			<dc:title>Top Five Movies</dc:title>
			<dc:description>Movie reviews by guys from a boring college.</dc:description>
			<license rdf:resource="http://creativecommons.org/licenses/by-nc-sa/2.5/" />
			<dc:type rdf:resource="http://purl.org/dc/dcmitype/Text" />
		</Work>
		<License rdf:about="http://creativecommons.org/licenses/by-nc-sa/2.5/">
			<permits rdf:resource="http://web.resource.org/cc/Reproduction"/>
			<permits rdf:resource="http://web.resource.org/cc/Distribution"/>
			<requires rdf:resource="http://web.resource.org/cc/Notice"/>
			<requires rdf:resource="http://web.resource.org/cc/Attribution"/>
			<prohibits rdf:resource="http://web.resource.org/cc/CommercialUse"/>
			<permits rdf:resource="http://web.resource.org/cc/DerivativeWorks"/>
			<requires rdf:resource="http://web.resource.org/cc/ShareAlike"/>
		</License>
	</rdf:RDF> 
	-->

<!-- end footer -->