import os, requests
from jinja2 import FileSystemLoader, Environment
from dotenv import load_dotenv

load_dotenv()

domain = os.getenv("MAILGUN_DOMAIN")
template_loader = FileSystemLoader("templates")
template_env = Environment(loader=template_loader)

def render_template(template_filename, **context):
    return template_env.get_template(template_filename).render(**context)

def send_simple_message(to, subject, body, html):
    return requests.post(
  		f"https://api.mailgun.net/v3/{domain}/messages",
  		auth=("api", os.getenv('MAILGUN_API_KEY')),
  		data={
            "from": f"Mailgun Sandbox <postmaster@{domain}>",
			"to": [to],
  			"subject": subject,
  			"text": body,
            "html": html
        }
    )

def send_registration_email(email, username):
    return send_simple_message(
        email, 
        "Successfully signed up!",
        f"Hi {username}, you have registered!",
        render_template("email/action.html", username=username)
    )
