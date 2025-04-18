#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

""" Updates the database """
import json
import os
import bson
import pymongo
import logging
import argparse
import base64

from pymongo import MongoClient
from gridfs import GridFS

from inginious.common.base import load_json_or_yaml


def get_config(configfile):
    if not configfile:
        if os.path.isfile("./configuration.yaml"):
            configfile = "./configuration.yaml"
        elif os.path.isfile("./configuration.json"):
            configfile = "./configuration.json"
        else:
            raise Exception("No configuration file found")

    return load_json_or_yaml(configfile)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Configuration file", default="")
    parser.add_argument("-v", "--verbose", help="Display more output", action='store_true')
    args = parser.parse_args()

    config = get_config(args.config)

    mongo_client = MongoClient(host=config.get('mongo_opt', {}).get('host', 'localhost'))
    database = mongo_client[config.get('mongo_opt', {}).get('database', 'INGInious')]
    gridfs = GridFS(database)

    logger = logging.getLogger("inginious.db_update")

    db_version = database.db_version.find_one({})
    db_version = db_version['db_version'] if db_version else 0

    if db_version < 12:
        logger.info("Version prior to v0.4")
        exit(-1)

    if db_version < 13:
        print("Updating database to db_version 13")
        database.nonce.create_index(
            [("timestamp", pymongo.ASCENDING), ("nonce", pymongo.ASCENDING)],
            unique=True
        )
        database.nonce.create_index("expiration", expireAfterSeconds=0)
        db_version = 13

    if db_version < 14:
        print("Updating database to db_version 14")
        ss = database.submissions.find({},{"_id": 1, "input": 1})
        length = ss.count()
        index = 0
        for item in ss:
            index += 1
            if not index % 1000:
                print("...{}/{}".format(index, length))
            try:
                inp = item.get("input", {})
                gridfs_id = None
                if not isinstance(inp, dict): # retrieve from gridfs
                    gridfs_id = inp
                    inp = json.loads(gridfs.get(inp).read().decode('utf8'))

                for key in inp.keys():
                    if isinstance(inp[key], dict) and "value" in inp[key] and isinstance(inp[key]["value"], str):
                        inp[key]["value"] = base64.b64decode(inp[key]["value"])

                new_id = gridfs.put(bson.BSON.encode(inp))
                database.submissions.update_one({"_id": item["_id"]}, {"$set": {"input": new_id}})
                if gridfs_id is not None:
                    gridfs.delete(gridfs_id)
            except Exception as ex:
                print("!!! Exception for submission id {} : {}".format(item["_id"], str(ex)))
        db_version = 14

    if db_version < 15:
        print("Updating database to db_version 15")
        aggregations = database.aggregations.find({})
        for aggregation in aggregations:
            audience = database.audiences.insert_one({"courseid": aggregation["courseid"],
                                                         "description": aggregation["description"],
                                                         "students": aggregation["students"],
                                                         "tutors": aggregation["tutors"]})
            audience_id = bson.ObjectId(audience.inserted_id)

            database.courses.update_one({"_id": aggregation["courseid"]},
                                                 {"$push": {"students": {"$each": aggregation["students"]}}},
                                                 upsert=True)
            i = 1
            for group in aggregation["groups"]:
                database.groups.insert_one({"courseid": aggregation["courseid"], "description": "Group # " + str(i),
                                            "students": group["students"], "size": group["size"],
                                            "audiences": [audience_id]})
                i += 1

        db_version = 15

    if db_version < 16:
        print("Updating database to db_version 16")
        database.submissions.create_index([("status", pymongo.ASCENDING)])
        db_version = 16

    if db_version < 17:
        print("Updating database to db_version 17")
        database.users.update_many({}, {"$set": {"code_indentation": "4"}})
        db_version = 17

    database.db_version.update_one({}, {"$set": {"db_version": db_version}}, upsert=True)
        
    print("Database up to date")


if __name__ == "__main__":
    main()