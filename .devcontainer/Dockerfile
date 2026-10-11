FROM php:5.6-apache

# php:5.6 is built on Debian stretch, which now lives on the archive mirror. Its signing
# keys have expired, hence --allow-unauthenticated (dev image only).
RUN sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org|g; /stretch-updates/d' /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --allow-unauthenticated --no-install-recommends default-mysql-client \
 && rm -rf /var/lib/apt/lists/*

# mysql_* is what the site uses
RUN docker-php-ext-install mysql mysqli

# Serve web/ and run the old extensions (.php3, .inc and .html all contain PHP)
ENV APACHE_DOCUMENT_ROOT=/workspaces/topfivemovies/web
RUN sed -ri 's|/var/www/html|${APACHE_DOCUMENT_ROOT}|g' /etc/apache2/sites-available/*.conf /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf
COPY apache-topfive.conf /etc/apache2/conf-available/topfive.conf
COPY php-topfive.ini /usr/local/etc/php/conf.d/topfive.ini
RUN a2enconf topfive && a2enmod rewrite  # web/.htaccess uses RewriteRule

COPY entrypoint.sh /usr/local/bin/topfive-entrypoint
RUN chmod +x /usr/local/bin/topfive-entrypoint

ENTRYPOINT ["topfive-entrypoint"]
CMD ["apache2-foreground"]
