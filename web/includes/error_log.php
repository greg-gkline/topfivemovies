<?php
Include("/home/subclav/public_html/includes/db_auth.php");
if ( $db = GetPrimaryDB() )
{
	$request_method		= $REQUEST_METHOD;
	$request_uri		= $REQUEST_URI;
	$query_string		= $QUERY_STRING;
	$http_referer		= $HTTP_REFERER;
	$http_user_agent	= $HTTP_USER_AGENT;
	$remote_addr		= $REMOTE_ADDR;
	$http_host			= $HTTP_HOST;
	
	$remote_host		= gethostbyaddr($remote_addr);

	$query = sprintf("INSERT INTO errors (request_method, request_uri, http_referer, http_user_agent, remote_addr, remote_host, http_host) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s');",
		$request_method,
		$request_uri,
		$http_referer,
		$http_user_agent,
		$remote_addr,
		$remote_host,
		$http_host );
		
	mysql_query($query, $db);
}
?>
