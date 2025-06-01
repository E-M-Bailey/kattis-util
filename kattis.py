import sys

from configparser import ConfigParser
from collections.abc import Iterable
from functools import total_ordering
from pathlib import Path
from typing import Literal

import requests
from requests import Request, Response

import kattis_cli.submit as cli

type UserTab = Literal['favourite', 'problems',
                       'submissions', 'settings', 'email', 'account']

type ProblemTab = Literal['edit', 'metadata', 'submissions']

type ContestTab = Literal['contest', 'standings', 'problems', 'teams', 'rules']


class RequestCache:
    def __init__(self):
        self.cache: dict[Request, Response] = {}

    def __contains__(self, req: Request):
        return req in self.cache

    def invalidate(self, req: Request):
        self.cache.pop(req, None)

    def send(self, req: Request, use_cached: bool = True):
        if not use_cached or req not in self:
            self.cache[req] = requests.session().send(req.prepare())
        return self.cache[req]


@total_ordering
class Contest:
    def __init__(self, kattis: 'Kattis', id: str):
        self.kattis = kattis
        self.id = id

    def __str__(self):
        return self.id

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: object):
        return isinstance(other, Contest) and str(self) == str(other)

    def __lt__(self, other: object):
        if not isinstance(other, Contest):
            raise TypeError()
        return str(self) < str(other)

    def url(self):
        return self.kattis.contest_url(self)


@total_ordering
class Submission:
    def __init__(self, kattis: 'Kattis', id: str):
        self.kattis = kattis
        self.id = id

    def __str__(self):
        return self.id

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: object):
        return isinstance(other, Submission) and str(self) == str(other)

    def __lt__(self, other: object):
        if not isinstance(other, Submission):
            raise TypeError()
        return str(self) < str(other)

    def url(self, contest: Contest | str | None = None):
        return self.kattis.submission_url(self, contest)


@total_ordering
class Problem:
    def __init__(self, kattis: 'Kattis', name: str):
        self.kattis = kattis
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: object):
        return isinstance(other, Problem) and str(self) == str(other)

    def __lt__(self, other: object):
        if not isinstance(other, Problem):
            raise TypeError()
        return str(self) < str(other)

    def url(self, contest: Contest | str | None = None):
        return self.kattis.problem_url(self, contest)

    def statistics_url(self, contest: Contest | str | None = None):
        return self.kattis.problem_statistics_url(self, contest)


@total_ordering
class User:
    def __init__(self, kattis: 'Kattis', name: str):
        self.kattis = kattis
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: object):
        return isinstance(other, User) and str(self) == str(other)

    def __lt__(self, other: object):
        if not isinstance(other, User):
            raise TypeError()
        return str(self) < str(other)

    def url(self):
        return self.kattis.user_url(self)


