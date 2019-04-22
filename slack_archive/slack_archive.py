import json
import os
import shutil
from slacker import Slacker
from slack_archive.config import settings, the_crypter
from datetime import datetime
from time import sleep
import re


def retrieve_messages(pageable_object, channel_id, last_time, page_size=100):
    """ retrieves the messages from the passed in channel in json format and stores them in memory
    :param pageable_object:
    :type pageable_object: slacker.Channels or slacker.groups
    :param channel_id: slack channel id
    :type channel_id: str
    :param last_time: last download run time of the archiving in epoch seconds
    :type last_time: float
    :param page_size: page size
    :type page_size: int
    :return: list of messages in dict format
    :rtype: list(dict)
    """
    messages = []
    last_timestamp = None

    while True:
        response = pageable_object.history(
            channel=channel_id,
            latest=last_timestamp,
            oldest=last_time,
            count=page_size).body
        # Response has keys of ok, messages, and has_more
        print(response)
        messages.extend(response['messages'])

        if response['has_more']:
            last_timestamp = messages[-1]['ts']  # -1 means last element in a list
            sleep(2)  # Respect the Slack API rate limit
        else:
            break

    return messages


def timestamp_to_datetime(time_stamp):
    """ converts a timestamp in epoch seconds to a UTC timestamp
    :param time_stamp: timestamp in epoch seconds
    :type time_stamp: str
    :return: UTC datetime object
    :rtype: datetime
    """
    if '.' in time_stamp:
        t_list = time_stamp.split('.')
        if len(t_list) != 2:
            raise ValueError('Invalid time stamp')
        else:
            return datetime.utcfromtimestamp(float(t_list[0]))


def channel_rename(old_channel, new_channel):
    """ In the event of a channel rename, move all files from the old channel folder to the new one
    :param old_channel: path to the old channel folder of jsons
    :type old_channel: str
    :param new_channel: path to the new channel folder where jsons should move to
    :type new_channel: str
    :return: None
    """
    if not os.path.isdir(old_channel):
        return
    _mkdir(new_channel)
    for fileName in os.listdir(old_channel):
        shutil.move(os.path.join(old_channel, fileName), new_channel)
    os.rmdir(old_channel)


def parse_and_save_messages(folder_path, messages, channel_type):
    """ parses the message list into groupings by day and then saves the day groupings to a json
    :param folder_path: folder to save the jsons to
    :type folder_path: str
    :param messages: list of messages in dict format
    :type messages: list(dict)
    :param channel_type: what type of channel it is
    :type channel_type: str
    :return: None
    """
    name_change_flag = channel_type + "_name"

    current_file_date = ''
    current_messages = []
    for message in messages:
        # first store the date of the next message
        ts = timestamp_to_datetime(message['ts'])
        file_date = '{:%Y-%m-%d}'.format(ts)

        # if it's on a different day, write out the previous day's messages
        if file_date != current_file_date:
            if current_file_date:
                out_file_name = '{room}/{file}.json'.format(room=folder_path, file=current_file_date)
                _to_json(current_messages, out_file_name)
            current_file_date = file_date
            current_messages = []

        # check if current message is a name change
        # dms won't have name change events
        if channel_type != "im" and ('subtype' in message) and message['subtype'] == name_change_flag:
            old_name = message['old_name']
            new_name = message['name']
            channel_rename(old_name, new_name)
            folder_path = new_name

        current_messages.append(message)
    out_file_name = '{room}/{file}.json'.format(room=folder_path, file=current_file_date)
    _to_json(current_messages, out_file_name)


def download_channels(slack_object, channel_list, folder_path, last_time):
    """ Downloads the passed in channel list to the passed in folder path
    :param slack_object: the slack connection
    :type slack_object: slacker.Slacker()
    :param channel_list: list of channel properties dict
    :type channel_list: list(dict)
    :param folder_path: path to save channel folders to
    :type folder_path: str
    :param last_time: last download run time of the archiving in epoch seconds
    :type last_time: float
    :return: None
    """
    for channel in channel_list:
        channel_name = channel['name']
        print(channel_name)
        channel_path = os.path.join(folder_path, channel_name)
        _mkdir(channel_path)
        messages = retrieve_messages(slack_object, channel['id'], last_time)
        parse_and_save_messages(channel_path, messages, 'channel')
        sleep(2)

    return


def _to_json(data_to_save, file_path):
    """ writes the passed in user list to the passed in file path location
    :param data_to_save: data to save to a json
    :type data_to_save: list(dicts)
    :param file_path: path of the file to save to
    :type file_path: str
    :return: None
    """
    with open(file_path, 'w') as write_file:
        json.dump(data_to_save, write_file, indent=4)


