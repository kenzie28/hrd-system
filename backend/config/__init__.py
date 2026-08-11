import pymysql

# Django's `django.db.backends.mysql` expects the `mysqlclient` driver, but
# we use the pure-Python `pymysql` package instead (no system libmysqlclient
# needed, simpler to install in the Docker image). This shim makes pymysql
# masquerade as MySQLdb so Django's mysql backend works unchanged.
pymysql.install_as_MySQLdb()
