# Self Hosting

Licensed under the MIT. We will not support self hosting or copying our list whatsoever, you are on your own and you MUST additionally give credit and change the branding.

This is the source code for [Fates List](https://fateslist.xyz/)

BTW please add your bots there if you want to support us

!!! danger
    Fates List is extremely difficult to the point of almost impossible (without knowledge in python) to self host. It requires Ubuntu 20.04+ (support for Windows and MacOS will never be happening since we do not use it). It also needs a huge amount of moving parts. **This page is only meant for people developing Fates List**

**How to deploy**

1. Buy a domain (You will need a domain that can be added to Cloudflare in order to use Fates List. We use namecheap for this)
2. Add the domain to Cloudflare (see [this](https://support.cloudflare.com/hc/en-us/articles/201720164-Creating-a-Cloudflare-account-and-adding-a-website)). Our whole website requires Cloudflare as the DNS in order to work.
3. Buy a Linux VPS (You need a Linux VPS or a Linux home server with a public ip with port 443 open)

4a) In Cloudflare, create a record (A/CNAME) called @ that points to your VPS ip/hostname

4b) In Cloudflare, go to Speed &gt; Optimization. Enable AMP Real URL

4c) In Cloudflare, go to SSL/TLS, set the mode to Full (strict), enable Authenticated Origin Pull, make an origin certificate (in Origin Server) and save the private key as /key.pem on your VPS and the certificate as /cert.pem on your VPS

4d) Download [https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem](https://support.cloudflare.com/hc/en-us/article_attachments/360044928032/origin-pull-ca.pem) and save it on the VPS as /origin-pull-ca.pem.

1. Download this repo on the VPS using `git clone https://github.com/Fates-List/FatesList`. Make sure the location it is downloaded to is publicly accessible AKA not in a /root folder or anything like that.
2. Enter Fates List directory, copy config_secrets_template.py to config_secrets.py and fill in the required information on there. You do not need to change site_url or mobile_site_url fields (site and mobile_site do need to be filled in without the https://). 
3. Download, install and configure nginx, redis, rabbitmq, python3.10, PostgreSQL (using the pg_user and pg_pwd you setup in config.py). Run `su postgres` and then run `psql` and finally run  `\i schema.sql` to setup the postgres schema. Then install swarm64
4. Enter the admin folder, then run `python3 manage.py makemigrations` and then run `python3 manage.py migrate` (where python3 is python3.10)
5. Remove the /etc/nginx folder, then copy the nginx folder from this repo to /etc. Change the server_name values /etc/nginx/conf.d/default.conf to reflect your domain
6. Restart nginx
7. Install tmux, then run `tmux new -s main`
8. Install fastapi-limiter from [https://github.com/Fates-List/fastapi-limiter](https://github.com/Fates-List/fastapi-limiter) and aioredis from [https://github.com/Fates-List/aioredis-py](https://github.com/Fates-List/aioredis-py)
9. Run `pip3 install -r requirements.txt`
10. Run `./run` in the repo folder
11. Hit Ctrl-B. Then run `tmux new -s rabbit`. Then run `python3 rabbitmq_worker.py`


Fates List probihits the monetization or resale of coins for money
