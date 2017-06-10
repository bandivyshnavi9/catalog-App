Place your catalog project in this directory.
 Project Name: Item catalog
 Requirements: vagrant, Python
 
 This directory contains 
	templates folder, which contians HTML files.
	static folder, whcih contains application logo.
	client_secrets.json file, which contains all details of the client.
	database_setup.py file, which is need to connect database for this application.
	main.py file, which is the source file for this project.

	
Instructions to run the project
1. Open git bash outside the catalog file.
2. Enter vagrant up (to boot the vagrant environment)
3. Enter vagrant ssh (setups the connection)
4. Type cd /vagrant/catalog
5.Run python database_setup.py (to setup database connection)
6. Run python main.py
7. Open http://localhost:5000/


