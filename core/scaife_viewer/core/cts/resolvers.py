import glob
import json
import os
from collections import defaultdict
from functools import lru_cache

from django.core.cache import caches

from MyCapytain.common.reference import URN
from MyCapytain.errors import (
    InvalidURN,
    UndispatchedTextError,
    UnknownCollection,
)
from MyCapytain.resolvers.cts.local import CtsCapitainsLocalResolver
from MyCapytain.resources.collections.cts import (
    XmlCtsCitation,
    XmlCtsTextgroupMetadata,
    XmlCtsWorkMetadata,
)


cache = caches["cts_resolver"]


class LocalResolver(CtsCapitainsLocalResolver):
    RAISE_ON_UNKNOWN_COLLECTION = False

    def process_text_group(self, path):
        with open(path) as f:
            metadata = XmlCtsTextgroupMetadata.parse(resource=f)
        urn = str(metadata.urn)
        if urn in self.inventory["default"].textgroups:
            try:
                self.inventory[urn].update(metadata)
            except UnknownCollection as e:
                if self.RAISE_ON_UNKNOWN_COLLECTION:
                    raise e
                self.logger.warning(f"Unknown text group: {e}")
                try:
                    self.dispatcher.dispatch(metadata, path=path)
                except Exception:
                    pass
        else:
            self.dispatcher.dispatch(metadata, path=path)
        return metadata

    def process_work(self, text_group_metadata, path):
        text_group_urn = str(text_group_metadata.urn)
        with open(path) as f:
            metadata = XmlCtsWorkMetadata.parse(resource=f, parent=text_group_metadata,)
        work_urn = str(metadata.urn)
        if work_urn in text_group_metadata.works:
            try:
                self.inventory[work_urn].update(metadata)
            except UnknownCollection as e:
                if self.RAISE_ON_UNKNOWN_COLLECTION:
                    raise e
                self.logger.warning(f"Unknown work: {e}")
        return metadata

    @lru_cache()
    def load_text(self, path):
        with open(path) as f:
            text = self.CLASSES["text"](resource=self.xmlparse(f))
        return text

    def process_text(self, urn, base_path, to_remove=None):
        if to_remove is None:
            to_remove = []
        try:
            metadata = self.inventory[urn]
        except UnknownCollection as e:
            if self.RAISE_ON_UNKNOWN_COLLECTION:
                raise e
            self.logger.warning(f"Unknown text: {e}")
            # NOTE: Don't try and continue processing the text
            return

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
            if not metadata.citation.is_set():
                to_remove.append(urn)
                self.logger.warning(f"{metadata.path} has no passages")
        except FileNotFoundError:
            to_remove.append(urn)
            self.logger.warning(f"{metadata.path} does not exist")
        except Exception as e:
            # FIXME: Improve exception handling
            to_remove.append(urn)
            self.logger.warning(f"Unable to parse {metadata.path}: {e}")
        return metadata

    def extract_sv_metadata(self, folder):
        metadata_path = os.path.join(folder, ".scaife-viewer.json")
        try:
            return json.load(open(metadata_path))
        except FileNotFoundError:
            return {}

    def parse_from_cache(self, resource):
        """
        Get or set CTS inventory from a cache.
        """
        if cache.get("ti"):
            self.inventory = cache.get("ti")
            return
        to_remove = []
        repo_urn_lookup = defaultdict()
        for folder in resource:
            repo_metadata = self.extract_sv_metadata(folder)
            repo_metadata["texts"] = []

            text_group_paths = glob.iglob(f"{folder}/data/*/__cts__.xml")
            for text_group_path in text_group_paths:
                try:
                    text_group_metadata = self.process_text_group(text_group_path)
                    for work_path in glob.iglob(
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

        # TODO: pass by reference or not
        to_remove = self.clean_inventory(to_remove)

        # TODO: remove metadata entries that are not in inventory
        corpus_metadata = list(repo_urn_lookup.values())
        self.write_corpus_metadata(corpus_metadata)

        cache.set("ti", self.inventory, None)

    def parse(self, resource):
        return self.parse_from_cache(resource)

    def clean_inventory(self, to_remove):
        textgroups = self.inventory["default"].textgroups
        for tg_urn, text_group in textgroups.items():
            text_group_readable = False
            for work_urn, work in text_group.works.items():
                work_readable = False
                for text_urn, text in work.texts.items():
                    if text.readable:
                        work_readable = True
                    else:
                        to_remove.append(text_urn)
                if work_readable:
                    text_group_readable = True
                else:
                    to_remove.append(work_urn)
            if not text_group_readable:
                to_remove.append(tg_urn)
        for urn in to_remove:
            try:
                del self.inventory[urn]
            except UnknownCollection:
                pass
            else:
                self.logger.warning(f"Removed urn: {urn}")
        return to_remove

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
