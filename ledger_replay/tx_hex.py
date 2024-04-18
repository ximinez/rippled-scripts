import gdb
import binascii

def _value(sym_name):
    f = gdb.selected_frame()
    s = gdb.lookup_symbol(sym_name)[0]
    return s.value(f)

def _txid_to_hex_str(txid):
    pn = txid['data_']['_M_elems']
    num_bytes = 32
    mem = bytes(gdb.selected_inferior().read_memory(pn.address, num_bytes))
    return binascii.hexlify(mem).upper().decode('utf-8')

def _txid():
    v = _value('this')
    tid = v['ctx_']['tx']['tid_']
    return tid

def txid_hex():
    return _txid_to_hex_str(_txid())

class TxHex(gdb.Command):
    "Show the transaction hex"

    def __init__(self):
        super(TxHex, self).__init__("tx_hex", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            value = txid_hex()
            gdb.write(f"{value}\n")
        except gdb.error as e:
            gdb.write(f"Error: {str(e)}\n")

# Register the command
TxHex()
