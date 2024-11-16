import re
from string import punctuation
from typing import Dict
from email_validator import validate_email, EmailNotValidError

NO_EMAIL_ERROR = "No email address provided"

COMMON_DOMAIN_MISSPELLINGS = {
    "gimail": "gmail.com",
    "gmaill": "gmail.com",
    "g.mail": "gmail.com",
    "gnail": "gmail.com",
    "gmail.cok": "gmail.com",
    "gmail.comh": "gmail.com",
    "gmail.comaa": "gmail.com",
    "gmaik": "gmail.com",
    "gmqil": "gmail.com",
    "gmsil": "gmail.com",
    "gmzil": "gmail.com",
    "gmal": "gmail.com",
    "gmai": "gmail.com",
    "gmeil": "gmail.com",
    "gmailcon": "gmail.com",
    "gmil.cpor": "gmail.com",
    "gmail.es": "gmail.com",
    "gimel": "gmail.com",
    "gomail": "gmail.com",
    "hamel": "gmail.com",
    "gmalil": "gmail.com",
    "gamial": "gmail.com",
    "gamail": "gmail.com",
    "gmil": "gmail.com",
    "gail": "gmail.com",
    "gm": "gmail.com",
    "gamil": "gmail.com",
    "gmeal": "gmail.com",
    "gmale": "gmail.com",
    "gemeal": "gmail.com",
    "hotmal": "hotmail.com",
    "hoimail": "hotmail.com",
    "hotmai": "hotmail.com",
    "hotmaiil": "hotmail.com",
    "hotamil": "hotmail.com",
    "hotmeil": "hotmail.com",
    "hotmali": "hotmail.com",
    "yahooo": "yahoo.com",
    "yaho": "yahoo.com",
    "hahoo": "yahoo.com",
    "tahoo": "yahoo.com",
    "sol": "aol.com",
    "icolud.com": "icloud.com",
    "iclud": "icloud.com",
}

COMMON_DOMAINS = [
    "gmail",
    "hotmail",
    "yahoo",
    "aol",
    "outlook",
    "icloud",
    "rocketmail",
]

COMMON_NULLS = [
    "none",
    "dont have one",
    "doesn't have one",
    "no tengo",
    "no. tengo",
    "no te tengo",
    "no tiene",
    "no have",
    "no enail",
    "no email",
    "notengo",
    "notemgo",
    "no tengo uso el telefono",
    "none@none.com",
    "no",
    "n/a",
    "na",
    "ñ",
    "n",
    "na@na.com",
    "dont have one",
    "ca",
    "0@gmail.com",
    "0",
    "-",
    ".",
    "no email address",
    "null",
    "xxxxxxx",
    "xxxxxx",
    "xxxxx",
    "xxxx",
    "xxx",
    "xx",
    "x",
]


def clean_email(email: str) -> str:
    """
    Clean an email address
    :param email: The email address to clean
    :return: The cleaned email address
    """
    # remove whitespace
    email = email.replace(" ", "").strip()

    # remove all trailing punctuation
    while email[-1] in punctuation:
        email = email[:-1]

    # check for mailto:
    if email.startswith("mailto:"):
        email = email[7:]

    # check for .vom typos
    if email.endswith(".vom"):
        email = email[:-4] + ".com"

    # check for .col typos
    if email.endswith(".col"):
        email = email[:-4] + ".com"

    # check for .comp typos
    if email.endswith(".comp"):
        email = email[:-5] + ".com"

    # check for .como typos
    if email.endswith(".como"):
        email = email[:-5] + ".com"

    # check for @com typos
    if email.endswith("@com"):
        email = email[:-4] + ".com"

    # check for .clm typos
    if email.endswith(".clm"):
        email = email[:-4] + ".com"

    # check for .con typos
    if email.endswith(".con"):
        email = email[:-4] + ".com"

    # check for .c typos
    if email.endswith(".c"):
        email = email[:-2] + ".com"

    # check for ..com typos
    if email.endswith("..com"):
        email = email[:-5] + ".com"

    # check for doubled .com typos
    if email.endswith(".com.com"):
        email = email[:-8] + ".com"

    # check for numbers after .com via regular expression
    if re.search(r"\.com[0-9]$", email):
        email = email[:-5] + ".com"

    # check for common misspellings
    for misspelling, replacement in COMMON_DOMAIN_MISSPELLINGS.items():
        if email.endswith(misspelling):
            email = email.replace(misspelling, replacement)
        elif email.endswith(f"{misspelling}.com"):
            email = email.replace(f"{misspelling}.com", replacement)
        elif email.endswith(f"{misspelling}com"):
            email = email.replace(f"{misspelling}com", replacement)
        elif email.endswith(f"{misspelling}.es"):
            es_replace = replacement.replace(".com", ".es")
            email = email.replace(f"{misspelling}.es", es_replace)
        elif email.endswith(f"{misspelling}.mx"):
            mx_replace = replacement.replace(".com", ".mx")
            email = email.replace(f"{misspelling}.mx", mx_replace)

    # check for missing . in domain
    for domain in COMMON_DOMAINS:
        if email.endswith(f"{domain}com"):
            email = email.replace(f"{domain}com", f"{domain}.com")

    # check for at spelled out in domain
    for domain in COMMON_DOMAINS:
        if email.endswith(f"at{domain}.com"):
            email = email.replace(f"at{domain}.com", f"@{domain}.com")
        if email.endswith(f"at{domain}.mx"):
            email = email.replace(f"at{domain}.mx", f"@{domain}.mx")
        if email.endswith(f"at{domain}.es"):
            email = email.replace(f"at{domain}.es", f"@{domain}.es")

    # check for missing .com
    for domain in COMMON_DOMAINS:
        if (
            domain in email
            and not email.endswith(".com")
            and not "." in email.split("@")[-1]
        ):
            email = email.replace(domain, f"{domain}.com")

    # check for .co in common domains
    for domain in COMMON_DOMAINS:
        if email.endswith(f"{domain}.co"):
            email = email[:-3] + ".com"

    # check for missing @ symbol
    for domain in COMMON_DOMAINS:
        if domain in email and "@" not in email:
            email = email.replace(domain, f"@{domain}")

    # check for period after @
    if "@." in email:
        email = email.replace("@.", "@")

    # check for period before @
    if ".@" in email:
        email = email.replace(".@", "@")

    # check for duplicated @
    if "@@" in email:
        email = email.replace("@@", "@")

    # check for @ symbol in username
    at_count = email.count("@")
    if at_count > 1:
        email = email.replace("@", ".", at_count - 1)

    return email


def format_email(email: str, dns_check: bool = False) -> Dict[str, str]:
    """
    Format an email address to the standard
    :param email: The email address to format
    :return: The formatted email address
    """
    # first perform basic cleaning on the email address before validating
    email = email.strip().lower()

    # check for common nulls
    if email in COMMON_NULLS:
        return {"email": "", "error": NO_EMAIL_ERROR}

    # now correct common errors
    email = clean_email(email)

    try:
        email_info = validate_email(email, check_deliverability=dns_check)
        return {"email": email_info.normalized, "error": ""}
    except EmailNotValidError as e:
        return {"email": email, "error": str(e)}
