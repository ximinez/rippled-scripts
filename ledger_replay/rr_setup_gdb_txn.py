#!/usr/bin/env python3
"""
python script to setup transaction debugging

Given a transaction, this script fetches the corresponding ledger and parent ledger
and writes a file that may be useful to initialize a gdb debugging session

Typically run looks like:

rr_setup_gdb_txn.py -g gdb_startup.txt -t BE0F787A7105FAF5DB14E19C3F92E1EDAFA02054D3578FE5858D18BAE7FC50B2"

The output in gdb_startup.txt will then look like this:

set args --fg --conf /home/swd/.rippled/rippled.cfg --ledger 32FE20CF8D7CAE4A2B1F607AB308D274D8B97E53F2B3C37B18B23491FD114788
set $tx="BE0F787A7105FAF5DB14E19C3F92E1EDAFA02054D3578FE5858D18BAE7FC50B2"

The `$tx` pseudo variable is useful for setting conditional breakpoints. For example:

b Payment.cpp:360
condition $bpnum strcmp(txIDStr.c_str(), $tx)==0

(The txIDStr is a variable that contains the current transaction).
"""


import argparse
import collections
import copy
from contextlib import contextmanager
import json
import os
from os.path import expanduser
import subprocess
import time
import urllib.request, urllib.error, urllib.parse


def get_cur_rippled_dir():
    try:
        file_name = expanduser("~/scripts/cur_rippled_dir")
        with open(file_name, "r") as f:
            return f.readline().strip()
    except:
        return "."


def get_exe():
    """Find the rippled executable"""
    args = parse_args()
    if args.exe:
        return args.exe
    return expanduser("~/projs/ripple/ours/build/gcc.release.nounity/rippled")
    prefix = get_cur_rippled_dir() + "/build/"
    exe = ["rippled", "RippleD.exe"]
    to_test = [
        prefix + t + ".release.nounity/" + e
        for t in ["clang", "gcc", "msvc"]
        for e in exe
    ]
    for e in exe:
        to_test.insert(0, prefix + e)
    for t in to_test:
        if os.path.isfile(t):
            return t
    raise ValueError("No Exe Found")


# rippled can find it's default config from some hard-coded paths
#def default_cfg():
#    return expanduser("~/data/rippled/main.no_shards.dog/rippled.cfg")


class RippleClient(object):
    """Client to send commands to the rippled server"""

    def __init__(self, config_file):
        self.config_file = config_file
        self.exe = get_exe()
        print("Using: ", self.exe)

    def send_command(self, *args):
        print(args)
        to_run = [self.exe]
        if self.config_file:
            to_run.extend(["--conf", self.config_file])
        to_run.extend(args)
        print(to_run)
        max_retries = 4
        for retry_count in range(0, max_retries + 1):
            try:
                r = subprocess.check_output(to_run)
                return json.loads(r)["result"]
            except Exception as e:
                if retry_count == max_retries:
                    raise
                print(
                    "Got exception: %s\nretrying..%d of %d"
                    % (str(e), retry_count + 1, max_retries)
                )
                time.sleep(1)  # give process time to startup

    def request_ledger_from_index(self, index):
        def has_ledger(result):
            if not "ledger" in result:
                return False
            ledger = result["ledger"]
            if not "accepted" in ledger and not "closed" in ledger:
                return False
            if "accepted" in ledger and not ledger["accepted"]:
                return False
            if "closed" in ledger and not ledger["closed"]:
                return False
            if "needed_state_hashes" in result:
                return False
            if "needed_transaction_hashes" in result:
                return False
            return True

        index_as_str = str(index)
        while 1:
            result = self.send_command("ledger_request", index_as_str)
            if "result" in result:
                result = result["result"]
            print(result)
            if has_ledger(result):
                return result["ledger"]
            time.sleep(3)

    def txn_ledger_index(self, txn):
        def tx_info(tx, *args):
            try:
                params = []
                params.extend(args)
                params.extend(["tx", txn])
                return self.send_command(*params)
            except Exception as e:
                return {"exception": e}

        while 1:
            result = tx_info(txn)
            if "ledger_index" in result:
                return result["ledger_index"]
            print(result)
            if "error" in result and result["error"] == "txnNotFound":
                # Hit s2.ripple.com. IP hard-coded for now
                result = tx_info(txn, "--rpc_ip=34.209.58.100:51234")
                if "ledger_index" in result:
                    return result["ledger_index"]
                print(result)
            time.sleep(3)

    def stop(self):
        return self.send_command("stop")

    def set_log_level(self, log_level):
        return self.send_command("log_level", log_level)


