# Fates List

Licensed under the [MIT](LICENSE). We will not support self hosting or copying our list whatsoever, you are on your own and you MUST additionally give credit and follow the MIT license properly.

This is the source code for [Fates List](https://fateslist.xyz).

BTW please add your bots there if you want to support us

## Deploying (for contributors)

Run ```python manage.py site venv``` to setup a venv for Fates List

Then run ``python manage.py db setup`` after activating the created venv to setup the databases

To start the dragon (must be started before the main site): ``python manage.py site dragon``

To start the main site (must be started after dragon): ``python manage.py site run``

To start the manager bot (must be started after dragon): ``python manage.py site manager``

**Make sure /home/meow exists and you are logged in as meow while running Fates List. fates.sock is the main site socket and fatesws.sock is websocket socket**