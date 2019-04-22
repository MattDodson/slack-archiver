import unittest
import os
import shutil
import json
import datetime
from slackbot import slack_archive
from unittest.mock import MagicMock, patch, call


class RetrieveMessagesTestSuite(unittest.TestCase):

    def setUp(self):
        self.updated_ts = 123
        self.messages = [[{'name': 'message1', 'ts': self.updated_ts}], [{'name': 'message2', 'ts': 456}]]
        self.first_page = MagicMock()
        self.first_page.body = {'messages': self.messages[0], 'has_more': True}
        self.second_page = MagicMock()
        self.second_page.body = {'messages': self.messages[1], 'has_more': False}
        self.response = [self.first_page, self.second_page]
        self.pageable_object = MagicMock()
        self.channel_id = '123456'
        self.last_time = 0

    def tearDown(self):
        pass

    @patch('slackbot.slack_archive.sleep')
    def test_retrieve_messages(self, mock_sleep):
        self.pageable_object.history.side_effect = self.response
        actual = slack_archive.retrieve_messages(self.pageable_object, self.channel_id, self.last_time)
        self.assertEqual([self.messages[0][0], self.messages[1][0]], actual)


class TimestampToDatetimeTestSuite(unittest.TestCase):

    def setUp(self):
        self.fake_time = '1555786317.6852887'
        self.expected_result = datetime.datetime(2019, 4, 20, 18, 51, 57)

    def test_basic(self):
        actual_result = slack_archive.timestamp_to_datetime(self.fake_time)
        self.assertEqual(self.expected_result, actual_result)


class ChannelRenameTestSuite(unittest.TestCase):

    def setUp(self):
        self.top_folder = 'fake_folder'
        remove(self.top_folder)
        mkdir(self.top_folder)
        self.first_file_name = '2019-04-20.json'
        self.first_file = os.path.join(self.top_folder, self.first_file_name)
        open(self.first_file, 'a').close()
        self.second_file_name = '2019-04-19.json'
        self.second_file = os.path.join(self.top_folder, self.second_file_name)
        open(self.second_file, 'a').close()
        self.third_file_name = '2019-04-18.json'
        self.third_file = os.path.join(self.top_folder, self.third_file_name)
        open(self.third_file, 'a').close()
        self.fourth_file_name = '2019-04-17.json'
        self.fourth_file = os.path.join(self.top_folder, self.fourth_file_name)
        open(self.fourth_file, 'a').close()

        self.new_folder = 'new_folder'

    def tearDown(self):
        remove(self.top_folder)
        remove(self.new_folder)

    def test_full_move(self):
        # verify old folder exists and new one doesnt
        self.assertTrue(os.path.exists(self.top_folder))
        self.assertFalse(os.path.exists(self.new_folder))

        slack_archive.channel_rename(self.top_folder, self.new_folder)

        # verify all files exist in the new folder and the old one doesn't exist
        self.assertTrue(os.path.exists(self.new_folder))
        self.assertTrue(os.path.exists(os.path.join(self.new_folder, self.first_file_name)))
        self.assertTrue(os.path.exists(os.path.join(self.new_folder, self.second_file_name)))
        self.assertTrue(os.path.exists(os.path.join(self.new_folder, self.third_file_name)))
        self.assertTrue(os.path.exists(os.path.join(self.new_folder, self.fourth_file_name)))
        self.assertFalse(os.path.exists(self.top_folder))

    def test_folder_doesnt_exist(self):
        # verify old folder exists and new one doesnt
        self.assertTrue(os.path.exists(self.top_folder))
        self.assertFalse(os.path.exists(self.new_folder))

        slack_archive.channel_rename(self.new_folder, self.top_folder)

        # verify all files exist in the new folder and the old one doesn't exist
        self.assertFalse(os.path.exists(self.new_folder))
        self.assertTrue(os.path.exists(self.top_folder))


