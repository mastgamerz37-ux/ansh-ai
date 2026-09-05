import urllib.parse
import webbrowser

def send_email(to: str, subject: str = "", body: str = "") -> str:
    """
    Opens the default browser to Gmail's compose window pre-filled with details.
    """
    try:
        base_url = "https://mail.google.com/mail/?view=cm&fs=1"
        if to:
            base_url += f"&to={urllib.parse.quote(to)}"
        if subject:
            base_url += f"&su={urllib.parse.quote(subject)}"
        if body:
            base_url += f"&body={urllib.parse.quote(body)}"
        
        webbrowser.open(base_url)
        return f"Opened Gmail compose window to send email to {to}"
    except Exception as e:
        return f"Failed to open Gmail: {str(e)}"
