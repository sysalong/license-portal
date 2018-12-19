cd ..

git pull origin production

echo "appdep" | sudo -S systemctl restart apache2