class ParseAndSaveMessagesTestSuite(unittest.TestCase):

    def setUp(self):
        self.channel_type = 'public'
        self.folder_path = 'fake_folder'
        self.message1 = {'ts': '1555786317.6852887'}
        self.message2 = {'ts': '1555786318.6852887'}
        self.expected_file1 = '2019-04-20.json'
        self.file1_path = os.path.join(self.folder_path, self.expected_file1)
        self.message3 = {'ts': '1557786317.6852887'}
        self.expected_file2 = '2019-05-13.json'
        self.file2_path = os.path.join(self.folder_path, self.expected_file2)
        self.messages1 = [self.message1, self.message2, self.message3]

        # rename variables
        self.new_folder = 'new_fake_folder'
        self.message4 = {'ts': '1558786317.6852887', 'subtype': '{}_name'.format(self.channel_type),
                         'old_name': self.folder_path, 'name': self.new_folder}
        self.expected_file3 = '2019-05-25.json'
        self.file1_path_new = os.path.join(self.new_folder, self.expected_file1)
        self.file2_path_new = os.path.join(self.new_folder, self.expected_file2)
        self.file3_path_new = os.path.join(self.new_folder, self.expected_file3)
        self.messages2 = [self.message1, self.message2, self.message3, self.message4]
        mkdir(self.folder_path)

    def tearDown(self):
        remove(self.folder_path)
        remove(self.new_folder)

    @patch('slackbot.slack_archive.channel_rename')
    def test_no_name_change(self, mocked_rename):
        slack_archive.parse_and_save_messages(self.folder_path, self.messages1, self.channel_type)

        # Verify correct calls made and the files are made as expected
        mocked_rename.assert_not_called()
        self.assertTrue(os.path.exists(self.file1_path))
        self.assertTrue(os.path.exists(self.file2_path))
        with open(self.file1_path, 'r') as read_file:
            actual_file1 = json.load(read_file)
        self.assertEqual([self.message1, self.message2], actual_file1)
        with open(self.file2_path, 'r') as read_file:
            actual_file2 = json.load(read_file)
        self.assertEqual([self.message3], actual_file2)

    def test_name_change(self):
        slack_archive.parse_and_save_messages(self.folder_path, self.messages2, self.channel_type)

        # Verify correct calls made and the files are made as expected
        self.assertTrue(os.path.exists(self.file1_path_new))
        self.assertTrue(os.path.exists(self.file2_path_new))
        self.assertTrue(os.path.exists(self.file3_path_new))
        with open(self.file1_path_new, 'r') as read_file:
            actual_file1 = json.load(read_file)
        self.assertEqual([self.message1, self.message2], actual_file1)
        with open(self.file2_path_new, 'r') as read_file:
            actual_file2 = json.load(read_file)
        self.assertEqual([self.message3], actual_file2)
        with open(self.file3_path_new, 'r') as read_file:
            actual_file3 = json.load(read_file)
        self.assertEqual([self.message4], actual_file3)


class DownloadChannelsTestSuite(unittest.TestCase):

    def setUp(self):
        self.slack_object = MagicMock()
        self.channel1 = 'channel1'
        self.channel1_id = 123
        self.channel2 = 'channel2'
        self.channel2_id = 456
        self.channel_list = [{'name': self.channel1, 'id': self.channel1_id},
                             {'name': self.channel2, 'id': self.channel2_id}]
        self.folder_path = 'fake_folder_path'
        self.channel1_path = os.path.join(self.folder_path, self.channel1)
        self.channel2_path = os.path.join(self.folder_path, self.channel2)
        self.fake_messages = 'fake_messages'
        self.last_time = 0

    def tearDown(self):
        remove(self.folder_path)

    @patch('slackbot.slack_archive.retrieve_messages')
    @patch('slackbot.slack_archive.parse_and_save_messages')
    @patch('slackbot.slack_archive.sleep')
    def test_download_channels(self, mocked_sleep, mocked_parse, mocked_retrieve):
        # Verify folder doesn't exist and set up the return value of the retrieve messages
        self.assertFalse(os.path.exists(self.folder_path))
        mocked_retrieve.return_value = self.fake_messages

        slack_archive.download_channels(self.slack_object, self.channel_list, self.folder_path, self.last_time)

        # Verify methods were correctly called and folders created correctly
        mocked_retrieve.assert_has_calls([call(self.slack_object, self.channel1_id, self.last_time),
                                          call(self.slack_object, self.channel2_id, self.last_time)])
        mocked_parse.assert_has_calls([call(self.channel1_path, self.fake_messages, 'channel'),
                                       call(self.channel2_path, self.fake_messages, 'channel')])
        self.assertTrue(os.path.exists(self.channel1_path))
        self.assertTrue(os.path.exists(self.channel2_path))


class ToJsonTestSuite(unittest.TestCase):

    def setUp(self):
        self.fake_key1 = 'key1'
        self.fake_value1 = 'value1'
        self.fake_dict1 = {self.fake_key1: self.fake_value1}

        self.fake_key2 = 'key2'
        self.fake_value2 = 'value2'
        self.fake_dict2 = {self.fake_key2: self.fake_value2}

        self.fake_list = [self.fake_dict1, self.fake_dict2]
        self.fake_file = 'test.json'

    def tearDown(self):
        remove(self.fake_file)

    def test_write_to_json(self):
        # Verify the file doesn't exist before the test
        self.assertFalse(os.path.exists(self.fake_file))

        slack_archive._to_json(self.fake_list, self.fake_file)

        # Verify exists with expected contents in the right order
        self.assertTrue(os.path.exists(self.fake_file))
        with open(self.fake_file, 'r') as read_file:
            contents = json.load(read_file)
        self.assertDictEqual(self.fake_dict1, contents[0])
        self.assertDictEqual(self.fake_dict2, contents[1])


