import json
import os
import shlex
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import click
import requests

import ruamel.yaml as yaml
from github import Github, UnknownObjectException


class ReleaseResolver:
    def __init__(self, client, repo_name, data):
        self.client = client
        self.repo_name = repo_name
        self.sha = data["sha"]

    def fetch_latest_release(self, repo):
        latest_release = repo.get_latest_release()
        self.ref = latest_release.tag_name
        # NOTE: latest_commit_sha will differ from latest_release.target_committish, because
        # the release was created and then the tag was advanced if a HookSet was used
        self.latest_commit_sha = repo.get_commit(latest_release.target_commitish).sha
        # self.latest_commit_sha = repo.get_commit(self.ref).sha
        self.tarball_url = latest_release.tarball_url

    def fetch_latest_commit(self, repo):
        default_branch = repo.get_branch(repo.default_branch)
        self.ref = default_branch.name
        self.latest_commit_sha = default_branch.commit.sha
        self.tarball_url = f"https://api.github.com/repos/{self.repo_name}/tarball/{self.latest_commit_sha}"

    def resolve_release(self):
        diff_url = ""
        self.repo = self.client.get_repo(self.repo_name)
        # prefer default branch within the "manifest" approach
        try:
            self.fetch_latest_release(self.repo)
        except UnknownObjectException:
            click.echo(
                f'{self.repo_name} has no release data.  retrieving latest SHA from "{self.repo.default_branch}"'
            )
            self.fetch_latest_commit(self.repo)

        should_update = self.latest_commit_sha != self.sha
        if should_update:
            compared = self.repo.compare(self.sha, self.latest_commit_sha)
            diff_url = compared.html_url
        return should_update, diff_url

    def emit_status(self, should_update, diff_url):
        return [
            self.repo.full_name,
            should_update,
            self.sha,
            self.latest_commit_sha,
            diff_url,
        ]

    def update_corpus(self, corpus_dict):
        should_update, diff_url = self.resolve_release()

        corpus_dict[self.repo_name] = dict(
            ref=self.ref,
            sha=self.latest_commit_sha,
            tarball_url=self.tarball_url,
        )
        return self.emit_status(should_update, diff_url)


@click.group()
def cli():
    """
    Commands used to help develop and manage Scaife Viewer projects
    """


@cli.command()
@click.option(
    "--new-url",
    default="https://scaife-dev.perseus.org/corpora/corpus-metadata/",
    show_default=True,
)
@click.option(
    "--old-url",
    default="https://scaife.perseus.org/corpora/corpus-metadata/",
    show_default=True,
)
def diff_corpora_contents(new_url, old_url):
    """
    Diff two versions of the corpus-metadata manifest.

    If changes are detected, returns a diff to stdout.
    e.g. scaife diff-corproa-contents > diff.patch

    Returns error code 1 if the manifests are equal.

    """
    new_data = requests.get(new_url).json()
    old_data = requests.get(old_url).json()
    old_data = sorted(old_data, key=lambda x: x.get("repo"))
    new_data = sorted(new_data, key=lambda x: x.get("repo"))

    old_f = NamedTemporaryFile(suffix="old", mode="w+", delete=False)
    new_f = NamedTemporaryFile(suffix="new", mode="w+", delete=False)

    try:
        json.dump(old_data, old_f, indent=2, ensure_ascii=False, sort_keys=True)
        old_f.close()

        json.dump(new_data, new_f, indent=2, ensure_ascii=False, sort_keys=True)
        new_f.close()

        command_string = f"diff -U3 {old_f.name} {new_f.name}"

        result = subprocess.run(shlex.split(command_string), capture_output=True)
        if result.returncode == 0:
            raise click.ClickException("No content changes detected")

        content = result.stdout.decode("utf-8")
        content = content.replace(old_f.name, "old.json")
        content = content.replace(new_f.name, "new.json")
        click.echo(content)
    finally:
        os.unlink(new_f.name)
        os.unlink(old_f.name)


@cli.command()
@click.option(
    "--path",
    envvar="CONTENT_MANIFEST_PATH",
    default="data/content-manifests/production.yaml",
    show_default=True,
)
@click.option(
    "--github-access-token", envvar="GITHUB_ACCESS_TOKEN", default="", show_default=True
)
def update_manifest(path, github_access_token):
    """
    Update each entry in a content manifest to its latest GitHub release

    If releases are not found, defaults to the last commit
    on `master`.
    """

    # NOTE: Backported from https://github.com/scaife-viewer/scaife-cts-api/blob/0e3d702dcdeae966f8d37935e7c657e16c039cf3/scaife_cts_api/update_corpus_shas.py
    if github_access_token:
        client = Github(github_access_token)
    else:
        client = Github()

    statuses = []
    manifest = Path(path)
    corpus = yaml.round_trip_load(manifest.open())
    new_corpus = dict()
    for repo_name, data in corpus.items():
        resolver = ReleaseResolver(client, repo_name, data)

        status_result = resolver.update_corpus(new_corpus)
        statuses.append(status_result)

    yaml.round_trip_dump(new_corpus, manifest.open("w"))


if __name__ == "__main__":
    cli()
