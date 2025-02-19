"""Contains STIXToCollection class and entrypoint for stixToCollection_cli."""

import argparse
import copy
import json
import traceback
from uuid import uuid4
from datetime import datetime
from stix2elevator.stix_stepper import step_bundle
from stix2elevator.options import initialize_options, ElevatorOptions

# https://github.com/mitre-attack/attack-stix-data/blob/docs/data-sources/USAGE.md#the-attck-spec
X_MITRE_SPEC_VERSION = "2.1.0"


class STIXToCollection:
    """A STIXToCollection object."""

    @staticmethod
    def stix_to_collection(bundle, name, version, description=None):
        """Enhance an existing stix bundle with a ATT&CK Collection object.

        :param bundle: dictionary representation of a stix bundle
        :param name: name for the generated collection object
        :param version: parameter indicating the ATT&CK version for the generated collection object
        :param description: optional parameter describing the collection
        :returns: updated bundle, now containing a ATT&CK Collection object
        """
        working_bundle = copy.deepcopy(bundle)
        for obj in working_bundle["objects"]:  # check to see if this bundle already contains a collection
            if obj["type"] == "x-mitre-collection":
                return bundle
        if bundle.get("spec_version", "") == "2.0":
            try:
                print(
                    "[NOTE] - version 2.0 spec detected. Forcibly upgrading the bundle to 2.1 to support "
                    "collections."
                )
                initialize_options(ElevatorOptions(custom_property_prefix="mitre", silent=True))
                working_bundle = step_bundle(working_bundle)
                print(
                    "[NOTE] - NOTICE: ATT&CK in STIX 2.1 includes additional fields which were not present on the "
                    "STIX 2.0 data. These fields have not been added automatically and their absence may affect "
                    "compatibility with ingesting software. Please see "
                    "https://github.com/mitre-attack/attack-stix-data/blob/master/USAGE.md for more information."
                )
            except Exception as e:
                print(
                    f"[ERROR] - Unexpected issue encountered when trying to upgrade from 2.0 to 2.1: {e}. "
                    f"Terminating..."
                )
                print(f"[ERROR] - Full Error trace: {traceback.print_exc(e)}")
                return None
        if bundle.get("spec_version", "") != "2.1" and bundle.get("spec_version", "") != "2.0":
            print(
                f"[ERROR] - version {working_bundle.get('spec_version', '[NOT FOUND]')} is not one of [2.0, 2.1]. "
                f"This module only processes stix 2.0 and stix 2.1 bundles."
            )
        time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if not description:
            description = "This collection was autogenerated by STIXToCollection, as part of mitreattack-python"
        raw_collection = dict(
            type="x-mitre-collection",
            id=f"x-mitre-collection--{uuid4()}",
            spec_version="2.1",
            name=name,
            x_mitre_version=version,
            x_mitre_attack_spec_version=X_MITRE_SPEC_VERSION,
            description=description,
            created_by_ref="",
            created=time,
            modified=time,
            object_marking_refs=[],
            x_mitre_contents=[],
        )
        for obj in working_bundle["objects"]:
            if obj["type"] != "marking-definition":
                try:
                    raw_collection["x_mitre_contents"].append(
                        dict(object_ref=obj["id"], object_modified=obj["modified"])
                    )
                except KeyError as e:
                    print(f"[ERROR] - object {obj} is missing a necessary field: {e}. Exiting this script...")
                    return None
                if "object_marking_refs" in obj.keys():
                    for omr in obj["object_marking_refs"]:
                        if omr not in raw_collection["object_marking_refs"]:
                            raw_collection["object_marking_refs"].append(omr)
                if "created_by_ref" in obj.keys():
                    if obj["created_by_ref"] != raw_collection["created_by_ref"]:
                        if raw_collection["created_by_ref"] != "":
                            print(
                                f"[NOTE] multiple 'created_by_ref' values detected. "
                                f"{raw_collection['created_by_ref']} (first encountered) will take precedence over "
                                f"{obj['created_by_ref']}"
                            )
                            continue
                        raw_collection["created_by_ref"] = obj["created_by_ref"]

        working_bundle["objects"].insert(0, raw_collection)
        return working_bundle


def main(args):
    """Entrypoint for stixToCollection_cli."""
    with open(args.input, "r", encoding="utf-16") as f:
        bundle = json.load(f)
        with open(args.output, "w", encoding="utf-16") as f2:
            f2.write(
                json.dumps(
                    STIXToCollection.stix_to_collection(bundle, args.name, args.version, args.description), indent=4
                )
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update a STIX 2.0 or 2.1 bundle to include a collection object referencing the contents of the "
        "bundle."
    )
    parser.add_argument("name", type=str, help="the name for the generated collection object")
    parser.add_argument("version", help="the ATT&CK version for the generated collection object")
    parser.add_argument("--input", type=str, default="bundle.json", help="the input bundle file")
    parser.add_argument("--output", type=str, default="bundle_out.json", help="the output bundle file")
    parser.add_argument("--description", type=str, default=None, help="description to use for the generated collection")
    argv = parser.parse_args()
    main(argv)
