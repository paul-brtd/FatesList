#!/usr/bin/python3
def pinput(s):
    while True:
        tmp = input(s)
        if tmp == "":
            continue
        else:
            if tmp.isdigit():
                return int(tmp)
            return tmp

t = pinput("Enter the type (1 = CSS): ")
if t == 1:
    css_tag = pinput("Enter CSS Tag To Document: ")
    tag_desc = pinput("Enter tag description: ")
    print("\nOUTPUT:\n")
    print(f'<strong class="doc">{css_tag}</strong><span>{tag_desc}</span><br/>')
