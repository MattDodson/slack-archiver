import yaml
from slackbot.security import Security

# loads the settings variable to be used across the project
with open('settings.yaml', 'r') as read_file:
    settings = yaml.load(read_file, Loader=yaml.FullLoader)

# loads the encryption/decryption object to be used across the project
with open(settings['key_file'], 'r') as read_file:
    the_crypter = Security(read_file.read())
