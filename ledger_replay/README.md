# Step-by-step instructions to replay a transaction in a ledger

The intended audience for these instructions are `rippled` developers.
They are not guaranteed to be thorough or complete, or have relevant
error checking. They may not even necessarily be correct. Feel free to
submit a PR with improvements, but there is no promise of support.

## Steps

1. Determine the specific transaction ID that you want to replay. 
   This example, will use
   `5216B93EE88325FEC97DF3FCC36EA12C0078D0C85D437D9E52B4D9667FFE46FF`
2. The (local) `rippled` which will be replaying the transaction will
   need to have that ledger, as well as the previous ledger.
3. Use the [rr_setup_gdb_txn.py] script to automate determining and
   downloading grabbing those ledgers. `rr_setup_gdb_txn.py -g
   gdb_startup.txt -t
   5216B93EE88325FEC97DF3FCC36EA12C0078D0C85D437D9E52B4D9667FFE46FF -e
   <path_to_rippled_executable> --conf <path_to_rippled_config>`
4. The script will hammer `ledger_request` until it has all the
   transaction hashes and the ledger has been accepted and closed.
5. The `gdb_startup.txt` file should look something like this:
    ```
    set $tx="5216B93EE88325FEC97DF3FCC36EA12C0078D0C85D437D9E52B4D9667FFE46FF"
    set args -a --conf <path_to_rippled_config> --replay --load --ledger 0C37D7F5B78389923BF4B4D4EAE6C74FF13069130C81DCCC2DE4126FD93FEDC6
    ```
    `5216B93EE88325FEC97DF3FCC36EA12C0078D0C85D437D9E52B4D9667FFE46FF` is the hash of the transaction for this example, and
    `0C37D7F5B78389923BF4B4D4EAE6C74FF13069130C81DCCC2DE4126FD93FEDC6`
    is the hash of the ledger in which it was validated.
5. Once the ledgers are downloaded locally, edit your rippled.cfg to add
   the following startup commands:
    ```
    [rpc_startup]
    { "command": "log_level", "severity": "error" }
    # Replay the ledger
    { "command": "ledger_accept" }
    # Stop after the ledger has been replayed
    { "command": "stop" }
    ```
   * Since `rippled` will be in standalone mode, you could also run the
     commands manually from the command line once `rippled` is ready.
     This is handy if you don't want to change your config file, or if
     you forget before running gdb.
     ```
     $ rippled log_level error
     $ rippled ledger_accept
     $ rippled stop
     ```
6. Now run rippled in gdb. `gdb -x gdb_startup.txt <path_to_rippled>`
7. Optional: Import the [tx_hex.py] or [tx_breakpoint.py] script, and
   set a conditional breakpoint at `Transactor.cpp:834` where the
   condition is the transaction hash we're interested in.
    ```
    python
    sys.path.append(r'path/to/this/folder/if/necessary')
    import tx_breakpoint
    bp = tx_breakpoint.BPaymentTxStart ('Transactor.cpp:834')
    end
    ```
8. Once that breakpoint is hit, set another breakpoint in the transactor
   you're interested in (amm, payment, etc.) and off you go.
