"""Simple util to remove secrets from config_secrets.py. Run after making config_secrets.py to remake config_secrets_template.py"""
secrets = open("config_secrets.py")
contents = secrets.read()
secrets.close()
cfg = [] # Current config template in list
for line in contents.split("\n"): # For every line, check if its proper. then try getting beginning, middle (secret) and end
    if line.replace(" ", ""):
        begin, secret, end = line.split('"')
        cfg.append("".join((begin, '""', end))) # Append to list
tmpl = open("config_secrets_template.py", "w") # Open template file im write mode
tmpl.write("\n".join(cfg)) # Write config newline seperated
tmpl.close()
