from bam_core.utils.email import format_email


def test_spaces_in_email():
    """
    Test that spaces are removed from email addresses
    """
    email = "person@g mail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_trailing_periods_in_email():
    """
    Test that trailing periods are removed from email addresses
    """
    email = "person@gmail.com."
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_email_without_dot_com():
    """
    Test that common domains without .com are fixed
    """
    email = "person@gmail"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_email_without_at_symbol():
    """
    Test that common domains without an "@" are fixed
    """
    email = "persongmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_email_with_trailing_at_symbol():
    """
    Test that emails with a trailing "@" are fixed
    """
    email = "person@gmail.com@"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_common_domain_misspellings():
    """
    Test that common domain misspellings are fixed
    """
    email = "person@gmail.c"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_dot_es_emails_are_allowed():
    """
    Test that .es emails are allowed
    """
    email = "person@hotmail.es"
    result = format_email(email)
    assert result["email"] == email


def test_capitalization():
    """
    Test that capitalization is removed
    """
    email = "PERSON@hotmail.es"
    result = format_email(email)
    assert result["email"] == "person@hotmail.es"


def test_nulls_are_removed():
    """
    Test that nulls are removed
    """
    email = "none"
    result = format_email(email)
    assert result["email"] == ""
    assert result["error"] == "No email address provided"


def test_email_with_dot_co():
    """
    Test that emails with .co are fixed
    """
    email = "person@gmail.co"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_email_with_no_dot_in_domain():
    """
    Test that emails with no dot in the domain are fixed
    """
    email = "person@gmailcom"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_email_with_pluses_arent_removed():
    """
    Test that emails with a plus aren't removed.
    """
    email = "person+1@gmail.com"
    result = format_email(email)
    assert result["email"] == "person+1@gmail.com"


def test_dns_check():
    """
    Test that the DNS check works
    """
    email = "no@gmailll69.com"
    result = format_email(email, dns_check=True)
    assert result["email"] == email
    assert result["error"] == "The domain name gmailll69.com does not exist."


def test_multiple_errors():
    email = "FOOO bar@gmeil.con"
    result = format_email(email)
    assert result["email"] == "fooobar@gmail.com"


def test_hotmail_es_errors():
    email = "person@hotmeil.es"
    result = format_email(email)
    assert result["email"] == "person@hotmail.es"


def test_gmail_mx_errors():
    email = "person@gmeil.mx"
    result = format_email(email)
    assert result["email"] == "person@gmail.mx"


def test_email_dot_after_at_symbol():
    email = "person@.gmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_multiple_issues():
    email = " PERSON @.g.mail..com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_at_spelled_out():
    email = "person at gmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_space_instead_of_dot_in_domain():
    email = "person@yahoo com"
    result = format_email(email)
    assert result["email"] == "person@yahoo.com"


def test_no_space_in_domain_and_con_instead_of_com():
    email = "person@ gmail con"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_duplicated_at_symbol():
    email = "person@@gmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_dot_vom():
    email = "person@gmail.vom"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_at_com():
    email = "person@gmail@com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_mail_to():
    email = "mailto:person@gmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_period_before_at_symbol():
    email = "person.@gmail.com"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_number_after_dot_com():
    email = "person.@gmail.com1"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_qmqil_dot_com():
    email = "person.@gmqil.com1"
    result = format_email(email)
    assert result["email"] == "person@gmail.com"


def test_icolud_dot_com():
    email = "person@icolud.com"
    result = format_email(email)
    assert result["email"] == "person@icloud.com"


def test_dot_instead_of_at_symbol():
    email = "another.person.gmail.com"
    result = format_email(email)
    assert result["email"] == "another.person@gmail.com"

def test_dot_col():
    email = "test@gmail.col"
    result = format_email(email)
    assert result["email"] == "test@gmail.com"
