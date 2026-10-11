<?php
	$recent_articles = new articles();
	$recent_articles->type = 'movie|chick';
	$recent_articles->sortcol = 'date';
	$recent_articles->retrieve('5');

	$recent_topfives = new topfives();
	$recent_topfives->retrieve('5');
?>

<!-- begin recent -->
<div id="articlebar">
	<h2 id="recentadditions">Recent Additions</h2>	
	<div class="access"><a href="#skiprecent">skip recent additions</a></div>

	<div id="recent">
		<div id="recent_articles">
			<h3><a href="reviews.html">Articles</a></h3>
			<ul>
			<?php
				for ( $i = 0; $i < $recent_articles->count; $i++ )
				{
					$a = $recent_articles->get($i);
					printf("<li><a href='%s'>%s</a></li>\n", $a->getLink(), $a->title);
				}
			?>
			</ul>
		</div>
		
		<div id="recent_top5">
			<h3><a href="topfives.html">Top 5 Lists</a></h3>
			<ul>
			<?php
				for ( $i = 0; $i < $recent_topfives->count; $i++ )
				{
					$t = $recent_topfives->get($i);
					printf("<li><a href='%s'>%s</a></li>\n", $t->getLink(), $t->title);
				}
			?>
			</ul>
		</div>
	</div>
</div>
<a name="skiprecent" class="access">&nbsp;</a> 
<!-- end recent -->
