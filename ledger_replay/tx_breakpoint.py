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

TX_FLOW = None

class BPaymentTxStart (gdb.Breakpoint):
    '''Start of payment transaction'''
    def __init__(self, spec=None):
        if spec is None:
            spec = 'Payment.cpp:360'
        super().__init__(spec)
        self.tx = str(gdb.parse_and_eval('$tx'))
        if self.tx.startswith('"') and self.tx.endswith('"'):
            self.tx = self.tx[1:-1]

    def stop(self):
        global TX_FLOW
        TX_FLOW= txid_hex()
        return TX_FLOW == self.tx

