# Fates List

Licensed under the [MIT](LICENSE). We will not support self hosting or copying our list whatsoever, you are on your own and you MUST additionally give credit and follow the MIT license properly.

This is the source code for [Fates List](https://fateslist.xyz).

BTW please add your bots there if you want to support us

## Deploying (for contributors)

Follow [Snowtuft's README](https://github.com/Fates-List/Snowtuft) to setup Snowtuft+Snowfall on your VPS and install the dependencies for Fates List.

Then run ``python manage.py`` after activating the created venv to verify installation

To start the rabbitmq worker (must be started before the main site): ``python manage.py rabbit run``
To start the main site (must be started after rabbit): ``python manage.py site run``
