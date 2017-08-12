#!/usr/bin/env python3

import git
import os
import subprocess
import sys

import importlib.util

PWD = os.path.dirname(os.path.abspath(__file__))

def test_diffs(diffs):
    """Check the diffs, also print them and fail the test if they exist"""
    if diffs:
        for diff in diffs:
            print(diff)
        raise ValueError('Autogenerated files are not up to date')

def test_builds(docker_repo_tag_dir):
    """Check make build completes for the given repo tag directory"""
    command = ['make', 'build']
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        cwd=docker_repo_tag_dir,
        bufsize=1,
        universal_newlines=True) as p:
        for line in p.stdout:
            print(line, end='') # process line here

    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, p.args)

def main(argv=sys.argv[1:]):
    """Check travis context and trigger docker builds"""

    # Check environment
    # REPO = os.environ.get('REPO','ros')
    # TAG = os.environ.get('TAG','indigo')
    # TRAVIS_BRANCH = os.environ.get('TRAVIS_BRANCH','master')
    # TRAVIS_PULL_REQUEST_BRANCH = os.environ.get('TRAVIS_PULL_REQUEST_BRANCH','')
    # TRAVIS_BUILD_DIR = os.environ.get('TRAVIS_BUILD_DIR',os.path.join(PWD,'..'))

    REPO = os.environ['REPO']
    TAG = os.environ['TAG']
    OS_NAME = os.getenv('OS_NAME', '')
    OS_CODE_NAME = os.getenv('OS_CODE_NAME', '')

    TRAVIS_BRANCH = os.environ['TRAVIS_BRANCH']
    TRAVIS_PULL_REQUEST_BRANCH = os.environ['TRAVIS_PULL_REQUEST_BRANCH']
    TRAVIS_BUILD_DIR = os.environ['TRAVIS_BUILD_DIR']

    print("REPO: ", REPO)
    print("TAG: ", TAG)
    print("OS_NAME: ", OS_NAME)
    print("OS_CODE_NAME: ", OS_CODE_NAME)
    print("TRAVIS_BRANCH: ", TRAVIS_BRANCH)
    print("TRAVIS_PULL_REQUEST_BRANCH: ", TRAVIS_PULL_REQUEST_BRANCH)

    # Expand the repo/tag directory
    docker_repo_dir = os.path.join(TRAVIS_BUILD_DIR, REPO)
    docker_file_dir = os.path.join(docker_repo_dir, OS_NAME, OS_CODE_NAME)
    docker_repo_tag_dir = os.path.join(docker_file_dir, TAG)

    # Import the dockerfile generation script
    spec = importlib.util.spec_from_file_location(
        "create.dockerfiles",
        os.path.join(docker_repo_dir, 'create_dockerfiles.py'))
    create_dockerfiles = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(create_dockerfiles)

    # Run the dockerfile generation script
    create_dockerfiles.main(('dir', '-d' + docker_repo_tag_dir))

    # Create a git diff for the current repo
    repo = git.Repo(TRAVIS_BUILD_DIR) #, odbt=git.GitCmdObjectDB)
    diffs = repo.index.diff(None, create_patch=True)

    # Check if this is PR or Cron job test
    if TRAVIS_PULL_REQUEST_BRANCH:
        # If this is a PR test
        print("Testing Pull Request for Branch: ", TRAVIS_PULL_REQUEST_BRANCH)

        # Test that dockerfile generation has changed nothing
        # and that all dockerfiles are up to date
        test_diffs(diffs)

        target = repo.branches[TRAVIS_BRANCH].commit
        pull_request = repo.head.commit
        path_of_interest = os.path.join(REPO, OS_NAME, OS_CODE_NAME, TAG)
        pr_diffs = target.diff(pull_request, paths=[path_of_interest])

        if pr_diffs:
            # Test that the dockerfiles build
            test_builds(docker_repo_tag_dir)

    else:
        print("Testing CronJob for Branch: ", TRAVIS_BRANCH)

        # Test that dockerfile generation has changed nothing
        # and that all dockerfiles are up to date
        try:
            test_diffs(diffs)
        except ValueError as err:
            # TODO: auto make a PR on github with new patch
            raise

        # Test that the dockerfiles build
        test_builds(docker_repo_tag_dir)


if __name__ == '__main__':
    main()