class Kattis:
    CONFIG_FILENAME = '.kattisrc'
    # See cli._DEFAULT_CONFIG
    DEFAULT_CONFIG = Path('/usr/local/etc/kattisrc')
    # See cli._HEADERS
    HEADERS = {'User-Agent': 'kattis-cli-submit'}

    ### config ###

    @staticmethod
    def _default_config_paths() -> list[Path]:
        try:
            file = __file__
        except NameError:
            file = sys.orig_argv[0]

        file = Path(file)
        dirs = [Path('~').expanduser(), file.parent, file.resolve().parent]
        return [p / Kattis.CONFIG_FILENAME for p in dirs]

    @staticmethod
    def _read_config(paths: Iterable[Path]) -> ConfigParser:
        # See cli.get_config
        cfg = ConfigParser()
        if Kattis.DEFAULT_CONFIG.is_file():
            cfg.read(Kattis.DEFAULT_CONFIG)

        if not cfg.read(paths):
            raise cli.ConfigError()

        if not cfg.has_option('kattis', 'hostname'):
            cfg.set('kattis', 'hostname', 'open.kattis.com')

        return cfg

    def __init__(self, cfg_paths: Path | Iterable[Path] | None = None):
        if cfg_paths is None:
            cfg_paths = Kattis._default_config_paths()
        elif isinstance(cfg_paths, Path):
            cfg_paths = [cfg_paths]
        else:
            cfg_paths = list(cfg_paths)
        self.config = Kattis._read_config(cfg_paths)

    def get_cfg(self, option: str, default: str | None = None, section: str = 'kattis'):
        # See cli.get_url
        if self.config.has_option(section, option):
            return self.config.get(section, option)
        else:
            return default

    def get_url(self, option: str, default: str, section: str = 'kattis', hostname: str | None = None):
        # See cli.get_url
        if hostname is None:
            hostname = self.config.get(section, 'hostname')
        return self.get_cfg(option, f'https://{hostname}/{default}', section)

    ### basic info ###

    @property
    def username(self):
        return self.config.get('user', 'username')

    @property
    def password(self):
        return self.get_cfg('password', section='user')

    @property
    def token(self):
        return self.get_cfg('token', section='user')

    @property
    def hostname(self):
        return self.get_cfg('hostname', 'open.kattis.com')

    ### basic urls ###

    def login_url(self):
        return self.get_url('loginurl', 'login')

    def logout_url(self):
        return self.get_url('logouturl', 'logout')

    def submit_url(self, contest: Contest | str | None = None):
        if contest is None:
            return self.get_url('submissionurl', 'submit')
        else:
            return f'{self.contest_url(contest)}/submit'

    def submissions_url(self, contest: Contest | str | None = None):
        if contest is None:
            return self.get_url('submissionsurl', 'submissions')
        else:
            return f'{self.contest_url(contest)}/submissions'

    def problems_url(self, contest: Contest | str | None = None):
        if contest is None:
            return self.get_url('problemsurl', 'problems')
        else:
            return f'{self.contest_url(contest)}/problems'

    def contests_url(self):
        return self.get_url('contestsurl', 'contests')

    def past_contests_url(self):
        return self.get_url('pastcontestsurl', 'past-contests')

    def challenge_url(self):
        return self.get_url('challengeurl', 'challenge')

    def users_url(self):
        return self.get_url('usersurl', 'users')

    def ranklist_url(self):
        return self.get_url('ranklisturl', 'ranklist')

    def affiliations_url(self):
        return self.get_url('affiliationsurl', 'affiliations')

    def countries_url(self):
        return self.get_url('countriesurl', 'countries')

    def authors_url(self):
        return self.get_url('authorsurl', 'problem-authors')

    def sources_url(self):
        return self.get_url('sourcesurl', 'problem-sources')

    def jobs_url(self):
        return self.get_url('jobsurl', 'jobs')

    def relay_url(self):
        return self.get_url('relayurl', 'relay')

    def languages_url(self):
        return self.get_url('languagesurl', 'languages')

    def info_url(self):
        return self.get_url('infourl', 'info')

    def policies_url(self):
        return self.get_url('policiesurl', 'policies')

    def search_url(self):
        return self.get_url('searchurl', 'search')

    def support_url(self):
        return self.get_url('supporturl', 'supporter')

    def request_affiliation_url(self):
        return self.get_url('requestaffiliationurl', 'request-affiliation')

    ### other urls ###

    def submission_url(self, submission: Submission | str, contest: Contest | str | None = None):
        return f'{self.submissions_url(contest)}/{submission}'

    def problem_url(self, problem: Problem | str, contest: Contest | str | None = None):
        return f'{self.problems_url(contest)}/{problem}'

    def problem_statistics_url(self, problem: Problem | str, contest: Contest | str | None = None):
        return f'{self.problem_url(problem, contest)}/statistics'

    def contest_url(self, contest: Contest | str):
        return f'{self.contests_url()}/{contest}'

    def user_url(self, user: str | User | None = None):
        if user is None:
            user = self.username
        return f'{self.users_url()}/{user}'

    ### url params ###

    ### requests ###

    @property
    def cache(self):
        if not hasattr(self, '_cache'):
            self._cache = RequestCache()
        return self._cache

    def get(self,
            url: str,
            data: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
            use_cached: bool = True):
        req = Request(method='get',
                      url=url,
                      headers=Kattis.HEADERS,
                      data={} if data is None else data,
                      params={} if params is None else params,
                      cookies=self.cookies)
        return self.cache.send(req, use_cached)

    ### login ###

    def login(self, use_cached: bool = True):
        # See cli.main
        resp = self.cache.send(self.login_request, use_cached)
        if resp.status_code == 403:
            raise Exception(f'403: bad credentials for {self.username}')
        elif resp.status_code == 404:
            raise Exception(f'404: incorrect login URL {self.login_url()}')
        elif resp.status_code != 200:
            raise Exception(f'login failed with status {resp.status_code}')
        else:
            return resp

    def is_logged_in(self):
        return self.login_request in self.cache

    def logout(self):
        return self.cache.invalidate(self.login_request)

    @property
    def login_request(self):
        # See cli.login
        if self.password is None and self.token is None:
            raise cli.ConfigError('password and token both missing')
        data = {'user': self.username, 'script': 'true'}
        if self.password is not None:
            data['password'] = self.password
        if self.token is not None:
            data['token'] = self.token
        return Request('post', url=self.login_url(), data=data, headers=Kattis.HEADERS)

    @property
    def login_response(self):
        return self.login(use_cached=True)

    @property
    def cookies(self):
        return self.login_response.cookies

    @property
    def problem_cache(self):
        if not hasattr(self, '_problem_cache'):
            self._problem_cache: dict[str, Problem] = {}
        return self._problem_cache
