import json
import os
from collections import defaultdict

from scaife_viewer.atlas.conf import settings

from ..models import Node, Repo
from ..urn import URN


# TODO: determine if we want to create a metadata
# type, rather than treating this as "annotations"
ANNOTATIONS_DATA_PATH = os.path.join(
    settings.SV_ATLAS_DATA_DIR, "annotations", "repo-metadata"
)


def get_paths():
    if not os.path.exists(ANNOTATIONS_DATA_PATH):
        return []
    return [
        os.path.join(ANNOTATIONS_DATA_PATH, f)
        for f in os.listdir(ANNOTATIONS_DATA_PATH)
        if f.endswith(".json")
    ]


def get_github_client():
    # TODO: Add Github dependency, possibly make it optional
    from github import Github

    ACCESS_TOKEN = os.environ.get("GITHUB_ACCESS_TOKEN", "")
    if ACCESS_TOKEN:
        client = Github(ACCESS_TOKEN)
    else:
        client = Github()
    return client


def get_extra_metadata(client, repo_name):
    repo = client.get_repo(repo_name)
    if repo.fork:
        repo = repo.source
    return {
        "name": repo.name,
        "description": repo.description,
        "owner": repo.owner.name,
        "github_url": repo.html_url,
        "homepage_url": repo.homepage,
    }


def import_repo(data, namespaces, text_groups, works, client=None):
    if client is None:
        client = get_github_client()

    repo_name = data["repo"]
    urns = []
    for text in data["texts"]:
        urn = URN(f"{text}:")
        urns.append(str(urn))

        namespaces[urn.up_to(urn.NAMESPACE)].add(repo_name)
        text_groups[urn.up_to(urn.TEXTGROUP)].add(repo_name)
        works[urn.up_to(urn.WORK)].add(repo_name)

    repo_obj = Repo.objects.create(
        name=repo_name, sha=data["sha"], metadata=get_extra_metadata(client, repo_name)
    )
    repo_obj.urns.set(Node.objects.filter(urn__in=urns))

    print(repo_obj.name)


def import_repo_metadata(reset=False):
    # TODO: this assumes that the metadata is made up of
    # GitHub repos
    if reset:
        Repo.objects.all().delete()

    namespaces = defaultdict(set)
    text_groups = defaultdict(set)
    works = defaultdict(set)
    client = get_github_client()

    for path in get_paths():
        data = json.load(open(path))
        for repo in data:
            import_repo(repo, namespaces, text_groups, works, client=client)
