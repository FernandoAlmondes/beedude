from cryptography.fernet import Fernet

key = Fernet.generate_key()
f = Fernet(key)

print('Fernetkey:', key.decode())

# importing the function from utils
from django.core.management.utils import get_random_secret_key

# generating and printing the SECRET_KEY
print('Secretkey:', get_random_secret_key())