class BootstrapKeyValuesTestSuite(unittest.TestCase):

    def setUp(self):
        self.users = ['fake_users']
        self.public_channels = ['fake_public_channel']
        self.private_channels = ['fake_private_channel']
        pass

    def tearDown(self):
        pass

    @patch('slackbot.slack_archive.sleep', return_value=None)
    def test_basic(self, mocked_time):
        fake_connection = MagicMock()
        fake_connection.users.list.return_value.body.__getitem__.return_value = self.users
        fake_connection.channels.list.return_value.body.__getitem__.return_value = self.public_channels
        fake_connection.groups.list.return_value.body.__getitem__.return_value = self.private_channels
        actual_users, actual_public, actual_private = slack_archive.bootstrap_key_values(fake_connection)
        self.assertEqual(self.users, actual_users)
        self.assertEqual(self.public_channels, actual_public)
        self.assertEqual(self.private_channels, actual_private)


class RemoveTestSuite(unittest.TestCase):

    def setUp(self):
        self.fake_folder = 'fake_folder'
        self.fake_file = 'fake_file'
        self.nested_file = os.path.join(self.fake_folder, self.fake_file)

        remove(self.fake_folder)

        mkdir(self.fake_folder)
        open(self.nested_file, 'a').close()

    def tearDown(self):
        remove(self.fake_folder)

    def test_remove_file(self):
        # verify file exists
        self.assertTrue(os.path.exists(self.nested_file))

        slack_archive._remove(self.nested_file)

        # Verify it was removed
        self.assertFalse(os.path.exists(self.nested_file))

    def test_remove_folder(self):
        # verify folder exists
        self.assertTrue(os.path.exists(self.fake_folder))

        slack_archive._remove(self.fake_folder)

        # Verify it was removed
        self.assertFalse(os.path.exists(self.fake_folder))

    def test_remove_folder_and_contents(self):
        # verify folder and file exists
        self.assertTrue(os.path.exists(self.fake_folder))
        self.assertTrue(os.path.exists(self.nested_file))

        slack_archive._remove(self.fake_folder)

        # Verify it was removed
        self.assertFalse(os.path.exists(self.fake_folder))
        self.assertFalse(os.path.exists(self.nested_file))

    def test_remove_nothing(self):
        # verify file doesnt exist
        file_doesnt_exist = 'dont do anything'
        self.assertFalse(os.path.exists(file_doesnt_exist))

        slack_archive._remove(file_doesnt_exist)

        # Verify it still doesn't exist/didn't error
        self.assertFalse(os.path.exists(file_doesnt_exist))


class MkdirTestSuite(unittest.TestCase):

    def setUp(self):
        self.fake_dir = 'test_dir'
        self.fake_nested = 'nested_dir'
        self.fake_full_path = os.path.join(self.fake_dir, self.fake_nested)
        remove(self.fake_dir)

    def tearDown(self):
        remove(self.fake_dir)

    def test_folder_does_not_exist(self):
        # Make sure folder doesnt exist before
        self.assertFalse(os.path.exists(self.fake_dir))

        slack_archive._mkdir(self.fake_dir)

        # Test folder exists
        self.assertTrue(os.path.exists(self.fake_dir))
        self.assertTrue(os.path.isdir(self.fake_dir))

    def test_folder_exists(self):
        # Create folder and verify it exists before running
        os.makedirs(self.fake_dir)
        self.assertTrue(os.path.exists(self.fake_dir))

        slack_archive._mkdir(self.fake_dir)

        # Test folder exists
        self.assertTrue(os.path.exists(self.fake_dir))
        self.assertTrue(os.path.isdir(self.fake_dir))

    def test_nested_folder_creation(self):
        self.assertFalse(os.path.exists(self.fake_dir))
        self.assertFalse(os.path.exists(self.fake_full_path))
        slack_archive._mkdir(self.fake_full_path)

        # Test top level folder exists
        self.assertTrue(os.path.exists(self.fake_dir))
        self.assertTrue(os.path.isdir(self.fake_dir))
        # Test nested folder exists
        self.assertTrue(os.path.exists(self.fake_full_path))
        self.assertTrue(os.path.isdir(self.fake_full_path))