@contextmanager
def rippled_client(config_file, server_out=os.devnull, run_server=True):
    """Start a ripple server and return a client"""
    server = None
    try:
        to_run = None
        client = RippleClient(config_file)
        ping = client.send_command("ping")
        print(ping)
        if "status" in ping and ping["status"] == "success":
            # rippled is already running
            run_server=False
        if run_server:
            to_run = [client.exe, "--fg"]
            if client.config_file:
                to_run.extend(["--conf", client.config_file])
            fout = open(server_out, "w")
            server = subprocess.Popen(to_run, stdout=fout, stderr=subprocess.STDOUT)
            print("started rippled")
            time.sleep(1.5)  # give process time to startup
        yield client
    finally:
        if run_server and to_run:
            subprocess.Popen(to_run + ["stop"], stdout=fout, stderr=subprocess.STDOUT)
        if server:
            server.wait()


def parse_args():
    parser = argparse.ArgumentParser(
        description=("python script to interact with the rippled server")
    )

    parser.add_argument(
        "--conf",
        "-c",
        help=("rippled config file"),
    )

    parser.add_argument(
        "--replay_conf",
        "-r",
        help=("rippled replay config file"),
    )

    parser.add_argument(
        "--server_out",
        "-o",
        help=("file for server stdout and stderr"),
    )

    parser.add_argument(
        "--gdb",
        "-g",
        help=("gdb output file"),
    )
    parser.add_argument(
        "--txn",
        "-t",
        help=("txn"),
    )
    parser.add_argument(
        "--lidx",
        "-l",
        help=("ledger index"),
    )
    parser.add_argument(
        "--exe",
        "-e",
        help=("path to rippled executable"),
    )

    return parser.parse_known_args()[0]


def get_server_args():
    args = parse_args()
    run_server = True
    conf = args.conf
    #if not conf:
    #    conf = default_cfg()
    server_out = args.server_out or os.devnull
    return {
        "run_server": run_server,
        "config_file": conf,
        "server_out": server_out,
    }


def write_gdb_init(out_fh, ledger, txn, cfg_file):
    # Template for replaying a specific txs
    #     template = """
    # set args --fg --conf {cfg_file} --replay --ledger {ledger_hash}
    # set $tx="{tx_hash}"
    #     """
    # Template for replaying an entire ledger
    template = """
set $tx="{tx_hash}"
set args -a {cfg_file_param} --replay --load --ledger {ledger_hash}
    """
    cfg_file_param=""
    if cfg_file:
        cfg_file_param="--conf " + cfg_file
    print(
        template.format(ledger_hash=ledger, tx_hash=txn, cfg_file_param=cfg_file_param), file=out_fh
    )


# returns the ledger hash
def fetch_ledgers_(rip, idx):
    for i in [idx - 1, idx]:
        print("Fetching: {}".format(i))
        ledger = rip.request_ledger_from_index(i)
        if i == idx:
            lh = ledger["ledger_hash"]
        print("Done Fetching: {}".format(i))
    return lh


# returns the ledger hash
def fetch_ledger(txn):
    server_args = get_server_args()
    if not server_args:
        return
    server_args["server_out"] = os.devnull

    print(server_args)
    with rippled_client(**server_args) as rip:
        idx = rip.txn_ledger_index(txn)
        return fetch_ledgers_(rip, idx)


# returns the ledger hash
def fetch_ledger_by_index(idx):
    server_args = get_server_args()
    if not server_args:
        return
    server_args["server_out"] = os.devnull

    print(server_args)
    with rippled_client(**server_args) as rip:
        return fetch_ledgers_(rip, idx)


def run_main():
    args = parse_args()
    gdb_file = args.gdb
    if not gdb_file:
        print("gdb file required")
        sys.exit(1)
    txn = args.txn
    lidx = args.lidx
    if not txn and not lidx:
        print("txn or lidx required")
        sys.exit(1)
    conf = args.conf
    #if not conf:
    #    conf = default_cfg()

    replay_conf = args.replay_conf
    if not replay_conf:
        replay_conf = conf

    if lidx:
        lh = fetch_ledger_by_index(int(lidx))
    elif txn:
        lh = fetch_ledger(txn)
    else:
        print("txn or lidx required")
        sys.exit(1)

    with open(gdb_file, "w") as rf:
        write_gdb_init(rf, lh, txn, replay_conf)


if __name__ == "__main__":
    run_main()
