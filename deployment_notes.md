# Deploying `silwood_masters`

This is a recipe to create a live version of the web application, using AWS Lightsail.

## AWS Lightsail

Lightsail instances are pre-packaged virtual machines primarily designed to run websites and applications. You could use EC2 virtual machines and EBS storage, but Lightsail is faster and easier. You will need to have an AWS account and that does need payment details - although the first month is free, eventually you will be charged.

### Create a Lightsail instance

Go to the [Lightsail console](https://lightsail.aws.amazon.com/ls/webapp/home/instances) to create an instance. 

* Select an "OS only" blueprint and the most recent Ubuntu LTS.  The prepackaged "Apps + OS"  blueprints do not currently include web2py.

* Click change the SSH key pair and name and create a new SSH key. You will need to download the private key file (`key_name.pem`) and look after it - you'll never get another opportunity to save it. This private key can be used to connect via SSH and SFTP and can be given to other trusted people who might want access.

* Choose the instance specs, name the instance and then create it.

### Create a static IP

Your new instance has a public IP address, but if something happens and you need to recreate the instance then that IP address will change. 

* Go to the networking tab on the Lightsail console and click on create a static IP.
* Choose a name for the Static IP address and attach your newly created instance to the new static IP.

Now, if you do have to change the Lightsail instance - an OS upgrade or some hideous crash - then you can simply attach it to the same Static IP.

### Allow HTTPS connections

The default setup is that the instance will accept SSH and HTTP connections, but we will be setting up the application to use HTTPS.

* On the instance tab of the Lightsail console, click on the instance you created.
* Now click on the 'Networking' tab for the instance and, under the Firewall settings, click 'Add rule', select the 'HTTPS' application and click create.


## Instance setup

We now need to setup the Lightsail VM to serve this application. There is a Connect tab on the instance console containing a big orange button that will launch an SSH session in your browser. However, this relies on you being logged into AWS, so will only work for the account holder. More generally, an administrator can log in using the SSH key file as below. Note that `ubuntu` is the root account name.

```
# SSH session
ssh -i key_name.pem ubuntu@18.130.184.162
# SFTP
sftp -i key_name.pem ubuntu@18.130.184.162
```

### Install web2py

The first thing to do is install all the machinery needed to run a webserver and the application. Fortunately, web2py provides some canned recipes that do this automatically. We will use [web2py](http://www.web2py.com/) running under the [nginx](https://www.nginx.com/) webserver.

* Log in to the virtual machine using SSH or the AWS console.
* Download and run the recipe for setting up web2py using nginx on Ubuntu. This script requires some user input on occasion.

```sh
curl -O https://raw.githubusercontent.com/web2py/web2py/master/scripts/setup-web2py-nginx-uwsgi-ubuntu.sh
sudo sh setup-web2py-nginx-uwsgi-ubuntu.sh
```

* Reboot the instance

```sh
sudo reboot
```

After the instance restarts, you should be able to point a browser at your static IP address and see the web2py welcome application.

### Switching to python3

Assuming you have `python3` installed - and it should come by default with the instance image - you can now switch the webserver to use python3. This involves replacing the `uwsgi` installed by the script with the python3 version:

```sh
sudo apt install python3-pip
sudo -H pip uninstall uwsgi
sudo -H pip3 install uwsgi
reboot
```

### Install the application

* At the moment, the application repository is private, so you will need to authenticate to clone the application code. This is easier using HTTPS and you should be prompted for a password - note you need to set your username in the URL! Note that the `www-data` user is set here so that that account owns the application directory, otherwise you'll get permission errors when you try to access the website.

```sh
cd /home/www-data/web2py/applications
sudo -u www-data git clone git clone https://username@bitbucket.org/davidorme/marking_reports.git
```

* If you do get permission errors then you can probably fix it like this:

```sh
cd /home/www-data/web2py/applications
sudo chown -R www-data marking_reports
```

* You now need to install some python packages needed for the application. These are being installed globally (`-H`) rather than just into the site packages for the `ubuntu` account. You might as well install ipython as well - it is useful if you end up needing to debug the application on the server

```sh
cd /home/www-data/web2py/applications/marking_reports
sudo -H pip install -r requirements.txt
sudo -H pip install ipython
```

* The application uses the open source font DejaVu for producing PDFs using the `fpdf` package. The package is a bit old and simple but is quick and lightweight. Ubuntu often includes some of the font family in `/usr/share/fonts/truetype` but check to see if `DejaVuSansCondensed.ttf` and `DejaVuSansCondensed-Bold.ttf` are there. If not:

```sh
sudo apt-get install ttf-dejavu
```



* You need to set an admin user password for web2py in order to access the web2py admin application and the admin pages for `marking_reports`. You will need to make a note of what you enter here - once it is set it is not recoverable!

```sh
cd /home/www-data/web2py
sudo python -c "from gluon.main import save_password; save_password(raw_input('admin password: '),443)"
```

* Now just to make the user experience nicer, set the routes for web2py so that  `marking_reports/default` is used as the default and can be omitted from URLs.

```sh
echo "routers = dict(
    BASE = dict(
        default_application='marking_reports',
    )
)
" | sudo tee /home/www-data/web2py/routes.py
```

* Populating the database.

If you are moving an existing instance of the application rather than starting afresh, you now should need to simply move the `storage.sqlite` file from the old instance into the `databases` folder.

* **Configure the application**. The application requires some configuration information, which is stored in `private/appconfig.ini`. This is not included in the repo because it contains sensitive information, but an empty template is that you will need to complete and rename. The configuration sets up the database connection,  the email account used to send email from the application, the local location of the fonts directory for use by FPDF and a link used to share thesis reports with markers.

* If you restart the webserver and web2py, the IP address should go straight to the landing page for `marking_reports`. The commands below are generally useful for refreshing and testing changes to the server and web2py.

```sh
# Restart UWSGI and NGINX
sudo start uwsgi-emperor
sudo /etc/init.d/nginx restart
# Restart web2py leaving the webserver alone
sudo touch /etc/uwsgi/web2py.xml
```

## Email connections

AWS imposes limitations on connecting to email server via SMTP ports (e.g. 25). In order to send email via SMTP, you have to contact AWS and ask for those restrictions to be lifted.

https://console.aws.amazon.com/support/contacts?#/rdns-limits

It is also good to configure reverse DNS so that the IP address points to the domain as well as vice versa.

## Enabling HTTPS

Using HTTPS requires that the webserver is issued a valid certificate. [LetsEncrypt](https://letsencrypt.org/) is a free, non-profit certificate authority supported by a really good command line tool to issue and renew the certificate. 

However, you can only get a certificate for a domain name (`www.silwoodmasters.org`) and not an IP address (`18.130.184.162`), so you will need to obtain a domain name and then register an A Record that points that domain name to the Static IP you created. 

* Once you've done that then install the LetsEncrypt software:

```sh
sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

* You can now run the certbot, specifying the domain name

```sh
sudo certbot --nginx -d mydomainame.com -d www.mydomainame.com
```

* Restart the webserver as above and you should now have a secure HTTPS connection to the application. The [certbot website](https://certbot.eff.org/) has some neat tools to check whether it is working correctly.


## Box integration

The application uses Box to store student reports securely. This requires creating a Box App that provides access to the files. There are several types but JWT allows for token based access that does not require that users have a Box account of their own. So to enable this, a user with a Box account needs to set up a Box App using JWT. The app should have permission to read and download files but doesn't need any larger scope. It does need to have the advanced settings to "Generate User Access Tokens". You should also generate a new RSA key, which will automatically download a config file to allow remote access

Creating this app will generate a config file for accessing the Box app remotely. , which will need to be included in the web application `private` folder and also linked in the web application `appconfig.ini`
