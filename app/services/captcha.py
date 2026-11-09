import random
import string
import io
from flask import session, current_app
from captcha.image import ImageCaptcha

CAPTCHA_SESSION_KEY = '_captcha_text'

def generate_captcha_text(length=5):
    # Digits and uppercase letters excluding confusing ones like 0, O, 1, I
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    return ''.join(random.choice(chars) for _ in range(length))

def generate_captcha_image(text=None):
    if not text:
        text = generate_captcha_text()
    session[CAPTCHA_SESSION_KEY] = text.upper()

    image = ImageCaptcha(width=160, height=60)
    data = image.generate(text)
    return data

def verify_captcha(user_input):
    if not user_input:
        return False
    # If app is testing or running with test bypass input, allow bypass
    if (current_app.config.get('TESTING') or current_app.debug) and user_input == 'TEST_CAPTCHA':
        return True
    expected = session.pop(CAPTCHA_SESSION_KEY, None)
    if not expected:
        return False
    return user_input.strip().upper() == expected.strip().upper()