def bootstrap_key_values(slack_connection):
    """ caches values used throughout the downloading process
    :param slack_connection: logged in connection to slack
    :type slack_connection: Slacker
    :return: lists of the users, public channels, and dms
    :rtype: tuple(list[dicts], list, list
    """
    user_list = slack_connection.users.list().body['members']
    print("Found {0} Users".format(len(user_list)))
    sleep(2)
    print(sleep)

    channel_list = slack_connection.channels.list().body['channels']
    print("Found {0} Public Channels".format(len(channel_list)))
    sleep(2)

    private_channel_list = slack_connection.groups.list().body['groups']
    print("Found {0} Private Channels or Group DMs".format(len(private_channel_list)))
    sleep(2)

    return user_list, channel_list, private_channel_list


def _remove(path):
    """ removes a file or folder at the given path
    :param path: path to the file/folder to remove
    :type path: str
    :return: None
    """
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def _mkdir(directory):
    """ creates a directory structure from the passed in path
    :param path: directory structure to create
    :type path: str
    :return: None
    """
    if not os.path.isdir(directory):
        os.makedirs(directory)


def extract_date(folder_path):
    """ recursively gets the most recent date from a folder that contains files named in the YYYY-MM-DD format
    :param folder_path: path to the folder to search
    :type folder_path: str
    :return: date time in epoch seconds
    :rtype: float
    """
    most_recent_time = 0
    try:
        for i in os.listdir(folder_path):
            path = os.path.join(folder_path, i)
            regex_search = re.search('[0-9]{4}-[0-9]{2}-[0-9]{2}', i)
            if os.path.isdir(path):  # recurse
                most_recent_time = max([most_recent_time, extract_date(path)])
            elif regex_search:
                utc_time = datetime.strptime(regex_search.group(0), "%Y-%m-%d")
                most_recent_time = max([most_recent_time, (utc_time - datetime(1970, 1, 1)).total_seconds()])
    except (FileNotFoundError, NotADirectoryError):
        pass
    return most_recent_time


def pair_channels(i, j):
    """ finds like values in the passed in sorted lists
    :param i: first sorted list
    :type i: list
    :param j: second sorted list
    :type j: list
    :return: elements matched to elements in the list
    :rtype: list(tuple(element_in_first_list, element_in_second_list))
    """
    if not i:
        return [(None, x) for x in j]
    if not j:
        return [(x, None) for x in i]
    i = iter(i)
    j = iter(j)
    output_list = []
    value_1 = next(i, None)
    value_2 = next(j, None)
    while value_1 and value_2:
        if value_1 == value_2:
            output_list.append((value_1, value_2))
            value_1, value_2 = next(i, None), next(j, None)
        elif value_1 > value_2:
            output_list.append((None, value_2))
            value_2 = next(j, None)
        else:
            output_list.append((value_1, None))
            value_1 = next(i, None)

    if value_1:
        while value_1:
            output_list.append((value_1, None))
            value_1 = next(i, None)
    else:
        while value_2:
            output_list.append((None, value_2))
            value_2 = next(j, None)

    return output_list


def merge_json_list_by_ts(i, j):
    """ Merges two sorted json lists based on timestamp of json values
    :param i: first sorted list of json
    :type i: list
    :param j: second sorted list json
    :type j: list
    :return: sorted list of json messages
    :rtype: list(dict())
    """
    if not i:
        return j
    if not j:
        return i

    i = iter(i)
    j = iter(j)
    output_list = []
    value_1 = next(i, None)
    value_2 = next(j, None)
    try:
        while value_1 and value_2:
            if value_1['ts'] == value_2['ts']:
                output_list.append(value_1)
                output_list.append(value_2)
                value_1, value_2 = next(i, None), next(j, None)
            elif value_1['ts'] > value_2['ts']:
                output_list.append(value_2)
                value_2 = next(j, None)
            else:
                output_list.append(value_1)
                value_1 = next(i, None)

        if value_1:
            while value_1:
                output_list.append(value_1)
                value_1 = next(i, None)
        else:
            while value_2:
                output_list.append(value_2)
                value_2 = next(j, None)
    except KeyError:
        print('issue merging: \n {} \n {}'.format(value_1, value_2))

    return output_list


def merge_json_list_by_id(old_data, new_data):
    """ Merges two json lists based on ids. If the newer data is different, overwrite the old
        data and archive the old data in a .archive file
    :param old_data: first list of json
    :type old_data: list
    :param new_data: second list json
    :type new_data: list
    :return: new data to write to the file and data to archive
    :rtype: list(tuple(element_in_first_list, element_in_second_list)
    """
    if not old_data:
        return new_data
    if not new_data:
        return old_data

    current_list, archive_list = [], []
    for i in new_data:
        try:
            index = next(index_temp for index_temp, data_temp in enumerate(old_data) if i['id'] == data_temp['id'])
        except StopIteration:
            index = None
        if index is not None:
            if i != old_data[index]:
                archive_list.append(old_data[index])
            current_list.append(i)
        else:
            current_list.append(i)

    return current_list, archive_list


