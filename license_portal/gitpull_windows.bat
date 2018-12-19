@echo off

cd ..

git pull origin staging

net stop apache-webserver
net start apache-webserver
