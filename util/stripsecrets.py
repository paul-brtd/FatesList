"""Simple util to remove secrets from config_secrets.py"""
secrets = open("config_secrets.py")
contents = secrets.read()
for line in contents.split("\n"):
    if line.replace(" ", ""):
        begin, secret, end = line.split('"')
        print("".join((begin, '""', end)))
