# Fates List

Licensed under the MIT. We will not support self hosting or copying our list whatsoever, you are on your own and you MUST additionally give credit and change the branding.

This is the source code for [Fates List](https://fateslist.xyz)

BTW please add your bots there if you want to support us

**How to deploy**

1. Buy a domain (You will need a domain that can be added to Cloudflare in order to use Fates List. We use namecheap for this)

2. Add the domain to Cloudflare (see [this](https://support.cloudflare.com/hc/en-us/articles/201720164-Creating-a-Cloudflare-account-and-adding-a-website)). Our whole website requires Cloudflare as the DNS in order to work.

3. Buy a Linux VPS (You need a Linux VPS or a Linux home server with a public ip with port 443 open)

 4a) In Cloudflare, create a record (A/CNAME) called @ that points to your VPS ip/hostname

 4b) In Cloudflare, go to Speed > Optimization. Enable AMP Real URL
 
 4c) In Cloudflare, go to SSL/TLS, set the mode to Full (strict), enable Authenticated Origin Pull, make an origin certificate (in Origin Server) and save the private key as /key.pem on your VPS and the certificate as /cert.pem on your VPS
 
 4d) Download https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem and save it on the VPS as /origin-pull-ca.pem.

5. Download this repo on the VPS using "git clone https://github.com/Fates-List/FatesList"

6. Enter Fates List directory, copy config_secrets_template.py to config_secrets.py and fill in the required information on there. You do not need to change site_url or mobile_site_url fields (site and mobile_site do need to be filled in without the https://).

7. Download and install nginx, redis, python3 and PostgreSQL (using the pg_user and pg_pwd you setup in config.py). Run psql and then run \i schema.sql to setup the postgres schema

8. Remove the /etc/nginx folder, then copy the nginx folder from this repo to /etc. Change the server_name values /etc/nginx/conf.d/default.conf to reflect your domain

9. Restart nginx

10. Install tmux, then run "tmux"

11. Run "pip3 install -r requirements.txt"

12. Run "./run" in the repo folder

Fates List probihits the monetization or resale of coins for money
