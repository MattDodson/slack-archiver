import yaml
import os
from slackbot.security import Security

parent_dir = os.path.dirname(__file__)

# loads the settings variable to be used across the project
with open(os.path.join(parent_dir, 'settings.yaml'), 'r') as read_file:
    settings = yaml.load(read_file, Loader=yaml.FullLoader)

# loads the encryption/decryption object to be used across the project
with open(os.path.join(parent_dir, settings['key_file']), 'r') as read_file:
    the_crypter = Security(read_file.read())