def load_json(file_path):
    """ loads the data in the passed in file path
    :param file_path: path to the file to load
    :type file_path: str
    :return: data in the loaded list of json format
    :rtype: list
    """
    try:
        with open(file_path) as f:
            data = json.load(f)
    except Exception:
        return []
    return data


def merge_channel_folder(destination_channel, new_channel_data):
    """ merge the two channel folders
    :param destination_channel:
    :param new_channel_data:
    :return: True if the merge occurred correctly and the source folder was deleted. false otherwise
    :rtype: False
    """
    result = False
    destination_files = os.listdir(destination_channel)
    source_files = os.listdir(new_channel_data)
    for i in source_files:
        destination_file = os.path.join(destination_channel, i)
        source_file = os.path.join(new_channel_data, i)
        if i in destination_files:
            resultant_data = merge_json_list_by_ts(load_json(destination_file), load_json(source_file))
            _to_json(resultant_data, destination_file)
            os.remove(source_file)
        else:
            shutil.move(source_file, destination_file)
    if os.listdir(new_channel_data):
        shutil.rmtree(new_channel_data)
        result = True
    return result


def merge_archives(destination_folder, new_data_folder):
    """ Recursively merges two data set folders into one larger data set
    :param destination_folder: The path to the archive folder that contains all the historical data
    :type destination_folder: str
    :param new_data_folder: The path to the folder that contains newly downloaded data
    :type new_data_folder: str
    :return: True if the merge occurred correctly and the source folder was deleted. false otherwise
    :rtype: False
    """
    result = False
    paired_channels = pair_channels(os.listdir(destination_folder), os.listdir(new_data_folder))
    for i in paired_channels:
        dest_channel, new_data = i

        # if a top level file, merge by id
        if dest_channel == 'channels.json' or dest_channel == 'groups.json' or dest_channel == 'users.json':
            base_name, ext = os.path.splitext(dest_channel)
            destination_json = load_json(os.path.join(destination_folder, dest_channel))
            source_json = load_json(os.path.join(new_data_folder, new_data))
            current_list, archive_list = merge_json_list_by_id(destination_json, source_json)
            _to_json(current_list, os.path.join(destination_folder, '{}{}'.format(base_name, ext)))
            _to_json(archive_list, os.path.join(destination_folder, '{}.archive'.format(base_name)))
            os.remove(os.path.join(new_data_folder, new_data))
        else:  # Merge the channels
            if dest_channel is None:  # If channel is new, simply move the file to the new folder and move on
                destination_folder_path = os.path.join(destination_folder, new_data)
                _mkdir(destination_folder_path)
                new_channel_folder_path = os.path.join(new_data_folder, new_data)
                for j in os.listdir(new_channel_folder_path):
                    shutil.move(os.path.join(new_channel_folder_path, j),
                                os.path.join(destination_folder_path, j))
                continue
            if new_data is None:  # if there have been no new activity in a channel, move on
                continue

            dest_path = os.path.join(destination_folder, dest_channel)
            new_path = os.path.join(new_data_folder, new_data)
            merge_channel_folder(dest_path, new_path)
        print('{} | {}'.format(dest_channel, new_data))
    if os.listdir(new_data_folder):
        shutil.rmtree(new_data_folder)
        result = True
    return result


def main(token, last_time=0):
    """  downloads all public and private channel messages the user is connected to from the last timestamp
    :param token: encrypted slack token
    :type token: str
    :param last_time: last download run time of the archiving in epoch seconds
    :type last_time: float
    :return: None
    """

    slack = Slacker(token)

    orig_folder = slack.team.info().body['team']['domain']
    last_time_file = os.path.join(orig_folder, 'last_run.txt')
    if os.path.exists(last_time_file):
        with open(last_time_file, 'r') as read_file:
            last_time = float(read_file.read())
    todays_date = datetime.today().strftime('%d-%m-%y')
    current_folder_path = '{}-{}'.format(orig_folder, todays_date)
    _mkdir(current_folder_path)

    users, public_channels, private_channels = bootstrap_key_values(slack)

    _to_json(users, os.path.join(current_folder_path, 'users.json'))
    _to_json(public_channels, os.path.join(current_folder_path, 'channels.json'))
    _to_json(private_channels, os.path.join(current_folder_path, 'groups.json'))

    download_channels(slack.channels, public_channels, current_folder_path, last_time)
    download_channels(slack.groups, private_channels, current_folder_path, last_time)

    last_extracted_time = extract_date(current_folder_path)
    result = merge_archives(orig_folder, current_folder_path)
    with open(last_time_file, 'w') as write_file:
        write_file.write(str(last_extracted_time))
    if result:
        shutil.make_archive(orig_folder, 'zip', orig_folder)


if __name__ == "__main__":
    main(the_crypter.decrypt(settings['api_token']))
