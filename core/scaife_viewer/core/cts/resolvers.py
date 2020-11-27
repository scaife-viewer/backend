import glob
import json
import os
from collections import defaultdict
from functools import lru_cache

from MyCapytain.common.reference import URN
from MyCapytain.errors import InvalidURN, UndispatchedTextError
from MyCapytain.resolvers.cts.local import CtsCapitainsLocalResolver
from MyCapytain.resources.collections.cts import (
    XmlCtsCitation,
    XmlCtsTextgroupMetadata,
    XmlCtsWorkMetadata,
)


class LocalResolver(CtsCapitainsLocalResolver):
    def process_text_group(self, path):
        with open(path) as f:
            metadata = XmlCtsTextgroupMetadata.parse(resource=f)
        urn = str(metadata.urn)
        if urn in self.inventory:
            self.inventory[urn].update(metadata)
        else:
            self.dispatcher.dispatch(metadata, path=path)
        return metadata

    def process_work(self, text_group_metadata, path):
        text_group_urn = str(text_group_metadata.urn)
        with open(path) as f:
            metadata = XmlCtsWorkMetadata.parse(
                resource=f, parent=self.inventory[text_group_urn]
            )
        work_urn = str(metadata.urn)
        if work_urn in self.inventory[text_group_urn].works:
            self.inventory[work_urn].update(metadata)
        return metadata

    @lru_cache()
    def load_text(self, path):
        with open(path) as f:
            text = self.CLASSES["text"](resource=self.xmlparse(f))
        return text

    def process_text(self, urn, base_path, to_remove=None):
        if to_remove is None:
            to_remove = []
        metadata = self.inventory[urn]
        metadata.path = os.path.join(
            base_path,
            "{text_group}.{work}.{version}.xml".format(
                text_group=metadata.urn.textgroup,
                work=metadata.urn.work,
                version=metadata.urn.version,
            ),
        )
        try:
            text = self.load_text(metadata.path)
            cites = []
            for cite in reversed(text.citation):
                ckwargs = {
                    "xpath": cite.xpath.replace("'", '"'),
                    "scope": cite.scope.replace("'", '"'),
                    "name": cite.name,
                }
                if cites:
                    ckwargs["child"] = cites[-1]
                cites.append(XmlCtsCitation(**ckwargs))
            metadata.citation = cites[-1]
            self.logger.info(f"{metadata.path} has been parsed")
            if metadata.citation.is_set():
                self.texts.append(metadata)
            else:
                to_remove.append(urn)
                self.logger.warning(f"{metadata.path} has no passages")
        except FileNotFoundError:
            to_remove.append(urn)
            self.logger.warning(f"{metadata.path} does not exist")
        except Exception as e:
            to_remove.append(urn)
            self.logger.warning(f"{metadata.path} caused an error: {e}")
        return metadata

    def extract_sv_metadata(self, folder):
        metadata_path = os.path.join(folder, ".scaife-viewer.json")
        try:
            return json.load(open(metadata_path))
        except FileNotFoundError:
            return {}

    def parse(self, resource):
        to_remove = []
        repo_urn_lookup = defaultdict()
        for folder in resource:
            repo_metadata = self.extract_sv_metadata(folder)
            repo_metadata["texts"] = []

            text_group_paths = glob.glob(f"{folder}/data/*/__cts__.xml")
            for text_group_path in text_group_paths:
                try:
                    text_group_metadata = self.process_text_group(text_group_path)
                    for work_path in glob.glob(
                        f"{os.path.dirname(text_group_path)}/*/__cts__.xml"
                    ):
                        work_metadata = self.process_work(
                            text_group_metadata, work_path
                        )
                        for text_urn in work_metadata.texts:
                            self.process_text(
                                text_urn, os.path.dirname(work_path), to_remove
                            )
                            repo_metadata["texts"].append(text_urn)
                except UndispatchedTextError as e:
                    self.logger.warning(f"Error dispatching {text_group_path}: {e}")
                    if self.RAISE_ON_UNDISPATCHED:
                        raise
                except Exception as e:
                    self.logger.warning(f"Error while handling {text_group_path}: {e}")

            if repo_metadata.get("repo"):
                repo_urn_lookup[repo_metadata["repo"]] = repo_metadata

        self.clean_inventory(to_remove)

        corpus_metadata = list(repo_urn_lookup.values())
        self.write_corpus_metadata(corpus_metadata)

    def clean_inventory(self, to_remove):
        for metadata in self.inventory.descendants:
            if not metadata.readable and not metadata.readableDescendants:
                to_remove.append(metadata.urn)
        for urn in to_remove:
            if urn in self.inventory:
                del self.inventory[urn]

    def __getText__(self, urn):
        if not isinstance(urn, URN):
            urn = URN(urn)
        if len(urn) != 5:
            # this is different from MyCapytain in that we don't need to look
            # the first passage. let's always assume we get the right thing.
            raise InvalidURN()
        metadata = self.inventory[str(urn)]
        text = self.load_text(metadata.path)
        return text, metadata

    def write_corpus_metadata(self, data):
        from django.conf import settings

        corpus_metadata_path = os.path.join(
            settings.CTS_LOCAL_DATA_PATH, ".scaife-viewer.json"
        )
        json.dump(data, open(corpus_metadata_path, "w"), indent=2)
