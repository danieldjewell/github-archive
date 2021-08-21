import logging
import os
import shutil
import subprocess
from datetime import datetime
from threading import BoundedSemaphore, Thread

from github import Github

from github_archive.constants import DEFAULT_LOCATION, DEFAULT_NUM_THREADS, DEFAULT_TIMEOUT
from github_archive.logger import Logger

LOGGER = logging.getLogger(__name__)
CLONE_OPERATION = 'clone'
ORG_CONTEXT = 'orgs'
PERSONAL_CONTEXT = 'personal'
PULL_OPERATION = 'pull'
USER_CONTEXT = 'user'


class GithubArchive:
    def __init__(
        self,
        view=False,
        clone=False,
        pull=False,
        users=None,
        orgs=None,
        gists=None,
        timeout=DEFAULT_TIMEOUT,
        threads=DEFAULT_NUM_THREADS,
        token=None,
        location=DEFAULT_LOCATION,
    ):
        # Parameter variables
        self.view = view
        self.clone = clone
        self.pull = pull
        self.users = users.lower().split(',') if users else ''
        self.orgs = orgs.lower().split(',') if orgs else ''
        self.gists = gists.lower().split(',') if gists else ''
        self.timeout = timeout
        self.threads = threads
        self.token = token
        self.location = location
        # Internal variables
        self.github_instance = Github(self.token) if self.token else Github()
        self.authenticated_user = self.github_instance.get_user() if self.token else None
        self.authenticated_username = self.authenticated_user.login.lower() if self.token else None

    def run(self):
        """Run the tool based on the arguments passed via the CLI."""
        self.initialize_project()
        Logger.setup_logging(LOGGER, self.location)
        LOGGER.info('# GitHub Archive started...\n')
        start_time = datetime.now()

        # Personal (includes personal authenticated items)
        if self.token and self.authenticated_user_in_users and self.users:
            LOGGER.info('# Making API call to GitHub for personal repos...\n')
            personal_repos = self.get_personal_repos()

            if self.view:
                LOGGER.info('# Viewing user repos...\n')
                self.view_repos(personal_repos)
            if self.clone:
                LOGGER.info('# Cloning missing personal repos...\n')
                self.iterate_repos_to_archive(personal_repos, PERSONAL_CONTEXT, CLONE_OPERATION)
            if self.pull:
                LOGGER.info('# Pulling changes to personal repos...\n')
                self.iterate_repos_to_archive(personal_repos, PERSONAL_CONTEXT, PULL_OPERATION)

            # We remove the authenticated user from the list so that we don't double pull their
            # repos for the `users` logic.
            self.users.remove(self.authenticated_username)

        # Users (can include personal non-authenticated items)
        if self.users and len(self.users) > 0:
            LOGGER.info('# Making API calls to GitHub for user repos...\n')
            user_repos = self.get_all_user_repos()

            if self.view:
                LOGGER.info('# Viewing user repos...\n')
                self.view_repos(user_repos)
            if self.clone:
                LOGGER.info('# Cloning missing user repos...\n')
                self.iterate_repos_to_archive(user_repos, USER_CONTEXT, CLONE_OPERATION)
            if self.pull:
                LOGGER.info('# Pulling changes to user repos...\n')
                self.iterate_repos_to_archive(user_repos, USER_CONTEXT, PULL_OPERATION)

        # Orgs
        if self.orgs:
            LOGGER.info('# Making API calls to GitHub for org repos...\n')
            org_repos = self.get_all_org_repos()

            if self.view:
                LOGGER.info('# Viewing org repos...\n')
                self.view_repos(org_repos)
            if self.clone:
                LOGGER.info('# Cloning missing org repos...\n')
                self.iterate_repos_to_archive(org_repos, ORG_CONTEXT, CLONE_OPERATION)
            if self.pull:
                LOGGER.info('# Pulling changes to org repos...\n')
                self.iterate_repos_to_archive(org_repos, ORG_CONTEXT, PULL_OPERATION)

        # Gists
        if self.gists:
            LOGGER.info('# Making API call to GitHub for gists...\n')
            gists = self.get_all_gists()

            if self.view:
                LOGGER.info('# Viewing gists...\n')
                self.view_gists(gists)
            if self.clone:
                LOGGER.info('# Cloning missing gists...\n')
                self.iterate_gists_to_archive(gists, CLONE_OPERATION)
            if self.pull:
                LOGGER.info('# Pulling changes to gists...\n')
                self.iterate_gists_to_archive(gists, PULL_OPERATION)

        execution_time = f'Execution time: {datetime.now() - start_time}.'
        finish_message = f'GitHub Archive complete! {execution_time}\n'
        LOGGER.info(finish_message)

    def initialize_project(self):
        """Initialize the tool and ensure everything is in order before running any logic.

        This function ensures the minimum set of requirements are passed in to run the tool:
        1. a git operation
        2. a list of assets to run operations on
        """
        if not os.path.exists(self.location):
            os.makedirs(os.path.join(self.location, 'repos'))
            os.makedirs(os.path.join(self.location, 'gists'))

        if (self.users or self.orgs or self.gists) and not (self.view or self.clone or self.pull):
            message = 'A git operation must be specified when a list of users or orgs is provided.'
            LOGGER.critical(message)
            raise ValueError(message)
        elif not (self.users or self.orgs or self.gists) and (self.view or self.clone or self.pull):
            message = 'A list must be provided when a git operation is specified.'
            LOGGER.critical(message)
            raise ValueError(message)

    def authenticated_user_in_users(self):
        return self.authenticated_user.login.lower() in self.users

    def get_personal_repos(self):
        """Retrieve all repos of the authenticated user."""
        repos = self.authenticated_user.get_repos()
        LOGGER.debug('Personal repos retrieved!')

        return repos

    def get_all_user_repos(self):
        """Retrieve repos of all users in the users list provided and return a single list
        including every repo from each user flattened.
        """
        all_user_repos = []
        for user in self.users:
            formatted_user_name = user.strip()
            user_repos = self.github_instance.get_user(formatted_user_name).get_repos()
            all_user_repos.append(user_repos)
            LOGGER.debug(f'{formatted_user_name} repos retrieved!')

        flattened_user_repos_list = [repo for user_repos in all_user_repos for repo in user_repos]

        return flattened_user_repos_list

    def get_all_org_repos(self):
        """Retrieve repos of all orgs in the orgs list provided and return a single list
        including every repo from each org flattened.
        """
        all_org_repos = []
        for org in self.orgs:
            formatted_org_name = org.strip()
            org_repos = self.github_instance.get_organization(formatted_org_name).get_repos()
            all_org_repos.append(org_repos)
            LOGGER.debug(f'{formatted_org_name} repos retrieved!')

        flattened_org_repos_list = [repo for org_repos in all_org_repos for repo in org_repos]

        return flattened_org_repos_list

    def get_all_gists(self):
        """Retrieve all gists of the authenticated user."""
        all_user_gists = []
        for user in self.gists:
            formatted_user_name = user.strip()
            user_gists = self.github_instance.get_user(formatted_user_name).get_gists()
            all_user_gists.append(user_gists)
            LOGGER.debug(f'{formatted_user_name} gists retrieved!')

        flattened_user_repos_list = [gist for user_gists in all_user_gists for gist in user_gists]

        return flattened_user_repos_list

    def iterate_repos_to_archive(self, repos, context, operation):
        """Iterate over each repository and start a thread if it can be archived."""
        thread_limiter = BoundedSemaphore(self.threads)
        thread_list = []

        for repo in repos:
            repo_owner_username = repo.owner.login.lower()
            # We check the owner name here to ensure that we only iterate
            # through the user's personal repos which will exclude orgs.
            #
            # This is important because PyGithub will include a user's org repos
            # in the list of repos for an authenticated user out of the box.
            #
            # Instead, the user can pass the "--clone_orgs" or "--pull_orgs"
            # flags to allow for more granular control over which repos they get.
            if self.token and repo_owner_username != self.authenticated_username and context == PERSONAL_CONTEXT:
                continue
            else:
                repo_path = os.path.join(self.location, 'repos', repo_owner_username, repo.name)
                repo_thread = Thread(
                    target=self.archive_repo,
                    args=(
                        thread_limiter,
                        repo,
                        repo_path,
                        operation,
                    ),
                )
                thread_list.append(repo_thread)
                repo_thread.start()
        for thread in thread_list:
            thread.join()

    def iterate_gists_to_archive(self, gists, operation):
        """Iterate over each gist and start a thread if it can be archived."""
        thread_limiter = BoundedSemaphore(self.threads)
        thread_list = []

        for gist in gists:
            gist_path = os.path.join(self.location, 'gists', gist.id)
            gist_thread = Thread(
                target=self.archive_gist,
                args=(
                    thread_limiter,
                    gist,
                    gist_path,
                    operation,
                ),
            )
            thread_list.append(gist_thread)
            gist_thread.start()
        for thread in thread_list:
            thread.join()

    def view_repos(self, repos):
        """View a list of repos that will be cloned/pulled."""
        for repo in repos:
            repo_name = f'{repo.owner.login}/{repo.name}'
            LOGGER.info(repo_name)

    def view_gists(self, gists):
        """View a list of gists that will be cloned/pulled."""
        for gist in gists:
            gist_id = f'{gist.owner.login}/{gist.id}'
            LOGGER.info(gist_id)

    def archive_repo(self, thread_limiter, repo, repo_path, operation):
        """Clone and pull repos based on the operation passed"""
        if os.path.exists(repo_path) and operation == CLONE_OPERATION:
            pass
        else:
            commands = {
                CLONE_OPERATION: f'git clone {repo.ssh_url} {repo_path}',
                PULL_OPERATION: f'cd {repo_path} && git pull --rebase',
            }
            git_command = commands[operation]

            try:
                thread_limiter.acquire()
                subprocess.run(
                    git_command,
                    stdout=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True,
                    check=True,
                    timeout=self.timeout,
                )
                LOGGER.info(f'Repo: {repo.name} {operation} success!')
            except subprocess.TimeoutExpired:
                LOGGER.error(f'Git operation timed out archiving {repo.name}.')
                if os.path.exists(repo_path):
                    shutil.rmtree(repo_path)
            except subprocess.CalledProcessError as error:
                LOGGER.error(f'Failed to {operation} {repo.name}\n{error}')
                if os.path.exists(repo_path):
                    shutil.rmtree(repo_path)
            finally:
                thread_limiter.release()

    def archive_gist(self, thread_limiter, gist, gist_path, operation):
        """Clone and pull gists based on the operation passed"""
        if os.path.exists(gist_path) and operation == CLONE_OPERATION:
            pass
        else:
            commands = {
                CLONE_OPERATION: f'git clone {gist.html_url} {gist_path}',
                PULL_OPERATION: f'cd {gist_path} && git pull --rebase',
            }
            git_command = commands[operation]

            try:
                thread_limiter.acquire()
                subprocess.run(
                    git_command,
                    stdout=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True,
                    check=True,
                    timeout=self.timeout,
                )
                LOGGER.info(f'Gist: {gist.id} {operation} success!')
            except subprocess.TimeoutExpired:
                LOGGER.error(f'Git operation timed out archiving {gist.id}.')
                if os.path.exists(gist_path):
                    shutil.rmtree(gist_path)
            except subprocess.CalledProcessError as error:
                LOGGER.error(f'Failed to {operation} {gist.id}\n{error}')
                if os.path.exists(gist_path):
                    shutil.rmtree(gist_path)
            finally:
                thread_limiter.release()
