"""Experimental loader for a GitHub folder of ABF files.

``requests`` is not a SanPy dependency. Install it before running this script.
"""

import io

import requests

import sanpy


class bAnalysisDirWeb:
    """Load a directory of .abf from the web (for now from GitHub).

    Will etend this to Box, Dropbox, other?.
    """

    def __init__(self, cloudDict):
        """
        Args: cloudDict (dict): {
                    'owner': 'cudmore',
                    'repo_name': 'SanPy',
                    'path': 'data'
                    }
        """
        self._cloudDict = cloudDict
        self.loadFolder()

    def loadFolder(self):
        """Load using cloudDict"""

        """
        # use ['download_url'] to download abf file (no byte conversion)
        response[0] = {
            name : 171116sh_0018.abf
            path : data/171116sh_0018.abf
            sha : 5f3322b08d86458bf7ac8b5c12564933142ffd17
            size : 2047488
            url : https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master
            html_url : https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf
            git_url : https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17
            download_url : https://raw.githubusercontent.com/cudmore/SanPy/master/data/171116sh_0018.abf
            type : file
            _links : {'self': 'https://api.github.com/repos/cudmore/SanPy/contents/data/171116sh_0018.abf?ref=master', 'git': 'https://api.github.com/repos/cudmore/SanPy/git/blobs/5f3322b08d86458bf7ac8b5c12564933142ffd17', 'html': 'https://github.com/cudmore/SanPy/blob/master/data/171116sh_0018.abf'}
        }
        """

        owner = self._cloudDict["owner"]
        repo_name = self._cloudDict["repo_name"]
        path = self._cloudDict["path"]
        url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"

        # response is a list of dict
        response = requests.get(url).json()
        # print('response:', type(response))

        for idx, item in enumerate(response):
            if not item["name"].endswith(".abf"):
                continue
            print(idx)
            # use item['git_url']
            for k, v in item.items():
                print("  ", k, ":", v)

        #
        # test load
        download_url = response[1]["download_url"]
        content = requests.get(download_url).content

        fileLikeObject = io.BytesIO(content)
        ba = sanpy.bAnalysis(byteStream=fileLikeObject)
        # print(ba._abf)
        # print(ba.api_getHeader())
        ba.spikeDetect()
        print(ba.numSpikes)
