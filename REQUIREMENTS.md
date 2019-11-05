Requirements & Dependencies 
===========
- Python 3.6->3.7
===========
- PHP 5.6.x (tested also with 7.0)
	- PHP-CLI on the host for the relay scripts
	- MYSQL extension on the server
===========
Windows
- IIS7 (or perhaps all versions), must specifically have a MIME type to handle .JSON files:
	- application/json; charset=utf-8
- Load the mysql extension in the php.ini file. By default no extensions are loaded.
	- extension = php_mysql.dll
===========
phpMyAdmin 