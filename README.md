# Fates List

This is the source code for [Fates List](https://fateslist.xyz)

BTW please add your bots there if you want to support us

HubSport Track Code can be gotten by signing up for HubSpot at https://app.hubspot.com and copy pasting the script tag from the Track/Install Code given like '<script type="text/javascript" id="hs-script-loader" async defer src="//js.hs-scripts.com/REDACTED.js"></script>'


**How to deploy**

1. Buy a domain (You will need a domain that can be added to Cloudflare in order to use Fates List. We use namecheap for this)

2. Add the domain to Cloudflare (see [this](https://support.cloudflare.com/hc/en-us/articles/201720164-Creating-a-Cloudflare-account-and-adding-a-website)). Our whole website requires Cloudflare as the DNS in order to work.

3. Buy a Linux VPS (You need a Linux VPS or a Linux home server with a public ip with port 443 open)

4a) In Cloudflare, create a record (A/CNAME) called @ that points to your VPS ip/hostname

4b) In Cloudflare, create a record (A/CNAME) called m that points to your VPS ip/hostname

4c) In Cloudflare, go to Speed > Optimization. Enable AMP Real URL and enable Mobile Redirect to m.YOURDOMAIN with Keep Path ON

5. Download this repo on the VPS using "git clone https://github.com/Fates-List/FatesList/edit/main/README.md"

6. Enter Fates List directory, copy config_template.py to config.py and fill in the required information there