class ExtractDateTestSuite(unittest.TestCase):

    def setUp(self):
        self.top_folder = 'fake_folder'
        remove(self.top_folder)
        mkdir(self.top_folder)
        self.second_level_folder = os.path.join(self.top_folder, 'next_fake')
        mkdir(self.second_level_folder)
        self.empty_folder = os.path.join(self.top_folder, 'empty-folder')
        mkdir(self.empty_folder)
        self.most_recent_json = '2019-04-20.json'
        self.most_recent_json_file = os.path.join(self.top_folder, self.most_recent_json)
        open(self.most_recent_json_file, 'a').close()
        self.second_most_recent_json = '2019-04-19.json'
        self.second_most_recent_json_file = os.path.join(self.second_level_folder, self.second_most_recent_json)
        open(self.second_most_recent_json_file, 'a').close()
        self.third_most_recent_json = '2019-04-18.json'
        self.third_most_recent_json_file = os.path.join(self.second_level_folder, self.third_most_recent_json)
        open(self.third_most_recent_json_file, 'a').close()

    def tearDown(self):
        remove(self.top_folder)

    def test_full_folder_structure(self):
        expected_result = (datetime.datetime.strptime(self.most_recent_json.split('.')[0], "%Y-%m-%d") -
                           datetime.datetime(1970, 1, 1)).total_seconds()
        actual_result = slack_archive.extract_date(self.top_folder)
        self.assertEqual(expected_result, actual_result)

    def test_one_level_folder(self):
        expected_result = (datetime.datetime.strptime(self.second_most_recent_json.split('.')[0], "%Y-%m-%d") -
                           datetime.datetime(1970, 1, 1)).total_seconds()
        actual_result = slack_archive.extract_date(self.second_level_folder)
        self.assertEqual(expected_result, actual_result)

    def test_empty_folder(self):
        expected_result = 0
        actual_result = slack_archive.extract_date(self.empty_folder)
        self.assertEqual(expected_result, actual_result)


class PairChannelsTestSuite(unittest.TestCase):

    def setUp(self):
        self.test_list1 = ['a', 'b', 'c']
        self.test_list2 = ['b', 'c', 'd']
        self.test_list3 = ['a', 'b', 'e', 'g']
        self.test_list4 = ['c', 'd', 'f', 'h', 'i']
        self.empty_list = []

    def tearDown(self):
        pass

    def test_first_ends_first(self):
        expected_result = [('a', None), ('b', 'b'), ('c', 'c'), (None, 'd')]
        actual_result = slack_archive.pair_channels(self.test_list1, self.test_list2)
        self.assertEqual(expected_result, actual_result)

    def test_second_ends_first(self):
        expected_result = [(None, 'a'), ('b', 'b'), ('c', 'c'), ('d', None)]
        print(expected_result)
        actual_result = slack_archive.pair_channels(self.test_list2, self.test_list1)
        self.assertEqual(expected_result, actual_result)

    def test_empty_list_first(self):
        expected_result = [(None, 'a'), (None, 'b'), (None, 'c')]
        actual_result = slack_archive.pair_channels(self.empty_list, self.test_list1)
        self.assertEqual(expected_result, actual_result)

    def test_empty_list_second(self):
        expected_result = [('a', None), ('b', None), ('c', None)]
        actual_result = slack_archive.pair_channels(self.test_list1, self.empty_list)
        self.assertEqual(expected_result, actual_result)

    def test_both_empty(self):
        expected_result = []
        actual_result = slack_archive.pair_channels(self.empty_list, self.empty_list)
        self.assertEqual(expected_result, actual_result)

    def test_none_in_common(self):
        expected_result = [('a', None), ('b', None), (None, 'c'), (None, 'd'), ('e', None), (None, 'f'), ('g', None),
                           (None, 'h'), (None, 'i')]
        actual_result = slack_archive.pair_channels(self.test_list3, self.test_list4)
        self.assertEqual(expected_result, actual_result)


# TODO
class MergeJsonListByTsTestSuite(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertTrue(False)


# TODO
class MergeJsonListByIdTestSuite(unittest.TestCase):  # TODO

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertTrue(False)


# TODO
class LoadJsonTestSuite(unittest.TestCase):  # TODO

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertTrue(False)


# TODO
class MergeArchivesTestSuite(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertTrue(False)


# TODO
class MainTestSuite(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertTrue(False)


def remove(path):
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


def mkdir(path):
    """ creates a directory structure from the passed in path
    :param path: directory structure to create
    :type path: str
    :return: None
    """
    if not os.path.isdir(path):
        os.makedirs(path)


if __name__ == '__main__':
    unittest.main()
