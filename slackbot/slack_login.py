from slackbot.config import settings, the_crypter
from slacker import Slacker


def slack_logon(encrypted_token):
    """ logs on to the slack channel using the api token
    :param encrypted_token: the encrypted api token
    :type encrypted_token: str
    :return: logged on slack object
    :rtype Slacker.Slacker
    """
    slack = Slacker(the_crypter.decrypt(encrypted_token))
    return slack


slack_bot = slack_logon(settings['api_token'])
slack_bot.chat.post_message('#bot_testing', 'I LIVE', as_user=True)
