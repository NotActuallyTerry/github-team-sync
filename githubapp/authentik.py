import os
import logging
import authentik_client

LOG = logging.getLogger(__name__)


class Authentik:
    def __init__(self):
        self.USERNAME_ATTRIBUTE = os.environ.get("AUTHENTIK_USERNAME_ATTRIBUTE", None)
        self.UseGithubIDP = self.USERNAME_ATTRIBUTE is not None

        if self.UseGithubIDP and not self.USERNAME_ATTRIBUTE:
            raise Exception("AUTHENTIK_USERNAME_ATTRIBUTE not defined")

    def init_client(self):
        self.SERVER_URL = os.environ.get("AUTHENTIK_SERVER_URL", None)
        self.API_KEY = os.environ.get("AUTHENTIK_API_KEY", None)

        if not self.SERVER_URL:
            raise Exception("AUTHENTIK_SERVER_URL not defined")

        if not self.API_KEY:
            raise Exception("AUTHENTIK_API_KEY not defined")

        authentik_config = authentik_client.Configuration(
            host=("%s/api/v3" % self.SERVER_URL),
            access_token=self.API_KEY
        )

        authentik_api_client = authentik_client.ApiClient(authentik_config)
        authentik_core_client = authentik_client.CoreApi(authentik_api_client)

        return authentik_core_client

    def get_group_members(self, client: authentik_client.CoreApi = None, group_name: str = None):
        """
        Get a list of users that are in a group in Authentik

        :param client: An Authentik CoreApi client
        :type client: authentik_client.CoreApi

        :param group_name: Group name to look up
        :type group_name: str

        :return member_list: A list of dictionaries containing users
        :rtype member_list: authentik_client.User
        """
        member_list = []

        def get_members(client: authentik_client.CoreApi = None):
            """
            Get the users that are in this group

            :param client: An Authentik CoreApi client

            :return: A dictionary containing all users in the group
            """

            group = client.core_groups_list(name=group_name)

            if not group.pagination.count > 0:
                raise Exception(f"Cannot find group {group_name} in Authentik")

            return group.results[0].users_obj

        def get_github_username(user: authentik_client.User = None):
            """
            Gets the GitHub username from the user's Authentik profile
            This requires an oauth source mapper that inserts the
            GitHub username into the Authentik user's attributes

            :param user: A user object from the Authentik server

            :return: The user's GitHub username
            """

            # Authentik allows you to nest dictionaries within attributes
            # So if the attribute has a dot in it, we'll need to go down a level or two first

            if '.' in self.USERNAME_ATTRIBUTE:
                attributes = self.USERNAME_ATTRIBUTE.split('.')
                github_username = user.attributes

                try:
                    for attribute in attributes:
                        github_username = github_username[attribute]
                except:
                    raise Exception(f"Cannot find GitHub username for user")

            else:
                github_username = user.attributes[self.USERNAME_ATTRIBUTE]

            if not github_username or len(github_username) == 0:
                raise Exception("Cannot find Github username")

            return github_username

        for user in get_members(client=client):
            try:
                if self.UseGithubIDP:
                    username = get_github_username(user)
                else:
                    username = user.username
                    if not username:
                        raise Exception("Unable to find username in profile")
                    if "EMU_SHORTCODE" in os.environ:
                        username = username + "_" + os.environ["EMU_SHORTCODE"]
                member_list.append(
                    {
                        "username": username,
                        "email": user.email
                    }
                )
            except Exception as e:
                user_info = f'{user.username} ({user.email})'
                print(f"User {user_info}: {e}")
        return member_list
